from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from backend.specialties.base import BaseSpecialty
from backend.specialties.cardiology.state import CardiologyState

from backend.specialties.cardiology.extractor import (
    PatientInformationExtractor,
)

from backend.specialties.cardiology.question_manager import (
    QuestionManager,
)

from backend.specialties.cardiology.reasoning import (
    ClinicalReasoning,
)

try:
    from backend.general_physician.models.session_state import WSEvent
    from backend.general_physician.services import local_store as store
except ImportError:
    try:
        from general_physician.models.session_state import WSEvent
        from general_physician.services import local_store as store
    except ImportError:
        from models.session_state import WSEvent
        store = None


logger = logging.getLogger(__name__)
Emitter = Callable[[WSEvent], None]




# ---- Cardiology-specific state for LangGraph persistence ----

CardNode = Literal["SESSION_INIT", "QUESTIONING", "EVALUATION", "SESSION_COMPLETE"]


class CardState(BaseModel):
    """LangGraph state for Cardiology consultation, extending CardiologyState with persistence fields."""

    # Original CardiologyState fields
    patient_name: str = ""
    chief_complaint: str = ""
    symptoms: list[str] = Field(default_factory=list)
    duration: str = ""
    pain_location: str = ""
    pain_radiation: str = ""
    severity: str = ""
    associated_symptoms: list[str] = Field(default_factory=list)
    medical_history: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    smoking: bool = False
    diabetes: bool = False
    hypertension: bool = False
    family_history: bool = False
    questions_asked: list[str] = Field(default_factory=list)
    recommended_tests: list[str] = Field(default_factory=list)
    risk_level: str = "Unknown"
    emergency: bool = False
    consultation_complete: bool = False
    summary: str = ""

    # LangGraph persistence fields
    user_id: str = ""
    appointment_id: str = ""
    current_node: CardNode = "SESSION_INIT"
    conversation_history: list[dict[str, str]] = Field(default_factory=list)
    turn_count: int = 0
    doctor_id: str = "cardiology_doctor"
    doctor_name: str = "Dr. Cardiology"
    department: str = "cardiology"


class ConsultationController:

    def __init__(self):

        self.extractor = PatientInformationExtractor()

        self.question_manager = QuestionManager()

        self.reasoning = ClinicalReasoning()

    def process_message(
        self,
        state: CardiologyState,
        patient_message: str,
    ):

        # Step 1
        state = self.extractor.update_state(
            state,
            patient_message,
        )

        # Step 2
        next_question = self.question_manager.next_question(
            state
        )

        if next_question:

            return {
                "type": "question",
                "message": next_question,
                "state": state,
            }

        # Step 3

        result = self.reasoning.assess(
            state.symptoms,
        )

        state.risk_level = result["risk"]

        state.recommended_tests = result[
            "recommended_tests"
        ]

        state.consultation_complete = True

        return {
            "type": "consultation_complete",
            "result": result,
            "state": state,
        }


# ---- LangGraph node functions ----

def _card_session_init(state: CardState, emit: Emitter) -> CardState:
    """Initialize the cardiology consultation session."""
    if not state.chief_complaint:
        # Extract from first user message or use placeholder
        for m in state.conversation_history:
            if m.get("role") == "user" and m.get("content"):
                state.chief_complaint = m["content"].strip()
                break

    patient_name = state.patient_name or state.user_id.replace("_", " ").title()
    reply = (
        f"Hi {patient_name}, I'm {state.doctor_name}, your cardiology specialist. "
        "I'll review your heart-related symptoms and ask a few focused questions to help determine the best course of action."
    )

    emit(WSEvent(type="text", payload={"content": reply, "from": state.doctor_id}))
    state.conversation_history.append({"role": "assistant", "content": reply})
    state.current_node = "QUESTIONING"
    return state


