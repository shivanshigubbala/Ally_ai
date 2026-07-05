from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any, Callable

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from pathlib import Path

from backend.specialties.base import BaseSpecialty

logger = logging.getLogger(__name__)

try:
    from backend.db.pgvector_tracker import (
        append_timeline_entry,
        create_lab_work_item,
        create_notification,
        get_uploaded_files_for_user,
        get_user_health_context,
        get_user_messages,
        load_consultation_context,
        load_patient_history,
        load_patient_profile,
        save_message,
        upsert_consultation_context,
    )
    from backend.general_physician.department_config import get_department_config
    from backend.llm.nvidia_client import (
        ROUTING_MODEL,
        chat as nv_chat,
        stream_chat as nv_stream_chat,
    )
    from backend.general_physician.llm.prompts import (
        DOCTOR_NAME,
        DOCTOR_SYSTEM_PROMPT,
        EVALUATION_PROMPT,
    )
    from backend.models.session_state import DoctorState, WSEvent
    from backend.general_physician.rag.retriever import retrieve as rag_retrieve
    from backend.services import local_store as store
    from backend.shared.lab_client import create_lab_tests
except ImportError:
    from db.pgvector_tracker import (
        append_timeline_entry,
        create_lab_work_item,
        create_notification,
        get_uploaded_files_for_user,
        get_user_health_context,
        get_user_messages,
        load_consultation_context,
        load_patient_history,
        load_patient_profile,
        save_message,
        upsert_consultation_context,
    )
    from department_config import get_department_config
    from llm.nvidia_client import (
        ROUTING_MODEL,
        chat as nv_chat,
        stream_chat as nv_stream_chat,
    )
    from llm.prompts import (
        DOCTOR_NAME,
        DOCTOR_SYSTEM_PROMPT,
        EVALUATION_PROMPT,
    )
    from models.session_state import DoctorState, WSEvent
    from rag.retriever import retrieve as rag_retrieve
    from services import local_store as store
    from shared.lab_client import create_lab_tests


Emitter = Callable[[WSEvent], None]

from backend.general_physician.config import get_default_doctor_id, get_default_doctor_name

DOCTOR_ID = get_default_doctor_id()
DOCTOR_NAME = get_default_doctor_name()
DOCTOR_DEPT = "general"
MAX_QUESTIONS = 5
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _resolve_department(state: DoctorState | Any) -> str:
    dept = getattr(state, "department", None) or DOCTOR_DEPT
    return str(dept or DOCTOR_DEPT)


def _get_department_context(state: DoctorState | Any) -> dict[str, Any]:
    return get_department_config(_resolve_department(state))


def build_patient_context(state: DoctorState | Any) -> str:
    """Assemble a compact, human-readable patient context block for the doctor prompt."""
    patient_summary = getattr(state, "patient_summary", "") or ""
    visit_summary = getattr(state, "visit_summary", "") or ""
    current_complaint = getattr(state, "current_complaint", "") or getattr(state, "chief_complaint", "") or ""
    documents = getattr(state, "uploaded_documents", None) or []
    conversation_summary = getattr(state, "conversation_summary", "") or ""

    sections = []
    if patient_summary:
        sections.append("Patient Summary\n- " + patient_summary)
    else:
        sections.append("Patient Summary\n- No prior summary available.")

    if visit_summary:
        sections.append("Recent Visits\n- " + visit_summary)
    else:
        sections.append("Recent Visits\n- No prior visits recorded.")

    complaint_text = current_complaint or "No current complaint recorded."
    sections.append("Current Complaint\n- " + complaint_text)

    if documents:
        doc_sections = []
        for doc in documents[:3]:  # limit to 3 docs to keep prompt size sane
            if not isinstance(doc, dict):
                continue
            name = doc.get("filename") or doc.get("name") or doc.get("source") or "document"
            text = doc.get("text", "").strip()
            if text:
                # Truncate individual doc text to 2000 chars
                doc_sections.append(f"  [{name}]:\n  {text[:2000]}")
            else:
                doc_sections.append(f"  [{name}]: (no text extracted)")
        if doc_sections:
            sections.append("Uploaded Patient Documents\n" + "\n\n".join(doc_sections))
        else:
            sections.append("Uploaded Patient Documents\n- No readable content found.")
    else:
        sections.append("Uploaded Patient Documents\n- No documents uploaded.")

    if conversation_summary:
        sections.append("Conversation Summary\n- " + conversation_summary)
    else:
        sections.append("Conversation Summary\n- No conversation summary available.")

    return "\n\n".join(sections)


def _build_consultation_summary(
    chief_complaint: str | None,
    conversation_history: list[dict],
    tests_list: list[dict] | None,
    notes: str | None = None,
    medical_history: Any = None,
    parsed: dict | None = None,
) -> dict[str, Any]:
    user_messages = [str(m.get("content", "")).strip() for m in conversation_history if m.get("role") == "user" and m.get("content")]
    symptoms_text = " ".join(user_messages).strip()
    symptoms_preview = re.sub(r"\s+", " ", symptoms_text or "")
    if len(symptoms_preview) > 240:
        symptoms_preview = symptoms_preview[:237].rstrip() + "..."
    if not symptoms_preview:
        symptoms_preview = chief_complaint or "No additional symptoms recorded."

    lab_recommendations = []
    for test in tests_list or []:
        if not isinstance(test, dict):
            continue
        name = str(test.get("name", "")).strip()
        if not name:
            continue
        reason = str(test.get("reason", "")).strip() or "Routine follow-up assessment."
        lab_recommendations.append({"name": name, "reason": reason})

    parsed = parsed or {}
    clinical_assessment = (
        str(parsed.get("clinical_assessment") or parsed.get("assessment") or "").strip()
        or "The symptoms were reviewed and the patient was assessed for possible urgent causes."
    )
    possible_diagnosis = (
        str(parsed.get("possible_diagnosis") or parsed.get("diagnosis") or "").strip()
        or "No specific diagnosis was confirmed from the available information."
    )
    doctor_reasoning = (
        str(parsed.get("doctor_reasoning") or parsed.get("reasoning") or "").strip()
        or "The clinical interview, available history, and uploaded documents were reviewed to determine the most appropriate next step."
    )
    next_steps = (
        str(parsed.get("next_steps") or "").strip()
        or "Continue monitoring symptoms, follow up if they worsen, and seek urgent care for red-flag symptoms."
    )
    relevant_history = ""
    if isinstance(medical_history, dict):
        relevant_history = ", ".join(
            f"{key}: {value}" for key, value in medical_history.items() if value not in (None, "")
        )
    if not relevant_history:
        relevant_history = "No prior medical history recorded."

    return {
        "chief_complaint": (chief_complaint or "No chief complaint recorded").strip(),
        "symptoms": symptoms_preview or "No additional symptoms recorded.",
        "relevant_medical_history": relevant_history,
        "clinical_assessment": clinical_assessment,
        "doctor_reasoning": doctor_reasoning,
        "next_steps": next_steps,
        "recommended_tests": lab_recommendations,
        "observations": (notes or "The clinical interview was reviewed and documented.").strip(),
        "assessment": clinical_assessment,
        "next_steps": next_steps,
        "lab_recommendations": lab_recommendations,
        "possible_diagnosis": possible_diagnosis,
    }


