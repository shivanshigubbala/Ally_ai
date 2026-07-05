"""
Neurology Response Generator.

Builds the Neurology system prompt and generates
doctor responses using the NVIDIA LLM client.
"""

from __future__ import annotations

import logging

from backend.neurology.llm.nvidia_client import llm_client
from backend.neurology.llm.prompts import NEUROLOGY_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """
    Generates responses from the Neurology LLM.
    """

    def generate(
        self,
        *,
        patient_message: str,
        chief_complaint: str = "",
        patient_summary: str = "",
        name: str = "Unknown",
        age: str = "Unknown",
        gender: str = "Unknown",
        medical_history: str = "None",
        medications: str = "None",
        conversation: str = "",
        rag_context: str = "",
        history: list[dict] | None = None,
    ) -> str:
        """
        Generate a doctor response.
        """

        logger.info("Generating Neurology response.")

        system_prompt = NEUROLOGY_SYSTEM_PROMPT.format(
            chief_complaint=chief_complaint,
            patient_summary=patient_summary,
            name=name,
            age=age,
            gender=gender,
            medical_history=medical_history,
            medications=medications,
            conversation=conversation,
            rag_context=rag_context,
        )

        response = llm_client.generate_response(
            system_prompt=system_prompt,
            user_prompt=patient_message,
            history=history,
        )

        return response.strip()


response_generator = ResponseGenerator()

__all__ = [
    "ResponseGenerator",
    "response_generator",
]
