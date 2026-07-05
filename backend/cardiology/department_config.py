from __future__ import annotations

import os
from typing import Any

from backend.cardiology.config import get_default_doctor_id, get_default_doctor_name
from backend.cardiology.llm.prompts import (
    CARDIOLOGY_DOCTOR_NAME,
    CARDIOLOGY_DOCTOR_SYSTEM_PROMPT,
    CARDIOLOGY_EVALUATION_PROMPT,
)


def get_department_config(department: str | None = None) -> dict[str, Any]:
    """Always returns cardiology config since this is the cardiology module."""
    return {
        "department": "cardiology",
        "doctor_id": "d8",
        "doctor_name": CARDIOLOGY_DOCTOR_NAME,
        "system_prompt": CARDIOLOGY_DOCTOR_SYSTEM_PROMPT,
        "evaluation_prompt": CARDIOLOGY_EVALUATION_PROMPT,
        "knowledge_department": "cardiology",
        "is_cardiology": True,
        "is_neurology": False,
        "llm_provider": os.getenv("LLM_PROVIDER", "nvidia").strip().lower() or "nvidia",
        "llm_model": os.getenv("NVIDIA_MODEL", "meta/llama-2-8b").strip() or "meta/llama-2-8b",
    }
