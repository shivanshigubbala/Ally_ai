from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class NotificationStatus(str, Enum):
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    READ = "READ"
    FAILED = "FAILED"


class NotificationType(str, Enum):
    APPOINTMENT = "APPOINTMENT"
    LAB = "LAB"
    REPORT = "REPORT"
    CONSULTATION = "CONSULTATION"
    GENERAL = "GENERAL"


class Notification(BaseModel):
    """Canonical internal notification object shared by backend modules."""

    notification_id: str = Field(default_factory=lambda: str(uuid4()))
    patient_id: str | None = None
    internal_uuid: str = Field(default_factory=lambda: str(uuid4()))
    appointment_id: str | None = None
    consultation_context_id: str | None = None
    department: str | None = None
    doctor: str | None = None
    notification_type: NotificationType | str = NotificationType.GENERAL
    title: str = ""
    message: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: NotificationStatus | str = NotificationStatus.PENDING
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    read_at: str | None = None
    version: int = 1


__all__ = ["Notification", "NotificationStatus", "NotificationType"]
