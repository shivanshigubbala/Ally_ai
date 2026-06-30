from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

logger = logging.getLogger(__name__)

try:
    from backend.db.pgvector_tracker import (
        get_user_health_context,
        save_message,
    )
    from backend.llm.nvidia_client import (
        ROUTING_MODEL,
        chat as nv_chat,
        stream_chat as nv_stream_chat,
    )
    from backend.llm.prompts import (
        DOCTOR_NAME,
        DOCTOR_SYSTEM_PROMPT,
        EVALUATION_PROMPT,
    )
    from backend.models.session_state import DoctorState, WSEvent
    from backend.rag.retriever import retrieve as rag_retrieve
    from backend.services import local_store as store
except ImportError:
    from db.pgvector_tracker import (
        get_user_health_context,
        save_message,
    )
    from llm.nvidia_client import (
        ROUTING_MODEL,
        chat as nv_chat,
        stream_chat as nv_stream_chat,
    )
    from llm.prompts import (
        DOCTOR_NAME,
        DOCTOR_SYSTEM_PROMPT,
        EVALUATION_PROMPT,
    )
    from models.session_state import DoctorState, WSEvent
    from rag.retriever import retrieve as rag_retrieve
    from services import local_store as store


Emitter = Callable[[WSEvent], None]

DOCTOR_ID = "d5"
DOCTOR_NAME = DOCTOR_NAME
DOCTOR_DEPT = "general"
MAX_QUESTIONS = 10


def _remember(user_id: str, role: str, content: str, session_id: str | None = None) -> None:
    """Persist a single turn to the pgvector messages table (best-effort)."""
    try:
        save_message(user_id=user_id, role=role, content=content, session_id=session_id)
    except Exception:
        pass


def _load_prior_context(user_id: str, exclude_session_id: str | None) -> str:
    """Return a short transcript of this user's prior visits, or '' if none."""
    try:
        return get_user_health_context(user_id)
    except Exception:
        return ""


