"""Regression test: receptionist books appointment, doctor handoff is tab-based.

This captures the expected flow:
  1. Receptionist greets and helps select a doctor
  2. Receptionist helps pick a slot and confirms the booking
  3. Routing graph reaches DONE with an appointment_id
  4. The confirmation mentions the Appointments tab (not an auto-redirect)
  5. The WS router emits a doctor_ready event instead of auto-switching
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.graphs import routing_graph
from backend.services import local_store as store


def test_receptionist_full_booking_flow() -> None:
    """Simulate the full receptionist flow and verify DONE state + appointment_id."""
    routing_graph.reset_state("handoff_test")

    # Step 1 — initial greeting, intent, doctor selection
    state, events = routing_graph.run_step("handoff_test", "I have a headache", None)
    assert any(e.type == "doctor_select" for e in events)
    assert state.current_node in {"DOCTOR_SELECTION", "SLOT_SELECTION"}

    # Step 2 — select Dr. Shankar → auto-advance to slot selection
    state, events = routing_graph.run_step(
        "handoff_test",
        None,
        {"type": "select", "payload": {"id": "d5", "doctor_id": "d5"}},
    )
    slot_events = [e for e in events if e.type == "slot_select"]
    assert len(slot_events) >= 1, "Should emit slot_select after doctor selection"
    slots = slot_events[-1].payload.get("options", [])
    assert len(slots) > 0, "Should have available slots"

    # Step 3 — pick a slot → reach booking confirmation
    available = store.list_slots("d5")
    assert len(available) > 0
    slot = available[0]
    state, events = routing_graph.run_step(
        "handoff_test",
        None,
        {
            "type": "select",
            "payload": {
                "target": "slot",
                "id": slot["id"],
                "doctor_id": "d5",
            },
        },
    )
    assert state.current_node == "BOOKING_CONFIRMATION", (
        f"Expected BOOKING_CONFIRMATION, got {state.current_node}"
    )

    # Step 4 — confirm booking → DONE with appointment_id
    with patch("backend.graphs.routing_graph.nv_chat") as mock_chat:
        mock_chat.return_value = (
            "Your appointment is confirmed! Dr. Shankar is ready for you "
            "in the Appointments tab whenever you are."
        )
        state, events = routing_graph.run_step("handoff_test", "yes", None)

    assert state.current_node == "DONE", f"Expected DONE, got {state.current_node}"
    assert state.appointment_id is not None, "Should have an appointment_id"

    text_events = [e for e in events if e.type == "text"]
    assert any(
        "appointments" in (e.payload.get("content", "") or "").lower()
        for e in text_events
    ), "Confirmation should mention the Appointments tab"

    assert any(
        "ready" in (e.payload.get("content", "") or "").lower()
        for e in text_events
    ), "Confirmation should say the doctor is ready"


@pytest.mark.asyncio
async def test_router_emits_doctor_ready_instead_of_auto_switch() -> None:
    """Verify the WS router sends doctor_ready when routing completes,
    rather than auto-launching the doctor graph."""
    from backend.ws.router import _drive_routing

    mock_ws = MagicMock()
    mock_ws.send_text = AsyncMock()

    # Simulate the full routing flow by making the routing graph reach DONE
    routing_graph.reset_state("router_test")

    # Drill through the routing graph step by step
    routing_graph.run_step("router_test", "I have a headache", None)
    routing_graph.run_step(
        "router_test",
        None,
        {"type": "select", "payload": {"id": "d5", "doctor_id": "d5"}},
    )
    available = store.list_slots("d5")
    routing_graph.run_step(
        "router_test",
        None,
        {
            "type": "select",
            "payload": {
                "target": "slot",
                "id": available[0]["id"],
                "doctor_id": "d5",
            },
        },
    )

    with patch("backend.graphs.routing_graph.nv_chat") as mock_chat:
        mock_chat.return_value = "Confirmed! Ready in the Appointments tab."
        apt_id = await _drive_routing(mock_ws, "router_test", "yes", None)

    # The router should NOT have auto-launched the doctor — it should return
    # the appointment_id but keep the user in ROUTING state.
    from backend.ws.router import _user_state

    assert apt_id != "", "Should return a non-empty appointment_id"
    assert _user_state.get("router_test") == "ROUTING", (
        "User should stay in ROUTING state after booking"
    )

    # Check that a doctor_ready event was sent
    sent_calls = mock_ws.send_text.call_args_list
    doctor_ready_sent = False
    for call in sent_calls:
        text = call[0][0]
        try:
            evt = json.loads(text)
            if evt.get("type") == "doctor_ready":
                doctor_ready_sent = True
                assert "appointment_id" in evt.get("payload", {})
                assert "doctor_name" in evt.get("payload", {})
                break
        except (json.JSONDecodeError, TypeError):
            continue
    assert doctor_ready_sent, "Router should emit a doctor_ready event"
