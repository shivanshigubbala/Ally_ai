from typing import List

EMERGENCY_KEYWORDS = [
    "left arm pain",
    "jaw pain",
    "crushing chest pain",
    "shortness of breath",
    "difficulty breathing",
    "fainting",
    "collapse",
    "severe sweating",
]

CHEST_PAIN_TESTS = ["ECG", "Troponin", "2D Echocardiogram"]
PALPITATION_TESTS = ["ECG", "Holter Monitor"]
HYPERTENSION_TESTS = ["ECG", "Lipid Profile"]


class ClinicalReasoning:
    def assess(self, symptoms: List[str]):
        symptoms = [s.lower() for s in symptoms]
        emergency = any(keyword in " ".join(symptoms) for keyword in EMERGENCY_KEYWORDS)

        if emergency:
            return {
                "risk": "Emergency",
                "tests_required": True,
                "recommended_tests": ["ECG", "Troponin"],
                "needs_more_questions": False,
            }

        if "chest pain" in symptoms:
            return {
                "risk": "Moderate",
                "tests_required": True,
                "recommended_tests": CHEST_PAIN_TESTS,
                "needs_more_questions": True,
            }

        if "palpitations" in symptoms:
            return {
                "risk": "Moderate",
                "tests_required": True,
                "recommended_tests": PALPITATION_TESTS,
                "needs_more_questions": True,
            }

        if "high blood pressure" in symptoms:
            return {
                "risk": "Low",
                "tests_required": True,
                "recommended_tests": HYPERTENSION_TESTS,
                "needs_more_questions": False,
            }

        return {
            "risk": "Low",
            "tests_required": False,
            "recommended_tests": [],
            "needs_more_questions": True,
        }
