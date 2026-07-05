"""
Tests for the Neurology Test Recommender.

These tests validate rule-based test recommendation behaviour without
calling external services such as NVIDIA LLM, embeddings, PGVector, or
laboratory APIs.
"""

import os

os.environ.setdefault("NVIDIA_API_KEY", "test-key")

from backend.neurology.models.session_state import NeurologyDoctorState
from backend.neurology.services.consultation_controller import (
    ConsultationController,
)
from backend.neurology.services.test_recommender import TestRecommender


def create_state() -> NeurologyDoctorState:
    """Create a minimal valid NeurologyDoctorState."""

    return NeurologyDoctorState(
        user_id="user123",
        appointment_id="appt123",
        doctor_id="doctor123",
        department="Neurology",
    )


def create_complete_state() -> NeurologyDoctorState:
    """Create a state with required consultation information."""

    state = create_state()

    state.health_data = {
        "chief_complaint": "headache",
        "duration": "two days",
        "severity": "moderate",
        "symptoms": ["headache"],
    }

    return state


# ---------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------

def test_test_recommender_import():
    """TestRecommender should import successfully."""

    recommender = TestRecommender()

    assert recommender is not None


# ---------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------

def test_test_recommender_initialization():
    """TestRecommender should initialize supported tests."""

    recommender = TestRecommender()

    assert hasattr(recommender, "logger")
    assert hasattr(recommender, "MRI_BRAIN")
    assert hasattr(recommender, "BLOOD_TEST_PANEL")
    assert recommender.MRI_BRAIN == "MRI Brain"
    assert recommender.BLOOD_TEST_PANEL == "Blood Test Panel"


# ---------------------------------------------------------------------
# MRI Recommendation
# ---------------------------------------------------------------------

def test_needs_mri_returns_true_for_mri_symptoms():
    """MRI Brain should be recommended for MRI trigger symptoms."""

    recommender = TestRecommender()
    state = create_complete_state()

    state.health_data["severity"] = "severe"
    state.health_data["symptoms"] = ["persistent headache"]

    assert recommender.needs_mri(state) is True


# ---------------------------------------------------------------------
# Blood Test Recommendation
# ---------------------------------------------------------------------

def test_needs_blood_panel_returns_true_for_blood_panel_symptoms():
    """Blood Test Panel should be recommended for systemic symptoms."""

    recommender = TestRecommender()
    state = create_complete_state()

    state.health_data["symptoms"] = [
        "fatigue",
        "generalized weakness",
    ]

    assert recommender.needs_blood_panel(state) is True


# ---------------------------------------------------------------------
# Combined Recommendations
# ---------------------------------------------------------------------

def test_recommend_tests_returns_both_recommendations():
    """recommend_tests should return MRI Brain and Blood Test Panel."""

    recommender = TestRecommender()
    state = create_complete_state()

    state.health_data["symptoms"] = [
        "seizures",
        "fatigue",
    ]

    recommendations = recommender.recommend_tests(state)

    assert recommendations == [
        "MRI Brain",
        "Blood Test Panel",
    ]


def test_recommend_tests_returns_empty_list_when_no_tests_needed():
    """recommend_tests should return an empty list when no rules match."""

    recommender = TestRecommender()
    state = create_complete_state()

    state.health_data["chief_complaint"] = "mild tingling"
    state.health_data["symptoms"] = ["mild tingling"]
    state.health_data["severity"] = "mild"

    recommendations = recommender.recommend_tests(state)

    assert recommendations == []


# ---------------------------------------------------------------------
# ConsultationController Integration
# ---------------------------------------------------------------------

def test_consultation_controller_updates_test_recommendation_state():
    """ConsultationController should update test recommendation state."""

    controller = ConsultationController()
    state = create_complete_state()

    state.health_data["symptoms"] = [
        "seizures",
        "fatigue",
    ]

    def process_turn(
        state: NeurologyDoctorState,
        user_message: str,
    ) -> NeurologyDoctorState:
        controller.question_manager.update_conversation_history(
            state,
            role="user",
            content=user_message,
        )
        return state

    controller.question_manager.process_turn = process_turn
    controller.retriever.retrieve = lambda query: []
    controller.retriever.retrieve_context = lambda query: ""
    controller._generate_response = (
        lambda system_prompt, user_prompt, history=None: "Consultation response."
    )

    updated_state, response = controller.handle_consultation(
        state,
        "I have seizures and fatigue.",
    )

    assert isinstance(response, str)
    assert updated_state.tests_recommended is True
    assert updated_state.recommended_tests == [
        "MRI Brain",
        "Blood Test Panel",
    ]
    assert updated_state.user_lab_decision == "pending"
