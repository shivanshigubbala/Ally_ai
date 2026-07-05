"""
Lab Decision Handler for Neurology Doctor Agent.

This module handles patient decisions for recommended Neurology tests.

Responsibilities:
- Record whether the patient accepts or declines recommended tests
- Update consultation state fields related to lab decision tracking

NOT responsible for:
- Booking laboratory appointments
- Ordering tests
- Calling external lab services
- Generating lab reports
- Modifying recommendation logic
"""

from __future__ import annotations

import logging

from backend.neurology.models.session_state import NeurologyDoctorState

logger = logging.getLogger(__name__)


class LabDecisionHandler:
    """
    Handles patient responses to recommended Neurology tests.
    """

    ACCEPT = "accept"
    DECLINE = "decline"

    ACCEPTED = "accepted"
    DECLINED = "declined"

    def __init__(self) -> None:
        """Initialize the Lab Decision Handler."""

        self.logger = logging.getLogger(__name__)

        self.logger.info("Lab Decision Handler initialized")

    def handle_decision(
        self,
        state: NeurologyDoctorState,
        decision: str,
    ) -> NeurologyDoctorState:
        """
        Handle a patient's decision about recommended Neurology tests.

        Supports only explicit accept or decline decisions. Accepting records
        the patient's acceptance while preserving the recommended tests.
        Declining records the patient's decline and clears the active
        tests_recommended flag.

        Args:
            state: Current Neurology doctor consultation state.
            decision: Patient decision. Supported values are "accept" and
                "decline".

        Returns:
            Updated Neurology doctor consultation state.

        Raises:
            ValueError: If the decision is unsupported.
        """
        normalized_decision = decision.strip().lower()

        if normalized_decision == self.ACCEPT:
            state.user_lab_decision = self.ACCEPTED

            self.logger.info(
                "Patient accepted recommended tests",
                extra={
                    "user_id": state.user_id,
                    "test_count": len(state.recommended_tests),
                },
            )

            return state

        if normalized_decision == self.DECLINE:
            state.user_lab_decision = self.DECLINED
            state.tests_recommended = False

            self.logger.info(
                "Patient declined recommended tests",
                extra={
                    "user_id": state.user_id,
                    "test_count": len(state.recommended_tests),
                },
            )

            return state

        self.logger.warning(
            "Unsupported lab decision received",
            extra={
                "user_id": state.user_id,
                "decision": decision,
            },
        )
        raise ValueError(f"Unsupported lab decision: {decision}")


__all__ = ["LabDecisionHandler"]