def _extract_json(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _call_llm(messages: list[dict], model: str | None = None) -> str:
    use_model = model or ROUTING_MODEL  # Use 8B for speed
    return nv_chat(messages, model=use_model)


def _stream_into_emit(messages: list[dict], emit: Emitter, sender: str,
                      model: str | None = None) -> str:
    """Stream LLM output to the WS as text_delta events; return the full reply."""
    use_model = model or ROUTING_MODEL
    parts: list[str] = []
    try:
        for token in nv_stream_chat(messages, model=use_model):
            parts.append(token)
            emit(WSEvent(type="text_delta", payload={"delta": token, "from": sender}))
    except Exception:
        logger.exception(
            "Streaming LLM call failed sender=%s model=%s",
            sender, use_model,
        )
        if not parts:
            raise
    return "".join(parts)


def _format_messages(history: list[dict]) -> str:
    lines: list[str] = []
    for m in history:
        if m.get("role") in ("user", "assistant"):
            lines.append(f"{m['role']}: {m['content']}")
    return "\n".join(lines) or "(no prior conversation)"


# ---- Nodes --------------------------------------------------------------------


def session_init(state: DoctorState, emit: Emitter) -> DoctorState:
    # Capture the chief complaint once at session start. Prefer an explicit
    # user message in this session's history; otherwise pull the earliest
    # prior user message (from the routing phase) so the doctor's relevance
    # gate has the actual concern, not the user_id.
    if not state.chief_complaint:
        for m in state.conversation_history:
            if m.get("role") == "user" and m.get("content"):
                state.chief_complaint = m["content"].strip()
                break
    if not state.chief_complaint:
        try:
            prior_msgs = get_user_messages(
                state.user_id,
                limit=20,
                exclude_session_id=f"doctor:{state.user_id}:{state.appointment_id}",
            )
            for m in prior_msgs:
                if m.get("role") == "user" and m.get("content"):
                    state.chief_complaint = m["content"].strip()
                    break
        except Exception:
            pass

    rag_context = rag_retrieve(
        department=DOCTOR_DEPT,
        messages=state.conversation_history or [{"role": "user", "content": state.user_id}],
    )

    prior = _load_prior_context(
        state.user_id,
        exclude_session_id=f"doctor:{state.user_id}:{state.appointment_id}",
    )
    health_data = state.health_data or {}

    patient_name = state.user_id.replace("_", " ").title()

    system = DOCTOR_SYSTEM_PROMPT.format(
        rag_context=rag_context or "(no clinical reference retrieved)",
        name=patient_name,
        age=health_data.get("age", "unknown"),
        health_data=prior or "(no prior visits)",
        messages=_format_messages(state.conversation_history),
        q_count=0,
        chief_complaint=state.chief_complaint or "(not yet stated)",
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": "Begin the consultation."},
    ]
    try:
        reply = _stream_into_emit(messages, emit, sender=DOCTOR_ID)
    except Exception:
        logger.exception(
            "LLM stream failed in session_init() for user=%s apt=%s",
            state.user_id, state.appointment_id,
        )
        try:
            reply = _call_llm(messages)
            emit(WSEvent(type="text", payload={"content": reply, "from": DOCTOR_ID}))
        except Exception:
            logger.exception(
                "Fallback non-stream LLM also failed in session_init() user=%s",
                state.user_id,
            )
            reply = (
                "I'm having trouble starting the consultation right now - "
                f"could you tell me, in your own words, what's been bothering you, {patient_name}?"
            )
            emit(WSEvent(type="text", payload={"content": reply, "from": DOCTOR_ID}))
    state.conversation_history.append({"role": "assistant", "content": reply})
    state.current_node = "QUESTIONING"
    state.questions_asked = 0
    return state


def questioning(state: DoctorState, emit: Emitter) -> DoctorState:
    state.questions_asked = (state.questions_asked or 0) + 1

    if state.questions_asked >= MAX_QUESTIONS:
        emit(WSEvent(type="text", payload={
            "content": "Thanks for sharing all that - I have a good picture now. "
                       "Let me review everything and see if any tests are needed.",
            "from": DOCTOR_ID,
        }))
        state.current_node = "EVALUATION"
        return state

    rag_context = rag_retrieve(
        department=DOCTOR_DEPT,
        messages=state.conversation_history,
    )

    prior = _load_prior_context(
        state.user_id,
        exclude_session_id=f"doctor:{state.user_id}:{state.appointment_id}",
    )
    health_data = state.health_data or {}
    patient_name = state.user_id.replace("_", " ").title()

    system = DOCTOR_SYSTEM_PROMPT.format(
        rag_context=rag_context or "(no clinical reference retrieved)",
        name=patient_name,
        age=health_data.get("age", "unknown"),
        health_data=prior or "(no prior visits)",
        messages=_format_messages(state.conversation_history),
        q_count=state.questions_asked,
        chief_complaint=state.chief_complaint or "(not yet stated)",
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": "Ask your next single clinical question."},
    ]
    try:
        reply = _stream_into_emit(messages, emit, sender=DOCTOR_ID)
    except Exception:
        logger.exception(
            "LLM stream failed in questioning() for user=%s apt=%s q=%s",
            state.user_id, state.appointment_id, state.questions_asked,
        )
        try:
            reply = _call_llm(messages)
            emit(WSEvent(type="text", payload={"content": reply, "from": DOCTOR_ID}))
        except Exception:
            logger.exception(
                "Fallback non-stream LLM also failed in questioning() user=%s q=%s",
                state.user_id, state.questions_asked,
            )
            reply = (
                "I'm having trouble processing that right now - "
                "could you tell me a bit more about your main symptom?"
            )
            emit(WSEvent(type="text", payload={"content": reply, "from": DOCTOR_ID}))

    state.conversation_history.append({"role": "assistant", "content": reply})
    state.current_node = "QUESTIONING"
    return state


def evaluation(state: DoctorState, emit: Emitter) -> DoctorState:
    conv_text = "\n".join(
        f"{m['role']}: {m['content']}"
        for m in state.conversation_history
        if m["role"] in ("user", "assistant")
    )
    prompt = EVALUATION_PROMPT.format(conversation=conv_text)
    raw = _call_llm([{"role": "user", "content": prompt}], model=ROUTING_MODEL)
    parsed = _extract_json(raw) or {}

    state.lab_tests_recommended = bool(parsed.get("recommend_tests", False))
    state.tests_list = parsed.get("tests", [])

    if state.lab_tests_recommended and state.tests_list:
        test_names = ", ".join(t.get("name", "?") for t in state.tests_list)
        emit(WSEvent(type="text", payload={
            "content": (
                f"Based on what you've told me, I'd like to order a few quick tests "
                f"to be safe - {test_names}. They're routine and will help me confirm "
                f"what's going on. Is that okay?"
            ),
            "from": DOCTOR_ID,
        }))
        emit(WSEvent(type="lab_notification", payload={
            "tests": state.tests_list,
            "session_id": state.appointment_id,
        }))
        state.current_node = "LAB_NOTIFICATION"
    else:
        emit(WSEvent(type="text", payload={
            "content": (
                "Good news - based on everything you've told me, I don't think we need "
                "any tests right now. Get some rest, stay hydrated, and come back if "
                "anything changes or gets worse."
            ),
            "from": DOCTOR_ID,
        }))
        state.current_node = "SESSION_COMPLETE"
    return state


def lab_notification(state: DoctorState, emit: Emitter) -> DoctorState:
    pending = getattr(state, "pending_event", None) or {}
    decision = "pending"

    if pending.get("type") == "select":
        decision = pending.get("payload", {}).get("decision", "pending")
    else:
        for m in reversed(state.conversation_history):
            if m["role"] == "user":
                content = m["content"].lower().strip()
                if content in ("accept", "yes", "ok", "sure", "proceed", "go ahead"):
                    decision = "accept"
                elif content in ("reject", "no", "nope", "decline", "skip"):
                    decision = "reject"
                break

    state.user_lab_decision = decision
    state.pending_event = None

    if decision != "pending":
        state.current_node = "USER_DECISION"
    else:
        emit(WSEvent(type="lab_notification", payload={
            "tests": state.tests_list,
            "session_id": state.appointment_id,
            "waiting": True,
        }))
    return state


def user_decision(state: DoctorState, emit: Emitter) -> DoctorState:
    if state.user_lab_decision == "accept":
        emit(WSEvent(type="text", payload={
            "content": "Great, I'm ordering those tests now. You'll get the report shortly!",
            "from": DOCTOR_ID,
        }))
        state.current_node = "REPORT_PENDING"
    else:
        emit(WSEvent(type="text", payload={
            "content": "No problem. Watch for any new symptoms, stay hydrated, and feel free to come back anytime.",
            "from": DOCTOR_ID,
        }))
        state.current_node = "SESSION_COMPLETE"
    return state


def report_pending(state: DoctorState, emit: Emitter) -> DoctorState:
    emit(WSEvent(type="report_ready", payload={
        "inbox_id": f"report-{state.appointment_id}",
        "doctor": DOCTOR_NAME,
    }))
    emit(WSEvent(type="text", payload={
        "content": "Your lab report is ready. Take care, and follow up if anything changes!",
        "from": DOCTOR_ID,
    }))
    state.current_node = "SESSION_COMPLETE"
    return state


def session_complete(state: DoctorState, emit: Emitter) -> DoctorState:
    return state


# ---- Conditional edges --------------------------------------------------------


def _after_questioning(state: DoctorState) -> str:
    return "EVALUATION" if state.current_node == "EVALUATION" else "QUESTIONING"


def _after_evaluation(state: DoctorState) -> str:
    return "LAB_NOTIFICATION" if state.current_node == "LAB_NOTIFICATION" else "SESSION_COMPLETE"


def _after_decision(state: DoctorState) -> str:
    return "REPORT_PENDING" if state.current_node == "REPORT_PENDING" else "SESSION_COMPLETE"


# ---- Graph builder ------------------------------------------------------------


def build_graph() -> StateGraph:
    g = StateGraph(DoctorState)
    g.add_node("SESSION_INIT", session_init)
    g.add_node("QUESTIONING", questioning)
    g.add_node("EVALUATION", evaluation)
    g.add_node("LAB_NOTIFICATION", lab_notification)
    g.add_node("USER_DECISION", user_decision)
    g.add_node("REPORT_PENDING", report_pending)
    g.add_node("SESSION_COMPLETE", session_complete)

    g.set_entry_point("SESSION_INIT")
    g.add_edge("SESSION_INIT", "QUESTIONING")
    g.add_conditional_edges("QUESTIONING", _after_questioning, {
        "EVALUATION": "EVALUATION", "QUESTIONING": "QUESTIONING"
    })
    g.add_conditional_edges("EVALUATION", _after_evaluation, {
        "LAB_NOTIFICATION": "LAB_NOTIFICATION", "SESSION_COMPLETE": "SESSION_COMPLETE"
    })
    g.add_edge("LAB_NOTIFICATION", "USER_DECISION")
    g.add_conditional_edges("USER_DECISION", _after_decision, {
        "REPORT_PENDING": "REPORT_PENDING", "SESSION_COMPLETE": "SESSION_COMPLETE"
    })
    g.add_edge("REPORT_PENDING", "SESSION_COMPLETE")
    g.add_edge("SESSION_COMPLETE", END)

    return g


_checkpointer = MemorySaver()
_graph = build_graph().compile(checkpointer=_checkpointer)


def step(
    user_id: str,
    appointment_id: str,
    user_message: str | None,
    pending_event: dict | None,
) -> tuple[DoctorState, list[WSEvent]]:
    events: list[WSEvent] = []
    cfg = {"configurable": {"thread_id": f"doc:{user_id}:{appointment_id}"}}

    snap = _graph.get_state(cfg)
    if snap and snap.values:
        state = DoctorState(**snap.values)
    else:
        state = DoctorState(
            user_id=user_id,
            appointment_id=appointment_id,
            doctor_id=DOCTOR_ID,
            department=DOCTOR_DEPT,
        )

    if user_message:
        state.conversation_history.append({"role": "user", "content": user_message})
        _remember(
            user_id,
            "user",
            user_message,
            session_id=f"doctor:{user_id}:{appointment_id}",
        )
    if pending_event:
        state.pending_event = pending_event

    node_map = {
        "SESSION_INIT": session_init,
        "QUESTIONING": questioning,
        "EVALUATION": evaluation,
        "LAB_NOTIFICATION": lab_notification,
        "USER_DECISION": user_decision,
        "REPORT_PENDING": report_pending,
        "SESSION_COMPLETE": session_complete,
    }

    prev_len = len(state.conversation_history)
    for _ in range(20):
        if state.current_node == "SESSION_COMPLETE":
            break
        node_fn = node_map[state.current_node]
        state = node_fn(state, events.append)
        if state.current_node in {"QUESTIONING", "LAB_NOTIFICATION", "REPORT_PENDING"}:
            break

    for m in state.conversation_history[prev_len:]:
        if m["role"] == "assistant":
            _remember(
                user_id,
                "assistant",
                m["content"],
                session_id=f"doctor:{user_id}:{appointment_id}",
            )

    _graph.update_state(cfg, state.model_dump())
    return state, events
