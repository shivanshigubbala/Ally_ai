from backend.cardiology.specialty.state import CardiologyState


class QuestionManager:
    def next_question(self, state: CardiologyState):
        if not state.symptoms:
            return "Can you please describe your symptoms in more detail?"

        if "chest pain" in state.symptoms:
            if not state.pain_location:
                return "Where exactly is the chest pain located?"
            if not state.duration:
                return "How long have you been experiencing the pain?"
            if not state.pain_radiation:
                return "Does the pain spread to your left arm, jaw, shoulder, or back?"
            if not state.severity:
                return "On a scale of 1 to 10, how severe is the pain?"

        if not state.diabetes:
            return "Do you have diabetes?"
        if not state.hypertension:
            return "Have you ever been diagnosed with high blood pressure?"
        if not state.smoking:
            return "Do you smoke or have you smoked in the past?"
        if not state.family_history:
            return "Does anyone in your family have heart disease?"

        return None
