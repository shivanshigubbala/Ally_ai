from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Callable

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

logger = logging.getLogger(__name__)

try:
    from backend.db.pgvector_tracker import (
        get_user_health_context,
        get_user_messages,
        save_message,
    )
    from backend.llm.nvidia_client import (
        ROUTING_MODEL,
        chat as nv_chat,
        stream_chat as nv_stream_chat,
    )
    from backend.llm.prompts import (
        CARDIOLOGY_DOCTOR_NAME,
        CARDIOLOGY_DOCTOR_SYSTEM_PROMPT,
        CARDIOLOGY_EVALUATION_PROMPT,
    )
    from backend.models.session_state import DoctorState, WSEvent
    from backend.rag.retriever import retrieve as rag_retrieve
    from backend.specialties.cardiology.notification import (
        build_emergency_message,
        build_lab_accept_message,
        build_lab_notification_message,
        build_lab_reject_message,
        build_no_tests_message,
        build_report_ready_message,
    )
    from backend.specialties.cardiology.test_recommender import (
        DEFAULT_REPORT_RESULTS,
        EMERGENCY_TESTS,
        sanitize_tests,
    )
except ImportError:
    from db.pgvector_tracker import (
        get_user_health_context,
        get_user_messages,
        save_message,
    )
    from llm.nvidia_client import (
        ROUTING_MODEL,
        chat as nv_chat,
        stream_chat as nv_stream_chat,
    )
    from llm.prompts import (
        CARDIOLOGY_DOCTOR_NAME,
        CARDIOLOGY_DOCTOR_SYSTEM_PROMPT,
        CARDIOLOGY_EVALUATION_PROMPT,
    )
    from models.session_state import DoctorState, WSEvent
    from rag.retriever import retrieve as rag_retrieve
    from specialties.cardiology.notification import (
        build_emergency_message,
        build_lab_accept_message,
        build_lab_notification_message,
        build_lab_reject_message,
        build_no_tests_message,
        build_report_ready_message,
    )
    from specialties.cardiology.test_recommender import (
        DEFAULT_REPORT_RESULTS,
        EMERGENCY_TESTS,
        sanitize_tests,
    )


Emitter = Callable[[WSEvent], None]

DOCTOR_ID = "d8"
DOCTOR_NAME = CARDIOLOGY_DOCTOR_NAME
DOCTOR_DEPT = "cardiology"
MAX_QUESTIONS = 6

GUIDELINES_PATH = Path(__file__).resolve().parents[1] / "specialties" / "cardiology" / "guidelines.json"
REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"


def _load_emergency_keywords() -> list[str]:
    try:
        data = json.loads(GUIDELINES_PATH.read_text())
        return [k.lower() for k in data.get("emergency_red_flags", [])]
    except Exception:
        logger.warning("Could not load cardiology guidelines.json, using fallback red flags")
        return [
            "crushing chest pain",
            "severe chest pain",
            "chest pain radiating to left arm",
            "chest pain radiating to jaw",
            "fainting",
            "collapse",
            "severe shortness of breath",
        ]


EMERGENCY_KEYWORDS = _load_emergency_keywords()


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def _contains_any(text: str, phrases: list[str]) -> bool:
    lowered = _normalize_text(text)
    return any(phrase in lowered for phrase in phrases)


def _is_emergency(text: str) -> bool:
    return _contains_any(text, EMERGENCY_KEYWORDS)


def _build_initial_doctor_message(chief_complaint: str | None, patient_name: str) -> str:
    cleaned = (chief_complaint or "").strip()
    if not cleaned:
        return (
            f"Hi {patient_name}, I'm Dr. Rao. I'm here to help figure out what's "
            "going on with your heart today. What's been bothering you?"
        )
    lowered = _normalize_text(cleaned)
    if _contains_any(lowered, ["chest pain", "chest tightness", "pressure in chest"]):
        return (
            f"Thanks for telling me about the chest pain, {patient_name}. I'd like to "
            "ask a few focused questions so I can understand exactly what's happening."
        )
    if _contains_any(lowered, ["palpitations", "irregular heartbeat", "racing heart", "skipped beat"]):
        return (
            f"I hear you on the palpitations, {patient_name}. Let's go through a few "
            "questions so I can get a clearer picture of your heart rhythm."
        )
    return (
        f"Thanks for sharing that, {patient_name}. I'd like to ask a few focused "
        "questions about your heart health before we decide on next steps."
    )


