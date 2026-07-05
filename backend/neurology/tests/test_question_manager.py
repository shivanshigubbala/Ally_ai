"""
Tests for the Neurology Question Manager.

These tests validate the basic behaviour of the Question Manager
without calling external services such as NVIDIA LLM or RAG.

More advanced integration tests will be added later.
"""

from backend.neurology.models.session_state import NeurologyDoctorState
from backend.neurology.services.question_manager import QuestionManager


def create_state() -> NeurologyDoctorState:
    """Create a minimal valid NeurologyDoctorState."""

    return NeurologyDoctorState(
        user_id="user123",
        appointment_id="appt123",
        doctor_id="doctor123",
        department="Neurology",
    )


# ---------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------

def test_question_manager_import():
    """QuestionManager should import successfully."""

    qm = QuestionManager()

    assert qm is not None


# ---------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------

def test_question_manager_initialization():
    """QuestionManager should initialize correctly."""

    qm = QuestionManager()

    assert hasattr(qm, "logger")
    assert hasattr(qm, "patient_information_extractor")


# ---------------------------------------------------------------------
# State Validation
# ---------------------------------------------------------------------

def test_validate_state():
    """State validation should accept a valid state."""

    qm = QuestionManager()

    state = create_state()

    assert qm.validate_state(state) is True


# ---------------------------------------------------------------------
# Missing Fields
# ---------------------------------------------------------------------

def test_get_missing_fields():
    """Missing fields should be detected."""

    qm = QuestionManager()

    state = create_state()

    missing = qm.get_missing_fields(state)

    assert isinstance(missing, list)


# ---------------------------------------------------------------------
# Required Information
# ---------------------------------------------------------------------

def test_has_required_information_false():
    """Fresh state should not contain enough information."""

    qm = QuestionManager()

    state = create_state()

    assert qm.has_required_information(state) is False


# ---------------------------------------------------------------------
# Evaluation Readiness
# ---------------------------------------------------------------------

def test_ready_for_evaluation_false():
    """Fresh consultation should not be ready for evaluation."""

    qm = QuestionManager()

    state = create_state()

    assert qm.is_ready_for_evaluation(state) is False


# ---------------------------------------------------------------------
# Conversation Update
# ---------------------------------------------------------------------

def test_update_conversation_history():
    """Conversation history should be updated."""

    qm = QuestionManager()

    state = create_state()

    qm.update_conversation_history(
        state,
        role="user",
        content="I have a headache.",
    )

    assert len(state.conversation_history) == 1

    assert state.conversation_history[0]["role"] == "user"

    assert state.conversation_history[0]["content"] == "I have a headache."


# ---------------------------------------------------------------------
# Turn Counter
# ---------------------------------------------------------------------

def test_increment_turn():
    """Turn counter should increment."""

    qm = QuestionManager()

    state = create_state()

    previous = state.turn_count

    qm.increment_turn(state)

    assert state.turn_count == previous + 1


# ---------------------------------------------------------------------
# Question Counter
# ---------------------------------------------------------------------

def test_increment_questions():
    """Question counter should increment."""

    qm = QuestionManager()

    state = create_state()

    previous = state.questions_asked

    qm.increment_questions(state)

    assert state.questions_asked == previous + 1


# ---------------------------------------------------------------------
# Next Action
# ---------------------------------------------------------------------

def test_determine_next_action():
    """QuestionManager should return a valid workflow action."""

    qm = QuestionManager()

    state = create_state()

    action = qm.determine_next_action(state)

    assert action in (
        "QUESTIONING",
        "READY_FOR_EVALUATION",
        "EMERGENCY",
    )


# ---------------------------------------------------------------------
# Process Turn
# ---------------------------------------------------------------------

def test_process_turn_returns_state():
    """Processing a turn should always return NeurologyDoctorState."""

    qm = QuestionManager()

    state = create_state()

    updated = qm.process_turn(
        state,
        "I have had a headache for two days.",
    )

    assert isinstance(updated, NeurologyDoctorState)
