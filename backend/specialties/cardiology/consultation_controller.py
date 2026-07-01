from backend.specialties.cardiology.state import CardiologyState

from backend.specialties.cardiology.extractor import (
    PatientInformationExtractor,
)

from backend.specialties.cardiology.question_manager import (
    QuestionManager,
)

from backend.specialties.cardiology.reasoning import (
    ClinicalReasoning,
)


class ConsultationController:

    def __init__(self):

        self.extractor = PatientInformationExtractor()

        self.question_manager = QuestionManager()

        self.reasoning = ClinicalReasoning()

    def process_message(
        self,
        state: CardiologyState,
        patient_message: str,
    ):

        # Step 1
        state = self.extractor.update_state(
            state,
            patient_message,
        )

        # Step 2
        next_question = self.question_manager.next_question(
            state
        )

        if next_question:

            return {
                "type": "question",
                "message": next_question,
                "state": state,
            }

        # Step 3

        result = self.reasoning.assess(
            state.symptoms,
        )

        state.risk_level = result["risk"]

        state.recommended_tests = result[
            "recommended_tests"
        ]

        state.consultation_complete = True

        return {
            "type": "consultation_complete",
            "result": result,
            "state": state,
        }