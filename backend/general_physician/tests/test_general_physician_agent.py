import unittest

from backend.general_physician import (
    _build_initial_doctor_message,
    _sanitize_tests,
    _should_recommend_tests,
)


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


if __name__ == "__main__":
    unittest.main()
