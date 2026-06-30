from __future__ import annotations

import logging
from typing import Any, Callable

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

try:
    from backend.db.pgvector_tracker import save_message
    from backend.llm.nvidia_client import chat as nv_chat, ROUTING_MODEL
    from backend.models.session_state import RoutingState, WSEvent
    from backend.services import local_store as store
except ImportError:
    from db.pgvector_tracker import save_message
    from llm.nvidia_client import chat as nv_chat, ROUTING_MODEL
    from models.session_state import RoutingState, WSEvent
    from services import local_store as store


Emitter = Callable[[WSEvent], None]

logger = logging.getLogger(__name__)

GP_DOCTOR_ID = "d5"
GP_DOCTOR_NAME = "Dr. Shankar"


def _remember(user_id: str, role: str, content: str, session_id: str | None = None) -> None:
    """Persist a single turn to the pgvector messages table (best-effort)."""
    try:
        save_message(user_id=user_id, role=role, content=content, session_id=session_id)
    except Exception:
        pass  # Postgres down or schema missing — never break the chat.


def _llm_reply(system: str, user: str) -> str:
    return nv_chat([
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ], model=ROUTING_MODEL).strip()


RECEPTIONIST_PERSONA = (
    "You are Ally, a warm, caring human receptionist at Ally Hospital. "
    "You speak like a real person - naturally, with empathy and warmth. "
    "You NEVER sound robotic or scripted. You use casual, conversational language. "
    "Short responses (1-3 sentences). No bullet points, no markdown, no lists."
)


def greeting_node(state: RoutingState, emit: Emitter) -> RoutingState:
    if state.message_history and state.message_history[-1]["role"] == "assistant":
        return state
    patient_name = (state.user_id or "there").replace("_", " ").title()
    reply = (
        f"Hi {patient_name}! I'm Ally, here at Ally Hospital. "
        "How are you feeling today, and what brings you in?"
    )
    emit(WSEvent(type="text", payload={"content": reply}))
    state.message_history.append({"role": "assistant", "content": reply})
    state.current_node = "INTENT_CLASSIFICATION"
    return state


def intent_node(state: RoutingState, emit: Emitter) -> RoutingState:
    last_user = ""
    for m in reversed(state.message_history):
        if m["role"] == "user":
            last_user = m["content"]
            break
    if not last_user:
        return state

    reply = _llm_reply(
        RECEPTIONIST_PERSONA + (
            " The patient just described their symptoms. In 1-2 short sentences, acknowledge "
            "what they said warmly, then say you're going to book them with Dr. Shankar, "
            "our General Physician, who can help. No bullet points, no lists."
        ),
        f"Patient said: {last_user}",
    )
    emit(WSEvent(type="text", payload={"content": reply}))
    state.message_history.append({"role": "assistant", "content": reply})

    state.selected_dept = "general"
    state.selected_doctor = GP_DOCTOR_ID

    doc_name = GP_DOCTOR_NAME
    slots = store.list_slots(state.selected_doctor or GP_DOCTOR_ID)
    if slots:
        emit(WSEvent(type="slot_select", payload={
            "options": slots,
            "doctor_id": state.selected_doctor or GP_DOCTOR_ID,
            "doctor_name": doc_name,
        }))
        state.current_node = "SLOT_SELECTION"
    else:
        emit(WSEvent(type="text", payload={"content": "I'm sorry, there are no available slots right now. Please try again later."}))
        state.current_node = "DONE"
    return state


