"""
Consultation Controller for Neurology Doctor Agent.

This module defines the high-level controller structure for future
consultation orchestration.

Responsibilities:
- Coordinate existing Neurology service dependencies
- Provide extension points for consultation handling
- Keep future prompt and response generation logic isolated

NOT responsible for:
- Implementing consultation workflow logic
- MRI recommendations
- Blood Test recommendations
- Diagnosis
- Duplicating QuestionManager, Retriever, or LLM behavior
"""

from __future__ import annotations

import logging
from typing import Any

from backend.neurology.llm import NvidiaLLMClient, llm_client
from backend.neurology.models.session_state import NeurologyDoctorState
from backend.neurology.rag.retriever import Retriever
from backend.neurology.services.lab_decision_handler import LabDecisionHandler
from backend.neurology.services.lab_report_handler import LabReportHandler
from backend.neurology.services.question_manager import QuestionManager
from backend.neurology.services.test_recommender import TestRecommender

logger = logging.getLogger(__name__)


class ConsultationController:
    """
    Coordinates Neurology consultation dependencies.

    The controller is intentionally limited to dependency setup in this
    phase. Future commits will use these collaborators to orchestrate
    consultation turns, retrieve medical context, build prompts, and generate
    patient-facing responses.
    """

    QUESTIONING = "QUESTIONING"
    EVALUATION = "EVALUATION"

    def __init__(self) -> None:
        """Initialize the Consultation Controller dependencies."""

        self.logger = logging.getLogger(__name__)
        self.question_manager = QuestionManager()
        self.retriever = Retriever()
        self.test_recommender = TestRecommender()
        self.lab_decision_handler = LabDecisionHandler()
        self.lab_report_handler = LabReportHandler()
        self.llm_client: NvidiaLLMClient = llm_client

        self.logger.info("Consultation Controller initialized")

    def receive_report(
        self,
        state: NeurologyDoctorState,
        report_type: str,
        report_data: dict[str, Any],
    ) -> NeurologyDoctorState:
        """
        Receive a Neurology lab report and store it in consultation state.

        Delegates report validation and storage to LabReportHandler. The
        controller does not interpret report contents, diagnose, or call
        external services.

        Args:
            state: Current Neurology doctor consultation state.
            report_type: Type of report received.
            report_data: Raw report payload to store.

        Returns:
            Updated Neurology doctor consultation state.
        """
        updated_state = self.lab_report_handler.receive_report(
            state=state,
            report_type=report_type,
            report_data=report_data,
        )

        self.logger.info(
            "Lab report received",
            extra={
                "user_id": updated_state.user_id,
                "report_type": report_type,
            },
        )

        return updated_state

    def handle_consultation(
        self,
        state: NeurologyDoctorState,
        user_message: str,
    ) -> tuple[NeurologyDoctorState, str]:
        """
        Handle a single Neurology consultation turn.

        Coordinates the existing QuestionManager, Retriever, and LLM client
        for one patient message. The method delegates state updates and
        patient-information extraction to QuestionManager, retrieves Neurology
        knowledge with Retriever, builds a context-aware prompt, and generates
        a patient-facing response through the shared LLM client.

        Args:
            state: Current Neurology doctor consultation state.
            user_message: Latest patient message to process.

        Returns:
            Tuple containing the updated consultation state and generated LLM
            response.

        Raises:
            ValueError: If the incoming state is invalid.
            Exception: Propagates unexpected dependency failures after logging.
        """
        try:
            self.question_manager.validate_state(state)

            self.logger.info(
                "Consultation started",
                extra={
                    "user_id": state.user_id,
                    "appointment_id": state.appointment_id,
                    "message_length": len(user_message),
                },
            )

            lab_decision = self._extract_lab_decision(
                state=state,
                user_message=user_message,
            )

            if lab_decision:
                updated_state = self.lab_decision_handler.handle_decision(
                    state=state,
                    decision=lab_decision,
                )

                self.logger.info(
                    "Lab decision handled",
                    extra={
                        "user_id": updated_state.user_id,
                        "decision": lab_decision,
                    },
                )

                return updated_state, "Your decision has been recorded."

            updated_state = self.question_manager.process_turn(
                state=state,
                user_message=user_message,
            )

            next_step = self._determine_next_step(updated_state)

            self.logger.info(
                "Consultation decision selected",
                extra={
                    "user_id": updated_state.user_id,
                    "next_step": next_step,
                },
            )

            if next_step == self.QUESTIONING:
                self.logger.info(
                    "Questioning branch selected",
                    extra={"user_id": updated_state.user_id},
                )

                followup_response = (
                    self.question_manager.generate_followup_question(
                        updated_state
                    )
                )

                self.logger.info(
                    "Response generated",
                    extra={
                        "user_id": updated_state.user_id,
                        "response_length": len(followup_response),
                    },
                )

                return updated_state, followup_response

            self.logger.info(
                "Evaluation branch selected",
                extra={"user_id": updated_state.user_id},
            )

            retrieval_query = self.question_manager.build_retrieval_query(
                updated_state
            )

            retrieved_chunks: list[dict[str, Any]] = []
            medical_context = ""

            if retrieval_query:
                retrieved_chunks = self.retriever.retrieve(query=retrieval_query)
                updated_state.rag_chunks = retrieved_chunks
                medical_context = self.retriever.retrieve_context(
                    query=retrieval_query
                )
            else:
                updated_state.rag_chunks = []

            self.logger.info(
                "Retrieval completed",
                extra={
                    "user_id": updated_state.user_id,
                    "query_length": len(retrieval_query),
                    "chunk_count": len(updated_state.rag_chunks),
                    "context_length": len(medical_context),
                },
            )

            system_prompt, user_prompt = self._build_prompt(
                state=updated_state,
                medical_context=medical_context,
                latest_user_message=user_message,
            )

            self.logger.info(
                "Prompt built",
                extra={
                    "user_id": updated_state.user_id,
                    "system_prompt_length": len(system_prompt),
                    "user_prompt_length": len(user_prompt),
                },
            )

            llm_response = self._generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                history=updated_state.conversation_history,
            )

            self.logger.info(
                "Response generated",
                extra={
                    "user_id": updated_state.user_id,
                    "response_length": len(llm_response),
                },
            )

            self._evaluate_test_recommendations(updated_state)

            return updated_state, llm_response

        except ValueError:
            self.logger.exception(
                "Consultation state validation failed",
                extra={"user_id": getattr(state, "user_id", "unknown")},
            )
            raise

        except Exception as e:
            self.logger.exception(
                "Consultation handling failed",
                extra={
                    "user_id": getattr(state, "user_id", "unknown"),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise

    def _extract_lab_decision(
        self,
        state: NeurologyDoctorState,
        user_message: str,
    ) -> str | None:
        """
        Extract a supported lab decision from a patient message.

        The controller only detects whether a pending recommended-test decision
        is present. State updates are delegated to LabDecisionHandler.

        Args:
            state: Current Neurology doctor consultation state.
            user_message: Latest patient message.

        Returns:
            "accept", "decline", or None when the message is not a supported
            lab decision.
        """
        if not state.tests_recommended:
            return None

        normalized_message = user_message.strip().lower()

        if normalized_message == self.lab_decision_handler.ACCEPT:
            return self.lab_decision_handler.ACCEPT

        if normalized_message == self.lab_decision_handler.DECLINE:
            return self.lab_decision_handler.DECLINE

        return None

    def _evaluate_test_recommendations(
        self,
        state: NeurologyDoctorState,
    ) -> None:
        """
        Evaluate test recommendations and update consultation state flags.

        Delegates recommendation decisions to TestRecommender and only updates
        state fields that track whether tests were recommended. This method
        does not order tests, call lab services, book appointments, or change
        the user's lab decision.

        Args:
            state: Current Neurology doctor consultation state.
        """
        self.logger.info(
            "Evaluating test recommendations",
            extra={"user_id": state.user_id},
        )

        recommended_tests = self.test_recommender.recommend_tests(state)

        if recommended_tests:
            state.tests_recommended = True
            state.recommended_tests = recommended_tests

            if self.test_recommender.MRI_BRAIN in recommended_tests:
                self.logger.info(
                    "MRI recommended",
                    extra={"user_id": state.user_id},
                )

            if self.test_recommender.BLOOD_TEST_PANEL in recommended_tests:
                self.logger.info(
                    "Blood Test recommended",
                    extra={"user_id": state.user_id},
                )

            return

        state.tests_recommended = False
        state.recommended_tests = []

        self.logger.info(
            "No tests required",
            extra={"user_id": state.user_id},
        )

    def _determine_next_step(
        self,
        state: NeurologyDoctorState,
    ) -> str:
        """
        Determine whether the consultation should continue questioning.

        Uses the existing QuestionManager readiness checks so required
        information rules remain centralized in one service.

        Args:
            state: Current Neurology doctor consultation state.

        Returns:
            QUESTIONING if required information is missing, otherwise
            EVALUATION.
        """
        if self.question_manager.is_ready_for_evaluation(state):
            return self.EVALUATION

        return self.QUESTIONING

    def _build_prompt(
        self,
        state: NeurologyDoctorState,
        medical_context: str,
        latest_user_message: str,
    ) -> tuple[str, str]:
        """
        Build system and user prompts for the Neurology consultation response.

        Assembles prompt inputs from the current consultation state,
        conversation history, patient summary, retrieved medical context, and
        the latest patient message. The prompt is constrained to supportive
        consultation dialogue and must not add diagnosis or investigation
        recommendation behavior.

        Args:
            state: Current Neurology doctor consultation state.
            medical_context: Formatted medical context returned by Retriever.
            latest_user_message: Latest patient message in the consultation.

        Returns:
            Tuple containing the system prompt and user prompt.
        """
        health_data = state.health_data or {}
        conversation_history = state.conversation_history or []

        history_lines = []
        for message in conversation_history:
            role = message.get("role", "unknown")
            content = message.get("content", "")

            if content:
                history_lines.append(f"{role}: {content}")

        patient_summary_parts = []

        if state.patient_summary:
            patient_summary_parts.append(state.patient_summary)

        if state.visit_summary:
            patient_summary_parts.append(state.visit_summary)

        if state.symptom_summary:
            patient_summary_parts.append(state.symptom_summary)

        if health_data:
            patient_summary_parts.append(f"Health Data: {health_data}")

        system_prompt = """You are an experienced and empathetic neurologist conducting an initial patient consultation.

Your role is to respond conversationally, ask appropriate follow-up questions, and help collect relevant neurological history.

IMPORTANT RULES:
1. Do not diagnose the patient
2. Do not recommend MRI, Blood Tests, or other investigations
3. Do not provide treatment plans
4. Do not generate final medical recommendations
5. Keep the response professional, concise, and patient-facing"""

        prompt_parts = [
            "Neurology Consultation Context:",
            "",
            "Patient Summary:",
            "\n".join(patient_summary_parts) if patient_summary_parts else "Not available.",
            "",
            "Conversation History:",
            "\n".join(history_lines) if history_lines else "No prior conversation.",
            "",
            "Retrieved Medical Context:",
            medical_context if medical_context else "No retrieved context available.",
            "",
            "Latest Patient Message:",
            latest_user_message,
            "",
            (
                "Respond to the patient using the context above. Continue the "
                "consultation without diagnosis or test recommendation logic."
            ),
        ]

        return system_prompt, "\n".join(prompt_parts)

    def _generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        """
        Generate a Neurology consultation response using the existing LLM client.

        Future implementation will delegate response generation to the shared
        Neurology LLM client and normalize the returned assistant message for
        use by the consultation controller.

        Args:
            system_prompt: System instructions for the LLM.
            user_prompt: User prompt containing consultation context.
            history: Optional prior conversation history in chat-message form.

        Returns:
            Generated assistant response text.

        Raises:
            Exception: Propagates LLM client failures after the shared client
                logs request details.
        """
        return self.llm_client.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            history=history,
        )


__all__ = ["ConsultationController"]