def _persist_consultation_output(state: DoctorState) -> None:
    try:
        summary = state.consultation_summary or _build_consultation_summary(
            chief_complaint=state.chief_complaint or state.current_complaint,
            conversation_history=state.conversation_history,
            tests_list=state.tests_list,
            notes=getattr(state, "symptom_summary", "") or None,
        )
        state.consultation_summary = summary
        state.consultation_recommendations = summary.get("lab_recommendations", []) or state.tests_list
        state.consultation_status = "COMPLETED"

        intake_payload = {
            "patient_id": state.patient_id or state.user_id,
            "session_id": f"doctor:{state.user_id}:{state.appointment_id}",
            "chief_complaint": summary.get("chief_complaint", state.chief_complaint or state.current_complaint),
            "symptoms": [summary.get("symptoms", "")],
            "structured_summary": {
                "assessment": summary.get("assessment", ""),
                "next_steps": summary.get("next_steps", ""),
            },
            "selected_doctor": state.doctor_id,
            "selected_slot": None,
        }
        context_payload = {
            "internal_uuid": state.consultation_context_id or "",
            "patient_reference": state.patient_name or state.user_id,
            "patient_id": state.patient_id or state.user_id,
            "session_id": f"doctor:{state.user_id}:{state.appointment_id}",
            "appointment_id": state.appointment_id,
            "appointment_status": "booked",
            "consultation_status": "COMPLETED",
            "selected_department": state.department,
            "selected_doctor": state.doctor_id,
            "clinical_intake_record": intake_payload,
            "metadata": {
                "doctor_name": state.doctor_name or DOCTOR_NAME,
                "patient_name": state.patient_name or state.user_id,
                "consultation_summary": summary,
                "consultation_recommendations": state.consultation_recommendations,
                "conversation_history": state.conversation_history,
                "recommendation_status": getattr(state, "recommendation_status", "PENDING"),
                "lab_request_status": getattr(state, "lab_request_status", "NOT_REQUESTED"),
                "lab_request_created_at": getattr(state, "lab_request_created_at", None),
                "lab_request_payload": getattr(state, "lab_request_payload", {}),
            },
            "version": 1,
        }
        if state.consultation_context_id:
            context_payload["internal_uuid"] = state.consultation_context_id
        saved = upsert_consultation_context(context_payload)
        if saved:
            state.consultation_context_id = saved.get("internal_uuid") or state.consultation_context_id
    except Exception:
        logger.exception("Failed to persist consultation output for appointment=%s", state.appointment_id)


def _hydrate_consultation_context(state: DoctorState) -> None:
    try:
        context = None
        if state.consultation_context_id:
            context = load_consultation_context(internal_uuid=state.consultation_context_id)
        if not context:
            context = load_consultation_context(appointment_id=state.appointment_id)
        if not context:
            return
        state.consultation_context_id = context.get("internal_uuid") or state.consultation_context_id
        state.consultation_status = context.get("consultation_status") or state.consultation_status
        state.department = context.get("selected_department") or state.department
        state.doctor_id = context.get("selected_doctor") or state.doctor_id
        metadata = context.get("metadata") or {}
        if not state.patient_name:
            state.patient_name = context.get("patient_reference") or metadata.get("patient_name") or state.patient_name
        if not state.patient_id:
            state.patient_id = context.get("patient_id") or state.patient_id
        intake = context.get("clinical_intake_record") or {}
        if isinstance(intake, dict):
            if not state.chief_complaint and intake.get("chief_complaint"):
                state.chief_complaint = str(intake.get("chief_complaint"))
            if not state.current_complaint and intake.get("chief_complaint"):
                state.current_complaint = str(intake.get("chief_complaint"))
        if metadata.get("consultation_summary"):
            state.consultation_summary = metadata.get("consultation_summary")
        if metadata.get("consultation_recommendations"):
            state.consultation_recommendations = metadata.get("consultation_recommendations")
        if state.patient_id or state.user_id:
            patient_key = state.patient_id or state.user_id
            if not state.health_data:
                try:
                    state.health_data = load_patient_profile(patient_key) or {}
                except Exception:
                    pass
    except Exception:
        logger.exception("Failed to hydrate consultation context for appointment=%s", state.appointment_id)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def _coerce_uploaded_document(doc: Any) -> dict[str, Any] | None:
    if not isinstance(doc, dict):
        return None

    filename = doc.get("filename") or doc.get("name") or doc.get("source") or "uploaded document"
    text = doc.get("text") or doc.get("snippet") or ""
    if not isinstance(text, str):
        text = str(text or "")

    metadata = doc.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}

    return {
        "filename": str(filename),
        "text": text.strip(),
        "source": doc.get("source") or "uploaded_file",
        "metadata": metadata,
    }


