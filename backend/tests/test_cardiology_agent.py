import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from backend.graphs.cardiology_agent import (
        _build_initial_doctor_message,
        _is_emergency,
        _should_recommend_tests,
    )
    from backend.specialties.cardiology.test_recommender import sanitize_tests
except ImportError:
    from graphs.cardiology_agent import (
        _build_initial_doctor_message,
        _is_emergency,
        _should_recommend_tests,
    )
    from specialties.cardiology.test_recommender import sanitize_tests


class CardiologyAgentTests(unittest.TestCase):
    def test_no_tests_for_fine_patient(self):
        conversation = [
            {"role": "user", "content": "I'm feeling just fine, no symptoms at all."},
        ]
        self.assertFalse(
            _should_recommend_tests(
                parsed={"recommend_tests": True, "tests": [{"name": "ECG"}]},
                conversation=conversation,
                chief_complaint="feeling fine",
            )
        )

    def test_tests_recommended_for_chest_pain(self):
        conversation = [
            {"role": "user", "content": "I've had chest pain for the last hour."},
        ]
        self.assertTrue(
            _should_recommend_tests(
                parsed={"recommend_tests": True, "tests": [{"name": "ECG"}]},
                conversation=conversation,
                chief_complaint="chest pain",
            )
        )

    def test_initial_message_mentions_chest_pain(self):
        msg = _build_initial_doctor_message(
            chief_complaint="I have chest pain",
            patient_name="Asha",
        )
        self.assertIn("chest pain", msg.lower())

    def test_emergency_detection_true_for_red_flag(self):
        self.assertTrue(_is_emergency("I have severe chest pain and can't breathe"))

    def test_emergency_detection_false_for_mild_symptom(self):
        self.assertFalse(_is_emergency("I've been feeling a bit tired lately"))

    def test_sanitize_tests_normalizes_names(self):
        sanitized = sanitize_tests([
            {"name": "ecg", "reason": ""},
            {"name": "2D Echo", "reason": "Check function"},
            {"name": "MRI Brain", "reason": "Imaging"},
        ])
        names = [t["name"] for t in sanitized]
        self.assertIn("ECG", names)
        self.assertIn("Echocardiogram", names)
        self.assertNotIn("MRI Brain", names)


if __name__ == "__main__":
    unittest.main()