def _should_recommend_tests(parsed: dict | None, conversation: list[dict], chief_complaint: str | None) -> bool:
    parsed = parsed or {}
    if parsed.get("recommend_tests") is False:
        return False

    tests = sanitize_tests(parsed.get("tests") or [])
    if not tests:
        return False

    conversation_text = " ".join(
        str(m.get("content", "")) for m in conversation if m.get("role") in ("user", "assistant")
    )
    combined = f"{chief_complaint or ''} {conversation_text}".strip()
    lowered = _normalize_text(combined)

    if _contains_any(lowered, [
        "just fine", "feeling fine", "all good", "no symptoms",
        "no complaints", "nothing serious", "i'm fine", "i am fine",
    ]):
        return False

    red_flags = EMERGENCY_KEYWORDS + [
        "chest pain", "palpitations", "shortness of breath", "breathlessness",
        "leg swelling", "irregular heartbeat", "family history of heart disease",
    ]
    if _contains_any(lowered, red_flags):
        return True

    mild_only = ["fatigue", "tired", "occasional dizziness"]
    if _contains_any(lowered, mild_only) and not _contains_any(lowered, red_flags):
        return False

    return bool(parsed.get("recommend_tests"))


def _remember(user_id: str, role: str, content: str, session_id: str | None = None) -> None:
    try:
        save_message(user_id=user_id, role=role, content=content, session_id=session_id)
    except Exception:
        pass


def _load_prior_context(user_id: str, exclude_session_id: str | None) -> str:
    try:
        return get_user_health_context(user_id)
    except Exception:
        return ""


def _extract_json(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _ensure_reports_dir() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _generate_lab_report_pdf(
    report_id: str,
    doctor_name: str,
    patient_name: str,
    tests: list[dict[str, str]],
) -> str:
    _ensure_reports_dir()
    path = REPORTS_DIR / f"{report_id}.pdf"
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Helvetica", size=16)
    pdf.cell(0, 10, "Ally Hospital Cardiology Report", ln=True, align="C")
    pdf.ln(6)

    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 8, f"Patient: {patient_name}", ln=True)
    pdf.cell(0, 8, f"Doctor: {doctor_name}", ln=True)
    pdf.cell(0, 8, f"Report ID: {report_id}", ln=True)
    pdf.cell(0, 8, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
    pdf.ln(8)

    pdf.set_font("Helvetica", size=12, style="B")
    pdf.cell(0, 8, "Recommended Cardiac Tests and Results", ln=True)
    pdf.ln(4)
    pdf.set_font("Helvetica", size=11)

    for test in tests:
        pdf.set_font("Helvetica", size=12, style="B")
        pdf.cell(0, 7, f"{test['name']}", ln=True)
        pdf.set_font("Helvetica", size=11)
        result = DEFAULT_REPORT_RESULTS.get(test["name"], "Result: Normal.")
        pdf.multi_cell(0, 6, result)
        pdf.ln(3)

    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(
        0, 6,
        "These tests were ordered by Dr. Meera Rao during your cardiology consultation "
        "at Ally Hospital. Please follow up with your clinician if you have any "
        "questions about the results.",
    )
    pdf.output(str(path))
    return str(path)


def _call_llm(messages: list[dict], model: str | None = None) -> str:
    use_model = model or ROUTING_MODEL
    return nv_chat(messages, model=use_model)


def _stream_into_emit(messages: list[dict], emit: Emitter, sender: str, model: str | None = None) -> str:
    use_model = model or ROUTING_MODEL
    parts: list[str] = []
    try:
        for token in nv_stream_chat(messages, model=use_model):
            parts.append(token)
            emit(WSEvent(type="text_delta", payload={"delta": token, "from": sender}))
    except Exception:
        logger.exception("Streaming LLM call failed sender=%s model=%s", sender, use_model)
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
            "enough information", "enough detail", "move on to review",
            "ready to review", "ready to evaluate", "can proceed to evaluation",
            "i can evaluate now", "i have enough to", "sufficient information",
            "review everything", "no cardiac tests", "nothing concerning",
        ]
    )


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
    if not state.chief_complaint:
        for m in state.conversation_history:
            if m.get("role") == "user" and m.get("content"):
                state.chief_complaint = m["content"].strip()
                break
    if not state.chief_complaint:
        try:
            prior_msgs = get_user_messages(
                state.user_id, limit=20,
                exclude_session_id=f"doctor:{state.user_id}:{state.appointment_id}",
            )
            for m in prior_msgs:
                if m.get("role") == "user" and m.get("content"):
                    state.chief_complaint = m["content"].strip()
                    break
        except Exception:
            pass

    patient_name = state.user_id.replace("_", " ").title()

    if _is_emergency(state.chief_complaint or ""):
        state.emergency = True
        state.current_node = "EMERGENCY"
        return state

    reply = _build_initial_doctor_message(state.chief_complaint, patient_name)
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

    # Live emergency detection: any turn can trip this, not just the opener.
    if _is_emergency(last_user_msg) or _is_emergency(state.chief_complaint or ""):
        state.emergency = True
        state.current_node = "EMERGENCY"
        return state

    if state.questions_asked >= MAX_QUESTIONS:
        emit(WSEvent(type="text", payload={
            "content": "Thank you for sharing all of that - I have a good clinical "
                       "picture now. Let me review everything and see if any cardiac "
                       "tests are needed.",
            "from": DOCTOR_ID,
        }))
        state.current_node = "EVALUATION"
        return state

    rag_context = rag_retrieve(
        department=DOCTOR_DEPT,
        messages=state.conversation_history,
        chief_complaint=state.chief_complaint or None,
    )
    prior = _load_prior_context(
        state.user_id, exclude_session_id=f"doctor:{state.user_id}:{state.appointment_id}",
    )
    health_data = state.health_data or {}
    patient_name = state.user_id.replace("_", " ").title()

    state.symptom_summary = _update_symptom_summary(state, last_user_msg, "")

    system = CARDIOLOGY_DOCTOR_SYSTEM_PROMPT.format(
        rag_context=rag_context or "(no clinical reference retrieved)",
        name=patient_name,
        age=health_data.get("age", "unknown"),
        health_data=prior or "(no prior visits)",
        messages=_format_messages(state.conversation_history),
        chief_complaint=state.chief_complaint or "(not yet stated)",
        symptom_summary=state.symptom_summary or "(no symptoms discussed yet)",
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": "Ask your next single clinical question, or if you have enough information, say you're ready to proceed to evaluation."},
    ]

    try:
        reply = _stream_into_emit(messages, emit, sender=DOCTOR_ID)
    except Exception:
        logger.exception(
            "LLM stream failed in cardiology questioning() user=%s q=%s",
            state.user_id, state.questions_asked,
        )
        try:
            reply = _call_llm(messages)
            emit(WSEvent(type="text", payload={"content": reply, "from": DOCTOR_ID}))
        except Exception:
            logger.exception("Fallback non-stream LLM also failed in cardiology questioning()")
            reply = (
                "I'm having trouble processing that right now - could you tell me a "
                "bit more about your chest symptoms or heart-related concerns?"
            )
            emit(WSEvent(type="text", payload={"content": reply, "from": DOCTOR_ID}))

    state.symptom_summary = _update_symptom_summary(state, last_user_msg, reply)
    state.conversation_history.append({"role": "assistant", "content": reply})
    state.current_node = "EVALUATION" if _should_end_questioning(reply) else "QUESTIONING"
    return state


