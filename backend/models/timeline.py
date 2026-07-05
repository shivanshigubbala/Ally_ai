from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class TimelineHistoryEntry(BaseModel):
    """Single longitudinal history entry derived from a completed consultation."""

    entry_id: str = Field(default_factory=lambda: str(uuid4()))
    appointment_id: str | None = None
    consultation_context_id: str | None = None
    department: str | None = None
    doctor: str | None = None
    visit_date: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    chief_complaint: str = ""
    clinical_summary: str = ""
    assessment: str = ""
    recommended_tests: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "COMPLETED"


class PatientTimeline(BaseModel):
    """Canonical longitudinal medical history for a patient."""

    timeline_id: str = Field(default_factory=lambda: str(uuid4()))
    patient_id: str | None = None
    internal_uuid: str = Field(default_factory=lambda: str(uuid4()))
    version: int = 1
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    history: list[TimelineHistoryEntry] = Field(default_factory=list)


__all__ = ["PatientTimeline", "TimelineHistoryEntry"]
