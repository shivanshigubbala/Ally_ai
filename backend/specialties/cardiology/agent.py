from typing import List, Dict

from backend.cardiology.specialty import ConsultationController
from backend.specialties.cardiology.prompt import CARDIOLOGY_SYSTEM_PROMPT
from backend.specialties.cardiology.llm_adapter import CardiologyLLMAdapter


class CardiologyAgent:

    def __init__(self):
        self.system_prompt = CARDIOLOGY_SYSTEM_PROMPT
        self.llm = CardiologyLLMAdapter()

    def consult(
        self,
        patient_message: str,
        history: List[Dict]
    ):

        messages = [
            {
                "role": "system",
                "content": self.system_prompt,
            }
        ]

        messages.extend(history)

        messages.append(
            {
                "role": "user",
                "content": patient_message,
            }
        )

        response = self.llm.chat(messages)

        return response