def _card_questioning(state: CardState, emit: Emitter) -> CardState:
    """Process patient message and ask follow-up questions."""
    state.turn_count += 1

    # Get the last user message
    last_user_msg = ""
    if state.conversation_history and state.conversation_history[-1].get("role") == "user":
        last_user_msg = state.conversation_history[-1]["content"]

    # Use the controller to process the message
    controller = ConsultationController()

    # Create a temporary CardiologyState for the controller
    temp_state = CardiologyState()
    temp_state.patient_name = state.patient_name
    temp_state.chief_complaint = state.chief_complaint
    temp_state.symptoms = state.symptoms
    temp_state.duration = state.duration
    temp_state.pain_location = state.pain_location
    temp_state.pain_radiation = state.pain_radiation
    temp_state.severity = state.severity
    temp_state.associated_symptoms = state.associated_symptoms
    temp_state.medical_history = state.medical_history
    temp_state.medications = state.medications
    temp_state.allergies = state.allergies
    temp_state.smoking = state.smoking
    temp_state.diabetes = state.diabetes
    temp_state.hypertension = state.hypertension
    temp_state.family_history = state.family_history
    temp_state.questions_asked = state.questions_asked
    temp_state.recommended_tests = state.recommended_tests
    temp_state.risk_level = state.risk_level

    result = controller.process_message(temp_state, last_user_msg)

    # Update state from result
    state.symptoms = temp_state.symptoms
    state.duration = temp_state.duration
    state.pain_location = temp_state.pain_location
    state.pain_radiation = temp_state.pain_radiation
    state.severity = temp_state.severity
    state.associated_symptoms = temp_state.associated_symptoms
    state.medical_history = temp_state.medical_history
    state.medications = temp_state.medications
    state.allergies = temp_state.allergies
    state.smoking = temp_state.smoking
    state.diabetes = temp_state.diabetes
    state.hypertension = temp_state.hypertension
    state.family_history = temp_state.family_history
    state.questions_asked = temp_state.questions_asked
    state.recommended_tests = temp_state.recommended_tests
    state.risk_level = temp_state.risk_level

    if result["type"] == "question":
        # Emit the question and stay in QUESTIONING
        reply = result["message"]
        emit(WSEvent(type="text", payload={"content": reply, "from": state.doctor_id}))
        state.conversation_history.append({"role": "assistant", "content": reply})
        state.current_node = "QUESTIONING"
    else:  # consultation_complete
        # Move to evaluation
        state.consultation_complete = result.get("consultation_complete", True)
        state.current_node = "EVALUATION"

    return state


def _card_evaluation(state: CardState, emit: Emitter) -> CardState:
    """Emit evaluation summary and complete consultation."""
    summary = (
        f"Based on your symptoms, I've assessed your cardiovascular risk as {state.risk_level.upper()}. "
    )

    if state.recommended_tests:
        summary += f"I recommend the following tests: {', '.join(state.recommended_tests)}. "

    summary += "Please follow up with your primary care physician or a cardiologist as needed."

    emit(WSEvent(type="text", payload={"content": summary, "from": state.doctor_id}))
    state.conversation_history.append({"role": "assistant", "content": summary})
    state.summary = summary
    state.current_node = "SESSION_COMPLETE"
    return state


def _card_session_complete(state: CardState, emit: Emitter) -> CardState:
    """Mark session as complete."""
    state.consultation_complete = True
    return state


def _build_cardiology_graph() -> StateGraph:
    """Build the Cardiology consultation graph."""
    g = StateGraph(CardState)
    g.add_node("SESSION_INIT", _card_session_init)
    g.add_node("QUESTIONING", _card_questioning)
    g.add_node("EVALUATION", _card_evaluation)
    g.add_node("SESSION_COMPLETE", _card_session_complete)

    g.set_entry_point("SESSION_INIT")
    g.add_edge("SESSION_INIT", "QUESTIONING")

    # Conditional: QUESTIONING -> (QUESTIONING | EVALUATION)
    def _after_questioning(state: CardState) -> str:
        if state.current_node == "EVALUATION":
            return "EVALUATION"
        return "QUESTIONING"

    g.add_conditional_edges("QUESTIONING", _after_questioning, {
        "EVALUATION": "EVALUATION",
        "QUESTIONING": "QUESTIONING"
    })

    g.add_edge("EVALUATION", "SESSION_COMPLETE")
    g.add_edge("SESSION_COMPLETE", END)

    return g


_cardiology_checkpointer = MemorySaver()
_cardiology_graph = _build_cardiology_graph().compile(checkpointer=_cardiology_checkpointer)


