from __future__ import annotations

import os
from typing import Any

from backend.neurology.config import get_default_doctor_id, get_default_doctor_name
from backend.neurology.llm.prompts import (
    NEUROLOGY_DOCTOR_NAME,
    NEUROLOGY_DOCTOR_SYSTEM_PROMPT,
    NEUROLOGY_EVALUATION_PROMPT,
)


def get_department_config(department: str | None = None) -> dict[str, Any]:
    """Always returns neurology config since this is the neurology module."""
    return {
        "department": "neurology",
        "doctor_id": "d9",
        "doctor_name": NEUROLOGY_DOCTOR_NAME,
        "system_prompt": NEUROLOGY_DOCTOR_SYSTEM_PROMPT,
        "evaluation_prompt": NEUROLOGY_EVALUATION_PROMPT,
        "knowledge_department": "neurology",
        "is_cardiology": False,
        "is_neurology": True,
        "llm_provider": os.getenv("LLM_PROVIDER", "nvidia").strip().lower() or "nvidia",
        "llm_model": os.getenv("NVIDIA_MODEL", "meta/llama-2-8b").strip() or "meta/llama-2-8b",
    }
