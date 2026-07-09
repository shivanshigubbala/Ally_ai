# backend/general_physician/main.py
# FastAPI entrypoint. Owns the WebSocket dispatcher and the REST /chat shortcut.

import io
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse
import asyncio

try:
    from backend.neurology.graphs import routing_graph
    from backend.neurology.llm.nvidia_client import chat as nv_chat, ROUTING_MODEL
    from backend.neurology.models.session_state import ChatRequest, ChatResponse
    from backend.neurology.ws.router import router as ws_router
    from backend.neurology.db.pgvector_tracker import init_db, seed_default_user
    from pydantic import BaseModel, EmailStr, Field, validator
except ImportError:
    from graphs import routing_graph
    from llm.nvidia_client import chat as nv_chat, ROUTING_MODEL
    from models.session_state import ChatRequest, ChatResponse
    from ws.router import router as ws_router
    from db.pgvector_tracker import init_db, seed_default_user

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logging.getLogger("backend").setLevel(logging.INFO)
logging.getLogger("backend.neurology.graphs").setLevel(logging.INFO)
logging.getLogger("backend.neurology.ws").setLevel(logging.INFO)
logging.getLogger("backend.neurology.llm").setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
        seed_default_user()
    except Exception as exc:
        logging.warning("Database initialization skipped: %s", exc)
    yield