def _load_patient_documents(state: DoctorState) -> list[dict[str, Any]]:
    patient_id = (getattr(state, "patient_id", None) or getattr(state, "user_id", None) or "").strip()
    merged_docs: list[dict[str, Any]] = []

    for doc in getattr(state, "uploaded_documents", None) or []:
        normalized = _coerce_uploaded_document(doc)
        if normalized:
            merged_docs.append(normalized)

    if patient_id:
        try:
            persisted_docs = get_uploaded_files_for_user(patient_id)
        except Exception:
            persisted_docs = []
        for row in persisted_docs:
            normalized = _coerce_uploaded_document(row)
            if not normalized:
                continue
            if any(
                existing.get("filename") == normalized.get("filename") and existing.get("text") == normalized.get("text")
                for existing in merged_docs
            ):
                continue
            merged_docs.append(normalized)

    state.uploaded_documents = merged_docs
    return merged_docs


def _contains_any(text: str, phrases: list[str]) -> bool:
    lowered = _normalize_text(text)
    return any(phrase in lowered for phrase in phrases)


def _build_initial_doctor_message(chief_complaint: str | None, patient_name: str, doctor_name: str = "Dr. Shankar Dada", dept_name: str = "general physician") -> str:
    cleaned = (chief_complaint or "").strip()
    intro = f"Hi {patient_name}, I’m {doctor_name}, your {dept_name} doctor. "
    if not cleaned:
        return (
            intro + "Thanks for reaching out. I’m here to help you make sense of what’s going on today."
        )

    lowered = _normalize_text(cleaned)
    if _contains_any(lowered, [
        "just fine",
        "feeling fine",
        "all good",
        "no symptoms",
        "nothing at all",
        "no complaints",
        "nothing serious",
        "i'm fine",
        "i am fine",
        "okay",
        "ok",
    ]):
        return (
            intro + "If you’re feeling well and there are no new symptoms, I’d keep this simple and only look into testing if anything changes."
        )

    if _contains_any(lowered, ["cough", "cold", "flu", "sore throat", "headache", "body aches", "runny nose", "fever"]):
        complaint_hint = next(
            phrase for phrase in ["cough", "cold", "flu", "sore throat", "headache", "body aches", "runny nose", "fever"]
            if phrase in lowered
        )
        return (
            intro + f"Thanks for sharing that about your {complaint_hint}. I’m going to ask a couple of focused questions so I can tell whether this looks mild or needs a closer look."
        )

    return (
        intro + "I’d like to ask a few focused questions so I can give you the right next step."
    )


def _sanitize_tests(tests: list[dict] | None) -> list[dict]:
    mapping = {
        "CBC": {"name": "Complete Blood Count (CBC)", "reason": "Routine blood count check."},
        "BMP": {"name": "Basic Metabolic Panel (BMP)", "reason": "Routine metabolic and kidney function check."},
    }
    if not tests:
        return []
    sanitized: list[dict] = []
    seen: set[str] = set()
    for test in tests:
        if not isinstance(test, dict):
            continue
        name = str(test.get("name", "")).strip()
        key = name.upper()
        if key not in mapping:
            continue
        item = mapping[key].copy()
        reason = str(test.get("reason") or "").strip()
        if reason:
            item["reason"] = reason
        if item["name"] not in seen:
            sanitized.append(item)
            seen.add(item["name"])
    return sanitized


def _should_recommend_tests(parsed: dict | None, conversation: list[dict], chief_complaint: str | None) -> bool:
    parsed = parsed or {}
    if not parsed.get("tests"):
        return False

    conversation_text = " ".join(
        str(m.get("content", ""))
        for m in conversation
        if m.get("role") in ("user", "assistant")
    )
    combined = f"{chief_complaint or ''} {conversation_text}".strip()
    lowered = _normalize_text(combined)

    # RED FLAGS - CHECK FIRST AND OVERRIDE EVERYTHING ELSE
    red_flags = [
        "shortness of breath",
        "trouble breathing",
        "chest pain",
        "chest tightness",
        "heart attack",
        "heart racing",
        "palpitations",
        "blood",
        "bleeding",
        "severe pain",
        "passing out",
        "fainted",
        "collapse",
        "seizure",
        "convulsion",
        "confusion",
        "weight loss",
        "high fever",
        "39c",
        "39°c",
        "more than 2 weeks",
        "lasting more than 7 days",
        "persistent",
        "recurring",
        "recurrent",
        "coughing blood",
        "vomiting blood",
        "difficulty breathing",
        "loss of consciousness",
        "severe headache",
        "numbness",
        "paralysis",
        "vision changes",
        "slurred speech",
    ]
    # If ANY red flag is present, ALWAYS recommend tests
    if _contains_any(lowered, red_flags):
        return True

    # Only if NO red flags: check for mild patterns that don't need testing
    mild_patterns = [
        "cold",
        "cough",
        "mild",
        "viral",
        "flu",
        "sore throat",
        "runny nose",
        "sinus",
        "allergy",
        "fatigue",
    ]
    worsening_indicators = [
        "worse",
        "worsening",
        "severe",
        "breathing",
        "persistent",
    ]
    # If only mild patterns and no worsening, don't recommend tests
    if _contains_any(lowered, mild_patterns) and not _contains_any(lowered, worsening_indicators):
        return False

    # Check for "patient is fine" pattern - only applies if NO red flags detected
    if _contains_any(lowered, [
        "just fine",
        "feeling fine",
        "all good",
        "no symptoms",
        "nothing at all",
        "no complaints",
        "nothing serious",
        "i'm fine",
        "i am fine",
        "everything is fine",
    ]):
        return False

    # Default: trust the LLM's recommendation
    return bool(parsed.get("recommend_tests"))


def _remember(user_id: str, role: str, content: str, session_id: str | None = None) -> None:
    """Persist a single turn to the pgvector messages table (best-effort)."""
    try:
        save_message(user_id=user_id, role=role, content=content, session_id=session_id)
    except Exception:
        pass


