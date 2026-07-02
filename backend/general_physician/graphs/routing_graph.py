from __future__ import annotations

import logging
import re
from typing import Any, Callable

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

try:
    from backend.general_physician.db.pgvector_tracker import save_message
    from backend.general_physician.llm.nvidia_client import chat as nv_chat, ROUTING_MODEL
    from backend.general_physician.models.session_state import RoutingState, WSEvent
    from backend.general_physician.services import local_store as store
except ImportError:
    from db.pgvector_tracker import save_message
    from llm.nvidia_client import chat as nv_chat, ROUTING_MODEL
    from models.session_state import RoutingState, WSEvent
    from services import local_store as store


Emitter = Callable[[WSEvent], None]

logger = logging.getLogger(__name__)

from backend.general_physician.config import get_default_doctor_id, get_default_doctor_name

GP_DOCTOR_ID = get_default_doctor_id()
GP_DOCTOR_NAME = get_default_doctor_name()


def _extract_patient_name(text: str) -> str | None:
    # Accept names with hyphens, apostrophes and up to 4 words; be permissive for international letters
    patterns = [
        r"\bmy name is\s+([A-Za-zÀ-ÖØ-öø-ÿ'’\-]+(?:\s+[A-Za-zÀ-ÖØ-öø-ÿ'’\-]+){0,4})\b",
        r"\bi\s+am\s+([A-Za-zÀ-ÖØ-öø-ÿ'’\-]+(?:\s+[A-Za-zÀ-ÖØ-öø-ÿ'’\-]+){0,4})\b",
        r"\bi'm\s+([A-Za-zÀ-ÖØ-öø-ÿ'’\-]+(?:\s+[A-Za-zÀ-ÖØ-öø-ÿ'’\-]+){0,4})\b",
        r"\bcall me\s+([A-Za-zÀ-ÖØ-öø-ÿ'’\-]+(?:\s+[A-Za-zÀ-ÖØ-öø-ÿ'’\-]+){0,4})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip(" .")
            if name.lower() not in {"a", "an", "the"}:
                return name or None
    return None


def _extract_patient_id(text: str) -> str | None:
    # Match multiple id phrasings like "patient id is 42", "ID:42", "my id is 42"
    patterns = [
        r"\b(?:patient\s+)?id(?:entifier)?\s*(?:is|=|:)?\s*([0-9A-Za-z-]+)\b",
        r"\bID[:#]?\s*([0-9A-Za-z-]+)\b",
        r"\bmy\s+id\s*(?:is|=|:)?\s*([0-9A-Za-z-]+)\b",
    ]
    for p in patterns:
        match = re.search(p, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _extract_current_complaint(text: str) -> str:
    # Try to capture the primary complaint; stop at common conjunctions to avoid greediness
    match = re.search(r"(?:have|having|feel|feeling|need help with|suffering from|complain(?:ing)? of)\s+(.+)$", text, re.IGNORECASE)
    if match:
        complaint = match.group(1).strip(" ,.;:-")
        # split on ' and ' or ' but ' to avoid long trailing clauses
        complaint = re.split(r"\s+\band\b|\s+\bbut\b|\s+\bor\b", complaint, flags=re.IGNORECASE)[0]
        return complaint.strip()
    # fallback: use the whole text but trim after conjunctions
    t = text.strip(" ,.;:-")
    t = re.split(r"\s+\band\b|\s+\bbut\b|\s+\bor\b", t, flags=re.IGNORECASE)[0]
    return t.strip()


def _update_patient_intake(state: RoutingState, text: str | None) -> None:
    if not text:
        return

    lowered = text.lower()
    if not state.patient_name:
        name = _extract_patient_name(text)
        if name:
            state.patient_name = name
    if not state.patient_id:
        patient_id = _extract_patient_id(text)
        if patient_id:
            state.patient_id = patient_id
    if any(phrase in lowered for phrase in ["returning patient", "existing patient", "returning", "already a patient"]):
        state.returning_patient = True
    if not state.current_complaint:
        complaint = _extract_current_complaint(text)
        if complaint:
            state.current_complaint = complaint
    if not state.patient_name:
        state.patient_name = (state.user_id or "there").replace("_", " ").title()
    elif state.patient_name == (state.user_id or "there").replace("_", " ").title():
        state.patient_name = state.patient_name


def _remember(user_id: str, role: str, content: str, session_id: str | None = None) -> None:
    """Persist a single turn to the pgvector messages table (best-effort)."""
    try:
        save_message(user_id=user_id, role=role, content=content, session_id=session_id)
    except Exception:
        pass  # Postgres down or schema missing - never break the chat.


def _llm_reply(system: str, user: str) -> str:
    try:
        return nv_chat([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ], model=ROUTING_MODEL).strip()
    except Exception as exc:
        logger.warning("Routing LLM fallback: %s", exc)
        if user.startswith("Patient said:"):
            return (
                "Thank you for telling me that. I can help you book an appointment "
                "with Dr. Shankar right away."
            )
        if user.startswith("Confirming slot"):
            return "So I've got you down for that slot. Does that sound good to you?"
        if user == "Patient cancelled.":
            return "I understand. If you'd like to book another time, just let me know."
        if user.startswith("Appointment") and "confirmed" in user:
            return "Your appointment is confirmed! Dr. Shankar is ready to see you in the Appointments tab."
        if user == "Transitioning to doctor.":
            return "Dr. Shankar is ready for you in the Appointments tab."
        return "Okay, let me take care of that for you."


RECEPTIONIST_PERSONA = (
    "You are Ally, a warm, caring human receptionist at Ally Hospital. "
    "You speak like a real person - naturally, with empathy and warmth. "
    "You NEVER sound robotic or scripted. You use casual, conversational language. "
    "Short responses (1-3 sentences). No bullet points, no markdown, no lists."
)


def greeting_node(state: RoutingState, emit: Emitter) -> RoutingState:
    if state.message_history and state.message_history[-1]["role"] == "assistant":
        return state
    if state.message_history and state.message_history[-1]["role"] == "user":
        state.current_node = "INTENT_CLASSIFICATION"
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

    state.selected_dept = "general"
    if state.symptom_round == 0:
        reply = _llm_reply(
            RECEPTIONIST_PERSONA + (
                "The patient shared their concern clearly. Acknowledge it warmly and let them know "
                "you can help them choose a doctor and a time. No bullet points, no lists."
            ),
            f"Patient said: {last_user}",
        )
        emit(WSEvent(type="text", payload={"content": reply}))
        state.message_history.append({"role": "assistant", "content": reply})
        state.symptom_round = 1

        # Check if user immediately wants appointment (skip health questions)
        if any(keyword in last_user.lower() for keyword in ["appointment", "book", "doctor", "now", "asap", "urgent"]):
            state.skip_health_questions = True
            doctors = store.list_doctors(state.selected_dept)
            if doctors:
                emit(WSEvent(type="doctor_select", payload={
                    "options": doctors,
                    "department_id": state.selected_dept,
                }))
                state.current_node = "DOCTOR_SELECTION"
            else:
                emit(WSEvent(type="text", payload={"content": "I'm sorry, there are no doctors available right now. Please try again later."}))
                state.current_node = "DONE"
        else:
            state.current_node = "HEALTH_STATUS_QUESTIONS"
        return state

    if state.symptom_round == 1:
        reply = _llm_reply(
            RECEPTIONIST_PERSONA + (
                "The patient has already described their main symptom. Acknowledge that briefly, "
                "then ask another short follow-up about timing, severity, triggers, or whether anything "
                "has changed. Use a different angle than the prior question."
            ),
            f"Patient said: {last_user}",
        )
        emit(WSEvent(type="text", payload={"content": reply}))
        state.message_history.append({"role": "assistant", "content": reply})
        state.symptom_round = 2
        return state

    if state.symptom_round == 2:
        reply = _llm_reply(
            RECEPTIONIST_PERSONA + (
                "You've got a few follow-up details now. Acknowledge what they said warmly, then ask one more "
                "brief, specific question about location, intensity, swelling, or other symptoms before moving "
                "toward booking. No bullet points, no lists."
            ),
            f"Patient said: {last_user}",
        )
        emit(WSEvent(type="text", payload={"content": reply}))
        state.message_history.append({"role": "assistant", "content": reply})
        state.symptom_round = 3
        return state

    reply = _llm_reply(
        RECEPTIONIST_PERSONA + (
            "The patient has now shared several follow-up details. Acknowledge that warmly, then say you're "
            "going to help them choose a doctor and a time. No bullet points, no lists."
        ),
        f"Patient said: {last_user}",
    )
    emit(WSEvent(type="text", payload={"content": reply}))
    state.message_history.append({"role": "assistant", "content": reply})

    doctors = store.list_doctors(state.selected_dept)
    if doctors:
        emit(WSEvent(type="doctor_select", payload={
            "options": doctors,
            "department_id": state.selected_dept,
        }))
        state.current_node = "DOCTOR_SELECTION"
    else:
        emit(WSEvent(type="text", payload={"content": "I'm sorry, there are no doctors available right now. Please try again later."}))
        state.current_node = "DONE"
    return state


def health_status_questions_node(state: RoutingState, emit: Emitter) -> RoutingState:
    """Ask 2-3 health status questions before routing to doctor selection."""
    last_user = ""
    for m in reversed(state.message_history):
        if m["role"] == "user":
            last_user = m["content"]
            break
    
    if not last_user:
        return state

    # Ask 2-3 quick health status questions
    if state.health_question_round == 0:
        reply = _llm_reply(
            RECEPTIONIST_PERSONA + (
                "The patient is about to see a doctor. Ask one quick health question about their current status "
                "(e.g., any fever, difficulty breathing, or pain level?). Keep it brief and empathetic."
            ),
            f"Patient said: {last_user}",
        )
        emit(WSEvent(type="text", payload={"content": reply}))
        state.message_history.append({"role": "assistant", "content": reply})
        state.health_question_round = 1
        return state

    if state.health_question_round == 1:
        reply = _llm_reply(
            RECEPTIONIST_PERSONA + (
                "Ask a second quick health status question about their symptoms or medical background "
                "(e.g., any recent medications, allergies, or past surgeries?). Keep it brief."
            ),
            f"Patient said: {last_user}",
        )
        emit(WSEvent(type="text", payload={"content": reply}))
        state.message_history.append({"role": "assistant", "content": reply})
        state.health_question_round = 2
        return state

    if state.health_question_round == 2:
        reply = _llm_reply(
            RECEPTIONIST_PERSONA + (
                "Ask one final quick health question to get a complete picture before booking. "
                "Keep it brief, empathetic, and then tell the patient you'll help them choose a doctor."
            ),
            f"Patient said: {last_user}",
        )
        emit(WSEvent(type="text", payload={"content": reply}))
        state.message_history.append({"role": "assistant", "content": reply})
        state.health_question_round = 3

        doctors = store.list_doctors(state.selected_dept)
        if doctors:
            emit(WSEvent(type="doctor_select", payload={
                "options": doctors,
                "department_id": state.selected_dept,
            }))
            state.current_node = "DOCTOR_SELECTION"
        else:
            emit(WSEvent(type="text", payload={"content": "I'm sorry, there are no doctors available right now. Please try again later."}))
            state.current_node = "DONE"
        return state

    doctors = store.list_doctors(state.selected_dept)
    if doctors:
        emit(WSEvent(type="doctor_select", payload={
            "options": doctors,
            "department_id": state.selected_dept,
        }))
        state.current_node = "DOCTOR_SELECTION"
    else:
        emit(WSEvent(type="text", payload={"content": "I'm sorry, there are no doctors available right now. Please try again later."}))
        state.current_node = "DONE"
    return state


def doctor_selection_node(state: RoutingState, emit: Emitter) -> RoutingState:
    pending = state.pending_event or {}
    state.pending_event = None
    doctors = store.list_doctors(state.selected_dept or "general")
    for d in doctors:
        try:
            # derive availability from whether the doctor has any free slots
            slots = store.list_slots(d.get("id"))
            d["available"] = bool(slots)
        except Exception:
            # If store fails, fall back to marking doctor available to avoid blocking
            d["available"] = True

    if pending.get("type") == "select":
        selected_doctor = pending.get("payload", {}).get("id") or pending.get("payload", {}).get("doctor_id")
        if selected_doctor:
            state.selected_doctor = selected_doctor
        else:
            state.selected_doctor = state.selected_doctor or GP_DOCTOR_ID
    else:
        state.selected_doctor = state.selected_doctor or GP_DOCTOR_ID

    chosen = next((d for d in doctors if d["id"] == state.selected_doctor), None)
    if chosen and not chosen.get("available", True):
        emit(WSEvent(type="text", payload={"content": "I'm sorry, that doctor isn't available right now. Let's book with Dr. Shankar, who is available."}))
        state.selected_doctor = GP_DOCTOR_ID

    if not any(d["id"] == state.selected_doctor for d in doctors):
        state.selected_doctor = next((d["id"] for d in doctors if d.get("available", False)), GP_DOCTOR_ID)

    slots = store.list_slots(state.selected_doctor or GP_DOCTOR_ID)
    if slots:
        doc_name = next((d["name"] for d in doctors if d["id"] == state.selected_doctor), GP_DOCTOR_NAME)
        emit(WSEvent(type="slot_select", payload={
            "options": slots,
            "doctor_id": state.selected_doctor or GP_DOCTOR_ID,
            "doctor_name": doc_name,
        }))
        state.current_node = "SLOT_SELECTION"
    else:
        emit(WSEvent(type="text", payload={"content": "I'm sorry, there are no available slots for that doctor right now. Please try again later."}))
        state.current_node = "DONE"
    return state


def slot_node(state: RoutingState, emit: Emitter) -> RoutingState:
    pending = state.pending_event or {}
    state.pending_event = None

    if pending.get("type") == "select" and pending.get("payload", {}).get("target") == "slot":
        state.selected_slot = pending["payload"].get("id")
    elif pending.get("type") == "select":
        state.selected_slot = pending["payload"].get("id", "")
    else:
        slots = store.list_slots(state.selected_doctor or GP_DOCTOR_ID)
        doc_name = GP_DOCTOR_NAME
        emit(WSEvent(type="text", payload={
            "content": f"I understand. When you're ready, please pick a slot from the available times with {doc_name}."
        }))
        emit(WSEvent(type="slot_select", payload={
            "options": slots,
            "doctor_id": state.selected_doctor or GP_DOCTOR_ID,
        }))
        return state

    slots = store.list_slots(state.selected_doctor or GP_DOCTOR_ID)
    chosen = next((s for s in slots if s["id"] == state.selected_slot), None)
    if not chosen:
        emit(WSEvent(type="text", payload={"content": "That doesn't match any available slot. Please pick one from the list below."}))
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
            f"The patient selected {nice_time} with Dr. Shankar. "
            "Ask them to confirm the booking in one short, warm sentence."
        ),
        f"Confirming slot {chosen['id']} at {nice_time}.",
    )
    emit(WSEvent(type="text", payload={"content": reply}))
    state.message_history.append({"role": "assistant", "content": reply})
    state.current_node = "BOOKING_CONFIRMATION"
    return state