def slot_node(state: RoutingState, emit: Emitter) -> RoutingState:
    pending = state.pending_event or {}
    state.pending_event = None

    if pending.get("type") == "select" and pending.get("payload", {}).get("target") == "slot":
        state.selected_slot = pending["payload"].get("id")
    elif pending.get("type") == "select":
        # User chose something other than a slot — treat as invalid slot
        state.selected_slot = pending["payload"].get("id", "")
    else:
        # Text message during slot selection — acknowledge and re-show slots
        slots = store.list_slots(state.selected_doctor or GP_DOCTOR_ID)
        doc_name = GP_DOCTOR_NAME
        emit(WSEvent(type="text", payload={
            "content": f"I understand. When you're ready, please pick a slot from the available times with {doc_name} by typing the slot id (e.g. s1, s2, etc.)."
        }))
        emit(WSEvent(type="slot_select", payload={
            "options": slots,
            "doctor_id": state.selected_doctor or GP_DOCTOR_ID,
        }))
        return state

    slots = store.list_slots(state.selected_doctor or GP_DOCTOR_ID)
    chosen = next((s for s in slots if s["id"] == state.selected_slot), None)
    if not chosen:
        slots = store.list_slots(state.selected_doctor or GP_DOCTOR_ID)
        emit(WSEvent(type="text", payload={"content": f"That doesn't match any available slot. Please pick one from the list below."}))
        emit(WSEvent(type="slot_select", payload={"options": slots, "doctor_id": state.selected_doctor}))
        return state

    try:
        from datetime import datetime
        ts = datetime.fromisoformat(chosen["start_time"].replace("Z", "+00:00"))
        nice_time = ts.strftime("%A %d %B at %I:%M %p").lstrip("0")
    except Exception:
        nice_time = chosen["start_time"]

    reply = _llm_reply(
        RECEPTIONIST_PERSONA + (
            f" The patient picked a slot on {nice_time} with Dr. Shankar. "
            "Confirm this with them naturally and ask if they'd like to confirm. "
            "Something like 'So I've got you down for {nice_time} with Dr. Rivera - does that sound good?'"
        ),
        f"Confirming slot {chosen['id']} at {nice_time}.",
    )
    emit(WSEvent(type="text", payload={"content": reply}))
    state.current_node = "BOOKING_CONFIRMATION"
    return state


def booking_node(state: RoutingState, emit: Emitter) -> RoutingState:
    last_user = ""
    for m in reversed(state.message_history):
        if m["role"] == "user":
            last_user = m["content"].lower().strip()
            break

    cancelled = "cancel" in last_user or "no" in last_user or "nope" in last_user
    confirmed = "confirm" in last_user or "yes" in last_user or "yeah" in last_user or "sure" in last_user or "good" in last_user

    if not confirmed and not cancelled:
        reply = _llm_reply(
            RECEPTIONIST_PERSONA + " The patient didn't clearly confirm or cancel. Gently ask again if they'd like to confirm the booking.",
            f"Patient said: {last_user}",
        )
        emit(WSEvent(type="text", payload={"content": reply}))
        return state

    if cancelled:
        reply = _llm_reply(
            RECEPTIONIST_PERSONA + " The patient wants to cancel. Be understanding and tell them they can come back anytime.",
            "Patient cancelled.",
        )
        emit(WSEvent(type="text", payload={"content": reply}))
        state.current_node = "DONE"
        return state

    status, body = store.book_appointment(
        doctor_id=state.selected_doctor or GP_DOCTOR_ID,
        slot_id=state.selected_slot or "",
        patient=state.user_id,
        reason="booked via Ally receptionist",
    )

    if status == 409:
        reply = _llm_reply(
            RECEPTIONIST_PERSONA + " The slot was just taken by someone else. Apologize and show new available slots.",
            "Slot conflict - need new slot.",
        )
        emit(WSEvent(type="text", payload={"content": reply}))
        slots = store.list_slots(state.selected_doctor or GP_DOCTOR_ID)
        if slots:
            state.selected_slot = slots[0]["id"]
            emit(WSEvent(type="slot_select", payload={"options": slots, "doctor_id": state.selected_doctor}))
            state.current_node = "SLOT_SELECTION"
        return state

    if status >= 400:
        emit(WSEvent(type="text", payload={
            "content": f"Sorry, something went wrong on our end (code {status}). Could you try again?"
        }))
        return state

    state.appointment_id = body.get("id") if isinstance(body, dict) else None
    reply = _llm_reply(
        RECEPTIONIST_PERSONA + (
            f" The appointment is confirmed! Appointment ID: {state.appointment_id}. "
            "In 1-2 short sentences, congratulate the patient warmly and tell them "
            "Dr. Shankar will be right with them. No bullet points, no lists."
        ),
        f"Appointment {state.appointment_id} confirmed.",
    )
    emit(WSEvent(type="text", payload={"content": reply}))
    state.message_history.append({"role": "assistant", "content": f"Appointment {state.appointment_id} confirmed."})

    transition = _llm_reply(
        RECEPTIONIST_PERSONA + (
            " The appointment is booked. Now tell the patient that Dr. Shankar is ready to see them now "
            "and will be joining the chat. Say something warm like 'Dr. Shankar is coming online now to speak with you!'"
        ),
        "Transitioning to doctor.",
    )
    emit(WSEvent(type="text", payload={"content": transition}))
    state.current_node = "DONE"
    return state


