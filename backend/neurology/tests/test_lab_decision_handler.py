"""
Tests for the Neurology Lab Decision Handler.

These tests validate patient responses to recommended tests without calling
external services such as NVIDIA LLM, embeddings, PGVector, or laboratory APIs.
"""

import os

os.environ.setdefault("NVIDIA_API_KEY", "test-key")

from backend.neurology.models.session_state import (
    NeurologyDoctorState,
    NeurologyTest,
)
from backend.neurology.services.consultation_controller import (
    ConsultationController,
)
from backend.neurology.services.lab_decision_handler import LabDecisionHandler


def create_state() -> NeurologyDoctorState:
    """Create a minimal valid NeurologyDoctorState."""

    return NeurologyDoctorState(
        user_id="user123",
        appointment_id="appt123",
        doctor_id="doctor123",
        department="Neurology",
    )


def create_state_with_recommendations() -> NeurologyDoctorState:
    """Create a state with recommended Neurology tests."""

    state = create_state()

    state.tests_recommended = True
    state.recommended_tests = [
        NeurologyTest.MRI_BRAIN,
        NeurologyTest.BLOOD_TEST_PANEL,
    ]

    return state


# ---------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------

def test_lab_decision_handler_import():
    """LabDecisionHandler should import successfully."""

    handler = LabDecisionHandler()

    assert handler is not None


# ---------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------

def test_lab_decision_handler_initialization():
    """LabDecisionHandler should initialize correctly."""

    handler = LabDecisionHandler()

    assert hasattr(handler, "logger")
    assert handler.ACCEPT == "accept"
    assert handler.DECLINE == "decline"


# ---------------------------------------------------------------------
# Accept Decision
# ---------------------------------------------------------------------

def test_handle_decision_accept_updates_state():
    """Accepting tests should record accepted decision."""

    handler = LabDecisionHandler()
    state = create_state_with_recommendations()

    updated_state = handler.handle_decision(state, "accept")

    assert updated_state.user_lab_decision == "accepted"
    assert updated_state.tests_recommended is True
    assert updated_state.recommended_tests == [
        "MRI Brain",
        "Blood Test Panel",
    ]


# ---------------------------------------------------------------------
# Decline Decision
# ---------------------------------------------------------------------

def test_handle_decision_decline_updates_state():
    """Declining tests should record declined decision."""

    handler = LabDecisionHandler()
    state = create_state_with_recommendations()

    updated_state = handler.handle_decision(state, "decline")

    assert updated_state.user_lab_decision == "declined"
    assert updated_state.tests_recommended is False
    assert updated_state.recommended_tests == [
        "MRI Brain",
        "Blood Test Panel",
    ]


# ---------------------------------------------------------------------
# ConsultationController Integration
# ---------------------------------------------------------------------

def test_consultation_controller_handles_accept_decision():
    """ConsultationController should delegate accept decisions."""

    controller = ConsultationController()
    state = create_state_with_recommendations()

    updated_state, response = controller.handle_consultation(
        state,
        "accept",
    )

    assert isinstance(response, str)
    assert updated_state.user_lab_decision == "accepted"
    assert updated_state.tests_recommended is True
    assert updated_state.recommended_tests == [
        "MRI Brain",
        "Blood Test Panel",
    ]


def test_consultation_controller_handles_decline_decision():
    """ConsultationController should delegate decline decisions."""

    controller = ConsultationController()
    state = create_state_with_recommendations()

    updated_state, response = controller.handle_consultation(
        state,
        "decline",
    )

    assert isinstance(response, str)
    assert updated_state.user_lab_decision == "declined"
    assert updated_state.tests_recommended is False
    assert updated_state.recommended_tests == [
        "MRI Brain",
        "Blood Test Panel",
    ]
