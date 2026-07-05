from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

try:
    from backend.cardiology.graphs import routing_graph
    from backend.specialties.dispatcher import resolve_specialty
    from backend.cardiology import (
        DOCTOR_ID,
        step as gp_step,
    )
    from backend.cardiology.models.session_state import ClientEvent, WSEvent
    from backend.cardiology.services import local_store as store
except ImportError:
    from graphs import routing_graph
    from specialties.dispatcher import resolve_specialty
    from general_physician import (
        DOCTOR_ID,
        step as gp_step,
    )
    from models.session_state import ClientEvent, WSEvent
    from services import local_store as store


def _resolve_doctor_step(appointment_id: str):
    """Resolve the appointment's specialty implementation through the shared dispatcher."""
    apt = store.get_appointment(appointment_id) or {}
    department = apt.get("department") or "general"
    consultation_context = {
        "selected_department": department,
        "department": department,
    }
    specialty = resolve_specialty(consultation_context)
    return specialty.run_consultation


logger = logging.getLogger(__name__)


router = APIRouter()

_user_state: dict[str, str] = {}
_doctor_sessions: dict[str, str] = {}
# Stores extracted document text per "user_id:appointment_id" key
_doc_store: dict[str, list[dict]] = {}
# Active WebSocket connections by user_id
_connections: dict[str, WebSocket] = {}


async def _send(ws: WebSocket, event: WSEvent) -> None:
    await ws.send_text(event.model_dump_json())


async def notify_user_event(user_id: str, event: WSEvent) -> None:
    ws = _connections.get(user_id)
    if not ws:
        return
    try:
        await _send(ws, event)
    except Exception:
        logger.exception("Failed to notify user %s", user_id)


async def _generate_and_send_chart_delayed(
    ws: WebSocket,
    user_id: str,
    appointment_id: str,
    patient_name: str,
    current_complaint: str,
    dept: str,
    doctor_name: str,
    slot_id: str,
    message_history: list,
) -> None:
    try:
        await asyncio.sleep(4.0)  # Wait 4 seconds as requested
        
        history_str = ""
        for m in message_history:
            role_label = m.get("role", "user").title()
            content = m.get("content", "")
            if role_label and content:
                history_str += f"{role_label}: {content}\n"

        prompt = (
            "You are an intake coordinator. Summarize the patient's intake interview. "
            "Extract the following details into a concise, professional medical consultation chart:\n"
            "- Patient Name\n"
            "- Chief Complaint\n"
            "- Suggested Department\n"
            "- Confirmed Doctor\n"
            "- Selected Time Slot\n"
            "- Key Symptoms and Answers to Health Questions (such as fever, duration, pain location)\n\n"
            "Format the chart as clean Markdown with clear headings and bullet points. "
            "Be professional and direct, with no conversational filler."
        )

        try:
            from backend.cardiology.llm.nvidia_client import chat as nv_chat, ROUTING_MODEL
        except ImportError:
            from llm.nvidia_client import chat as nv_chat, ROUTING_MODEL

        try:
            chart_content = await asyncio.to_thread(
                nv_chat,
                [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Intake Interview History:\n{history_str}"}
                ],
                model=ROUTING_MODEL
            )
        except Exception as exc:
            logger.warning("Error generating consultation chart: %s", exc)
            chart_content = (
                f"### Intake Consultation Chart\n\n"
                f"- **Patient Name:** {patient_name or user_id}\n"
                f"- **Chief Complaint:** {current_complaint or 'Intake evaluation'}\n"
                f"- **Department:** {dept.title() if dept else 'General Physician'}\n"
                f"- **Doctor:** {doctor_name}\n"
                f"- **Slot:** {slot_id}\n"
                f"- **Status:** Confirmed"
            )

        event = WSEvent(type="consultation_chart", payload={
            "appointment_id": appointment_id,
            "chart_content": chart_content,
        })
        await _send(ws, event)
    except Exception as e:
        logger.exception("Background chart generation failed")


async def _drive_routing(ws: WebSocket, user_id: str, message: str | None,
                         pending_event: dict | None) -> str:
    if message is not None:
        await _send(ws, WSEvent(type="thinking", payload={"content": "Ally is typing..."}))
    state, events = await asyncio.to_thread(
        routing_graph.run_step, user_id, message, pending_event)
    for ev in events:
        await _send(ws, ev)

    if state.current_node == "DONE":
        if state.appointment_id:
            # Instead of auto-switching to doctor, emit a doctor_ready event
            # so the frontend can offer a tab-based handoff.
            doctors = store.list_doctors(state.selected_dept or "general")
            doc_name = next(
                (d["name"] for d in doctors if d["id"] == state.selected_doctor),
                "Dr. Shankar",
            )
            
            # Start background task to generate consultation chart after delay
            asyncio.create_task(
                _generate_and_send_chart_delayed(
                    ws,
                    user_id,
                    state.appointment_id,
                    state.patient_name or "",
                    state.current_complaint or "",
                    state.selected_dept or "general",
                    doc_name,
                    state.selected_slot or "",
                    state.message_history,
                )
            )

            # booking_node already emits doctor_ready; avoid duplicate events.
            routing_graph.reset_state(user_id)
            _user_state[user_id] = "ROUTING"
            return state.appointment_id
        _user_state[user_id] = "DONE"
    else:
        _user_state[user_id] = "ROUTING"
    return ""


