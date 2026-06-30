import asyncio
import json
import queue
import threading
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

import websockets


class DoctorGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Ally Doctor Chat GUI")

        frame = ttk.Frame(root, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")
        root.rowconfigure(0, weight=1)
        root.columnconfigure(0, weight=1)

        conn_frame = ttk.Frame(frame)
        conn_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        conn_frame.columnconfigure(1, weight=1)

        ttk.Label(conn_frame, text="Backend WS URL:").grid(row=0, column=0, sticky="w")
        self.url_entry = ttk.Entry(conn_frame)
        self.url_entry.insert(0, "ws://127.0.0.1:8000/ws/")
        self.url_entry.grid(row=0, column=1, sticky="ew", padx=(6, 6))

        ttk.Label(conn_frame, text="User ID:").grid(row=0, column=2, sticky="w")
        self.user_entry = ttk.Entry(conn_frame, width=18)
        self.user_entry.insert(0, "doctor_user")
        self.user_entry.grid(row=0, column=3, sticky="ew")

        self.connect_button = ttk.Button(conn_frame, text="Connect", command=self.start_connection)
        self.connect_button.grid(row=0, column=4, sticky="e", padx=(6, 0))

        self.chat_display = ScrolledText(frame, wrap="word", state="disabled", width=88, height=24)
        self.chat_display.grid(row=1, column=0, sticky="nsew")
        frame.rowconfigure(1, weight=1)

        input_frame = ttk.Frame(frame)
        input_frame.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        input_frame.columnconfigure(0, weight=1)

        self.input_entry = ttk.Entry(input_frame)
        self.input_entry.grid(row=0, column=0, sticky="ew")
        self.input_entry.bind("<Return>", self.on_send_click)

        self.send_button = ttk.Button(input_frame, text="Send", command=self.on_send_click)
        self.send_button.grid(row=0, column=1, sticky="e", padx=(6, 0))

        self.status_label = ttk.Label(frame, text="Disconnected.")
        self.status_label.grid(row=3, column=0, sticky="w", pady=(6, 0))

        self.send_queue: queue.Queue[tuple[str, dict]] = queue.Queue()
        self.ws_thread: threading.Thread | None = None
        self.running = False
        self.pending_choice: dict | None = None

    def start_connection(self) -> None:
        if self.running:
            return
        url = self.url_entry.get().strip()
        user_id = self.user_entry.get().strip() or "doctor_user"
        self.ws_url = url.rstrip("/") + "/" + user_id
        self.append_text(f"Connecting to {self.ws_url}...\n")
        self.status_label.config(text="Connecting...")
        self.running = True
        self.connect_button.config(state="disabled")
        self.ws_thread = threading.Thread(target=self.run_ws_loop, daemon=True)
        self.ws_thread.start()

    def append_text(self, text: str) -> None:
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", text)
        self.chat_display.see("end")
        self.chat_display.configure(state="disabled")

    def update_status(self, status: str) -> None:
        self.root.after(0, lambda: self.status_label.config(text=status))

    def display_event(self, event: dict) -> None:
        ev_type = event.get("type")
        payload = event.get("payload", {})
        if ev_type == "thinking":
            self.append_text("[System] Ally is thinking...\n")
            self.update_status("Thinking...")
            return

        if ev_type == "text_delta":
            delta = payload.get("delta", "")
            self.append_text(delta)
            return

        if ev_type == "text":
            sender = payload.get("from", "Ally / Dr. Shankar")
            self.append_text(f"[{sender}] {payload.get('content', '')}\n")
            self.update_status("Connected")
            return

        if ev_type == "slot_select":
            options = payload.get("options", [])
            self.pending_choice = {"target": "slot", "options": options}
            self.append_text("[System] Available slots:\n")
            for option in options:
                self.append_text(f"   - {option.get('start_time')} (id: {option.get('id')})\n")
            self.append_text("[System] Type a slot id to choose it, or type any message to continue.\n")
            self.update_status("Choose a slot")
            return

        if ev_type == "doctor_select":
            options = payload.get("options", [])
            self.pending_choice = {"target": "doctor", "options": options}
            self.append_text("[System] Select a doctor if prompted:\n")
            for option in options:
                self.append_text(f"   - {option.get('name')} (id: {option.get('id')})\n")
            self.append_text("[System] Type a doctor id to choose it.\n")
            self.update_status("Choose doctor")
            return

        if ev_type == "lab_notification":
            self.pending_choice = {"target": "lab"}
            tests = payload.get("tests", [])
            self.append_text("[Doctor] Lab tests recommended:\n")
            for test in tests:
                self.append_text(f"   - {test.get('name')}: {test.get('reason', '')}\n")
            self.append_text("[System] Type 'accept' to proceed or 'reject' to skip.\n")
            self.update_status("Lab decision")
            return

        if ev_type == "report_ready":
            inbox_id = payload.get("inbox_id")
            self.append_text(f"[System] Report ready: {inbox_id}\n")
            self.update_status("Report ready")
            return

        self.append_text(f"[Event {ev_type}] {json.dumps(payload)}\n")

    def on_send_click(self, event: tk.Event | None = None) -> None:
        text = self.input_entry.get().strip()
        if not text or not self.running:
            return
        self.input_entry.delete(0, "end")
        message_text = text
        self.append_text(f"[You] {message_text}\n")

        if self.pending_choice is not None:
            target = self.pending_choice.get("target")
            options = self.pending_choice.get("options", [])
            option_ids = {o.get("id") for o in options}
            if target in {"slot", "doctor"} and message_text in option_ids:
                self.send_queue.put(("select", {"target": target, "id": message_text}))
                self.pending_choice = None
                return
            if target == "lab":
                decision = "accept" if message_text.lower() in {"accept", "yes", "ok", "sure"} else "reject"
                self.send_queue.put(("select", {"target": "lab", "decision": decision}))
                self.pending_choice = None
                return

        self.send_queue.put(("text", {"content": message_text}))

    async def send_loop(self, ws: websockets.WebSocketClientProtocol) -> None:
        while True:
            kind, payload = await asyncio.get_event_loop().run_in_executor(None, self.send_queue.get)
            if kind == "close":
                break
            if kind == "text":
                data = {"type": "text", "payload": payload}
            else:
                data = {"type": "select", "payload": payload}
            try:
                await ws.send(json.dumps(data))
            except Exception as exc:
                self.root.after(0, lambda: self.append_text(f"[Error] Failed to send: {exc}\n"))
                break

    async def recv_loop(self, ws: websockets.WebSocketClientProtocol) -> None:
        try:
            while True:
                text = await ws.recv()
                event = json.loads(text)
                self.root.after(0, lambda ev=event: self.display_event(ev))
        except websockets.ConnectionClosed:
            self.root.after(0, lambda: self.append_text("[System] Connection closed.\n"))
            self.root.after(0, lambda: self.update_status("Disconnected"))
        except Exception as exc:
            self.root.after(0, lambda: self.append_text(f"[Error] Receive failed: {exc}\n"))
            self.root.after(0, lambda: self.update_status("Error"))

    async def ws_main(self) -> None:
        try:
            async with websockets.connect(self.ws_url) as ws:
                self.root.after(0, lambda: self.update_status("Connected"))
                await asyncio.gather(self.recv_loop(ws), self.send_loop(ws))
        except Exception as exc:
            self.root.after(0, lambda: self.append_text(f"[Error] Connection failed: {exc}\n"))
            self.root.after(0, lambda: self.update_status("Disconnected"))

    def run_ws_loop(self) -> None:
        asyncio.set_event_loop(asyncio.new_event_loop())
        try:
            asyncio.get_event_loop().run_until_complete(self.ws_main())
        finally:
            self.running = False


if __name__ == "__main__":
    root = tk.Tk()
    app = DoctorGUI(root)
    root.mainloop()