app = FastAPI(title="Ally AI Backend", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(ws_router)


@app.get("/")
def root() -> dict:
    return {"status": "Ally AI backend running"}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def chunk_text(text: str, chunk_size: int = 800, chunk_overlap: int = 150) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - chunk_overlap
    return chunks


@app.post("/upload-document/{user_id}/{appointment_id}")
async def upload_document(
    user_id: str,
    appointment_id: str,
    file: UploadFile = File(...),
) -> dict:
    """
    Receive a document (PDF / TXT / image) uploaded before consultation.
    Extracts plain text, chunks it, generates embeddings, and stores it in the
    pgvector knowledge base for RAG, in addition to the in-memory store.
    """
    try:
        from backend.neurology.ws.router import _doc_store
    except ImportError:
        from ws.router import _doc_store  # type: ignore

    content = await file.read()
    filename = file.filename or "document"
    extracted = ""

    lower_name = filename.lower()
    if lower_name.endswith(".pdf"):
        try:
            import fitz  # pymupdf
            pdf = fitz.open(stream=content, filetype="pdf")
            pages = [page.get_text() for page in pdf]
            extracted = "\n".join(pages).strip()
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"PDF extraction failed: {exc}") from exc
    elif lower_name.endswith((".txt", ".md", ".csv")):
        try:
            extracted = content.decode("utf-8", errors="replace").strip()
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Text decode failed: {exc}") from exc
    else:
        # For images or unsupported types, store a placeholder so the doctor
        # at least knows a document was provided.
        extracted = f"[Patient uploaded a file: {filename}. Manual review required.]"

    doc_key = f"{user_id}:{appointment_id}"
    if doc_key not in _doc_store:
        _doc_store[doc_key] = []
    _doc_store[doc_key].append({
        "filename": filename,
        "text": extracted[:8000],  # cap at 8k chars to keep prompt size reasonable
    })
    logging.info("Stored uploaded document for %s (appointment=%s) filename=%s text_len=%d", user_id, appointment_id, filename, len(extracted))
    # Ensure a session exists for this appointment so messages and knowledge can be tied to it
    session_id = appointment_id or None
    file_id = None
    try:
        from backend.neurology.db.pgvector_tracker import (
            create_session,
            insert_uploaded_file,
            mark_uploaded_file_status,
        )
        if session_id:
            create_session(session_id, user_id, current_state="ROUTING")
        # persist upload metadata
        snippet = extracted[:1000]
        file_id = insert_uploaded_file(session_id, user_id, filename, snippet)
    except Exception:
        pass

    # Notify connected client that upload was received
    try:
        try:
            from backend.neurology.ws.router import notify_user_event
            from backend.neurology.models.session_state import WSEvent
        except ImportError:
            from ws.router import notify_user_event  # type: ignore
            from models.session_state import WSEvent  # type: ignore

        ev = WSEvent(type="upload_received", payload={"filename": filename, "session_id": session_id, "file_id": file_id})
        # fire-and-forget: don't block upload
        import asyncio
        asyncio.create_task(notify_user_event(user_id, ev))
    except Exception:
        pass

    # Chunk, embed, and store in pgvector knowledge base
    chunks: list[tuple[int, str]] = []
    if lower_name.endswith(".pdf"):
        try:
            import fitz
            pdf = fitz.open(stream=content, filetype="pdf")
            for page_num, page in enumerate(pdf, 1):
                page_text = page.get_text().strip()
                if page_text:
                    sub_chunks = chunk_text(page_text, chunk_size=800, chunk_overlap=150)
                    for sc in sub_chunks:
                        chunks.append((page_num, sc))
        except Exception as exc:
            logging.warning("Could not extract page-by-page text: %s", exc)

    if not chunks and extracted:
        sub_chunks = chunk_text(extracted, chunk_size=800, chunk_overlap=150)
        for sc in sub_chunks:
            chunks.append((1, sc))

    if chunks:
        try:
            try:
                from backend.neurology.llm.embeddings import embed_passages
                from backend.neurology.db.pgvector_tracker import insert_knowledge_chunks
            except ImportError:
                from llm.embeddings import embed_passages  # type: ignore
                from db.pgvector_tracker import insert_knowledge_chunks  # type: ignore

            passage_texts = [item[1] for item in chunks]
            embeddings = embed_passages(passage_texts)

            for (page_num, content_str), emb in zip(chunks, embeddings):
                insert_knowledge_chunks(
                    department="general",
                    source=filename,
                    page=page_num,
                    contents=[content_str],
                    embeddings=[emb],
                    patient_id=user_id,
                )
            logging.info("Successfully chunked and embedded document %s for user %s (%d chunks)", filename, user_id, len(chunks))
            # mark uploaded file as indexed
            try:
                if file_id is not None:
                    mark_uploaded_file_status(file_id, "indexed")
                    try:
                        from backend.neurology.ws.router import notify_user_event
                        from backend.neurology.models.session_state import WSEvent
                    except ImportError:
                        from ws.router import notify_user_event  # type: ignore
                        from models.session_state import WSEvent  # type: ignore
                    ev2 = WSEvent(type="upload_indexed", payload={"filename": filename, "session_id": session_id, "file_id": file_id, "chunks": len(chunks)})
                    import asyncio
                    asyncio.create_task(notify_user_event(user_id, ev2))
            except Exception:
                pass
        except Exception as exc:
            logging.error("RAG pipeline failed for uploaded document: %s", exc, exc_info=True)
            try:
                if file_id is not None:
                    mark_uploaded_file_status(file_id, "failed")
            except Exception:
                pass

    return {"ok": True, "filename": filename, "text_length": len(extracted)}


@app.get("/reports/{report_id}")
def download_report(report_id: str) -> FileResponse:
    # Ensure local reports directory exists
    reports_dir = Path(__file__).resolve().parents[0] / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    report_path = reports_dir / f"{report_id}.pdf"
    if not report_path.exists():
        # Try fetching from the lab microservice
        import httpx
        try:
            lab_url = f"http://lab:8082/reports/download?id={report_id}"
            resp = httpx.get(lab_url)
            if resp.status_code == 200:
                # Save binary content locally
                report_path.write_bytes(resp.content)
        except Exception:
            pass

    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")

    return FileResponse(
        str(report_path),
        filename=f"{report_id}.pdf",
        media_type="application/pdf",
    )


@app.get("/uploaded-files/{user_id}/{appointment_id}")
def list_uploaded_files(user_id: str, appointment_id: str):
    try:
        from backend.neurology.db.pgvector_tracker import get_uploaded_files_for_session
    except ImportError:
        from db.pgvector_tracker import get_uploaded_files_for_session  # type: ignore

    try:
        files = get_uploaded_files_for_session(appointment_id)
        return {"ok": True, "files": files}
    except Exception:
        return {"ok": False, "files": []}