def booking_node(state: RoutingState, emit: Emitter) -> RoutingState:
    last_user = ""
    for m in reversed(state.message_history):
        if m["role"] == "user":
            last_user = m["content"].lower().strip()
            break

    # Use word-boundary regexes to avoid substring false positives and detect common confirmations/cancellations
    cancelled = bool(re.search(r"\b(cancel|cancelled|nope|never|abort|stop)\b", last_user))
    # Confirm phrases - ensure we don't pick up 'not sure' by checking 'not' proximity
    confirmed = bool(re.search(r"\b(confirm|confirmed|yes|yep|yeah|sure|ok|okay)\b", last_user))
    # Also consider explicit selection phrases
    if not confirmed and any(phrase in last_user for phrase in ("selected a time slot", "selected a slot", "i'll take that", "i will take that")):
        confirmed = True
    # If 'not' appears near a confirmation (e.g., 'not sure', 'not confirmed'), treat as not confirmed
    if confirmed and re.search(r"\bnot\b\s+\b(confirm|sure|yes)\b", last_user):
        confirmed = False

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

    # Re-verify that the selected slot still exists and is available to avoid races
    slots = store.list_slots(state.selected_doctor or GP_DOCTOR_ID)
    chosen = next((s for s in slots if s["id"] == state.selected_slot), None)
    if not chosen:
        emit(WSEvent(type="text", payload={"content": "That slot is no longer available — please pick another from the list."}))
        emit(WSEvent(type="slot_select", payload={"options": slots, "doctor_id": state.selected_doctor}))
        state.current_node = "SLOT_SELECTION"
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
            "Congratulate the patient warmly and tell them Dr. Shankar is ready "
            "to see them in the Appointments tab. No bullet points, no lists."
        ),
        f"Appointment {state.appointment_id} confirmed.",
    )
    emit(WSEvent(type="text", payload={"content": reply}))
    state.message_history.append({"role": "assistant", "content": f"Appointment {state.appointment_id} confirmed."})

    emit(WSEvent(type="doctor_ready", payload={
        "appointment_id": state.appointment_id,
        "doctor_id": state.selected_doctor or GP_DOCTOR_ID,
        "doctor_name": GP_DOCTOR_NAME,
    }))
    state.current_node = "DONE"
    return state