def _load_prior_context(user_id: str, exclude_session_id: str | None) -> str:
    """Return a short transcript of this user's prior visits, or '' if none."""
    try:
        return get_user_health_context(user_id)
    except Exception:
        return ""


def _extract_json(text: str) -> dict | None:
    # Robustly extract the first balanced JSON object from text.
    if not text:
        return None
    start = None
    depth = 0
    in_str = False
    escape = False
    for i, ch in enumerate(text):
        if start is None:
            if ch == '{':
                start = i
                depth = 1
                continue
            else:
                continue
        # inside potential JSON
        if in_str:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == '"':
                in_str = False
            continue
        else:
            if ch == '"':
                in_str = True
                continue
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    candidate = text[start:i+1]
                    try:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        # try to continue searching for another balanced object
                        start = None
                        depth = 0
                        in_str = False
                        escape = False
                        continue
    return None


LAB_TESTS = [
    {
        "name": "Complete Blood Count (CBC)",
        "reason": "Evaluates red and white blood cells, hemoglobin, and platelets.",
    },
    {
        "name": "Basic Metabolic Panel (BMP)",
        "reason": "Checks electrolytes, kidney function, and metabolic status.",
    },
]


def _call_llm(messages: list[dict], model: str | None = None) -> str:
    use_model = model or ROUTING_MODEL  # Use 8B for speed
    return nv_chat(messages, model=use_model)


def _stream_into_emit(messages: list[dict], emit: Emitter, sender: str,
                      model: str | None = None) -> str:
    """Stream LLM output to the WS as text_delta events; return the full reply."""
    use_model = model or ROUTING_MODEL
    parts: list[str] = []
    try:
        for token in nv_stream_chat(messages, model=use_model):
            parts.append(token)
            emit(WSEvent(type="text_delta", payload={"delta": token, "from": sender}))
    except Exception:
        logger.exception(
            "Streaming LLM call failed sender=%s model=%s",
            sender, use_model,
        )
        if not parts:
            raise
    return "".join(parts)


def _format_messages(history: list[dict]) -> str:
    lines: list[str] = []
    for m in history:
        if m.get("role") in ("user", "assistant"):
            lines.append(f"{m['role']}: {m['content']}")
    return "\n".join(lines) or "(no prior conversation)"


def _should_end_questioning(reply: str) -> bool:
    lower = reply.lower()
    return any(
        phrase in lower
        for phrase in [
            "enough information",
            "enough detail",
            "move on to review",
            "ready to review",
            "ready to evaluate",
            "can proceed to evaluation",
            "i can evaluate now",
            "i have enough to",
            "sufficient information",
            "review everything",
            "rest and fluids",
            "mild case",
            "nothing serious",
        ]
    )


_NEGATION_WORDS = {"no", "none", "nothing", "nope", "nah", "na", "not", "not really", "not at all", "everything is fine", "everything looks fine", "everything goes well", "all good", "i'm fine", "i am fine"}


def _is_negation(text: str) -> bool:
    lower = text.lower().strip().rstrip(".?!,")
    if lower in _NEGATION_WORDS:
        return True
    return any(lower.startswith(w) for w in ("no ", "none ", "nothing ", "not really", "not at all", "everything is"))


def _update_symptom_summary(state: DoctorState, user_message: str, doctor_reply: str) -> str:
    parts = []
    if state.symptom_summary:
        parts.append(state.symptom_summary)
    if user_message:
        parts.append(f"Patient says: {user_message}")
    if doctor_reply:
        q = doctor_reply.strip()
        if "?" in q:
            q = q[:q.index("?") + 1]
            parts.append(f"Doctor asked: {q}")
    return "\n".join(parts[-6:])


# ---- Nodes --------------------------------------------------------------------


def session_init(state: DoctorState, emit: Emitter) -> DoctorState:
    _hydrate_consultation_context(state)

    # Capture the chief complaint once at session start. Prefer an explicit
    # user message in this session's history; otherwise pull the earliest
    # prior user message (from the routing phase) so the doctor's relevance
    # gate has the actual concern, not the user_id.
    if not state.chief_complaint:
        for m in state.conversation_history:
            if m.get("role") == "user" and m.get("content"):
                state.chief_complaint = m["content"].strip()
                break
    if state.patient_name and not state.patient_name.strip():
        state.patient_name = None
    if not state.chief_complaint:
        try:
            prior_msgs = get_user_messages(
                state.user_id,
                limit=20,
                exclude_session_id=f"doctor:{state.user_id}:{state.appointment_id}",
            )
            for m in prior_msgs:
                if m.get("role") == "user" and m.get("content"):
                    state.chief_complaint = m["content"].strip()
                    break
        except Exception:
            pass

    _load_patient_documents(state)

    rag_context = rag_retrieve(
        department=_resolve_department(state),
        messages=state.conversation_history or [{"role": "user", "content": state.user_id}],
        chief_complaint=state.chief_complaint or None,
        patient_id=state.patient_id or state.user_id,
    )

    prior = _load_prior_context(
        state.user_id,
        exclude_session_id=f"doctor:{state.user_id}:{state.appointment_id}",
    )
    health_data = state.health_data or {}

    patient_name = state.patient_name or state.user_id.replace("_", " ").title()
    department_context = _get_department_context(state)
    doc_name = state.doctor_name or department_context.get("doctor_name") or "Dr. Shankar Dada"
    dept_name = "general physician"

    greeting_prefix = f"Hi {patient_name}, I’m {doc_name}, your {dept_name} doctor. "

    if state.uploaded_documents:
        summary = "I see you uploaded the following document(s): " + ", ".join(
            doc.get("filename", "a document") for doc in state.uploaded_documents[:3]
        )
        reply = (
            f"{greeting_prefix}I’m reviewing your uploaded document(s) first. "
            f"{summary}. "
            "Then I’ll ask a couple of focused questions so I can understand your concern and next steps."
        )
    else:
        reply = _build_initial_doctor_message(state.chief_complaint, patient_name, doc_name, dept_name)

    emit(WSEvent(type="text", payload={"content": reply, "from": DOCTOR_ID}))
    state.conversation_history.append({"role": "assistant", "content": reply})
    state.current_node = "QUESTIONING"
    state.questions_asked = 0
    return state


