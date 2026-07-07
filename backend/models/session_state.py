# backend/general_physician/models/session_state.py
# Bhargav (P2-B3, P4-B1, P4-B2).
# LangGraph state shapes + IC-13 WebSocket envelope for the routing & doctor graphs.

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


# ---- IC-13 WebSocket envelope -------------------------------------------------

WSEventType = Literal[
    "text",
    "text_delta",
    "thinking",
    "dept_select",
    "doctor_select",
    "slot_select",
    "lab_notification",
    "report_ready",
    "doctor_ready",
    "upload_received",
    "upload_indexed",
    "emergency_alert",
    "consultation_chart",
]

ClientEventType = Literal["text", "select", "start_consultation"]


class WSEvent(BaseModel):
    """Server -> client event (IC-13)."""

    type: WSEventType
    payload: dict[str, Any] = Field(default_factory=dict)


class ClientEvent(BaseModel):
    """Client -> server event."""

    type: ClientEventType
    payload: dict[str, Any] = Field(default_factory=dict)


# ---- REST shortcuts -----------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    user_id: str | None = None
    history: list[ChatMessage] = Field(default_factory=list)
    system: str | None = None


class ChatMessage(BaseModel):
    role: str = Field(pattern=r"^(system|user|assistant)$")
    content: str


class ChatResponse(BaseModel):
    reply: str
    model: str
    doctors: list[dict] = Field(default_factory=list)
    slots: list[dict] = Field(default_factory=list)
    routing: dict | None = None


# ---- RoutingGraph state -------------------------------------------------------

RoutingNode = Literal[
    "GREETING",
    "INTENT_CLASSIFICATION",
    "HEALTH_STATUS_QUESTIONS",
    "DOCTOR_SELECTION",
    "SLOT_SELECTION",
    "BOOKING_CONFIRMATION",
    "DONE",
]


class RoutingState(BaseModel):
    """State carried through the RoutingGraph nodes."""

    user_id: str
    current_node: RoutingNode = "GREETING"
    selected_dept: str | None = None
    selected_doctor: str | None = None
    selected_slot: str | None = None
    appointment_id: str | None = None

    @field_validator("appointment_id", mode="before")
    @classmethod
    def _coerce_appointment_id(cls, v: Any) -> str | None:
        return str(v) if v is not None else None
    health_data: dict[str, Any] = Field(default_factory=dict)
    message_history: list[dict[str, str]] = Field(default_factory=list)
    pending_event: dict[str, Any] | None = None
    symptom_round: int = 0
    health_question_round: int = 0
    skip_health_questions: bool = False
    patient_id: str | None = None
    patient_name: str | None = None
    returning_patient: bool = False
    current_complaint: str = ""
    patient_summary: str = ""
    visit_summary: str = ""
    uploaded_documents: list[dict[str, Any]] = Field(default_factory=list)
    conversation_summary: str = ""
    consultation_context_id: str | None = None
    consultation_status: str = "CREATED"
    intake_summary: dict[str, str] = Field(default_factory=dict)
    recommended_department: str | None = None
    department_confidence: float | None = None
    canonical_intake: Any | None = None


# ---- DoctorGraph state --------------------------------------------------------

DoctorNode = Literal[
    "SESSION_INIT",
    "QUESTIONING",
    "EMERGENCY",
    "EVALUATION",
    "LAB_NOTIFICATION",
    "USER_DECISION",
    "REPORT_PENDING",
    "SESSION_COMPLETE",
]


class DoctorState(BaseModel):
    user_id: str
    appointment_id: str

    @field_validator("appointment_id", mode="before")
    @classmethod
    def _coerce_doctor_appointment_id(cls, v: Any) -> str:
        return str(v) if v is not None else ""
    doctor_id: str
    doctor_name: str | None = None
    department: str
    health_data: dict[str, Any] = Field(default_factory=dict)
    rag_chunks: list[dict[str, Any]] = Field(default_factory=list)
    conversation_history: list[dict[str, str]] = Field(default_factory=list)
    turn_count: int = 0
    questions_asked: int = 0
    chief_complaint: str = ""
    current_node: DoctorNode = "SESSION_INIT"
    lab_tests_recommended: bool = False
    tests_list: list[dict[str, str]] = Field(default_factory=list)
    user_lab_decision: Literal["accept", "reject", "pending"] = "pending"
    recommendation_status: str = "PENDING"
    lab_request_status: str = "NOT_REQUESTED"
    lab_request_created_at: str | None = None
    lab_request_payload: dict[str, Any] = Field(default_factory=dict)
    pending_event: dict[str, Any] | None = None
    symptom_summary: str = ""
    consecutive_negatives: int = 0
    patient_id: str | None = None
    patient_name: str | None = None
    returning_patient: bool = False
    current_complaint: str = ""
    patient_summary: str = ""
    visit_summary: str = ""
    uploaded_documents: list[dict[str, Any]] = Field(default_factory=list)
    conversation_summary: str = ""
    consultation_context_id: str | None = None
    consultation_status: str = "CREATED"
    consultation_summary: dict[str, Any] = Field(default_factory=dict)
    consultation_recommendations: list[dict[str, str]] = Field(default_factory=list)
    follow_up_allowed: bool = False
    consultation_chart: str = ""