@app.get("/nv-test")
def nv_test() -> dict:
    try:
        msg = nv_chat(
            [{"role": "user", "content": "Say OK in one word."}],
            model=ROUTING_MODEL,
        )
        return {"status": "ok", "model": ROUTING_MODEL, "response": msg}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc



@app.post("/internal/report_ready")
async def internal_report_ready(payload: dict = Body(...)) -> dict:
    """Internal webhook for lab services to notify that a report is ready.

    Expects keys: report_id, appointment_id, user_id, download_url, report_url, doctor, tests
    """
    try:
        # Best-effort persist notification (non-blocking failures should not fail the request)
        try:
            from backend.neurology.db.pgvector_tracker import create_notification
        except Exception:
            from db.pgvector_tracker import create_notification  # type: ignore

        notif = {
            "notification_id": f"report:{payload.get('report_id')}",
            "patient_id": payload.get("user_id") or payload.get("patient_id"),
            "appointment_id": payload.get("appointment_id"),
            "notification_type": "REPORT",
            "title": "Lab report ready",
            "message": "Your lab report is ready to view.",
            "metadata": {"report_id": payload.get("report_id"), "download_url": payload.get("download_url"), "report_url": payload.get("report_url")},
            "status": "PENDING",
        }
        try:
            create_notification(notif)
        except Exception:
            pass

        # notify user over websocket if connected
        try:
            from backend.neurology.ws.router import notify_user_event
            from backend.neurology.models.session_state import WSEvent
        except Exception:
            from ws.router import notify_user_event  # type: ignore
            from models.session_state import WSEvent  # type: ignore

        user = payload.get("user_id") or payload.get("patient_id")
        if user:
            user_str = str(user)
            if user_str.isdigit():
                try:
                    from backend.db.pgvector_tracker import _conn
                    with _conn() as conn:
                        with conn.cursor() as cur:
                            cur.execute("SELECT id FROM users WHERE go_user_id = %s", (int(user_str),))
                            row = cur.fetchone()
                            if row:
                                user = row[0]
                except Exception:
                    pass
            ev = WSEvent(type="report_ready", payload={
                "report_id": payload.get("report_id"),
                "appointment_id": payload.get("appointment_id"),
                "session_id": payload.get("appointment_id"),
                "report_url": payload.get("report_url"),
                "download_url": payload.get("download_url"),
                "tests": payload.get("tests"),
                "doctor": payload.get("doctor"),
            })
            asyncio.create_task(notify_user_event(str(user), ev))
    except Exception:
        pass
    return {"ok": True}


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest = Body(...)) -> ChatResponse:
    """REST shortcut that drives the same RoutingGraph as the WebSocket."""
    user_id = req.user_id or "rest-user"
    state, events = routing_graph.run_step(
        user_id=user_id,
        message=req.message,
        pending_event=None,
    )

    reply = ""
    doctors: list[dict] = []
    slots: list[dict] = []

    for ev in events:
        if ev.type == "text":
            reply = ev.payload.get("content", reply)
        elif ev.type == "doctor_select":
            doctors = ev.payload.get("options") or []
        elif ev.type == "slot_select":
            slots = ev.payload.get("options") or []

    return ChatResponse(
        reply=reply,
        model=ROUTING_MODEL,
        doctors=doctors,
        slots=slots,
        routing={"doctor_id": state.selected_doctor} if state.selected_doctor else None,
    )



class RegistrationRequest(BaseModel):
    name: str = Field(..., min_length=2)
    age: int | None = None
    gender: str | None = None
    phone: str
    email: EmailStr | None = None
    city: str | None = None
    emergency_contact: str | None = None
    consent: bool = False
    # client-side migration helpers removed for simplicity

    @validator("phone")
    def phone_must_look_valid(cls, v: str) -> str:  # simple validation
        s = v.strip()
        if len(s) < 7 or len(s) > 30:
            raise ValueError("phone looks invalid")
        return s