# ---- Edge routing -------------------------------------------------------------

def _route_after_intent(state: RoutingState) -> str:
    if not state.selected_dept:
        return "GREETING"
    return "DOCTOR_SELECTION" if state.skip_health_questions else "HEALTH_STATUS_QUESTIONS"


def _route_after_health_questions(state: RoutingState) -> str:
    return "DOCTOR_SELECTION" if state.current_node == "DOCTOR_SELECTION" else "HEALTH_STATUS_QUESTIONS"


def _route_after_doctor_selection(state: RoutingState) -> str:
    return "SLOT_SELECTION" if state.current_node == "SLOT_SELECTION" else "GREETING"


def _route_after_slot(state: RoutingState) -> str:
    return "BOOKING_CONFIRMATION" if state.selected_slot else "DONE"


def _route_after_booking(state: RoutingState) -> str:
    return "DONE" if state.current_node == "DONE" else "SLOT_SELECTION"


# ---- Graph assembly -----------------------------------------------------------

def build_graph():
    g = StateGraph(RoutingState)
    g.add_node("GREETING", greeting_node)
    g.add_node("INTENT_CLASSIFICATION", intent_node)
    g.add_node("HEALTH_STATUS_QUESTIONS", health_status_questions_node)
    g.add_node("DOCTOR_SELECTION", doctor_selection_node)
    g.add_node("SLOT_SELECTION", slot_node)
    g.add_node("BOOKING_CONFIRMATION", booking_node)

    g.set_entry_point("GREETING")
    g.add_edge("GREETING", "INTENT_CLASSIFICATION")
    g.add_conditional_edges("INTENT_CLASSIFICATION", _route_after_intent,
                            {"DOCTOR_SELECTION": "DOCTOR_SELECTION", "HEALTH_STATUS_QUESTIONS": "HEALTH_STATUS_QUESTIONS", "GREETING": "GREETING"})
    g.add_conditional_edges("HEALTH_STATUS_QUESTIONS", _route_after_health_questions,
                            {"DOCTOR_SELECTION": "DOCTOR_SELECTION", "HEALTH_STATUS_QUESTIONS": "HEALTH_STATUS_QUESTIONS"})
    g.add_conditional_edges("DOCTOR_SELECTION", _route_after_doctor_selection,
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
        _update_patient_intake(state, message)
        state.message_history.append({"role": "user", "content": message})
        _remember(user_id, "user", message, session_id=f"routing:{user_id}")
    state.pending_event = pending_event

    prev_history_len = len(state.message_history)
    iterations = 0
    for _ in range(20):
        iterations += 1
        if state.current_node in ("DONE",):
            break
        node_fn = _NODE_FNS[state.current_node]
        logger.info("run_step invoking node user=%s node=%s", user_id, state.current_node)
        state = node_fn(state, events.append)
        logger.info(
            "run_step node done user=%s node=%s -> next=%s events=%d",
            user_id, state.current_node, state.current_node, len(events),
        )
        if state.current_node == "DONE":
            break
        last_event = events[-1] if events else None
        if last_event and last_event.type in {"doctor_select", "slot_select"}:
            break
        if last_event and last_event.type == "text":
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
    "HEALTH_STATUS_QUESTIONS": health_status_questions_node,
    "DOCTOR_SELECTION": doctor_selection_node,
    "SLOT_SELECTION": slot_node,
    "BOOKING_CONFIRMATION": booking_node,
}

