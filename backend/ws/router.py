from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

try:
    from backend.graphs import routing_graph
    from backend.graphs.general_physician_agent import (
        DOCTOR_ID,
        step as doctor_step,
    )
    from backend.models.session_state import ClientEvent, WSEvent
    from backend.services import local_store as store
except ImportError:
    from graphs import routing_graph
    from graphs.general_physician_agent import (
        DOCTOR_ID,
        step as doctor_step,
    )
    from models.session_state import ClientEvent, WSEvent
    from services import local_store as store


logger = logging.getLogger(__name__)


router = APIRouter()

_user_state: dict[str, str] = {}


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
            _user_state[user_id] = "DOCTOR"
            appointment_id = state.appointment_id
            first_user_msg = next(
                (m["content"] for m in state.message_history if m.get("role") == "user"),
                None,
            )
            await _drive_doctor(ws, user_id, appointment_id, first_user_msg, None)
            return appointment_id
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
                if _user_state.get(user_id) == "DOCTOR" and appointment_id:
                    await _drive_doctor(ws, user_id, appointment_id,
                                        evt.payload.get("content"), evt.model_dump())
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
                # Continue the loop; do NOT close the connection on a processing error.
                continue
    except WebSocketDisconnect:
        return
