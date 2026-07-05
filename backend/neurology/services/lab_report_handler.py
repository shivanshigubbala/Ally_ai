"""
Lab Report Handler for Neurology Doctor Agent.

This module receives Neurology lab report information and stores it in the
consultation state.

Responsibilities:
- Validate supported Neurology report types
- Store received report payloads on the consultation state

NOT responsible for:
- Interpreting reports
- Diagnosing conditions
- Generating summaries
- Calling external lab services
- Updating test recommendation decisions
"""

from __future__ import annotations

import logging
from typing import Any

from backend.neurology.models.session_state import (
    NeurologyDoctorState,
    NeurologyTest,
)

logger = logging.getLogger(__name__)


class LabReportHandler:
    """
    Receives and stores Neurology lab reports.
    """

    SUPPORTED_REPORT_TYPES = {
        NeurologyTest.MRI_BRAIN.value,
        NeurologyTest.BLOOD_TEST_PANEL.value,
    }

    def __init__(self) -> None:
        """Initialize the Lab Report Handler."""

        self.logger = logging.getLogger(__name__)

        self.logger.info("Lab Report Handler initialized")

    def receive_report(
        self,
        state: NeurologyDoctorState,
        report_type: str,
        report_data: dict[str, Any],
    ) -> NeurologyDoctorState:
        """
        Receive and store a Neurology lab report.

        Validates that the report type is supported by the Neurology service,
        then appends the raw report information to state.uploaded_documents.
        The report is stored only; no interpretation or diagnosis is performed.

        Args:
            state: Current Neurology doctor consultation state.
            report_type: Type of report received. Supported values are
                "MRI Brain" and "Blood Test Panel".
            report_data: Raw report payload to store.

        Returns:
            Updated Neurology doctor consultation state.

        Raises:
            ValueError: If report_type is unsupported.
        """
        if report_type not in self.SUPPORTED_REPORT_TYPES:
            self.logger.warning(
                "Unsupported Neurology report type received",
                extra={
                    "user_id": state.user_id,
                    "report_type": report_type,
                },
            )
            raise ValueError(f"Unsupported report type: {report_type}")

        report_document = {
            "type": "lab_report",
            "department": "neurology",
            "report_type": report_type,
            "data": report_data,
        }

        state.uploaded_documents.append(report_document)

        self.logger.info(
            "Neurology lab report stored",
            extra={
                "user_id": state.user_id,
                "report_type": report_type,
                "document_count": len(state.uploaded_documents),
            },
        )

        return state


__all__ = ["LabReportHandler"]
