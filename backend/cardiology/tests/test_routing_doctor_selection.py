from backend.cardiology.agent import build_patient_context
from backend.cardiology.graphs import routing_graph
from backend.cardiology.models.session_state import DoctorState


def test_receptionist_emits_doctor_selection_before_slots():
    routing_graph.reset_state("test_user")
    state, events = routing_graph.run_step("test_user", "I feel sick", None)
    assert state.current_node == "HEALTH_STATUS_QUESTIONS"

    state, events = routing_graph.run_step("test_user", "It hurts on the left side", None)
    assert state.current_node == "HEALTH_STATUS_QUESTIONS"

    state, events = routing_graph.run_step("test_user", "I've had it for two days", None)
    assert state.current_node == "HEALTH_STATUS_QUESTIONS"

    state, events = routing_graph.run_step("test_user", "I also have a mild fever", None)
    assert state.current_node == "DOCTOR_SELECTION"
    assert any(event.type == "doctor_select" for event in events)


def test_receptionist_emits_single_follow_up_per_user_turn():
    routing_graph.reset_state("single_turn_user")

    state, events = routing_graph.run_step("single_turn_user", "I have a headache", None)

    text_events = [event for event in events if event.type == "text"]
    assert len(text_events) == 1, "A single user turn should produce one receptionist reply"
    assert state.current_node in {"HEALTH_STATUS_QUESTIONS", "INTENT_CLASSIFICATION"}


def test_build_patient_context_includes_profile_and_recent_history():
    state = DoctorState(
        user_id="ctx_user",
        appointment_id="apt-1",
        doctor_id="d5",
        department="general",
        patient_name="Maya Patel",
        patient_summary="Known patient with migraine history.",
        visit_summary="Follow-up visit for headache.",
        conversation_summary="Discussed duration and triggers.",
        uploaded_documents=[{"name": "report.pdf"}],
        conversation_history=[{"role": "user", "content": "I have a headache"}],
    )

    context = build_patient_context(state)

    assert "Patient Summary" in context
    assert "Recent Visits" in context
    assert "Current Complaint" in context
    assert "Conversation Summary" in context