def emergency(state: DoctorState, emit: Emitter) -> DoctorState:
    msg = build_emergency_message()
    emit(WSEvent(type="emergency_alert", payload={"content": msg, "from": DOCTOR_ID}))
    emit(WSEvent(type="text", payload={"content": msg, "from": DOCTOR_ID}))
    state.conversation_history.append({"role": "assistant", "content": msg})

    state.risk_level = "Emergency"
    state.tests_list = list(EMERGENCY_TESTS)
    state.lab_tests_recommended = True

    test_names = ", ".join(t.get("name", "?") for t in state.tests_list)
    emit(WSEvent(type="text", payload={
        "content": (
            f"While you're getting emergency help, I'm also flagging {test_names} "
            "as tests your care team should run immediately."
        ),
        "from": DOCTOR_ID,
    }))
    emit(WSEvent(type="lab_notification", payload={
        "tests": state.tests_list,
        "session_id": state.appointment_id,
        "urgent": True,
    }))
    state.current_node = "LAB_NOTIFICATION"
    return state


def evaluation(state: DoctorState, emit: Emitter) -> DoctorState:
    conv_text = "\n".join(
        f"{m['role']}: {m['content']}" for m in state.conversation_history
        if m["role"] in ("user", "assistant")
    )
    prompt = CARDIOLOGY_EVALUATION_PROMPT.format(
        conversation=conv_text,
        chief_complaint=state.chief_complaint or "(not stated)",
    )
    raw = _call_llm([{"role": "user", "content": prompt}], model=ROUTING_MODEL)
    parsed = _extract_json(raw) or {}

    state.risk_level = parsed.get("risk_level") or "Low"
    state.tests_list = sanitize_tests(parsed.get("tests") or [])
    state.lab_tests_recommended = _should_recommend_tests(
        parsed, state.conversation_history, state.chief_complaint,
    )

    if state.lab_tests_recommended and state.tests_list:
        emit(WSEvent(type="text", payload={
            "content": build_lab_notification_message(state.tests_list),
            "from": DOCTOR_ID,
        }))
        emit(WSEvent(type="lab_notification", payload={
            "tests": state.tests_list,
            "session_id": state.appointment_id,
        }))
        state.current_node = "LAB_NOTIFICATION"
    else:
        emit(WSEvent(type="text", payload={
            "content": build_no_tests_message(),
            "from": DOCTOR_ID,
        }))
        state.current_node = "SESSION_COMPLETE"
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
        emit(WSEvent(type="text", payload={"content": build_lab_accept_message(), "from": DOCTOR_ID}))
        state.current_node = "REPORT_PENDING"
    else:
        emit(WSEvent(type="text", payload={"content": build_lab_reject_message(), "from": DOCTOR_ID}))
        state.current_node = "SESSION_COMPLETE"
    return state


