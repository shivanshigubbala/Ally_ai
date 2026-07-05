"""
Test Recommender for Neurology Doctor Agent.

This module defines the structure for future Neurology investigation
recommendation logic.

Responsibilities:
- Define supported Neurology investigations
- Provide extension points for test recommendation decisions

NOT responsible for:
- Implementing MRI recommendation logic
- Implementing Blood Test recommendation logic
- Diagnosis
- Appointment booking
- Modifying consultation state
"""

from __future__ import annotations

import logging
from typing import Any

from backend.neurology.models.session_state import (
    NeurologyDoctorState,
    NeurologyTest,
)

logger = logging.getLogger(__name__)


class TestRecommender:
    """
    Determines whether Neurology investigations should be recommended.

    The recommender is intentionally limited to structure in this phase.
    Future commits will add clinical rule checks while reusing the existing
    NeurologyDoctorState and NeurologyTest models.
    """

    MRI_BRAIN = NeurologyTest.MRI_BRAIN
    BLOOD_TEST_PANEL = NeurologyTest.BLOOD_TEST_PANEL

    def __init__(self) -> None:
        """Initialize the Test Recommender."""

        self.logger = logging.getLogger(__name__)

        self.logger.info("Test Recommender initialized")

    def recommend_tests(
        self,
        state: NeurologyDoctorState,
    ) -> list[NeurologyTest]:
        """
        Recommend Neurology investigations for the current consultation.

        Inspects the completed consultation state using simple rule-based
        checks and returns supported tests when the patient's reported
        information suggests they may be clinically appropriate.

        Args:
            state: Current Neurology doctor consultation state.

        Returns:
            List of recommended Neurology tests. The state is not modified.
        """
        recommended_tests = []

        if self.needs_mri(state):
            recommended_tests.append(self.MRI_BRAIN)
            self.logger.info(
                "MRI Brain recommended",
                extra={"user_id": state.user_id},
            )

        if self.needs_blood_panel(state):
            recommended_tests.append(self.BLOOD_TEST_PANEL)
            self.logger.info(
                "Blood Test Panel recommended",
                extra={"user_id": state.user_id},
            )

        if not recommended_tests:
            self.logger.info(
                "No tests recommended",
                extra={"user_id": state.user_id},
            )

        return recommended_tests

    def needs_mri(
        self,
        state: NeurologyDoctorState,
    ) -> bool:
        """
        Determine whether MRI Brain should be recommended.

        Uses simple rule-based matching against existing patient information
        in the consultation state. MRI Brain is recommended when the state
        suggests symptoms such as severe or persistent headache, seizures,
        focal neurological deficit, one-sided weakness, sudden vision loss,
        suspected stroke, altered consciousness, or recurrent unexplained
        dizziness.

        Args:
            state: Current Neurology doctor consultation state.

        Returns:
            True if MRI Brain should be recommended, otherwise False.
        """
        consultation_text = self._build_consultation_text(state)

        mri_keywords = {
            "severe headache",
            "persistent headache",
            "seizure",
            "seizures",
            "focal neurological deficit",
            "focal deficit",
            "weakness on one side",
            "one-sided weakness",
            "sudden vision loss",
            "vision loss",
            "suspected stroke",
            "stroke",
            "altered consciousness",
            "loss of consciousness",
            "recurrent unexplained dizziness",
        }

        mri_combinations = (
            ("severe", "headache"),
            ("persistent", "headache"),
            ("weakness", "one side"),
            ("one-sided", "weakness"),
            ("sudden", "vision loss"),
            ("recurrent", "dizziness"),
            ("unexplained", "dizziness"),
        )

        return (
            any(keyword in consultation_text for keyword in mri_keywords)
            or self._contains_any_combination(
                consultation_text,
                mri_combinations,
            )
        )

    def needs_blood_panel(
        self,
        state: NeurologyDoctorState,
    ) -> bool:
        """
        Determine whether a Blood Test Panel should be recommended.

        Uses simple rule-based matching against existing patient information
        in the consultation state. Blood Test Panel is recommended when the
        state suggests metabolic or systemic causes such as fatigue,
        generalized weakness, confusion, nutritional deficiency suspicion,
        electrolyte imbalance suspicion, or unexplained dizziness.

        Args:
            state: Current Neurology doctor consultation state.

        Returns:
            True if Blood Test Panel should be recommended, otherwise False.
        """
        consultation_text = self._build_consultation_text(state)

        blood_panel_keywords = {
            "fatigue",
            "generalized weakness",
            "confusion",
            "nutritional deficiency",
            "nutrition deficiency",
            "vitamin deficiency",
            "electrolyte imbalance",
            "electrolyte abnormality",
            "unexplained dizziness",
        }

        blood_panel_combinations = (
            ("generalized", "weakness"),
            ("nutritional", "deficiency"),
            ("nutrition", "deficiency"),
            ("electrolyte", "imbalance"),
            ("unexplained", "dizziness"),
        )

        return (
            any(
                keyword in consultation_text
                for keyword in blood_panel_keywords
            )
            or self._contains_any_combination(
                consultation_text,
                blood_panel_combinations,
            )
        )

    def _build_consultation_text(
        self,
        state: NeurologyDoctorState,
    ) -> str:
        """
        Build searchable text from existing consultation state fields.

        Args:
            state: Current Neurology doctor consultation state.

        Returns:
            Lowercase text containing available patient information.
        """
        text_parts = [
            state.chief_complaint,
            state.symptom_summary,
            state.patient_summary,
            state.visit_summary,
            state.conversation_summary,
        ]

        self._append_health_data(text_parts, state.health_data)

        for message in state.conversation_history:
            text_parts.append(message.get("content", ""))

        return " ".join(part for part in text_parts if part).lower()

    def _append_health_data(
        self,
        text_parts: list[str],
        health_data: dict[str, Any],
    ) -> None:
        """
        Append health data values to searchable text parts.

        Args:
            text_parts: Mutable list of text fragments.
            health_data: Patient health data from consultation state.
        """
        for value in health_data.values():
            if isinstance(value, str):
                text_parts.append(value)

            elif isinstance(value, list):
                text_parts.extend(
                    item for item in value if isinstance(item, str)
                )

    def _contains_any_combination(
        self,
        consultation_text: str,
        combinations: tuple[tuple[str, ...], ...],
    ) -> bool:
        """
        Check whether all terms in any keyword combination are present.

        Args:
            consultation_text: Lowercase searchable consultation text.
            combinations: Term groups that should be matched together.

        Returns:
            True if any complete term group is present, otherwise False.
        """
        return any(
            all(term in consultation_text for term in combination)
            for combination in combinations
        )


__all__ = ["TestRecommender"]