def questioning(state: DoctorState, emit: Emitter) -> DoctorState:
    state.questions_asked = (state.questions_asked or 0) + 1

    last_user_msg = ""
    if state.conversation_history and state.conversation_history[-1].get("role") == "user":
        last_user_msg = state.conversation_history[-1]["content"]

    # EMERGENCY ESCALATION: If red flags detected, skip to evaluation immediately
    emergency_keywords = [
        "chest pain", "chest tightness", "heart attack", "heart racing",
        "shortness of breath", "trouble breathing", "can't breathe",
        "passing out", "fainted", "collapse", "collapsing",
        "severe pain", "excruciating", "unbearable",
        "vomiting blood", "coughing blood", "bleeding heavily",
        "seizure", "convulsion", "loss of consciousness",
        "difficulty breathing", "severe headache", "worst headache",
    ]
    conv_text = " ".join(
        str(m.get("content", ""))
        for m in state.conversation_history[-3:] if m.get("role") == "user"
    ).lower()
    if _contains_any(conv_text, emergency_keywords):
        msg = (
            "This sounds serious and needs immediate evaluation. "
            "Let me review what you've told me to determine the right tests."
        )
        state.conversation_history.append({"role": "assistant", "content": msg})
        emit(WSEvent(type="text", payload={"content": msg, "from": DOCTOR_ID}))
        state.current_node = "EVALUATION"
        return state

    if _is_negation(last_user_msg):
        state.consecutive_negatives = (state.consecutive_negatives or 0) + 1
    else:
        state.consecutive_negatives = 0

    if state.consecutive_negatives >= 3:
        msg = (
            "It sounds like this is a mild case with no concerning symptoms — "
            "I think rest and fluids should do. Let me wrap up our consultation."
        )
        state.conversation_history.append({"role": "assistant", "content": msg})
        emit(WSEvent(type="text", payload={"content": msg, "from": DOCTOR_ID}))
        state.current_node = "EVALUATION"
        return state

    if state.questions_asked >= MAX_QUESTIONS:
        emit(WSEvent(type="text", payload={
            "content": "Thanks for sharing all that - I have a good picture now. "
                       "Let me review everything and see if any tests are needed.",
            "from": DOCTOR_ID,
        }))
        state.current_node = "EVALUATION"
        return state

    rag_context = rag_retrieve(
        department=_resolve_department(state),
        messages=state.conversation_history,
        chief_complaint=state.chief_complaint or None,
        patient_id=state.patient_id or state.user_id,
    )

    prior = _load_prior_context(
        state.user_id,
        exclude_session_id=f"doctor:{state.user_id}:{state.appointment_id}",
    )
    health_data = state.health_data or {}
    patient_name = state.user_id.replace("_", " ").title()

    state.symptom_summary = _update_symptom_summary(state, last_user_msg, "")

    department_context = _get_department_context(state)
    system = department_context.get("system_prompt", DOCTOR_SYSTEM_PROMPT).format(
        rag_context=rag_context or "(no clinical reference retrieved)",
        name=patient_name,
        age=health_data.get("age", "unknown"),
        health_data=prior or "(no prior visits)",
        patient_context=build_patient_context(state),
        messages=_format_messages(state.conversation_history),
        q_count=state.questions_asked,
        chief_complaint=state.chief_complaint or "(not yet stated)",
        symptom_summary=state.symptom_summary or "(no symptoms discussed yet)",
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": "Ask your next single clinical question, or if you have enough information, say you can proceed to evaluation."},
    ]
    try:
        reply = _stream_into_emit(messages, emit, sender=DOCTOR_ID)
    except Exception:
        logger.exception(
            "LLM stream failed in questioning() for user=%s apt=%s q=%s",
            state.user_id, state.appointment_id, state.questions_asked,
        )
        try:
            reply = _call_llm(messages)
            emit(WSEvent(type="text", payload={"content": reply, "from": DOCTOR_ID}))
        except Exception:
            logger.exception(
                "Fallback non-stream LLM also failed in questioning() user=%s q=%s",
                state.user_id, state.questions_asked,
            )
            reply = (
                "I'm having trouble processing that right now - "
                "could you tell me a bit more about your main symptom?"
            )
            emit(WSEvent(type="text", payload={"content": reply, "from": DOCTOR_ID}))

    state.symptom_summary = _update_symptom_summary(state, last_user_msg, reply)
    state.conversation_history.append({"role": "assistant", "content": reply})
    if _should_end_questioning(reply):
        state.current_node = "EVALUATION"
    else:
        state.current_node = "QUESTIONING"
    return state


