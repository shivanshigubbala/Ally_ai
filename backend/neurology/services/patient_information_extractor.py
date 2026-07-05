"""
Patient Information Extractor for Neurology service.

This module extracts structured patient information from conversation history.

Responsibilities:
- Parse conversation history
- Extract latest patient message
- Prepare data for downstream processing

NOT responsible for:
- Diagnosis
- Treatment recommendations
- Emergency detection
- Test recommendations
- LLM inference
- RAG retrieval
"""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.neurology.llm import llm_client
from backend.neurology.models.session_state import NeurologyDoctorState

logger = logging.getLogger(__name__)


class PatientInformationExtractor:
    """
    Extracts structured patient information from conversation history.

    This component reads the consultation conversation and prepares
    the patient data for downstream processing by other services.
    """

    def __init__(self) -> None:
        """Initialize the Patient Information Extractor."""
        logger.info("Patient Information Extractor initialized")

    def extract_information(
        self, state: NeurologyDoctorState
    ) -> NeurologyDoctorState:
        """
        Extract and structure patient information from conversation history.

        This method processes the conversation history and updates the state
        with extracted patient information. The state is returned unchanged
        for this initial implementation, with TODOs for future expansion.

        Args:
            state: Current consultation state

        Returns:
            Updated state with extracted information
        """
        # Validate state
        if not state:
            logger.error("Cannot extract information: state is None")
            return state

        # Validate conversation history
        if not state.conversation_history:
            logger.warning(
                "Cannot extract information: conversation history is empty",
                extra={"user_id": state.user_id, "appointment_id": state.appointment_id},
            )
            return state

        logger.info(
            "Information extraction started",
            extra={
                "user_id": state.user_id,
                "appointment_id": state.appointment_id,
                "conversation_length": len(state.conversation_history),
            },
        )

        # Retrieve latest patient message
        latest_message = self._get_latest_patient_message(state.conversation_history)

        if latest_message:
            logger.info(
                "Latest patient message found",
                extra={
                    "user_id": state.user_id,
                    "message_length": len(latest_message),
                },
            )
        else:
            logger.warning(
                "No patient message found in conversation history",
                extra={"user_id": state.user_id},
            )
            return state

        # Build extraction prompts
        system_prompt, user_prompt = self._build_extraction_prompt(latest_message)

        logger.info(
            "Extraction prompt built",
            extra={"user_id": state.user_id},
        )

        # Call LLM for information extraction
        try:
            logger.info(
                "LLM extraction request started",
                extra={"user_id": state.user_id},
            )

            raw_response = llm_client.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

            logger.info(
                "LLM response received",
                extra={
                    "user_id": state.user_id,
                    "response_length": len(raw_response),
                },
            )

            # Parse JSON response
            logger.info(
                "JSON parsing started",
                extra={"user_id": state.user_id},
            )

            extracted_data = self._parse_llm_response(raw_response)

            if extracted_data is None:
                logger.warning(
                    "JSON parsing failed, returning state unchanged",
                    extra={"user_id": state.user_id},
                )
                return state

            logger.info(
                "JSON parsing successful",
                extra={"user_id": state.user_id},
            )

            # Merge extracted data into health_data
            logger.info(
                "Health data merge started",
                extra={"user_id": state.user_id},
            )

            state.health_data = self._merge_health_data(
                state.health_data, extracted_data
            )

            logger.info(
                "Health data updated",
                extra={"user_id": state.user_id},
            )

        except Exception as e:
            logger.error(
                f"LLM extraction request failed: {e}",
                extra={
                    "user_id": state.user_id,
                    "error_type": type(e).__name__,
                },
            )
            return state

        logger.info(
            "Information extraction completed",
            extra={"user_id": state.user_id},
        )

        return state

    def _get_latest_patient_message(self, history: list[dict[str, str]]) -> str | None:
        """
        Retrieve the latest patient message from conversation history.

        Args:
            history: Conversation history list

        Returns:
            Latest patient message content, or None if not found
        """
        if not history:
            return None

        # Iterate in reverse to find the most recent user message
        for message in reversed(history):
            if message.get("role") == "user":
                return message.get("content")

        return None

    def _build_extraction_prompt(self, patient_message: str) -> tuple[str, str]:
        """
        Build system and user prompts for LLM-based information extraction.

        Args:
            patient_message: Latest patient message from conversation

        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        system_prompt = (
            "You are a patient information extraction assistant for a neurology clinic. "
            "Your ONLY job is to extract information that the patient has explicitly stated. "
            "\n\n"
            "IMPORTANT CONSTRAINTS:\n"
            "- NEVER diagnose or suggest diagnoses\n"
            "- NEVER recommend tests or investigations\n"
            "- NEVER recommend treatments\n"
            "- NEVER answer medical questions\n"
            "- NEVER infer or assume facts not explicitly mentioned\n"
            "- Extract ONLY what the patient has stated\n"
            "\n\n"
            "Return ONLY valid JSON with no additional text, markdown, or explanation.\n"
            "If information is not mentioned, use empty string or empty array.\n"
            "\n\n"
            "Expected JSON schema:\n"
            "{\n"
            '  "chief_complaint": "string",\n'
            '  "symptoms": ["string"],\n'
            '  "duration": "string",\n'
            '  "severity": "string",\n'
            '  "medical_history": ["string"],\n'
            '  "medications": ["string"],\n'
            '  "allergies": ["string"],\n'
            '  "red_flag_symptoms": ["string"]\n'
            "}"
        )

        user_prompt = f"Extract patient information from this message:\n\n{patient_message}"

        return system_prompt, user_prompt

    def _parse_llm_response(self, raw_response: str) -> dict[str, Any] | None:
        """
        Parse JSON response from LLM.

        Attempts to parse the raw response as JSON. If parsing fails,
        logs the error and returns None. Does not raise exceptions.

        Args:
            raw_response: Raw text response from LLM

        Returns:
            Parsed dictionary if successful, None if parsing failed
        """
        try:
            parsed = json.loads(raw_response)

            # Validate expected schema and apply defaults
            expected_fields = {
                "chief_complaint": "",
                "symptoms": [],
                "duration": "",
                "severity": "",
                "medical_history": [],
                "medications": [],
                "allergies": [],
                "red_flag_symptoms": [],
            }

            # Create result with all expected fields
            result = {}
            for field, default_value in expected_fields.items():
                if field in parsed:
                    result[field] = parsed[field]
                else:
                    result[field] = default_value

            return result

        except json.JSONDecodeError as e:
            logger.error(
                f"JSON parsing error: {e}",
                extra={"raw_response": raw_response[:100]},
            )
            return None

        except (KeyError, TypeError) as e:
            logger.error(
                f"JSON validation error: {e}",
                extra={"error_type": type(e).__name__},
            )
            return None

        except Exception as e:
            logger.error(
                f"Unexpected error during JSON parsing: {e}",
                extra={"error_type": type(e).__name__},
            )
            return None

    def _merge_health_data(
        self, existing: dict[str, Any], extracted: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Intelligently merge extracted data with existing health data.

        Rules:
        - Do not overwrite existing strings with empty strings
        - Do not overwrite existing lists with empty lists
        - Append unique values to existing lists
        - Replace only if extracted value is meaningful

        Args:
            existing: Existing health data dictionary
            extracted: Newly extracted health data

        Returns:
            Merged health data dictionary
        """
        merged = existing.copy() if existing else {}

        for key, value in extracted.items():
            # Handle string fields
            if isinstance(value, str):
                # Only update if value is not empty
                if value:
                    merged[key] = value
                # If value is empty and key doesn't exist, set default
                elif key not in merged:
                    merged[key] = value

            # Handle list fields
            elif isinstance(value, list):
                # Only update if list is not empty
                if value:
                    if key in merged and isinstance(merged[key], list):
                        # Append unique values only
                        existing_set = set(merged[key])
                        for item in value:
                            if item not in existing_set:
                                merged[key].append(item)
                    else:
                        merged[key] = value
                # If list is empty and key doesn't exist, set default
                elif key not in merged:
                    merged[key] = value

            else:
                # For other types, set if key doesn't exist
                if key not in merged:
                    merged[key] = value

        return merged
