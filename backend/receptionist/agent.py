import json
import logging
import re
from typing import Any, Tuple

from backend.models.session_state import WSEvent
from backend.llm.nvidia_client import chat as nv_chat, ROUTING_MODEL
from backend.services import local_store as store
from backend.shared import appointment_client as appointment_client

logger = logging.getLogger(__name__)

# Temporary in-memory state store for the simple receptionist
_states = {}

class SimpleRoutingState:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.message_history = []
        self.current_node = "GREETING"
        self.selected_dept = None
        self.selected_doctor = None
        self.selected_slot = None
        self.appointment_id = None
        self.patient_name = user_id.replace("_", " ").title()

RECEPTIONIST_PERSONA = (
    "You are Ally, a warm, caring human receptionist at Ally Hospital. "
    "You speak like a real person - naturally, with empathy and warmth. "
    "You NEVER sound robotic or scripted. You use casual, conversational language. "
    "Short responses (1-3 sentences). No bullet points, no markdown, no lists."
)

def _llm_reply(system: str, user: str) -> str:
    try:
        return nv_chat([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ], model=ROUTING_MODEL).strip()
    except Exception as exc:
        logger.warning("Routing LLM fallback: %s", exc)
        return "Okay, let me help you with that."

def run_step(user_id: str, message: str | None, pending_event: dict | None) -> Tuple[Any, list[WSEvent]]:
    if user_id not in _states:
        _states[user_id] = SimpleRoutingState(user_id)
    
    state = _states[user_id]
    events = []

    if message:
        state.message_history.append({"role": "user", "content": message})

    # State Machine
    if state.current_node == "GREETING":
        reply = f"Hi {state.patient_name}! I'm Ally, here at Ally Hospital. How are you feeling today, and what brings you in?"
        events.append(WSEvent(type="text", payload={"content": reply}))
        state.message_history.append({"role": "assistant", "content": reply})
        state.current_node = "INTENT"
        return state, events

    elif state.current_node == "INTENT":
        if not message:
            return state, events
        
        # Simple keyword based routing
        lower_msg = message.lower()
        if any(k in lower_msg for k in ["heart", "chest", "palpitation"]):
            state.selected_dept = "cardiology"
        elif any(k in lower_msg for k in ["headache", "brain", "seizure", "numbness"]):
            state.selected_dept = "neurology"
        else:
            state.selected_dept = "general"

        reply = _llm_reply(
            RECEPTIONIST_PERSONA + f" The patient shared their concern. Warmly acknowledge it and say you will help them book an appointment with our {state.selected_dept} department.",
            f"Patient said: {message}"
        )
        events.append(WSEvent(type="text", payload={"content": reply}))
        state.message_history.append({"role": "assistant", "content": reply})
        
        # Go to doctor selection
        doctors = store.list_doctors(state.selected_dept) or store.list_doctors("general")
        events.append(WSEvent(type="doctor_select", payload={
            "options": doctors,
            "department_id": state.selected_dept,
            "recommended_department": state.selected_dept
        }))
        state.current_node = "DOCTOR_SELECTION"
        return state, events

    elif state.current_node == "DOCTOR_SELECTION":
        if pending_event and pending_event.get("type") == "select":
            payload = pending_event.get("payload", {})
            state.selected_doctor = payload.get("id") or payload.get("doctor_id")
        
        if not state.selected_doctor:
            state.selected_doctor = "d5" # fallback to GP
            
        slots = store.list_slots(state.selected_doctor)
        events.append(WSEvent(type="slot_select", payload={
            "options": slots,
            "doctor_id": state.selected_doctor
        }))
        state.current_node = "SLOT_SELECTION"
        return state, events

    elif state.current_node == "SLOT_SELECTION":
        if pending_event and pending_event.get("type") == "select":
            state.selected_slot = pending_event.get("payload", {}).get("id")
        
        if state.selected_slot:
            reply = "Great! Should I go ahead and confirm that time slot for you?"
            events.append(WSEvent(type="text", payload={"content": reply}))
            state.message_history.append({"role": "assistant", "content": reply})
            state.current_node = "BOOKING"
        else:
            events.append(WSEvent(type="text", payload={"content": "Please select a slot."}))
        return state, events

    elif state.current_node == "BOOKING":
        lower_msg = (message or "").lower()
        if "yes" in lower_msg or "confirm" in lower_msg or "sure" in lower_msg or "ok" in lower_msg:
            # Try to book using the store (local in-memory or appointment service wrapper).
            try:
                status, body = store.book_appointment(
                    doctor_id=state.selected_doctor,
                    slot_id=state.selected_slot,
                    patient=state.patient_name or state.user_id,
                    reason=state.current_complaint or "",
                    department=state.selected_dept,
                )
                if status >= 200 and status < 300:
                    _raw_id = body.get("id")
                    state.appointment_id = str(_raw_id) if _raw_id is not None else None
                    doctor_name = next((d["name"] for d in store.list_doctors(state.selected_dept) if d["id"] == state.selected_doctor), "Doctor")
                    reply = _llm_reply(
                        RECEPTIONIST_PERSONA + f" The appointment is confirmed! Appointment ID: {state.appointment_id}. Congratulate the patient warmly and tell them {doctor_name} is ready to see them in the Appointments tab.",
                        f"Appointment {state.appointment_id} confirmed.",
                    )
                    events.append(WSEvent(type="text", payload={"content": reply}))
                    state.message_history.append({"role": "assistant", "content": reply})
                    events.append(WSEvent(type="doctor_ready", payload={
                        "appointment_id": state.appointment_id,
                        "doctor_id": state.selected_doctor,
                        "doctor_name": doctor_name,
                        "department": state.selected_dept,
                        "consultation_status": "CREATED",
                    }))
                else:
                    # Booking failed - inform user
                    err = body.get("error") if isinstance(body, dict) else str(body)
                    reply = f"Sorry, I couldn't book that slot: {err}. Please try another time." 
                    events.append(WSEvent(type="text", payload={"content": reply}))
                    state.message_history.append({"role": "assistant", "content": reply})
            except Exception as exc:
                logger.exception("Booking failed: %s", exc)
                reply = "Sorry, I couldn't complete the booking due to a server error. Please try again later."
                events.append(WSEvent(type="text", payload={"content": reply}))
                state.message_history.append({"role": "assistant", "content": reply})
            state.current_node = "DONE"
        else:
            events.append(WSEvent(type="text", payload={"content": "Booking cancelled or not confirmed."}))
            state.current_node = "DONE"
        return state, events

    return state, events

def has_in_progress_booking(user_id: str) -> bool:
    if user_id not in _states:
        return False
    return _states[user_id].current_node not in ("GREETING", "DONE")

def reset_state(user_id: str) -> None:
    if user_id in _states:
        del _states[user_id]