def evaluation(state: DoctorState, emit: Emitter) -> DoctorState:
    conv_text = "\n".join(
        f"{m['role']}: {m['content']}"
        for m in state.conversation_history
        if m["role"] in ("user", "assistant")
    )
    patient_context = build_patient_context(state)
    department_context = _get_department_context(state)
    evaluation_prompt = department_context.get("evaluation_prompt", EVALUATION_PROMPT)
    prompt = (
        f"{evaluation_prompt}\n\n"
        f"Conversation:\n{conv_text}\n\n"
        f"Chief Complaint:\n{state.chief_complaint or '(not stated)'}\n\n"
        f"Patient Context:\n{patient_context}\n\n"
        f"Relevant Medical History:\n{json.dumps(state.health_data or {}, default=str)}\n\n"
        "Return a JSON object with keys: clinical_assessment, possible_diagnosis, doctor_reasoning, next_steps, recommended_tests. "
        "recommended_tests must be a list of supported tests from the existing catalog only: Complete Blood Count (CBC) and Basic Metabolic Panel (BMP). "
        "Recommend at most 2 tests."
    )
    raw = _call_llm([{"role": "user", "content": prompt}], model=ROUTING_MODEL)
    parsed = _extract_json(raw) or {}

    state.lab_tests_recommended = _should_recommend_tests(
        parsed,
        state.conversation_history,
        state.chief_complaint,
    )
    urgent = False
    try:
        text = " ".join(m.get("content", "") for m in state.conversation_history)
        urgent = _contains_any(text, [
            "chest pain",
            "trouble breathing",
            "severe pain",
            "fainting",
            "collapse",
            "confusion",
            "vomiting blood",
            "coughing blood",
        ])
    except Exception:
        urgent = False

    recommended_tests = _sanitize_tests(parsed.get("recommended_tests") or parsed.get("tests"))
    if len(recommended_tests) > 2:
        recommended_tests = recommended_tests[:2]
    if state.lab_tests_recommended and not recommended_tests:
        recommended_tests = LAB_TESTS.copy()
    if not state.lab_tests_recommended:
        recommended_tests = []
    state.tests_list = recommended_tests

    consultation_summary = _build_consultation_summary(
        chief_complaint=state.chief_complaint or state.current_complaint,
        conversation_history=state.conversation_history,
        tests_list=state.tests_list,
        notes=getattr(state, "symptom_summary", "") or None,
        medical_history=state.health_data or {},
        parsed=parsed,
    )
    state.consultation_summary = consultation_summary
    state.consultation_recommendations = consultation_summary.get("lab_recommendations", []) or state.tests_list

    patient_name = state.patient_name or state.user_id.replace("_", " ").title()
    if state.lab_tests_recommended and state.tests_list:
        test_names = ", ".join(t.get("name", "?") for t in state.tests_list)
        closing_message = (
            f"Based on our conversation, {patient_name}, my clinical assessment is that {consultation_summary.get('clinical_assessment', 'the symptoms are being monitored carefully')}. "
            f"Possible diagnosis: {consultation_summary.get('possible_diagnosis', 'no specific diagnosis confirmed')}. "
            f"Next steps: {consultation_summary.get('next_steps', 'continue monitoring and follow up if symptoms worsen')}. "
            f"I recommend {test_names} to help clarify things further."
        )
        emit(WSEvent(type="text", payload={
            "content": closing_message,
            "from": DOCTOR_ID,
        }))
        emit(WSEvent(type="lab_notification", payload={
            "tests": state.tests_list,
            "session_id": state.appointment_id,
            "doctor_name": state.doctor_name or DOCTOR_NAME,
            "doctor_id": state.doctor_id,
            "department": state.department,
            "urgent": urgent,
        }))
        state.current_node = "LAB_NOTIFICATION"
    else:
        closing_message = (
            f"Based on our conversation, {patient_name}, my clinical assessment is that {consultation_summary.get('clinical_assessment', 'the symptoms appear manageable for now')}. "
            f"Possible diagnosis: {consultation_summary.get('possible_diagnosis', 'no specific diagnosis confirmed')}. "
            f"Next steps: {consultation_summary.get('next_steps', 'continue monitoring and seek urgent care if symptoms worsen')}."
        )
        emit(WSEvent(type="text", payload={
            "content": closing_message,
            "from": DOCTOR_ID,
        }))
        # Allow the patient to ask follow-up questions after the summary
        # instead of ending the session immediately.
        state.follow_up_allowed = True
    return state


def lab_notification(state: DoctorState, emit: Emitter) -> DoctorState:
    pending = getattr(state, "pending_event", None) or {}
    decision = "pending"

    if pending.get("type") == "select":
        decision = pending.get("payload", {}).get("decision", "pending")
    else:
        for m in reversed(state.conversation_history):
            if m["role"] == "user":
                content = m["content"].lower().strip()
                if content in ("accept", "yes", "ok", "sure", "proceed", "go ahead"):
                    decision = "accept"
                elif content in ("reject", "no", "nope", "decline", "skip"):
                    decision = "reject"
                break

    state.user_lab_decision = decision
    state.pending_event = None

    if decision != "pending":
        state.current_node = "USER_DECISION"
    else:
        emit(WSEvent(type="lab_notification", payload={
            "tests": state.tests_list,
            "session_id": state.appointment_id,
            "waiting": True,
        }))
    return state