def report_pending(state: DoctorState, emit: Emitter) -> DoctorState:
    report_id = f"report-{state.appointment_id}"
    patient_name = state.user_id.replace("_", " ").title()
    try:
        _generate_lab_report_pdf(report_id, DOCTOR_NAME, patient_name, state.tests_list)
    except Exception:
        logger.exception("Failed to generate cardiology lab report PDF for report_id=%s", report_id)

    emit(WSEvent(type="report_ready", payload={
        "inbox_id": report_id,
        "report_id": report_id,
        "report_url": f"/reports/{report_id}",
        "doctor": DOCTOR_NAME,
        "tests": state.tests_list,
    }))
    emit(WSEvent(type="text", payload={"content": build_report_ready_message(), "from": DOCTOR_ID}))
    state.current_node = "SESSION_COMPLETE"
    return state


def session_complete(state: DoctorState, emit: Emitter) -> DoctorState:
    return state


# ---- Conditional edges --------------------------------------------------------


def _after_session_init(state: DoctorState) -> str:
    return "EMERGENCY" if state.current_node == "EMERGENCY" else "QUESTIONING"


def _after_questioning(state: DoctorState) -> str:
    if state.current_node == "EMERGENCY":
        return "EMERGENCY"
    return "EVALUATION" if state.current_node == "EVALUATION" else "QUESTIONING"


def _after_evaluation(state: DoctorState) -> str:
    return "LAB_NOTIFICATION" if state.current_node == "LAB_NOTIFICATION" else "SESSION_COMPLETE"


def _after_decision(state: DoctorState) -> str:
    return "REPORT_PENDING" if state.current_node == "REPORT_PENDING" else "SESSION_COMPLETE"


# ---- Graph builder --------------------------------------------------------------


def build_graph() -> StateGraph:
    g = StateGraph(DoctorState)
    g.add_node("SESSION_INIT", session_init)
    g.add_node("QUESTIONING", questioning)
    g.add_node("EMERGENCY", emergency)
    g.add_node("EVALUATION", evaluation)
    g.add_node("LAB_NOTIFICATION", lab_notification)
    g.add_node("USER_DECISION", user_decision)
    g.add_node("REPORT_PENDING", report_pending)
    g.add_node("SESSION_COMPLETE", session_complete)

    g.set_entry_point("SESSION_INIT")
    g.add_conditional_edges("SESSION_INIT", _after_session_init, {
        "EMERGENCY": "EMERGENCY", "QUESTIONING": "QUESTIONING"
    })
    g.add_conditional_edges("QUESTIONING", _after_questioning, {
        "EMERGENCY": "EMERGENCY", "EVALUATION": "EVALUATION", "QUESTIONING": "QUESTIONING"
    })
    g.add_edge("EMERGENCY", "LAB_NOTIFICATION")
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
        state = DoctorState(
            user_id=user_id,
            appointment_id=appointment_id,
            doctor_id=DOCTOR_ID,
            department=DOCTOR_DEPT,
        )

    if user_message:
        state.conversation_history.append({"role": "user", "content": user_message})
        _remember(user_id, "user", user_message, session_id=f"doctor:{user_id}:{appointment_id}")
    if pending_event:
        state.pending_event = pending_event

    node_map = {
        "SESSION_INIT": session_init,
        "QUESTIONING": questioning,
        "EMERGENCY": emergency,
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
        if state.current_node in {"QUESTIONING", "LAB_NOTIFICATION"}:
            break

    for m in state.conversation_history[prev_len:]:
        if m["role"] == "assistant":
            _remember(user_id, "assistant", m["content"], session_id=f"doctor:{user_id}:{appointment_id}")

    _graph.update_state(cfg, state.model_dump())
    return state, events
