import unittest
from unittest.mock import patch

from backend.general_physician import (
    _build_initial_doctor_message,
    _sanitize_tests,
    _should_recommend_tests,
)
from backend.general_physician import agent as gp_agent
from backend.general_physician.models.session_state import DoctorState


class GeneralPhysicianAgentTests(unittest.TestCase):
    def test_no_tests_for_fine_patient(self):
        conversation = [
            {"role": "user", "content": "I'm feeling just fine, no symptoms at all."},
        ]
        self.assertFalse(
            _should_recommend_tests(
                parsed={"recommend_tests": True, "tests": [{"name": "CBC"}]},
                conversation=conversation,
                chief_complaint="feeling fine",
            )
        )

    def test_initial_message_is_specific_not_generic(self):
        msg = _build_initial_doctor_message(
            chief_complaint="I have a cough",
            patient_name="Asha",
        )
        self.assertIn("cough", msg.lower())
        self.assertNotIn("i'm glad", msg.lower())

    def test_sanitize_tests_allows_only_cbc_bmp(self):
        sanitized = _sanitize_tests([
            {"name": "CBC", "reason": "Check cells"},
            {"name": "BMP", "reason": "Check electrolytes"},
            {"name": "ESR", "reason": "Inflammation"},
            {"name": "MRI", "reason": "Imaging"},
        ])
        self.assertEqual(len(sanitized), 2)
        self.assertEqual(sanitized[0]["name"], "Complete Blood Count (CBC)")
        self.assertEqual(sanitized[1]["name"], "Basic Metabolic Panel (BMP)")

    def test_build_consultation_summary_includes_sections_and_recommendations(self):
        summary = gp_agent._build_consultation_summary(
            chief_complaint="headache",
            conversation_history=[
                {"role": "user", "content": "I have a headache"},
                {"role": "assistant", "content": "How long has it been going on?"},
                {"role": "user", "content": "Two days and it is severe"},
            ],
            tests_list=[{"name": "Complete Blood Count (CBC)", "reason": "Check blood count"}],
            notes="The pain is one-sided and worsened by light.",
        )

        self.assertEqual(summary["chief_complaint"], "headache")
        self.assertIn("two days", summary["symptoms"].lower())
        self.assertEqual(summary["assessment"], "The symptoms were reviewed and the patient was assessed for possible urgent causes.")
        self.assertEqual(len(summary["lab_recommendations"]), 1)
        self.assertEqual(summary["lab_recommendations"][0]["name"], "Complete Blood Count (CBC)")

    def test_persist_consultation_output_updates_context_metadata(self):
        state = DoctorState(
            user_id="patient_1",
            appointment_id="a1",
            doctor_id="d5",
            doctor_name="Dr. Shankar",
            department="general",
            consultation_context_id="ctx-1",
            conversation_history=[{"role": "user", "content": "I have a headache"}],
        )
        summary = gp_agent._build_consultation_summary(
            chief_complaint="headache",
            conversation_history=state.conversation_history,
            tests_list=[{"name": "Complete Blood Count (CBC)", "reason": "Check blood count"}],
            notes="The pain is one-sided.",
        )
        state.consultation_summary = summary
        state.consultation_recommendations = summary["lab_recommendations"]

        with patch("backend.general_physician.agent.upsert_consultation_context") as mock_upsert:
            mock_upsert.return_value = {"internal_uuid": "ctx-1"}
            gp_agent._persist_consultation_output(state)

        mock_upsert.assert_called_once()
        payload = mock_upsert.call_args.args[0]
        self.assertEqual(payload["internal_uuid"], "ctx-1")
        self.assertEqual(payload["consultation_status"], "COMPLETED")
        self.assertIn("consultation_summary", payload["metadata"])
        self.assertEqual(payload["metadata"]["consultation_summary"]["chief_complaint"], "headache")


if __name__ == "__main__":
    unittest.main()