def user_decision(state: DoctorState, emit: Emitter) -> DoctorState:
    if state.user_lab_decision == "accept":
        state.recommendation_status = "ACCEPTED"
        state.lab_request_status = "PENDING_LAB"
        state.lab_request_created_at = datetime.utcnow().isoformat()
        lab_request_id = f"labreq:{state.appointment_id}"
        work_item = None
        try:
            work_item = create_lab_work_item(
                lab_request_id=lab_request_id,
                patient_id=state.patient_id or state.user_id,
                appointment_id=state.appointment_id,
                consultation_context_id=state.consultation_context_id,
                doctor_name=state.doctor_name or DOCTOR_NAME,
                department=state.department,
                requested_tests=state.tests_list,
                status="PENDING",
            )
        except Exception:
            logger.exception("Failed to create lab work item for appointment=%s", state.appointment_id)
        try:
            create_notification({
                "notification_id": f"notif:{lab_request_id}",
                "patient_id": state.patient_id or state.user_id,
                "appointment_id": state.appointment_id,
                "consultation_context_id": state.consultation_context_id,
                "department": state.department,
                "doctor": state.doctor_name or DOCTOR_NAME,
                "notification_type": "LAB",
                "title": "Lab request accepted",
                "message": "A lab request has been created for the recommended tests and is pending review.",
                "metadata": {
                    "lab_request_id": lab_request_id,
                    "source": "general_physician_agent",
                    "status": state.lab_request_status,
                },
                "status": "PENDING",
            })
        except Exception:
            logger.exception("Failed to persist notification for lab request=%s", lab_request_id)

        lab_response = None
        try:
            lab_response = create_lab_tests(
                appointment_id=state.appointment_id or "0",
                user_id=state.patient_id or state.user_id or "0",
                doctor_id=state.doctor_id or state.doctor_name or DOCTOR_NAME,
                department=state.department,
                tests=state.tests_list,
                session_id=state.appointment_id,
            )
        except Exception:
            logger.exception("Failed to trigger lab service for appointment=%s", state.appointment_id)

        # If the lab client returned a mocked reports payload (when the lab
        # service is unavailable), emit a `report_ready` event for each
        # generated report so the frontend can show and download them.
        try:
            if isinstance(lab_response, dict) and lab_response.get("reports"):
                for r in lab_response.get("reports"):
                    pdf_name = r.get("pdf_name") or r.get("test") or None
                    path = r.get("path") or r.get("pdf_name") or None
                    report_id = pdf_name or f"report-{state.appointment_id}-{len(str(r))}"
                    # Emit a report_ready event; frontend will resolve relative
                    # `report_url` paths against the backend base URL.
                    emit(WSEvent(type="report_ready", payload={
                        "report_id": report_id,
                        "report_url": path,
                        "download_url": path,
                        "tests": state.tests_list,
                        "doctor": state.doctor_name or DOCTOR_NAME,
                        "user_id": state.patient_id or state.user_id,
                    }))
        except Exception:
            logger.exception("Failed to emit mock report_ready events for appointment=%s", state.appointment_id)

        state.lab_request_payload = {
            "patient_id": state.patient_id or state.user_id,
            "appointment_id": state.appointment_id,
            "tests": state.tests_list,
            "status": state.lab_request_status,
            "created_at": state.lab_request_created_at,
            "lab_request_id": lab_request_id,
            "lab_work_item": work_item,
        }
        try:
            append_timeline_entry(
                patient_id=state.patient_id or state.user_id,
                entry={
                    "appointment_id": state.appointment_id,
                    "consultation_context_id": state.consultation_context_id,
                    "department": state.department,
                    "doctor": state.doctor_name or DOCTOR_NAME,
                    "visit_date": datetime.utcnow().isoformat(),
                    "chief_complaint": state.chief_complaint or state.current_complaint or "",
                    "clinical_summary": state.consultation_summary.get("summary") or state.consultation_summary.get("clinical_assessment") or "",
                    "assessment": state.consultation_summary.get("assessment") or state.consultation_summary.get("clinical_assessment") or "",
                    "recommended_tests": state.consultation_summary.get("recommended_tests") or state.tests_list or [],
                    "status": "COMPLETED",
                },
            )
        except Exception:
            logger.exception("Failed to append consultation timeline entry for appointment=%s", state.appointment_id)
        emit(WSEvent(type="text", payload={
            "content": "I’ve noted your choice and created a pending laboratory request for the recommended tests.",
            "from": DOCTOR_ID,
        }))
    else:
        state.recommendation_status = "REJECTED"
        state.lab_request_status = "NOT_REQUESTED"
        state.lab_request_created_at = datetime.utcnow().isoformat()
        state.lab_request_payload = {
            "patient_id": state.patient_id or state.user_id,
            "appointment_id": state.appointment_id,
            "tests": state.tests_list,
            "status": state.lab_request_status,
            "created_at": state.lab_request_created_at,
        }
        emit(WSEvent(type="text", payload={
            "content": "No problem. I’ve recorded that you declined the recommended lab tests.",
            "from": DOCTOR_ID,
        }))
    state.current_node = "SESSION_COMPLETE"
    return state


def report_pending(state: DoctorState, emit: Emitter) -> DoctorState:
    emit(WSEvent(type="text", payload={
        "content": "Your lab request is being tracked. No report has been generated.",
        "from": DOCTOR_ID,
    }))
    state.current_node = "SESSION_COMPLETE"
    return state


def session_complete(state: DoctorState, emit: Emitter) -> DoctorState:
    if not state.consultation_summary:
        state.consultation_summary = _build_consultation_summary(
            chief_complaint=state.chief_complaint or state.current_complaint,
            conversation_history=state.conversation_history,
            tests_list=state.tests_list,
            notes=getattr(state, "symptom_summary", "") or None,
        )
    if not state.consultation_recommendations:
        state.consultation_recommendations = state.consultation_summary.get("lab_recommendations", []) or state.tests_list
    _persist_consultation_output(state)
    return state


# ---- Conditional edges --------------------------------------------------------


def _after_questioning(state: DoctorState) -> str:
    return "EVALUATION" if state.current_node == "EVALUATION" else "QUESTIONING"


def _after_evaluation(state: DoctorState) -> str:
    # If lab notification was scheduled, transition there.
    if state.current_node == "LAB_NOTIFICATION":
        return "LAB_NOTIFICATION"
    # If follow-ups are allowed, go back to questioning so the doctor can
    # continue the consultation; otherwise complete the session.
    if getattr(state, "follow_up_allowed", False):
        # reset the flag so follow-up is a single transition window
        state.follow_up_allowed = False
        return "QUESTIONING"
    return "SESSION_COMPLETE"


def _after_decision(state: DoctorState) -> str:
    return "REPORT_PENDING" if state.current_node == "REPORT_PENDING" else "SESSION_COMPLETE"


# ---- Graph builder ------------------------------------------------------------


def build_graph() -> StateGraph:
    g = StateGraph(DoctorState)
    g.add_node("SESSION_INIT", session_init)
    g.add_node("QUESTIONING", questioning)
    g.add_node("EVALUATION", evaluation)
    g.add_node("LAB_NOTIFICATION", lab_notification)
    g.add_node("USER_DECISION", user_decision)
    g.add_node("REPORT_PENDING", report_pending)
    g.add_node("SESSION_COMPLETE", session_complete)

    g.set_entry_point("SESSION_INIT")
    g.add_edge("SESSION_INIT", "QUESTIONING")
    g.add_conditional_edges("QUESTIONING", _after_questioning, {
        "EVALUATION": "EVALUATION", "QUESTIONING": "QUESTIONING"
    })
    g.add_conditional_edges("EVALUATION", _after_evaluation, {
        "LAB_NOTIFICATION": "LAB_NOTIFICATION", "SESSION_COMPLETE": "SESSION_COMPLETE"
    })
    g.add_edge("LAB_NOTIFICATION", "USER_DECISION")
    g.add_conditional_edges("USER_DECISION", _after_decision, {
        "REPORT_PENDING": "REPORT_PENDING", "SESSION_COMPLETE": "SESSION_COMPLETE"
    })
    g.add_edge("REPORT_PENDING", "SESSION_COMPLETE")
    g.add_edge("SESSION_COMPLETE", END)

    return g


