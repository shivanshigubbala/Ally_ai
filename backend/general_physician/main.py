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

try:
    from backend.general_physician.graphs import routing_graph
    from backend.general_physician.llm.nvidia_client import chat as nv_chat, ROUTING_MODEL
    from backend.general_physician.models.session_state import ChatRequest, ChatResponse
    from backend.general_physician.ws.router import router as ws_router
    from backend.general_physician.db.pgvector_tracker import init_db, seed_default_user
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
logging.getLogger("backend.general_physician.graphs").setLevel(logging.INFO)
logging.getLogger("backend.general_physician.ws").setLevel(logging.INFO)
logging.getLogger("backend.general_physician.llm").setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
        seed_default_user()
    except Exception:
        pass  # pg not available, continue with in-memory store
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


@app.post("/upload-document/{user_id}/{appointment_id}")
async def upload_document(
    user_id: str,
    appointment_id: str,
    file: UploadFile = File(...),
) -> dict:
    """
    Receive a document (PDF / TXT / image) uploaded before consultation.
    Extracts plain text and stores it in the ws router's in-memory doc store
    so the doctor agent can read it during the session.
    """
    try:
        from backend.general_physician.ws.router import _doc_store
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

    return {"ok": True, "filename": filename, "text_length": len(extracted)}


@app.get("/reports/{report_id}")
def download_report(report_id: str) -> FileResponse:
    # backend/main.py -> parents[0] is backend/. Both cardiology_agent.py and
    # general_physician_agent.py write PDFs to backend/reports/ (their own
    # parents[1] is also backend/), so this route must look in the same place.
    report_path = Path(__file__).resolve().parents[0] / "reports" / f"{report_id}.pdf"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(
        str(report_path),
        filename=f"{report_id}.pdf",
        media_type="application/pdf",
    )


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