@app.post("/register")
def register(req: RegistrationRequest = Body(...)) -> dict:
    """Register a new patient, create a session, and return the permanent Patient ID.

    The endpoint will attempt to migrate any client-side artifacts identified
    by `client_user_id` into the newly created patient record.
    """
    try:
        from backend.neurology.db.pgvector_tracker import (
            create_patient,
            create_session,
        )
    except ImportError:
        from db.pgvector_tracker import create_patient, create_session  # type: ignore

    # Validate consent
    if not req.consent:
        raise HTTPException(status_code=422, detail="Consent is required to register")

    # Create patient
    patient_id = create_patient(
        name=req.name.strip(),
        age=req.age,
        phone=req.phone.strip(),
        email=str(req.email) if req.email else None,
        city=req.city,
        emergency_contact=req.emergency_contact,
        consent=req.consent,
    )

    # Create a distinct session for this patient (session != patient id)
    import uuid
    session_id = f"sess-{uuid.uuid4()}"
    try:
        create_session(session_id, patient_id, current_state="ROUTING")
    except Exception:
        # non-fatal if DB unavailable
        pass

    return {"ok": True, "patient_id": patient_id, "session_id": session_id}


class LoginRequest(BaseModel):
    email: str


@app.post("/login")
def login(req: LoginRequest = Body(...)) -> dict:
    try:
        from backend.neurology.db.pgvector_tracker import get_patient_by_email, create_session
    except ImportError:
        from db.pgvector_tracker import get_patient_by_email, create_session  # type: ignore

    patient = get_patient_by_email(req.email.strip())
    if not patient:
        raise HTTPException(status_code=404, detail="No account found for that email.")

    patient_id = patient["id"]
    import uuid
    session_id = f"sess-{uuid.uuid4()}"
    try:
        create_session(session_id, patient_id, current_state="ROUTING")
    except Exception:
        pass

    health_data = patient.get("health_data", {})
    return {
        "ok": True,
        "patient_id": patient_id,
        "session_id": session_id,
        "profile": {
            "id": patient_id,
            "name": patient["name"],
            "email": health_data.get("email") if isinstance(health_data, dict) else None,
            "phone": health_data.get("phone") if isinstance(health_data, dict) else None,
            "age": patient.get("age"),
            "city": health_data.get("city") if isinstance(health_data, dict) else None,
            "emergency_contact": health_data.get("emergency_contact") if isinstance(health_data, dict) else None,
            "consent": health_data.get("consent", False) if isinstance(health_data, dict) else False,
        },
    }


@app.get("/patient/{patient_id}")
def get_patient(patient_id: str) -> dict:
    try:
        from backend.neurology.db.pgvector_tracker import get_patient_by_id
    except ImportError:
        from db.pgvector_tracker import get_patient_by_id  # type: ignore

    patient = get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    health_data = patient.get("health_data", {})
    return {
        "ok": True,
        "patient_id": patient["id"],
        "profile": {
            "id": patient["id"],
            "name": patient.get("name"),
            "email": health_data.get("email") if isinstance(health_data, dict) else None,
            "phone": health_data.get("phone") if isinstance(health_data, dict) else None,
            "age": patient.get("age"),
            "city": health_data.get("city") if isinstance(health_data, dict) else None,
            "emergency_contact": health_data.get("emergency_contact") if isinstance(health_data, dict) else None,
            "consent": health_data.get("consent", False) if isinstance(health_data, dict) else False,
        },
    }


@app.get("/patient/validate/{patient_id}")
def validate_patient(patient_id: str) -> dict:
    try:
        from backend.neurology.db.pgvector_tracker import get_patient_by_id
    except ImportError:
        from db.pgvector_tracker import get_patient_by_id  # type: ignore

    if not get_patient_by_id(patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"ok": True, "patient_id": patient_id}