_checkpointer = MemorySaver()
_graph = build_graph().compile(checkpointer=_checkpointer)


class GeneralPhysicianSpecialty(BaseSpecialty):
    """Adapter that lets the existing GP workflow participate in the shared specialty framework."""

    department = "general"

    def initialize_consultation(self, patient_id: str | None = None, appointment_id: str | None = None, **kwargs: Any) -> DoctorState:
        return DoctorState(
            user_id=patient_id or kwargs.get("user_id") or "",
            appointment_id=appointment_id or kwargs.get("appointment_id") or "",
            doctor_id=kwargs.get("doctor_id") or DOCTOR_ID,
            doctor_name=kwargs.get("doctor_name") or DOCTOR_NAME,
            department=kwargs.get("department") or DOCTOR_DEPT,
            patient_id=patient_id,
        )

    def load_consultation_context(self, appointment_id: str | None = None, **kwargs: Any) -> dict[str, Any] | None:
        if appointment_id:
            return load_consultation_context(appointment_id=appointment_id)
        return None

    def load_patient_history(self, patient_id: str | None = None, **kwargs: Any) -> list[dict[str, Any]]:
        if patient_id:
            return load_patient_history(patient_id=patient_id, limit=kwargs.get("limit", 50))
        return []

    def load_patient_documents(self, patient_id: str | None = None, appointment_id: str | None = None, **kwargs: Any) -> list[dict[str, Any]]:
        if not patient_id:
            return []
        try:
            return get_uploaded_files_for_user(patient_id) or []
        except Exception:
            return []

    def run_consultation(self, user_id: str, appointment_id: str, user_message: str | None = None, pending_event: dict | None = None, **kwargs: Any) -> tuple[DoctorState, list[WSEvent]]:
        return step(user_id, appointment_id, user_message, pending_event)

    def generate_summary(self, state: Any, **kwargs: Any) -> dict[str, Any]:
        return getattr(state, "consultation_summary", None) or {}

    def recommend_labs(self, state: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return getattr(state, "consultation_recommendations", None) or []

    def complete_consultation(self, state: Any, **kwargs: Any) -> dict[str, Any]:
        return {
            "status": getattr(state, "consultation_status", "CREATED"),
            "summary": getattr(state, "consultation_summary", None) or {},
            "recommendations": getattr(state, "consultation_recommendations", None) or [],
        }


def step(
    user_id: str,
    appointment_id: str,
    user_message: str | None,
    pending_event: dict | None,
) -> tuple[DoctorState, list[WSEvent]]:
    events: list[WSEvent] = []
    cfg = {"configurable": {"thread_id": f"doc:{user_id}:{appointment_id}"}}

    snap = _graph.get_state(cfg)
    if snap and snap.values:
        state = DoctorState(**snap.values)
    else:
        # First call for this appointment — create a fresh state.
        # Pull any documents the user uploaded before starting the consultation.
        uploaded_docs: list[dict] = []
        try:
            from backend.ws.router import _doc_store
        except ImportError:
            try:
                from ws.router import _doc_store  # type: ignore
            except ImportError:
                _doc_store = {}
        doc_key = f"{user_id}:{appointment_id}"
        uploaded_docs = _doc_store.pop(doc_key, [])
        logger.info("Doctor session init: user=%s appointment=%s uploaded_docs=%d", user_id, appointment_id, len(uploaded_docs))

        doctor_id = DOCTOR_ID
        department = DOCTOR_DEPT
        doctor_name = DOCTOR_NAME
        patient_name = None
        patient_id = user_id
        try:
            apt = store.get_appointment(appointment_id)
            if apt:
                doctor_id = apt.get("doctor_id") or doctor_id
                department = apt.get("department") or department
                patient_name = apt.get("patient") or None
                patient_id = apt.get("patient_id") or user_id
                if doctor_id:
                    doctor_name = next(
                        (d["name"] for d in store.list_doctors(department) if d["id"] == doctor_id),
                        doctor_name,
                    )
        except Exception:
            pass

        state = DoctorState(
            user_id=user_id,
            appointment_id=appointment_id,
            doctor_id=doctor_id,
            doctor_name=doctor_name,
            department=department,
            patient_name=patient_name,
            patient_id=patient_id,
            uploaded_documents=uploaded_docs,
        )

    if user_message:
        state.conversation_history.append({"role": "user", "content": user_message})
        _remember(
            user_id,
            "user",
            user_message,
            session_id=f"doctor:{user_id}:{appointment_id}",
        )
    if pending_event:
        state.pending_event = pending_event

    node_map = {
        "SESSION_INIT": session_init,
        "QUESTIONING": questioning,
        "EVALUATION": evaluation,
        "LAB_NOTIFICATION": lab_notification,
        "USER_DECISION": user_decision,
        "REPORT_PENDING": report_pending,
        "SESSION_COMPLETE": session_complete,
    }

    prev_len = len(state.conversation_history)
    for _ in range(20):
        if state.current_node == "SESSION_COMPLETE":
            break
        node_fn = node_map[state.current_node]
        state = node_fn(state, events.append)
        if state.current_node in {"QUESTIONING", "LAB_NOTIFICATION", "REPORT_PENDING"}:
            break

    for m in state.conversation_history[prev_len:]:
        if m["role"] == "assistant":
            _remember(
                user_id,
                "assistant",
                m["content"],
                session_id=f"doctor:{user_id}:{appointment_id}",
            )

    _graph.update_state(cfg, state.model_dump())
    return state, events
