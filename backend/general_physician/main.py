# backend/general_physician/main.py
# FastAPI entrypoint. Owns the WebSocket dispatcher and the REST /chat shortcut.

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException
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
app.include_router(ws_router)


@app.get("/")
def root() -> dict:
    return {"status": "Ally AI backend running"}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


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

