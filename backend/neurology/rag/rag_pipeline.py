"""
Neurology Retrieval-Augmented Generation (RAG) Pipeline.

Coordinates the complete workflow:

Patient Question
        ↓
Retriever
        ↓
Relevant Neurology Knowledge
        ↓
Response Generator
        ↓
Doctor Response
"""

from __future__ import annotations

import logging

from backend.neurology.llm.response_generator import response_generator
from backend.neurology.rag.retriever import retriever

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    End-to-end Neurology RAG pipeline.
    """

    def answer(
        self,
        *,
        patient_message: str,
        chief_complaint: str = "",
        patient_summary: str = "",
        name: str = "Unknown",
        age: str = "Unknown",
        gender: str = "Unknown",
        medical_history: str = "",
        medications: str = "",
        conversation: str = "",
        history: list[dict] | None = None,
    ) -> str:
        """
        Retrieve relevant knowledge and generate
        a Neurology doctor's response.
        """

        logger.info("Starting Neurology RAG pipeline.")

        rag_context = retriever.retrieve_context(
            patient_message
        )

        logger.info(
            "Retrieved %d characters of RAG context.",
            len(rag_context),
        )

        response = response_generator.generate(
            patient_message=patient_message,
            chief_complaint=chief_complaint or patient_message,
            patient_summary=patient_summary,
            name=name,
            age=age,
            gender=gender,
            medical_history=medical_history,
            medications=medications,
            conversation=conversation,
            rag_context=rag_context,
            history=history,
        )

        logger.info("Neurology response generated.")

        return response


rag_pipeline = RAGPipeline()
