from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

try:
    from backend.graphs import routing_graph
    from backend.graphs.doctors.general_physician.agent import (
        DOCTOR_ID,
        step as doctor_step,
    )
    from backend.models.session_state import ClientEvent, WSEvent
    from backend.services import local_store as store
except ImportError:
    from graphs import routing_graph
    from graphs.doctors.general_physician.agent import (
        DOCTOR_ID,
        step as doctor_step,
    )
    from models.session_state import ClientEvent, WSEvent
    from services import local_store as store


logger = logging.getLogger(__name__)


router = APIRouter()

_user_state: dict[str, str] = {}
_doctor_sessions: dict[str, str] = {}


async def _send(ws: WebSocket, event: WSEvent) -> None:
    await ws.send_text(event.model_dump_json())


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
            await _send(ws, WSEvent(type="doctor_ready", payload={
                "appointment_id": state.appointment_id,
                "doctor_name": doc_name,
                "doctor_id": state.selected_doctor or DOCTOR_ID,
            }))
            # Reset routing graph so the receptionist can handle new requests
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
    if message is not None or pending_event is not None:
        await _send(ws, WSEvent(type="thinking", payload={"content": "Dr. Shankar is thinking..."}))
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
    # Pass the first user message from the routing history as the doctor's context.
    await _drive_doctor(ws, user_id, appointment_id, None, None)


@router.websocket("/ws/{user_id}")
async def ws_endpoint(ws: WebSocket, user_id: str) -> None:
    await ws.accept()
    routing_graph.reset_state(user_id)
    _user_state[user_id] = "ROUTING"
    appointment_id = await _drive_routing(ws, user_id, None, None)

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
            except Exception:
                logger.exception(
                    "WebSocket handler error for user=%s (state=%s, has_apt=%s)",
                    user_id,
                    _user_state.get(user_id),
                    bool(appointment_id),
                )
                try:
                    await _send(ws, WSEvent(
                        type="text",
                        payload={
                            "content": "I hit a snag - please try again.",
                            "from": DOCTOR_ID,
                        },
                    ))
                except Exception:
                    logger.exception("Failed to send error notice to client user=%s", user_id)
                continue
    except WebSocketDisconnect:
        if user_id in _doctor_sessions:
            del _doctor_sessions[user_id]
        return
