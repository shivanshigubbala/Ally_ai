from backend.cardiology.specialty.state import CardiologyState
from backend.cardiology.specialty.extractor import PatientInformationExtractor
from backend.cardiology.specialty.question_manager import QuestionManager
from backend.cardiology.specialty.reasoning import ClinicalReasoning


class ConsultationController:
    def __init__(self):
        self.extractor = PatientInformationExtractor()
        self.question_manager = QuestionManager()
        self.reasoning = ClinicalReasoning()

    def process_message(self, state: CardiologyState, patient_message: str):
        state = self.extractor.update_state(state, patient_message)
        next_question = self.question_manager.next_question(state)

        if next_question:
            return {"type": "question", "message": next_question, "state": state}

        result = self.reasoning.assess(state.symptoms)
        state.risk_level = result["risk"]
        state.recommended_tests = result["recommended_tests"]
        state.consultation_complete = True

        return {"type": "consultation_complete", "result": result, "state": state}
