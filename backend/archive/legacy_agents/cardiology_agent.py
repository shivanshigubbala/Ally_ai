from typing import List, Dict

from backend.specialties.cardiology.prompt import CARDIOLOGY_SYSTEM_PROMPT

try:
    from backend.llm.nvidia_client import chat
except ImportError:
    from llm.nvidia_client import chat


class CardiologyAgent:

    def __init__(self):
        self.system_prompt = CARDIOLOGY_SYSTEM_PROMPT

    def consult(self, patient_message: str, history: List[Dict]):
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": patient_message})
        response = chat(messages)
        return response
