from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class CanonicalIntake(BaseModel):
    """Canonical intake contract shared by receptionist-driven workflows."""

    patient_id: str | None = None
    session_id: str | None = None
    chief_complaint: str = ""
    symptoms: list[str] = Field(default_factory=list)
    duration: str = ""
    severity: str = ""
    relevant_history: str = ""
    structured_summary: dict[str, Any] = Field(default_factory=dict)
    recommended_department: str = "general"
    confidence_score: float = 0.0
    recommended_doctors: list[str] = Field(default_factory=list)
    selected_doctor: str | None = None
    selected_slot: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: int = 1


class ConsultationContext(BaseModel):
    """Canonical handoff object persisted for downstream doctor workflows."""

    patient_reference: str | None = None
    patient_id: str | None = None
    internal_uuid: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str | None = None
    clinical_intake_record: CanonicalIntake | None = None
    selected_department: str | None = None
    selected_doctor: str | None = None
    appointment_id: str | None = None

    @field_validator("appointment_id", mode="before")
    @classmethod
    def coerce_appointment_id(cls, v: Any) -> str | None:
        if v is None:
            return None
        return str(v)
    appointment_status: str = "booked"
    consultation_status: str = "CREATED"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)