# ---- Edge routing -------------------------------------------------------------

def _route_after_intent(state: RoutingState) -> str:
    return "SLOT_SELECTION" if state.selected_dept else "GREETING"


def _route_after_slot(state: RoutingState) -> str:
    return "BOOKING_CONFIRMATION" if state.selected_slot else "DONE"


def _route_after_booking(state: RoutingState) -> str:
    return "DONE" if state.current_node == "DONE" else "SLOT_SELECTION"


# ---- Graph assembly -----------------------------------------------------------

def build_graph():
    g = StateGraph(RoutingState)
    g.add_node("GREETING", greeting_node)
    g.add_node("INTENT_CLASSIFICATION", intent_node)
    g.add_node("SLOT_SELECTION", slot_node)
    g.add_node("BOOKING_CONFIRMATION", booking_node)

    g.set_entry_point("GREETING")
    g.add_edge("GREETING", "INTENT_CLASSIFICATION")
    g.add_conditional_edges("INTENT_CLASSIFICATION", _route_after_intent,
                            {"SLOT_SELECTION": "SLOT_SELECTION", "GREETING": "GREETING"})
    g.add_conditional_edges("SLOT_SELECTION", _route_after_slot,
                            {"BOOKING_CONFIRMATION": "BOOKING_CONFIRMATION", "DONE": END})
    g.add_conditional_edges("BOOKING_CONFIRMATION", _route_after_booking,
                            {"DONE": END, "SLOT_SELECTION": "SLOT_SELECTION"})
    return g


_checkpointer = MemorySaver()
_graph = build_graph().compile(checkpointer=_checkpointer)


def reset_state(user_id: str) -> None:
    """Reset the graph state for this user so a fresh session starts on next call."""
    cfg = {"configurable": {"thread_id": user_id}}
    _graph.update_state(cfg, RoutingState(user_id=user_id).model_dump())


def run_step(user_id: str, message: str | None, pending_event: dict | None) -> tuple[RoutingState, list[WSEvent]]:
    events: list[WSEvent] = []
    cfg = {"configurable": {"thread_id": user_id}}

    snapshot = _graph.get_state(cfg)
    if snapshot and snapshot.values and (snapshot.values.get("current_node") not in (None, "DONE")):
        state = RoutingState(**snapshot.values)
    else:
        state = RoutingState(user_id=user_id)

    logger.info(
        "run_step enter user=%s msg=%r pending=%s current_node=%s",
        user_id,
        (message[:60] + "...") if message and len(message) > 60 else message,
        pending_event.get("type") if pending_event else None,
        state.current_node,
    )

    if message:
        state.message_history.append({"role": "user", "content": message})
        _remember(user_id, "user", message, session_id=f"routing:{user_id}")
    state.pending_event = pending_event

    prev_node = ""
    prev_history_len = len(state.message_history)
    iterations = 0
    for _ in range(20):
        iterations += 1
        if state.current_node in ("DONE",):
            break
        if state.current_node == prev_node:
            logger.info("run_step break: same node twice user=%s node=%s", user_id, state.current_node)
            break
        prev_node = state.current_node
        node_fn = _NODE_FNS[state.current_node]
        logger.info("run_step invoking node user=%s node=%s", user_id, state.current_node)
        state = node_fn(state, events.append)
        logger.info(
            "run_step node done user=%s node=%s -> next=%s events=%d",
            user_id, prev_node, state.current_node, len(events),
        )
        if state.current_node == "DONE":
            break
        last_event = events[-1] if events else None
        if last_event and last_event.type == "slot_select":
            break
        if last_event and last_event.type == "text" and state.current_node != prev_node:
            if state.current_node in ("SLOT_SELECTION", "BOOKING_CONFIRMATION"):
                break

    logger.info(
        "run_step exit user=%s iters=%d final_node=%s events=%d",
        user_id, iterations, state.current_node, len(events),
    )

    for m in state.message_history[prev_history_len:]:
        if m["role"] == "assistant":
            _remember(user_id, "assistant", m["content"], session_id=f"routing:{user_id}")

    _graph.update_state(cfg, state.model_dump())
    return state, events


_NODE_FNS = {
    "GREETING": greeting_node,
    "INTENT_CLASSIFICATION": intent_node,
    "SLOT_SELECTION": slot_node,
    "BOOKING_CONFIRMATION": booking_node,
}