def step(
    user_id: str,
    appointment_id: str,
    user_message: str | None,
    pending_event: dict | None,
) -> tuple[CardState, list[WSEvent]]:
    """Run one step of the cardiology consultation."""
    events: list[WSEvent] = []
    cfg = {"configurable": {"thread_id": f"card:{user_id}:{appointment_id}"}}

    snap = _cardiology_graph.get_state(cfg)
    if snap and snap.values:
        state = CardState(**snap.values)
    else:
        # Initialize fresh state
        doctor_id = "cardiology_doctor"
        doctor_name = "Dr. Ally"
        patient_name = None

        # Try to get appointment details from store
        if store:
            try:
                apt = store.get_appointment(appointment_id)
                if apt:
                    patient_name = apt.get("patient") or None
            except Exception:
                pass

        state = CardState(
            user_id=user_id,
            appointment_id=appointment_id,
            doctor_id=doctor_id,
            doctor_name=doctor_name,
            patient_name=patient_name or "",
            department="cardiology",
        )

    # Add user message to conversation history if provided
    if user_message:
        state.conversation_history.append({"role": "user", "content": user_message})

    if pending_event:
        # Not used in basic cardiology, but accepted for interface compatibility
        pass

    # Run the graph until it reaches a stopping point
    prev_len = len(state.conversation_history)
    for _ in range(20):
        if state.current_node == "SESSION_COMPLETE":
            break

        node_fn_map = {
            "SESSION_INIT": _card_session_init,
            "QUESTIONING": _card_questioning,
            "EVALUATION": _card_evaluation,
            "SESSION_COMPLETE": _card_session_complete,
        }

        node_fn = node_fn_map.get(state.current_node)
        if not node_fn:
            break

        state = node_fn(state, events.append)

        # Stop at interactive nodes
        if state.current_node in {"QUESTIONING", "EVALUATION"}:
            break

    # Persist state
    _cardiology_graph.update_state(cfg, state.model_dump())

    return state, events


class CardiologySpecialty(BaseSpecialty):
    """Adapter that lets the existing cardiology controller participate in the shared specialty framework."""

    department = "cardiology"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__()
        self._controller = ConsultationController()
        self._kwargs = kwargs

    def initialize_consultation(self, patient_id: str | None = None, appointment_id: str | None = None, **kwargs: Any) -> CardState:
        state = CardState(
            user_id=patient_id or "",
            appointment_id=appointment_id or "",
            patient_name=kwargs.get("patient_name") or "",
            doctor_id="cardiology_doctor",
            doctor_name="Dr. Ally",
            department="cardiology",
        )
        return state

    def load_consultation_context(self, appointment_id: str | None = None, **kwargs: Any) -> Any:
        return kwargs.get("consultation_context") or None

    def load_patient_history(self, patient_id: str | None = None, **kwargs: Any) -> list[dict[str, Any]]:
        return kwargs.get("patient_history") or []

    def load_patient_documents(self, patient_id: str | None = None, appointment_id: str | None = None, **kwargs: Any) -> list[dict[str, Any]]:
        return kwargs.get("patient_documents") or []

    def run_consultation(self, user_id: str, appointment_id: str, user_message: str | None = None, pending_event: dict | None = None, **kwargs: Any) -> tuple[CardState, list[WSEvent]]:
        """Run the cardiology consultation using the step function."""
        return step(user_id, appointment_id, user_message, pending_event)

    def generate_summary(self, state: Any, **kwargs: Any) -> dict[str, Any]:
        return {
            "summary": getattr(state, "summary", ""),
            "risk_level": getattr(state, "risk_level", "Unknown"),
            "recommended_tests": getattr(state, "recommended_tests", []),
            "consultation_complete": getattr(state, "consultation_complete", False),
        }

    def recommend_labs(self, state: Any, **kwargs: Any) -> list[dict[str, Any]]:
        tests = getattr(state, "recommended_tests", []) or []
        return [{"name": test, "reason": "Cardiology assessment"} for test in tests]

    def complete_consultation(self, state: Any, **kwargs: Any) -> dict[str, Any]:
        return {
            "status": "COMPLETED" if getattr(state, "consultation_complete", False) else "IN_PROGRESS",
            "summary": self.generate_summary(state),
            "recommendations": self.recommend_labs(state),
        }
