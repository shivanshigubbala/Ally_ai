# backend/general_physician/main.py
# FastAPI entrypoint. Owns the WebSocket dispatcher and the REST /chat shortcut.

import io
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse
import asyncio

ROOT_PATH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_PATH))

from backend.general_physician.graphs import routing_graph
from backend.llm.nvidia_client import chat as nv_chat, ROUTING_MODEL
from backend.models.session_state import ChatRequest, ChatResponse
from backend.ws.router import router as ws_router
from backend.db.pgvector_tracker import init_db, seed_default_user
from pydantic import BaseModel, EmailStr, Field, validator

load_dotenv(ROOT_PATH / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logging.getLogger("backend").setLevel(logging.INFO)
logging.getLogger("backend.general_physician.graphs").setLevel(logging.INFO)
logging.getLogger("backend.ws").setLevel(logging.INFO)
logging.getLogger("backend.general_physician.llm").setLevel(logging.INFO)


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
    allow_origins=["*"],
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


@app.post("/reset-db")
def reset_db() -> dict:
    try:
        from backend.db.pgvector_tracker import _conn, init_db
    except ImportError:
        from db.pgvector_tracker import _conn, init_db # type: ignore
    
    with _conn() as conn:
        with conn.cursor() as cur:
            # Delete entries from Go tables first so they are re-seeded cleanly
            cur.execute("DELETE FROM lab_reports CASCADE")
            cur.execute("DELETE FROM time_slots CASCADE")
            cur.execute("DELETE FROM doctors CASCADE")
            cur.execute("DELETE FROM departments CASCADE")

            tables = [
                "appointments",
                "messages",
                "sessions",
                "consultation_contexts",
                "uploaded_files",
                "notifications",
                "patient_timelines",
                "lab_work_items"
            ]
            for t in tables:
                cur.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
        conn.commit()
    
    init_db()
    
    from pathlib import Path
    import shutil
    reports_root = Path(__file__).resolve().parent / "reports"
    if reports_root.exists():
        try:
            shutil.rmtree(reports_root)
            reports_root.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
            
    return {"ok": True, "message": "Database flushed and re-seeded successfully"}


@app.post("/delete-patient")
def delete_patient(patient_id: str = Body(..., embed=True)) -> dict:
    try:
        from backend.db.pgvector_tracker import _conn
    except ImportError:
        from db.pgvector_tracker import _conn

    if not _conn:
        raise HTTPException(status_code=500, detail="Database connection not available")

    # Get the go_user_id first
    go_user_id = None
    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT go_user_id FROM users WHERE id = %s", (patient_id,))
                row = cur.fetchone()
                if row:
                    go_user_id = row[0]

                # 1. Delete lab reports
                if go_user_id is not None:
                    cur.execute(
                        "DELETE FROM lab_reports WHERE appointment_id IN (SELECT id FROM appointments WHERE user_id = %s)",
                        (str(go_user_id),)
                    )

                # 2. Delete from Python tables
                cur.execute("DELETE FROM appointments WHERE patient_id = %s OR user_id = %s", (patient_id, str(go_user_id) if go_user_id else ""))
                cur.execute("DELETE FROM messages WHERE user_id = %s", (patient_id,))
                cur.execute("DELETE FROM sessions WHERE patient_id = %s", (patient_id,))
                cur.execute("DELETE FROM consultation_contexts WHERE patient_id = %s", (patient_id,))
                cur.execute("DELETE FROM uploaded_files WHERE user_id = %s", (patient_id,))
                cur.execute("DELETE FROM notifications WHERE patient_id = %s", (patient_id,))
                cur.execute("DELETE FROM patient_timelines WHERE patient_id = %s", (patient_id,))
                cur.execute("DELETE FROM lab_work_items WHERE patient_id = %s", (patient_id,))
                cur.execute("DELETE FROM users WHERE id = %s", (patient_id,))

                # 3. Delete from Go table
                if go_user_id is not None:
                    cur.execute("DELETE FROM appointment_users WHERE id = %s", (go_user_id,))
            conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database deletion failed: {e}")

    # Delete generated report files for this patient
    from pathlib import Path
    reports_root = Path(__file__).resolve().parent / "reports"
    if reports_root.exists():
        for dept_dir in reports_root.glob("*"):
            if dept_dir.is_dir():
                for f in dept_dir.glob(f"*_{patient_id}.pdf"):
                    try:
                        f.unlink()
                    except Exception:
                        pass
                if go_user_id:
                    for f in dept_dir.glob(f"*_{go_user_id}.pdf"):
                        try:
                            f.unlink()
                        except Exception:
                            pass

    return {"ok": True, "message": f"Successfully deleted patient {patient_id} and all associated records."}


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
        from backend.ws.router import _doc_store
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
        from backend.db.pgvector_tracker import (
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
            from backend.ws.router import notify_user_event
            from backend.models.session_state import WSEvent
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
                from backend.llm.embeddings import embed_passages
                from backend.db.pgvector_tracker import insert_knowledge_chunks
            except ImportError:
                from llm.embeddings import embed_passages  # type: ignore
                from db.pgvector_tracker import insert_knowledge_chunks  # type: ignore

            passage_texts = [item[1] for item in chunks]
            embeddings = embed_passages(passage_texts)

            # Determine department for this upload from the appointment if possible
            dept = "general"
            try:
                from backend.services import local_store as store
                apt = store.get_appointment(appointment_id) if appointment_id else None
                if apt and isinstance(apt, dict):
                    dept = apt.get("department") or dept
            except Exception:
                pass
            for (page_num, content_str), emb in zip(chunks, embeddings):
                insert_knowledge_chunks(
                    department=dept,
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
                        from backend.ws.router import notify_user_event
                        from backend.models.session_state import WSEvent
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


@app.get("/reports/{department}/{filename}")
def get_report(department: str, filename: str):
    """Serve generated report files from backend/reports/<department>/filename."""
    try:
        from fastapi import HTTPException
        from pathlib import Path
        path = Path(__file__).resolve().parents[1] / "reports" / department / filename
        if not path.exists() or not path.is_file():
            raise HTTPException(status_code=404, detail="Report not found")
        return FileResponse(path)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to read report file")
    


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
        from backend.db.pgvector_tracker import get_uploaded_files_for_session
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
            from backend.db.pgvector_tracker import create_notification
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
            from backend.ws.router import notify_user_event
            from backend.models.session_state import WSEvent
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

            # Trigger generating the consolidated Prescription PDF now that lab reports are ready
            try:
                from backend.shared.prescription_pdf import generate_prescription_pdf, save_prescription_notification_and_emit
            except ImportError:
                from shared.prescription_pdf import generate_prescription_pdf, save_prescription_notification_and_emit

            try:
                prescription_meta = generate_prescription_pdf(payload.get("appointment_id"))
                if prescription_meta:
                    save_prescription_notification_and_emit(
                        appointment_id=payload.get("appointment_id"),
                        pdf_path=prescription_meta.get("pdf_path"),
                        doctor_name=prescription_meta.get("doctor_name"),
                        patient_id=prescription_meta.get("patient_id"),
                        department=prescription_meta.get("department")
                    )
            except Exception as e:
                print("Failed to generate prescription PDF in internal_report_ready callback:", e)
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
    # Medical history - optional, stored in health_data JSONB
    conditions: str | None = None
    medications: str | None = None
    allergies: str | None = None
    health_assessment: dict | None = None

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
        from backend.db.pgvector_tracker import (
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
        gender=req.gender,
    )

    # Create a distinct session for this patient (session != patient id)
    import uuid
    session_id = f"sess-{uuid.uuid4()}"
    try:
        create_session(session_id, patient_id, current_state="ROUTING")
    except Exception:
        # non-fatal if DB unavailable
        pass

    # Persist extra medical history into health_data (best-effort)
    try:
        from backend.db.pgvector_tracker import _conn, HAS_PG
        import psycopg2.extras as _extras
        import json as _json
        if HAS_PG and any([req.conditions, req.medications, req.allergies, req.health_assessment]):
            with _conn() as conn:
                if conn is not None:
                    _cur = conn.cursor(cursor_factory=_extras.RealDictCursor)
                    _cur.execute("SELECT health_data FROM users WHERE id=%s", (patient_id,))
                    _row = _cur.fetchone()
                    if _row:
                        _hd = _row["health_data"] if isinstance(_row["health_data"], dict) else {}
                        if req.conditions: _hd["conditions"] = req.conditions
                        if req.medications: _hd["medications"] = req.medications
                        if req.allergies: _hd["allergies"] = req.allergies
                        if req.health_assessment: _hd["healthAssessment"] = req.health_assessment
                        _cur.execute("UPDATE users SET health_data=%s WHERE id=%s", (_json.dumps(_hd), patient_id))
    except Exception:
        pass

    return {"ok": True, "patient_id": patient_id, "session_id": session_id}


class LoginRequest(BaseModel):
    email: str


@app.post("/login")
def login(req: LoginRequest = Body(...)) -> dict:
    """Look up an existing patient by email. Returns patient_id + profile."""
    try:
        from backend.db.pgvector_tracker import get_patient_by_email
    except ImportError:
        from db.pgvector_tracker import get_patient_by_email  # type: ignore

    patient = get_patient_by_email(req.email.strip().lower())
    if not patient:
        raise HTTPException(status_code=404, detail="No account found with that email")

    import uuid
    session_id = f"sess-{uuid.uuid4()}"
    patient_id = patient.get("id") or patient.get("patient_id", "")
    return {
        "ok": True,
        "patient_id": patient_id,
        "session_id": session_id,
        "profile": {
            "name": patient.get("name", ""),
            "email": patient.get("email", req.email),
            "gender": patient.get("gender", ""),
            "age": patient.get("age"),
            "phone": patient.get("phone", ""),
        },
    }


@app.get("/patient/validate/{patient_id}")
def validate_patient(patient_id: str) -> dict:
    try:
        from backend.db.pgvector_tracker import get_patient_by_id
    except ImportError:
        from db.pgvector_tracker import get_patient_by_id  # type: ignore

    if not get_patient_by_id(patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"ok": True, "patient_id": patient_id}


class ProfileUpdateRequest(BaseModel):
    patient_id: str
    name: str
    phone: str
    city: str | None = None
    emergency_contact: str | None = None
    age: int | None = None
    bloodGroup: str | None = None
    # Medical history fields
    conditions: str | None = None
    medications: str | None = None
    allergies: str | None = None
    healthAssessment: dict | None = None


@app.put("/profile")
def update_profile(req: ProfileUpdateRequest = Body(...)) -> dict:
    try:
        from backend.db.pgvector_tracker import _conn, HAS_PG
        import psycopg2.extras
    except ImportError:
        from db.pgvector_tracker import _conn, HAS_PG  # type: ignore
        import psycopg2.extras

    if not HAS_PG:
        return {"ok": True, "note": "Profile stored client-side only (no DB)"}

    import json

    with _conn() as conn:
        if conn is None:
            return {"ok": True, "note": "Profile stored client-side only (no DB)"}

        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT health_data FROM users WHERE id=%s", (req.patient_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Patient not found")

        health_data: dict = row["health_data"] if isinstance(row["health_data"], dict) else {}

        # Persist extra medical history fields
        if req.conditions is not None:
            health_data["conditions"] = req.conditions
        if req.medications is not None:
            health_data["medications"] = req.medications
        if req.allergies is not None:
            health_data["allergies"] = req.allergies
        if req.healthAssessment is not None:
            health_data["healthAssessment"] = req.healthAssessment
        if req.bloodGroup:
            health_data["bloodGroup"] = req.bloodGroup

        cur.execute(
            "UPDATE users SET name = %s, age = %s, health_data = %s WHERE id = %s",
            (req.name, req.age or 0, json.dumps(health_data), req.patient_id),
        )
        cur.close()

    return {"ok": True}


@app.get("/notifications/{patient_id}")
def get_patient_notifications(patient_id: str, status: str | None = None, limit: int = 50) -> dict:
    """Fetch notifications for a patient from the DB."""
    try:
        from backend.db.pgvector_tracker import get_notifications
    except ImportError:
        from db.pgvector_tracker import get_notifications  # type: ignore
    try:
        items = get_notifications(patient_id=patient_id, status=status or None, limit=limit)
        return {"ok": True, "notifications": items}
    except Exception:
        return {"ok": True, "notifications": []}


@app.post("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: str) -> dict:
    """Mark a notification as read in the DB."""
    try:
        from backend.db.pgvector_tracker import mark_read
    except ImportError:
        from db.pgvector_tracker import mark_read  # type: ignore
    try:
        result = mark_read(notification_id)
        if result:
            return {"ok": True, "notification": result}
        return {"ok": False, "detail": "Notification not found"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/patient/{patient_id}/timeline")
def get_timeline(patient_id: str) -> dict:
    """Return the patient longitudinal consultation timeline."""
    try:
        from backend.db.pgvector_tracker import get_patient_timeline
    except ImportError:
        from db.pgvector_tracker import get_patient_timeline  # type: ignore
    try:
        timeline = get_patient_timeline(patient_id=patient_id)
        if not timeline:
            return {"ok": True, "timeline": {"history": []}}
        return {"ok": True, "timeline": timeline}
    except Exception:
        return {"ok": True, "timeline": {"history": []}}


@app.get("/patient/{patient_id}/history")
def get_patient_history_endpoint(patient_id: str, limit: int = 20) -> dict:
    """Return the patient message/session history."""
    try:
        from backend.db.pgvector_tracker import load_patient_history
    except ImportError:
        from db.pgvector_tracker import load_patient_history  # type: ignore
    try:
        history = load_patient_history(patient_id=patient_id, limit=limit)
        return {"ok": True, "history": history}
    except Exception:
        return {"ok": True, "history": []}
