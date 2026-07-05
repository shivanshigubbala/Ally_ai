"""
Developer CLI for the Ally AI Neurology Doctor.

This utility allows developers to test the complete
Neurology RAG pipeline without using the frontend.

Usage:

python -m backend.neurology.tools.chat_cli
"""

from __future__ import annotations

import sys

from backend.neurology.rag.rag_pipeline import rag_pipeline


def print_banner() -> None:
    """Display welcome banner."""

    print("\n" + "=" * 70)
    print(" Ally AI - Neurology Doctor (Developer CLI)")
    print("=" * 70)
    print("Type 'exit' or 'quit' to stop.\n")


def main() -> None:
    """Start an interactive CLI session."""

    print_banner()

    conversation = ""

    while True:

        try:
            patient_message = input("Patient > ").strip()

        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye.")
            sys.exit(0)

        if not patient_message:
            continue

        if patient_message.lower() in {"exit", "quit"}:
            print("Session ended.")
            break

        try:

            response = rag_pipeline.answer(
                patient_message=patient_message,
                chief_complaint=patient_message,
                conversation=conversation,
            )

            print("\nDoctor >")
            print(response)
            print()

            conversation += (
                f"Patient: {patient_message}\n"
                f"Doctor: {response}\n\n"
            )

        except Exception as exc:

            print("\nERROR")
            print(exc)
            print()


if __name__ == "__main__":
    main()