async def _drive_doctor(ws: WebSocket, user_id: str, appointment_id: str,
                        message: str | None,
                        pending_event: dict | None) -> None:
    doctor_step = _resolve_doctor_step(appointment_id)
    if message is not None or pending_event is not None:
        await _send(ws, WSEvent(type="thinking", payload={"content": "The doctor is thinking..."}))
    _, events = await asyncio.to_thread(
        doctor_step, user_id, appointment_id, message, pending_event)
    for ev in events:
        await _send(ws, ev)


async def _handle_start_consultation(ws: WebSocket, user_id: str,
                                     payload: dict) -> None:
    appointment_id = payload.get("appointment_id", "")
    if not appointment_id:
        await _send(ws, WSEvent(type="text", payload={
            "content": "No appointment ID provided.",
        }))
        return

    _doctor_sessions[user_id] = appointment_id
    logger.info("Start consultation requested: user=%s appointment=%s", user_id, appointment_id)

    # Docs stay in _doc_store — agent.py's step() picks them up when creating
    # the initial DoctorState, avoiding Pydantic validation issues.

    # Kick off the session init (first doctor message).
    # If DB is available, check uploaded_files for this session and block
    # starting the doctor until all files are indexed.
    try:
        from backend.cardiology.db.pgvector_tracker import get_uploaded_files_for_session
    except Exception:
        try:
            from db.pgvector_tracker import get_uploaded_files_for_session  # type: ignore
        except Exception:
            get_uploaded_files_for_session = None

    if get_uploaded_files_for_session:
        try:
            files = get_uploaded_files_for_session(appointment_id)
            pending = [f for f in files if (f.get("status") or "") != "indexed"]
            if pending:
                await _send(ws, WSEvent(type="text", payload={
                    "content": "We are processing your uploaded documents. Please wait a moment and try starting the consultation again.",
                }))
                # leave _doctor_sessions set but do not start doctor graph
                return
        except Exception:
            # if check fails, proceed to start doctor to avoid blocking unnecessarily
            pass

    await _drive_doctor(ws, user_id, appointment_id, None, None)


@router.websocket("/ws/{user_id}")
async def ws_endpoint(ws: WebSocket, user_id: str) -> None:
    await ws.accept()
    # register connection
    _connections[user_id] = ws
    if not routing_graph.has_in_progress_booking(user_id):
        routing_graph.reset_state(user_id)
        _user_state[user_id] = "ROUTING"
        appointment_id = await _drive_routing(ws, user_id, None, None)
    else:
        _user_state[user_id] = "ROUTING"
        appointment_id = ""

    try:
        while True:
            raw = await ws.receive_text()
            try:
                evt = ClientEvent(**json.loads(raw))
            except Exception:
                await _send(ws, WSEvent(type="text", payload={"content": "Malformed event."}))
                continue

            try:
                if evt.type == "start_consultation":
                    await _handle_start_consultation(ws, user_id, evt.payload)
                    continue

                if evt.type == "select":
                    # If this select has a start_consultation action, handle it
                    action = evt.payload.get("action", "")
                    if action == "start_consultation":
                        await _handle_start_consultation(ws, user_id, evt.payload)
                        continue

                # Route text/select messages based on context
                msg_context = evt.payload.get("context", "receptionist")
                if msg_context == "doctor":
                    # If we already have an active doctor session for this user, drive it.
                    if user_id in _doctor_sessions:
                        apt_id = _doctor_sessions[user_id]
                        await _drive_doctor(ws, user_id, apt_id,
                                            evt.payload.get("content"), evt.model_dump())
                    else:
                        # No active doctor session: try to extract a session/appointment id
                        # from the payload (e.g. lab decision carries session_id). If found,
                        # attach it as the doctor's session and route the event to the
                        # doctor graph so decisions like lab accept/reject are handled.
                        possible_apt = evt.payload.get("session_id") or evt.payload.get("appointment_id")
                        if possible_apt:
                            _doctor_sessions[user_id] = possible_apt
                            await _drive_doctor(ws, user_id, possible_apt,
                                                evt.payload.get("content"), evt.model_dump())
                        else:
                            # Fall back to routing if we can't determine an appointment id
                            apt = await _drive_routing(ws, user_id, evt.payload.get("content"), evt.model_dump())
                            if apt:
                                appointment_id = apt
                elif _user_state.get(user_id) == "DONE":
                    routing_graph.reset_state(user_id)
                    _user_state[user_id] = "ROUTING"
                    apt = await _drive_routing(ws, user_id, None, None)
                    if apt:
                        appointment_id = apt
                else:
                    apt = await _drive_routing(ws, user_id, evt.payload.get("content"),
                                               evt.model_dump())
                    if apt:
                        appointment_id = apt
            except Exception as e:
                logger.exception(
                    "WebSocket handler error for user=%s (state=%s, has_apt=%s)",
                    user_id,
                    _user_state.get(user_id),
                    bool(appointment_id),
                )
                try:
                    error_msg = str(e) if str(e) else "I hit a snag - please try again."
                    await _send(ws, WSEvent(
                        type="text",
                        payload={
                            "content": f"I hit a snag - {error_msg}",
                            "from": DOCTOR_ID,
                        },
                    ))
                except Exception:
                    logger.exception("Failed to send error notice to client user=%s", user_id)
                continue
    except WebSocketDisconnect:
        if user_id in _doctor_sessions:
            del _doctor_sessions[user_id]
        if user_id in _connections:
            del _connections[user_id]
        return
