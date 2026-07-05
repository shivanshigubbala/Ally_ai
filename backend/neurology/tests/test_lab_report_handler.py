"""
Tests for the Neurology Lab Report Handler.

These tests validate report receiving and storage without calling external
services such as NVIDIA LLM, embeddings, PGVector, or laboratory APIs.
"""

import os

os.environ.setdefault("NVIDIA_API_KEY", "test-key")

from backend.neurology.models.session_state import NeurologyDoctorState
from backend.neurology.services.consultation_controller import (
    ConsultationController,
)
from backend.neurology.services.lab_report_handler import LabReportHandler


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

def test_lab_report_handler_import():
    """LabReportHandler should import successfully."""

    handler = LabReportHandler()

    assert handler is not None


# ---------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------

def test_lab_report_handler_initialization():
    """LabReportHandler should initialize correctly."""

    handler = LabReportHandler()

    assert hasattr(handler, "logger")
    assert hasattr(handler, "SUPPORTED_REPORT_TYPES")
    assert "MRI Brain" in handler.SUPPORTED_REPORT_TYPES
    assert "Blood Test Panel" in handler.SUPPORTED_REPORT_TYPES


# ---------------------------------------------------------------------
# MRI Brain Report
# ---------------------------------------------------------------------

def test_receive_mri_brain_report_stores_document():
    """MRI Brain reports should be stored in consultation state."""

    handler = LabReportHandler()
    state = create_state()
    report_data = {"report_id": "mri123", "filename": "mri.pdf"}

    updated_state = handler.receive_report(
        state=state,
        report_type="MRI Brain",
        report_data=report_data,
    )

    assert len(updated_state.uploaded_documents) == 1
    assert updated_state.uploaded_documents[0]["report_type"] == "MRI Brain"
    assert updated_state.uploaded_documents[0]["data"] == report_data


# ---------------------------------------------------------------------
# Blood Test Panel Report
# ---------------------------------------------------------------------

def test_receive_blood_test_panel_report_stores_document():
    """Blood Test Panel reports should be stored in consultation state."""

    handler = LabReportHandler()
    state = create_state()
    report_data = {"report_id": "blood123", "filename": "blood.pdf"}

    updated_state = handler.receive_report(
        state=state,
        report_type="Blood Test Panel",
        report_data=report_data,
    )

    assert len(updated_state.uploaded_documents) == 1
    assert (
        updated_state.uploaded_documents[0]["report_type"]
        == "Blood Test Panel"
    )
    assert updated_state.uploaded_documents[0]["data"] == report_data


# ---------------------------------------------------------------------
# Report Storage
# ---------------------------------------------------------------------

def test_receive_report_stores_report_metadata():
    """Stored report should include report metadata and raw data."""

    handler = LabReportHandler()
    state = create_state()
    report_data = {"report_id": "mri123", "status": "ready"}

    updated_state = handler.receive_report(
        state=state,
        report_type="MRI Brain",
        report_data=report_data,
    )

    document = updated_state.uploaded_documents[0]

    assert document["type"] == "lab_report"
    assert document["department"] == "neurology"
    assert document["report_type"] == "MRI Brain"
    assert document["data"] == report_data


# ---------------------------------------------------------------------
# ConsultationController Integration
# ---------------------------------------------------------------------

def test_consultation_controller_receives_lab_report():
    """ConsultationController should delegate report receiving."""

    controller = ConsultationController()
    state = create_state()
    report_data = {"report_id": "mri123", "filename": "mri.pdf"}

    updated_state = controller.receive_report(
        state=state,
        report_type="MRI Brain",
        report_data=report_data,
    )

    assert len(updated_state.uploaded_documents) == 1
    assert updated_state.uploaded_documents[0]["report_type"] == "MRI Brain"
    assert updated_state.uploaded_documents[0]["data"] == report_data
