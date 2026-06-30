# backend/main.py
# FastAPI entrypoint. Owns the WebSocket dispatcher and the REST /chat shortcut.

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException

try:
    from backend.graphs import routing_graph
    from backend.llm.nvidia_client import chat as nv_chat, ROUTING_MODEL
    from backend.models.session_state import ChatRequest, ChatResponse
    from backend.ws.router import router as ws_router
    from backend.db.pgvector_tracker import init_db, seed_default_user
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
logging.getLogger("backend.graphs").setLevel(logging.INFO)
logging.getLogger("backend.ws").setLevel(logging.INFO)
logging.getLogger("backend.llm").setLevel(logging.INFO)


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


@app.get("/nv-test")
def nv_test() -> dict:
    try:
        msg = nv_chat([{"role": "user", "content": "Say OK in one word."}], model=ROUTING_MODEL)
        return {"status": "ok", "model": ROUTING_MODEL, "response": msg}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest = Body(...)) -> ChatResponse:
    """REST shortcut that drives the same RoutingGraph as the WebSocket."""
    user_id = req.user_id or "rest-user"
    state, events = routing_graph.run_step(
        user_id=user_id, message=req.message, pending_event=None,
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
