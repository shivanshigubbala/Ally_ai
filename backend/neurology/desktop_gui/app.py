"""
Ally AI Neurology Desktop GUI

Developer GUI for testing the Neurology backend.
"""

from __future__ import annotations

import tkinter as tk
from tkinter.scrolledtext import ScrolledText

import requests

API_URL = "http://localhost:8000/chat"


class NeurologyGUI:

    def __init__(self):

        self.root = tk.Tk()
        self.root.title("Ally AI - Neurology Doctor")
        self.root.geometry("800x650")

        self.build_ui()

    def build_ui(self):

        title = tk.Label(
            self.root,
            text="Ally AI Neurology Doctor",
            font=("Segoe UI", 18, "bold"),
        )
        title.pack(pady=10)

        self.chat_box = ScrolledText(
            self.root,
            wrap=tk.WORD,
            state="disabled",
            font=("Segoe UI", 11),
        )

        self.chat_box.pack(
            fill=tk.BOTH,
            expand=True,
            padx=10,
            pady=10,
        )

        self.message_entry = tk.Entry(
            self.root,
            font=("Segoe UI", 12),
        )

        self.message_entry.pack(
            fill=tk.X,
            padx=10,
            pady=5,
        )

        self.message_entry.bind(
            "<Return>",
            self.send_message,
        )

        send_button = tk.Button(
            self.root,
            text="Send",
            command=self.send_message,
            height=2,
        )

        send_button.pack(
            pady=5,
        )

    def append_message(
        self,
        sender: str,
        message: str,
    ):

        self.chat_box.configure(state="normal")

        self.chat_box.insert(
            tk.END,
            f"{sender}: {message}\n\n",
        )

        self.chat_box.configure(state="disabled")
        self.chat_box.see(tk.END)

    def send_message(
        self,
        event=None,
    ):

        message = self.message_entry.get().strip()

        if not message:
            return

        self.append_message("Patient", message)

        self.message_entry.delete(
            0,
            tk.END,
        )

        try:

            response = requests.post(
                API_URL,
                json={
                    "message": message,
                },
                timeout=120,
            )

            response.raise_for_status()

            doctor_reply = response.json()["response"]

            self.append_message(
                "Doctor",
                doctor_reply,
            )

        except Exception as e:

            self.append_message(
                "Error",
                str(e),
            )

    def run(self):

        self.root.mainloop()


if __name__ == "__main__":

    NeurologyGUI().run()
