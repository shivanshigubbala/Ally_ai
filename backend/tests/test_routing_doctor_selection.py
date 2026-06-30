from backend.graphs import routing_graph


def test_receptionist_emits_doctor_selection_before_slots():
    routing_graph.reset_state("test_user")
    state, events = routing_graph.run_step("test_user", "I feel sick", None)

    assert state.current_node in {"DOCTOR_SELECTION", "SLOT_SELECTION"}
    assert any(event.type == "doctor_select" for event in events)
