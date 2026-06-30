"""
Interactive CLI to test the full Ally AI workflow as a user.
Run this, then just type your messages like you're chatting with the hospital.

Workflow:
  1. Receptionist (Ally) greets you
  2. You describe symptoms
  3. Ally books you with Dr. Shankar (GP)
  4. You pick a slot, confirm
  5. Dr. Shankar starts consultation
  6. You answer questions for up to 10 turns
  7. Doctor suggests lab tests if needed
  8. You accept/reject tests
"""

import asyncio
import json
import os
import sys

try:
    import websockets
except ImportError:
    print("Installing websockets...")
    os.system(f"{sys.executable} -m pip install websockets")
    import websockets


async def _read_line(prompt: str = "") -> str:
    """Read a line from stdin without blocking the asyncio event loop."""
    line = await asyncio.get_event_loop().run_in_executor(None, input, prompt)
    return (line or "").strip()


async def _drain_pending(ws, timeout: float = 0.8) -> None:
    """Non-blocking drain of any already-buffered WS frames."""
    while True:
        try:
            resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=timeout))
        except asyncio.TimeoutError:
            return
        ev_type = resp.get("type")
        payload = resp.get("payload", {})
        if ev_type == "text_delta":
            print(payload.get("delta", ""), end="", flush=True)
        elif ev_type == "text":
            content = payload.get("content", "")
            print(f"\n[{payload.get('from', 'Ally / Dr. Shankar')}] {content}", flush=True)
        elif ev_type == "thinking":
            print("\n[Dr. Shankar is thinking...]", flush=True)
        elif ev_type == "slot_select":
            slots = payload.get("options", [])
            print("\n[Available slots:]")
            for s in slots:
                print(f"   - {s['start_time']} (id: {s['id']})")
            print("   [Type a slot id like 's1' to pick one, or type anything else to chat]")
        elif ev_type == "doctor_select":
            doctors = payload.get("options", [])
            print("\n[Doctors available:]")
            for d in doctors:
                print(f"   - {d['name']} (id: {d['id']})")
        elif ev_type == "lab_notification":
            tests = payload.get("tests", [])
            print("\n[Doctor recommends lab tests:]")
            for t in tests:
                print(f"   - {t['name']}: {t.get('reason', '')}")
            print("   [Type 'accept' to proceed, or 'reject' to skip]")


async def chat():
    user_id = await _read_line("Enter your user ID (default: test_user): ")
    user_id = user_id or "test_user"
    uri = f"ws://localhost:8000/ws/{user_id}"

    print(f"\nConnecting to {uri} ...")
    print("=" * 60)
    print("ALLY HOSPITAL - Receptionist & General Physician")
    print("Type your messages like you're talking to the hospital.")
    print("Type 'quit' to exit.")
    print("=" * 60)

    async with websockets.connect(uri) as ws:
        resp = json.loads(await ws.recv())
        print(f"\n[Ally] {resp['payload'].get('content', '')}")

        while True:
            msg = await _read_line("\n[You] ")
            if msg.lower() in ("quit", "exit"):
                break

            # Drain any buffered WS frames first so we don't pile up events
            # while the user was reading.
            await _drain_pending(ws)
            await ws.send(json.dumps({"type": "text", "payload": {"content": msg}}))

            thinking_shown = False
            streaming_header_shown = False
            streamed_sender = None
            while True:
                try:
                    resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=120.0))
                except asyncio.TimeoutError:
                    if not thinking_shown:
                        print("\n[Dr. Shankar is still thinking...]")
                        thinking_shown = True
                    continue

                ev_type = resp["type"]
                payload = resp["payload"]

                if ev_type == "text_delta":
                    delta = payload.get("delta", "")
                    sender = payload.get("from", "Dr. Shankar")
                    if not streaming_header_shown:
                        print(f"\n[{sender}] ", end="", flush=True)
                        streaming_header_shown = True
                        streamed_sender = sender
                    print(delta, end="", flush=True)
                    continue

                if ev_type == "text":
                    sender = payload.get("from", "Ally / Dr. Shankar")
                    content = payload.get("content", "")
                    if streaming_header_shown:
                        sys.stdout.write("\n")
                        sys.stdout.flush()
                        streaming_header_shown = False
                        streamed_sender = None
                    print(f"\n[{sender}] {content}")
                    if payload.get("session_complete"):
                        print("\n[Session complete]")
                        return
                    # Drain any tokens that arrived while we were processing,
                    # then break out so the outer loop prompts the user.
                    await _drain_pending(ws)
                    break

                if streaming_header_shown:
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    streaming_header_shown = False
                    streamed_sender = None

                if ev_type == "thinking":
                    if not thinking_shown:
                        print("\n[Dr. Shankar is thinking...]")
                        thinking_shown = True
                    continue

                elif ev_type == "doctor_select":
                    doctors = payload.get("options", [])
                    print("\n[Doctors available:]")
                    for d in doctors:
                        print(f"   - {d['name']} (id: {d['id']})")
                    auto = payload.get("auto_select")
                    if auto:
                        print(f"   [Auto-selecting: {auto}]")
                        await ws.send(json.dumps({
                            "type": "select",
                            "payload": {"target": "doctor", "id": auto}
                        }))

                elif ev_type == "slot_select":
                    slots = payload.get("options", [])
                    slot_ids = {s["id"] for s in slots}
                    print("\n[Available slots:]")
                    for s in slots:
                        print(f"   - {s['start_time']} (id: {s['id']})")
                    print("   [Type a slot id like 's1' to pick one, or type anything else to chat]")
                    slot_choice = await _read_line("\n[You] ")
                    first_word = slot_choice.split()[0] if slot_choice else ""
                    if first_word in slot_ids:
                        await ws.send(json.dumps({
                            "type": "select",
                            "payload": {"target": "slot", "id": first_word}
                        }))
                    else:
                        await ws.send(json.dumps({
                            "type": "text",
                            "payload": {"content": slot_choice.strip()}
                        }))
                    # Go back to receiving events (don't loop the outer input)
                    continue

                elif ev_type == "lab_notification":
                    tests = payload.get("tests", [])
                    print("\n[Doctor recommends lab tests:]")
                    for t in tests:
                        print(f"   - {t['name']}: {t.get('reason', '')}")
                    print("   [Type 'accept' to proceed, or 'reject' to skip]")
                    lab_choice = await _read_line("\n[You] ")
                    decision = "accept" if lab_choice.lower() == "accept" else "reject"
                    await ws.send(json.dumps({
                        "type": "select",
                        "payload": {"target": "lab", "decision": decision}
                    }))
                    continue

                elif ev_type == "report_ready":
                    print(f"\n[Report ready] inbox_id: {payload.get('inbox_id', '')}")
                    print("[Workflow complete!]")
                    return

                else:
                    print(f"\n[Event: {ev_type}] {json.dumps(payload)[:120]}")
                    # After any unknown event, prompt the user for next input.
                    break


if __name__ == "__main__":
    asyncio.run(chat())
