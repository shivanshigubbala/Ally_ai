"""
Tests for the Neurology Consultation Controller.

These tests validate controller wiring and orchestration without calling
external services such as NVIDIA LLM, embeddings, or PGVector.
"""

import os

os.environ.setdefault("NVIDIA_API_KEY", "test-key")

from backend.neurology.models.session_state import NeurologyDoctorState
from backend.neurology.services.consultation_controller import (
    ConsultationController,
)


def create_state() -> NeurologyDoctorState:
    """Create a minimal valid NeurologyDoctorState."""

    return NeurologyDoctorState(
        user_id="user123",
        appointment_id="appt123",
        doctor_id="doctor123",
        department="Neurology",
    )


def create_complete_state() -> NeurologyDoctorState:
    """Create a NeurologyDoctorState with required information."""

    state = create_state()

    state.health_data = {
        "chief_complaint": "headache",
        "duration": "two days",
        "severity": "moderate",
        "symptoms": ["headache", "dizziness"],
    }

    return state


# ---------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------

def test_consultation_controller_import():
    """ConsultationController should import successfully."""

    controller = ConsultationController()

    assert controller is not None


# ---------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------

def test_consultation_controller_initialization():
    """ConsultationController should initialize dependencies."""

    controller = ConsultationController()

    assert hasattr(controller, "logger")
    assert hasattr(controller, "question_manager")
    assert hasattr(controller, "retriever")
    assert hasattr(controller, "llm_client")


# ---------------------------------------------------------------------
# Consultation Flow
# ---------------------------------------------------------------------

def test_handle_consultation_returns_state_and_response():
    """handle_consultation should return updated state and response text."""

    controller = ConsultationController()
    state = create_state()

    def process_turn(
        state: NeurologyDoctorState,
        user_message: str,
    ) -> NeurologyDoctorState:
        controller.question_manager.update_conversation_history(
            state,
            role="user",
            content=user_message,
        )
        controller.question_manager.increment_turn(state)
        controller.question_manager.increment_questions(state)
        return state

    controller.question_manager.process_turn = process_turn
    controller.question_manager.generate_followup_question = (
        lambda state: "Could you tell me more about your symptoms?"
    )

    updated_state, response = controller.handle_consultation(
        state,
        "I have had a headache for two days.",
    )

    assert isinstance(updated_state, NeurologyDoctorState)
    assert isinstance(response, str)
    assert len(response) > 0
    assert len(updated_state.conversation_history) == 1
    assert updated_state.conversation_history[0]["role"] == "user"
    assert controller.question_manager.validate_state(updated_state) is True


# ---------------------------------------------------------------------
# Decision Engine
# ---------------------------------------------------------------------

def test_determine_next_step_questioning():
    """Missing required information should continue questioning."""

    controller = ConsultationController()
    state = create_state()

    next_step = controller._determine_next_step(state)

    assert next_step == "QUESTIONING"


def test_determine_next_step_evaluation():
    """Complete required information should move to evaluation."""

    controller = ConsultationController()
    state = create_complete_state()

    next_step = controller._determine_next_step(state)

    assert next_step == "EVALUATION"


# ---------------------------------------------------------------------
# Prompt Generation
# ---------------------------------------------------------------------

def test_build_prompt_contains_user_message_and_context():
    """Prompt generation should include user message and medical context."""

    controller = ConsultationController()
    state = create_complete_state()
    state.conversation_history.append({
        "role": "user",
        "content": "I have had a headache for two days.",
    })

    medical_context = "Headache context from Neurology knowledge base."
    user_message = "I have had a headache for two days."

    system_prompt, user_prompt = controller._build_prompt(
        state=state,
        medical_context=medical_context,
        latest_user_message=user_message,
    )

    assert isinstance(system_prompt, str)
    assert isinstance(user_prompt, str)
    assert len(system_prompt) > 0
    assert len(user_prompt) > 0
    assert user_message in user_prompt
    assert medical_context in user_prompt
