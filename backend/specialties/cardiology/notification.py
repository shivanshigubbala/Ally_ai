"""Message builders for cardiology consultation notifications.

Keeps user-facing copy for the lab-test prompt and the emergency alert
in one place, separate from the graph control flow, so wording can be
tuned/tested without touching backend/graphs/cardiology_agent.py.
"""

from __future__ import annotations


def build_lab_notification_message(tests: list[dict[str, str]]) -> str:
    test_names = ", ".join(t.get("name", "?") for t in tests)
    return (
        f"Based on what you've told me, I'd like to order a few cardiac tests "
        f"to be safe - {test_names}. This will help me get a clearer picture of "
        f"what's going on with your heart. Is that okay?"
    )


def build_no_tests_message() -> str:
    return (
        "Good news - based on everything you've told me, I don't see a need for "
        "cardiac tests right now. Let's keep an eye on things, and please come "
        "back right away if anything changes or gets worse."
    )


def build_emergency_message() -> str:
    return (
        "What you're describing could be a sign of a serious cardiac emergency. "
        "Please stop what you're doing and call your local emergency number or "
        "go to the nearest emergency room right now - don't wait or drive "
        "yourself if you can avoid it. I'm flagging this as urgent so the team "
        "here is aware."
    )


def build_lab_accept_message() -> str:
    return "Thanks - the lab has been requested. You'll get your cardiac report shortly!"


def build_lab_reject_message() -> str:
    return (
        "No problem. Please watch closely for any new or worsening symptoms - "
        "especially chest pain, breathlessness, or fainting - and seek care "
        "immediately if they occur."
    )


def build_report_ready_message() -> str:
    return "Your cardiac report is ready. Take care, and follow up if anything changes!"
