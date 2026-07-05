"""
Question Manager for Neurology Doctor Agent.

This module orchestrates the consultation workflow by managing state transitions,
tracking information collection, and determining when the consultation is ready
for evaluation.

Responsibilities:
- Manage consultation turns
- Track conversation history
- Extract and validate patient information
- Determine workflow state transitions
- Track question count and turn count

NOT responsible for:
- LLM inference
- RAG retrieval
- Diagnosis
- Test recommendations
- Report generation
"""

from __future__ import annotations

import logging
import re
from typing import Any

from backend.neurology.config import settings
from backend.neurology.llm.nvidia_client import llm_client
from backend.neurology.models.session_state import (
    NeurologyDoctorState,
    NeurologyTest,
)
from backend.neurology.services.patient_information_extractor import (
    PatientInformationExtractor,
)

try:
    from backend.neurology.rag import retriever
except ImportError:
    retriever = None

logger = logging.getLogger(__name__)


class QuestionManager:
    """
    Orchestrates the Neurology consultation workflow.
    """

    # Workflow constants
    QUESTIONING = "QUESTIONING"
    READY_FOR_EVALUATION = "EVALUATION"
    EMERGENCY = "EMERGENCY"

    REQUIRED_FIELDS = {
        "chief_complaint",
        "duration",
        "severity",
        "symptoms",
    }

    def __init__(self) -> None:
        """Initialize the Question Manager."""

        self.logger = logging.getLogger(__name__)
        self.patient_information_extractor = PatientInformationExtractor()

        self.logger.info("Question Manager initialized")

    def process_turn(
        self, state: NeurologyDoctorState, user_message: str
    ) -> NeurologyDoctorState:
        """
        Process a single consultation turn.

        This method manages the entire workflow for one turn:
        1. Validates the state
        2. Adds the user message to conversation history
        3. Extracts patient information
        4. Updates turn and question counts
        5. Determines next action
        6. Returns the updated state

        Args:
            state: Current consultation state
            user_message: User's message in this turn

        Returns:
            Updated consultation state

        Raises:
            ValueError: If state is invalid
        """
        try:
            # Validate state
            self.validate_state(state)

            logger.info(
                "Processing consultation turn",
                extra={
                    "user_id": state.user_id,
                    "turn_count": state.turn_count,
                    "message_length": len(user_message),
                },
            )

            # Add user message to conversation history
            self.update_conversation_history(state, "user", user_message)

            # Extract information from the message
            state = self.patient_information_extractor.extract_information(state)

            logger.info(
                "Patient information extracted",
                extra={"user_id": state.user_id},
            )

            # Update conversation history to record extraction
            self.update_conversation_history(
                state,
                "assistant",
                "Information noted and processed.",
            )

            logger.info(
                "Conversation updated",
                extra={"user_id": state.user_id},
            )

            # Increment counters
            self.increment_turn(state)
            self.increment_questions(state)

            # Determine next action
            next_action = self.determine_next_action(state)

            # Check for emergency
            if self.detect_emergency(state):
                logger.warning(
                    "Emergency detected, transitioning to EMERGENCY node",
                    extra={"user_id": state.user_id},
                )
                return state

            # If questioning is complete, evaluate investigations
            if next_action == self.READY_FOR_EVALUATION:
                # Retrieve medical context
                self.retrieve_medical_context(state)

                # Check if consultation is complete
                if self.is_consultation_complete(state):
                    logger.info(
                        "Consultation questioning complete",
                        extra={"user_id": state.user_id},
                    )

                    # Evaluate investigations
                    self.evaluate_investigations(state)

                    # Set final recommendation summary
                    state.final_recommendation = (
                        "Neurology consultation completed. "
                        f"Tests recommended: {len(state.recommended_tests)}. "
                        "Ready for physician evaluation."
                    )

                    logger.info(
                        "Ready for evaluation",
                        extra={
                            "user_id": state.user_id,
                            "tests_recommended": state.tests_recommended,
                            "test_count": len(state.recommended_tests),
                        },
                    )

            logger.info(
                "Question Manager completed",
                extra={
                    "user_id": state.user_id,
                    "current_node": state.current_node,
                    "turn_count": state.turn_count,
                },
            )

            return state

        except ValueError as e:
            logger.error(
                f"State validation failed: {e}",
                extra={"user_id": getattr(state, "user_id", "unknown")},
            )
            raise

        except Exception as e:
            logger.error(
                f"Error processing consultation turn: {e}",
                extra={
                    "user_id": getattr(state, "user_id", "unknown"),
                    "error_type": type(e).__name__,
                },
            )
            raise

    def validate_state(self, state: NeurologyDoctorState) -> None:
        """
        Validate that the state contains all required fields.

        Args:
            state: State to validate

        Raises:
            ValueError: If required fields are missing
        """
        if not state:
            raise ValueError("State cannot be None")

        required_attributes = [
            "user_id",
            "appointment_id",
            "doctor_id",
            "conversation_history",
            "health_data",
        ]

        for attr in required_attributes:
            if not hasattr(state, attr):
                raise ValueError(f"State missing required attribute: {attr}")

        if not state.user_id:
            raise ValueError("State user_id cannot be empty")

        if not isinstance(state.conversation_history, list):
            raise ValueError("conversation_history must be a list")

        if not isinstance(state.health_data, dict):
            raise ValueError("health_data must be a dictionary")
        return True

    def update_conversation_history(
        self, state: NeurologyDoctorState, role: str, content: str
    ) -> None:
        """
        Add a message to the conversation history.

        Args:
            state: Current state to update
            role: Message role ("user", "assistant", "system")
            content: Message content
        """
        message = {"role": role, "content": content}
        state.conversation_history.append(message)

    def increment_turn(self, state: NeurologyDoctorState) -> None:
        """
        Increment the turn counter.

        Args:
            state: Current state to update
        """
        state.turn_count += 1

    def increment_questions(self, state: NeurologyDoctorState) -> None:
        """
        Increment the questions asked counter.

        Args:
            state: Current state to update
        """
        state.questions_asked += 1

    def determine_next_action(self, state: NeurologyDoctorState) -> str:
        """
        Determine the next workflow action based on collected information.

        Returns one of:
        - QUESTIONING: More information is needed
        - READY_FOR_EVALUATION: All required information collected
        - EMERGENCY: Emergency detected

        Args:
            state: Current state

        Returns:
            Next action constant
        """
        # Check for emergency flags in health_data
        if state.health_data.get("red_flag_symptoms"):
            logger.warning(
                "Emergency indicators detected",
                extra={"user_id": state.user_id},
            )
            state.current_node = self.EMERGENCY
            return self.EMERGENCY

        # Check if ready for evaluation
        if self.is_ready_for_evaluation(state):
            logger.info(
                "Ready for evaluation",
                extra={"user_id": state.user_id},
            )
            state.current_node = self.READY_FOR_EVALUATION
            return self.READY_FOR_EVALUATION

        # Need more information
        missing = self.get_missing_fields(state)
        logger.info(
            "Missing information",
            extra={
                "user_id": state.user_id,
                "missing_fields": missing,
            },
        )
        state.current_node = self.QUESTIONING
        return self.QUESTIONING

    def has_required_information(self, state: NeurologyDoctorState) -> bool:
        """
        Check if all required information has been collected.

        Required fields:
        - chief_complaint
        - duration
        - severity
        - symptoms

        Args:
            state: Current state

        Returns:
            True if all required fields exist and are non-empty
        """
        health_data = state.health_data or {}

        for field in self.REQUIRED_FIELDS:
            value = health_data.get(field)

            # String fields must be non-empty
            if isinstance(value, str):
                if not value or not value.strip():
                    return False

            # List fields must have at least one item
            elif isinstance(value, list):
                if not value or len(value) == 0:
                    return False

            # Missing field
            else:
                return False

        return True

    def get_missing_fields(self, state: NeurologyDoctorState) -> list[str]:
        """
        Get list of missing required fields.

        Args:
            state: Current state

        Returns:
            List of missing field names
        """
        missing = []
        health_data = state.health_data or {}

        for field in self.REQUIRED_FIELDS:
            value = health_data.get(field)

            # String fields must be non-empty
            if isinstance(value, str):
                if not value or not value.strip():
                    missing.append(field)

            # List fields must have at least one item
            elif isinstance(value, list):
                if not value or len(value) == 0:
                    missing.append(field)

            # Missing field
            else:
                missing.append(field)

        return missing

    def is_ready_for_evaluation(self, state: NeurologyDoctorState) -> bool:
        """
        Determine if the consultation has enough information for evaluation.

        The consultation is ready for evaluation when:
        - All required fields are present
        - All required fields have meaningful values
        - No required fields are missing

        Args:
            state: Current state

        Returns:
            True if ready for evaluation, False otherwise
        """
        return self.has_required_information(state)

    def build_system_prompt(self) -> str:
        """
        Build the system prompt for the Neurology LLM.

        Instructs the LLM to behave like an experienced neurologist
        conducting an initial consultation while collecting information.

        Returns:
            System prompt string
        """
        return """You are an experienced and empathetic neurologist conducting an initial patient consultation.

Your role is to gather detailed information about the patient's neurological symptoms and medical history.

IMPORTANT RULES:
1. Ask ONE question at a time
2. Be empathetic and professional
3. NEVER diagnose or provide medical opinions
4. NEVER recommend specific tests or treatments
5. NEVER mention MRI or Blood Test specifically
6. NEVER explain diseases or conditions
7. Focus ONLY on collecting information
8. Ask follow-up questions to clarify symptoms
9. Your response should be a single, clear question

Respond with ONLY the question, nothing else."""

    def build_user_prompt(
        self,
        state: NeurologyDoctorState,
        missing_fields: list[str],
    ) -> str:
        """
        Build the user prompt with consultation context.

        Explains what information is known and what is still missing.

        Args:
            state: Current consultation state
            missing_fields: List of missing required fields

        Returns:
            User prompt string
        """
        health_data = state.health_data or {}

        # Get known information
        chief_complaint = health_data.get("chief_complaint", "")
        symptom_summary = health_data.get("symptoms", [])
        duration = health_data.get("duration", "")
        severity = health_data.get("severity", "")

        # Build context
        prompt_parts = [
            "Patient Consultation Information:",
            "",
        ]

        if chief_complaint:
            prompt_parts.append(f"Chief Complaint: {chief_complaint}")

        if symptom_summary:
            symptoms_str = ", ".join(symptom_summary)
            prompt_parts.append(f"Reported Symptoms: {symptoms_str}")

        if duration:
            prompt_parts.append(f"Duration: {duration}")

        if severity:
            prompt_parts.append(f"Severity: {severity}")

        prompt_parts.extend([
            "",
            "Missing Information Still Needed:",
        ])

        for field in missing_fields:
            prompt_parts.append(f"- {field}")

        prompt_parts.extend([
            "",
            "Based on the information above, ask ONE follow-up question to gather more information.",
            "Focus on the missing fields.",
            "Do not ask about tests or treatments.",
        ])

        return "\n".join(prompt_parts)

    def generate_followup_question(self, state: NeurologyDoctorState) -> str:
        """
        Generate a follow-up question using the NVIDIA LLM.

        This method:
        1. Identifies missing required fields
        2. Builds system and user prompts
        3. Calls the LLM
        4. Cleans and validates the response
        5. Adds the question to conversation history

        If LLM fails, returns a safe fallback question.

        Args:
            state: Current consultation state

        Returns:
            Follow-up question string
        """
        try:
            # Get missing fields
            missing_fields = self.get_missing_fields(state)

            if not missing_fields:
                logger.warning(
                    "No missing fields for question generation",
                    extra={"user_id": state.user_id},
                )
                return self._get_fallback_question()

            logger.info(
                "Building prompts for question generation",
                extra={
                    "user_id": state.user_id,
                    "missing_fields": missing_fields,
                },
            )

            # Build prompts
            system_prompt = self.build_system_prompt()
            user_prompt = self.build_user_prompt(state, missing_fields)

            logger.info(
                "Calling NVIDIA LLM for question generation",
                extra={"user_id": state.user_id},
            )

            # Call LLM
            response = llm_client.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                history=state.conversation_history,
            )

            # Clean and validate response
            question = self.clean_question(response)

            if not question:
                logger.warning(
                    "LLM returned empty question after cleaning",
                    extra={"user_id": state.user_id},
                )
                return self._get_fallback_question()

            logger.info(
                "Question generated",
                extra={
                    "user_id": state.user_id,
                    "question_length": len(question),
                },
            )

            return question

        except Exception as e:
            logger.error(
                "Error generating question",
                extra={
                    "user_id": state.user_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            return self._get_fallback_question()

    def clean_question(self, raw_response: str) -> str:
        """
        Clean and normalize a generated question.

        This method:
        1. Strips whitespace
        2. Removes numbering (1., 2., etc.)
        3. Removes bullet points
        4. Extracts first meaningful question if multiple present
        5. Ensures question ends with '?'

        Args:
            raw_response: Raw LLM response

        Returns:
            Cleaned question string
        """
        if not raw_response:
            return ""

        # Strip whitespace
        text = raw_response.strip()

        # Remove numbering (1., 2., etc.)
        text = re.sub(r"^\d+\.\s*", "", text)

        # Remove bullet points (-, *, •)
        text = re.sub(r"^[\-\*•]\s*", "", text)

        # Split by question marks and take first meaningful sentence
        sentences = text.split("?")
        if sentences:
            first_part = sentences[0].strip()

            # Remove any remaining prefixes
            first_part = re.sub(r"^[\d\.\-\*•\s]+", "", first_part)
            first_part = first_part.strip()

            if first_part:
                # Ensure it ends with ?
                if not first_part.endswith("?"):
                    first_part += "?"
                return first_part

        return ""

    def _get_fallback_question(self) -> str:
        """
        Get a safe fallback question when LLM fails.

        Returns:
            Fallback question string
        """
        fallback = "Could you tell me a little more about your symptoms?"
        logger.info("Using fallback question")
        return fallback

    def should_use_rag(self, state: NeurologyDoctorState) -> bool:
        """
        Determine if RAG retrieval should be performed.

        RAG is used only when sufficient patient information has been collected:
        - Chief complaint exists
        - Symptoms exist
        - Duration exists
        - Severity exists

        Args:
            state: Current consultation state

        Returns:
            True if all required fields exist, False otherwise
        """
        health_data = state.health_data or {}

        # Check all required fields
        chief_complaint = health_data.get("chief_complaint", "")
        symptoms = health_data.get("symptoms", [])
        duration = health_data.get("duration", "")
        severity = health_data.get("severity", "")

        has_chief_complaint = bool(chief_complaint and chief_complaint.strip())
        has_symptoms = bool(symptoms and len(symptoms) > 0)
        has_duration = bool(duration and duration.strip())
        has_severity = bool(severity and severity.strip())

        logger.info(
            "Checking if RAG is required",
            extra={
                "user_id": state.user_id,
                "has_chief_complaint": has_chief_complaint,
                "has_symptoms": has_symptoms,
                "has_duration": has_duration,
                "has_severity": has_severity,
            },
        )

        return (
            has_chief_complaint
            and has_symptoms
            and has_duration
            and has_severity
        )

    def build_retrieval_query(self, state: NeurologyDoctorState) -> str:
        """
        Build a concise medical search query for RAG retrieval.

        Uses chief complaint, symptoms, duration, severity, and medical history
        to create a focused search query.

        Args:
            state: Current consultation state

        Returns:
            Concise medical search query string
        """
        health_data = state.health_data or {}

        query_parts = []

        # Add chief complaint
        chief_complaint = health_data.get("chief_complaint", "").strip()
        if chief_complaint:
            query_parts.append(chief_complaint)

        # Add symptoms
        symptoms = health_data.get("symptoms", [])
        if symptoms and isinstance(symptoms, list):
            query_parts.extend(symptoms)

        # Add duration
        duration = health_data.get("duration", "").strip()
        if duration:
            query_parts.append(duration)

        # Add severity
        severity = health_data.get("severity", "").strip()
        if severity:
            query_parts.append(severity)

        # Add medical history if available
        medical_history = health_data.get("medical_history", [])
        if medical_history and isinstance(medical_history, list):
            query_parts.extend(medical_history[:2])  # Limit to 2 items

        # Join all parts into a concise query
        query = " ".join(query_parts).strip()

        logger.info(
            "Building retrieval query",
            extra={
                "user_id": state.user_id,
                "query_length": len(query),
            },
        )

        return query

    def retrieve_medical_context(self, state: NeurologyDoctorState) -> None:
        """
        Retrieve medical context relevant to the patient's condition.

        Calls the Neurology Retriever to find relevant medical knowledge
        based on the patient's symptoms and medical history. Retrieved chunks
        are stored in state.rag_chunks for later use.

        If retrieval fails, sets state.rag_chunks to an empty list and continues.

        Args:
            state: Current consultation state (modified in-place)
        """
        try:
            # Check if retriever is available
            if retriever is None:
                logger.warning(
                    "Retriever not available, skipping RAG retrieval",
                    extra={"user_id": state.user_id},
                )
                self.attach_context(state)
                return

            # Check if we should use RAG
            if not self.should_use_rag(state):
                logger.info(
                    "Insufficient information for RAG retrieval",
                    extra={"user_id": state.user_id},
                )
                self.attach_context(state)
                return

            # Build retrieval query
            query = self.build_retrieval_query(state)

            if not query:
                logger.warning(
                    "Empty retrieval query, skipping RAG",
                    extra={"user_id": state.user_id},
                )
                self.attach_context(state)
                return

            logger.info(
                "Calling Retriever for medical context",
                extra={
                    "user_id": state.user_id,
                    "query": query,
                    "top_k": settings.top_k,
                },
            )

            # Call retriever
            chunks = retriever.retrieve(
                query=query,
                top_k=settings.top_k,
            )

            # Ensure chunks is a list
            if not isinstance(chunks, list):
                chunks = []

            logger.info(
                "Retrieved medical context",
                extra={
                    "user_id": state.user_id,
                    "chunk_count": len(chunks),
                },
            )

            # Attach to state
            state.rag_chunks = chunks

        except Exception as e:
            logger.warning(
                "Retriever failed",
                extra={
                    "user_id": state.user_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            # Set empty chunks and continue
            state.rag_chunks = []

    def attach_context(self, state: NeurologyDoctorState) -> None:
        """
        Ensure retrieved chunks are properly attached to state.

        This method ensures state.rag_chunks is always initialized as an empty
        list if not already set. Does not modify state.health_data.

        Args:
            state: Current consultation state (modified in-place)
        """
        if not hasattr(state, "rag_chunks") or state.rag_chunks is None:
            state.rag_chunks = []

        logger.info(
            "Context attached to state",
            extra={
                "user_id": state.user_id,
                "chunk_count": len(state.rag_chunks) if state.rag_chunks else 0,
            },
        )

    def detect_emergency(self, state: NeurologyDoctorState) -> bool:
        """
        Detect emergency neurological conditions.

        Checks health_data for emergency symptoms and indicators:
        - Sudden weakness or paralysis
        - Facial drooping
        - Slurred speech
        - Loss of consciousness
        - New seizure or status epilepticus
        - Confusion or altered mental status
        - Stroke symptoms
        - Severe head injury
        - Persistent altered consciousness

        If emergency detected:
        - Sets state.current_node = "EMERGENCY"
        - Creates state.pending_event with alert type
        - Returns True to interrupt workflow

        Args:
            state: Current consultation state

        Returns:
            True if emergency detected, False otherwise
        """
        try:
            health_data = state.health_data or {}

            # Emergency keywords to search for
            emergency_keywords = {
                "sudden weakness",
                "facial drooping",
                "slurred speech",
                "loss of consciousness",
                "new seizure",
                "status epilepticus",
                "confusion",
                "stroke symptoms",
                "severe head injury",
                "persistent altered mental status",
                "unable to move",
                "paralysis",
                "unconscious",
                "unresponsive",
            }

            # Check symptoms
            symptoms = health_data.get("symptoms", [])
            if symptoms and isinstance(symptoms, list):
                symptoms_lower = " ".join(symptoms).lower()
                for keyword in emergency_keywords:
                    if keyword in symptoms_lower:
                        logger.warning(
                            "Emergency condition detected",
                            extra={
                                "user_id": state.user_id,
                                "emergency_symptom": keyword,
                            },
                        )
                        state.current_node = "EMERGENCY"
                        state.pending_event = {
                            "type": "emergency_alert",
                            "message": (
                                "Immediate emergency evaluation required. "
                                "Please contact emergency services."
                            ),
                        }
                        return True

            # Check red flag symptoms
            red_flags = health_data.get("red_flag_symptoms", [])
            if red_flags and isinstance(red_flags, list) and len(red_flags) > 0:
                logger.warning(
                    "Red flag symptoms detected",
                    extra={
                        "user_id": state.user_id,
                        "red_flags": red_flags,
                    },
                )
                state.current_node = "EMERGENCY"
                state.pending_event = {
                    "type": "emergency_alert",
                    "message": (
                        "Immediate emergency evaluation required. "
                        "Please contact emergency services."
                    ),
                }
                return True

            return False

        except Exception as e:
            logger.error(
                "Error detecting emergency",
                extra={
                    "user_id": state.user_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            return False

    def is_consultation_complete(self, state: NeurologyDoctorState) -> bool:
        """
        Determine if all necessary information has been collected.

        Consultation is complete when:
        - Chief complaint exists
        - Symptoms collected
        - Duration of symptoms exists
        - Severity assessment exists
        - Medical history collected
        - Medications documented
        - Allergies documented
        - All required fields are non-empty

        Args:
            state: Current consultation state

        Returns:
            True if all required information collected, False otherwise
        """
        health_data = state.health_data or {}

        # Check all required fields
        required_fields = {
            "chief_complaint": str,
            "symptoms": list,
            "duration": str,
            "severity": str,
            "medical_history": list,
            "medications": list,
            "allergies": list,
        }

        for field, expected_type in required_fields.items():
            value = health_data.get(field)

            if expected_type == str:
                # String field must be non-empty and non-whitespace
                if not value or not isinstance(value, str) or not value.strip():
                    logger.info(
                        "Consultation incomplete",
                        extra={
                            "user_id": state.user_id,
                            "missing_field": field,
                        },
                    )
                    return False

            elif expected_type == list:
                # List field must have at least one item
                if (
                    not value
                    or not isinstance(value, list)
                    or len(value) == 0
                ):
                    logger.info(
                        "Consultation incomplete",
                        extra={
                            "user_id": state.user_id,
                            "missing_field": field,
                        },
                    )
                    return False

        logger.info(
            "Consultation questioning complete",
            extra={"user_id": state.user_id},
        )
        return True

    def should_recommend_mri(self, state: NeurologyDoctorState) -> bool:
        """
        Determine if MRI Brain investigation should be recommended.

        MRI is recommended for findings suggesting structural brain pathology:
        - Persistent neurological deficit
        - Seizure or seizure-like activity
        - Brain tumor suspicion
        - Focal weakness or motor deficit
        - Vision changes or eye movement disorder
        - New onset severe headache
        - Head trauma or concussion
        - Altered consciousness
        - Suspected stroke

        Args:
            state: Current consultation state

        Returns:
            True if MRI should be recommended, False otherwise
        """
        health_data = state.health_data or {}

        # MRI indication keywords
        mri_keywords = {
            "persistent neurological deficit",
            "seizure",
            "focal weakness",
            "vision changes",
            "new onset severe headache",
            "head trauma",
            "altered consciousness",
            "unconscious",
            "stroke",
            "tumor",
            "brain tumor",
            "focal deficit",
            "weakness",
            "tremor",
            "coordination",
            "balance",
            "vertigo",
            "dizziness",
        }

        # Check symptoms
        symptoms = health_data.get("symptoms", [])
        if symptoms and isinstance(symptoms, list):
            symptoms_lower = " ".join(symptoms).lower()
            for keyword in mri_keywords:
                if keyword in symptoms_lower:
                    logger.info(
                        "MRI Brain recommended",
                        extra={
                            "user_id": state.user_id,
                            "indication": keyword,
                        },
                    )
                    return True

        # Check chief complaint
        chief_complaint = health_data.get("chief_complaint", "").lower()
        if chief_complaint:
            for keyword in mri_keywords:
                if keyword in chief_complaint:
                    logger.info(
                        "MRI Brain recommended",
                        extra={
                            "user_id": state.user_id,
                            "indication": keyword,
                        },
                    )
                    return True

        return False

    def should_recommend_blood_panel(self, state: NeurologyDoctorState) -> bool:
        """
        Determine if Blood Test Panel should be recommended.

        Blood tests are recommended when symptoms suggest possible metabolic,
        infectious, or systemic causes of neurological symptoms:
        - Neuropathy or nerve-related symptoms
        - Fatigue or generalized weakness
        - Confusion or cognitive changes
        - Memory problems
        - Electrolyte imbalance suspicion
        - Vitamin deficiency suspicion
        - Fever with neurological symptoms
        - Metabolic encephalopathy suspicion

        Args:
            state: Current consultation state

        Returns:
            True if Blood Test Panel should be recommended, False otherwise
        """
        health_data = state.health_data or {}

        # Blood test indication keywords
        blood_test_keywords = {
            "neuropathy",
            "fatigue",
            "confusion",
            "memory problems",
            "weakness",
            "generalized weakness",
            "electrolyte",
            "vitamin deficiency",
            "fever",
            "infection",
            "metabolic",
            "encephalopathy",
            "numbness",
            "tingling",
            "cognitive",
            "difficulty concentrating",
            "brain fog",
        }

        # Check symptoms
        symptoms = health_data.get("symptoms", [])
        if symptoms and isinstance(symptoms, list):
            symptoms_lower = " ".join(symptoms).lower()
            for keyword in blood_test_keywords:
                if keyword in symptoms_lower:
                    logger.info(
                        "Blood Test Panel recommended",
                        extra={
                            "user_id": state.user_id,
                            "indication": keyword,
                        },
                    )
                    return True

        # Check chief complaint
        chief_complaint = health_data.get("chief_complaint", "").lower()
        if chief_complaint:
            for keyword in blood_test_keywords:
                if keyword in chief_complaint:
                    logger.info(
                        "Blood Test Panel recommended",
                        extra={
                            "user_id": state.user_id,
                            "indication": keyword,
                        },
                    )
                    return True

        return False

    def evaluate_investigations(self, state: NeurologyDoctorState) -> None:
        """
        Evaluate and determine recommended investigations.

        Based on patient symptoms and clinical presentation:
        1. Evaluates need for MRI Brain
        2. Evaluates need for Blood Test Panel
        3. Appends to state.recommended_tests (avoiding duplicates)
        4. Sets state.tests_recommended if any tests are needed
        5. Updates state.current_node appropriately

        If tests are recommended:
        - state.current_node = "LAB_NOTIFICATION"

        Otherwise:
        - state.current_node = "READY_FOR_EVALUATION"

        Args:
            state: Current consultation state (modified in-place)
        """
        try:
            # Initialize recommended_tests if needed
            if not hasattr(state, "recommended_tests"):
                state.recommended_tests = []

            if not isinstance(state.recommended_tests, list):
                state.recommended_tests = []

            tests_to_add = []

            # Check MRI recommendation
            if self.should_recommend_mri(state):
                if NeurologyTest.MRI_BRAIN not in state.recommended_tests:
                    tests_to_add.append(NeurologyTest.MRI_BRAIN)

            # Check Blood Test Panel recommendation
            if self.should_recommend_blood_panel(state):
                if NeurologyTest.BLOOD_TEST_PANEL not in state.recommended_tests:
                    tests_to_add.append(NeurologyTest.BLOOD_TEST_PANEL)

            # Add all recommended tests
            state.recommended_tests.extend(tests_to_add)

            # Update state based on recommendations
            if tests_to_add:
                state.tests_recommended = True
                state.current_node = "LAB_NOTIFICATION"

                logger.info(
                    "Investigations recommended",
                    extra={
                        "user_id": state.user_id,
                        "tests": [t.value for t in tests_to_add],
                        "total_tests": len(state.recommended_tests),
                    },
                )
            else:
                state.tests_recommended = False
                state.current_node = "READY_FOR_EVALUATION"

                logger.info(
                    "No investigations recommended",
                    extra={"user_id": state.user_id},
                )

        except Exception as e:
            logger.error(
                "Error evaluating investigations",
                extra={
                    "user_id": state.user_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            # Default to evaluation node on error
            state.current_node = "READY_FOR_EVALUATION"
            state.tests_recommended = False
