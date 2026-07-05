from __future__ import annotations

import os
from typing import Any

from backend.general_physician.config import get_default_doctor_id, get_default_doctor_name
from backend.general_physician.llm.prompts import (
    CARDIOLOGY_DOCTOR_NAME,
    CARDIOLOGY_DOCTOR_SYSTEM_PROMPT,
    CARDIOLOGY_EVALUATION_PROMPT,
    DOCTOR_NAME,
    DOCTOR_SYSTEM_PROMPT,
    EVALUATION_PROMPT,
)


def get_department_config(department: str | None = None) -> dict[str, Any]:
    dept = (department or "general").strip().lower()
    if dept == "cardiology":
        return {
            "department": "cardiology",
            "doctor_id": "d8",
            "doctor_name": CARDIOLOGY_DOCTOR_NAME,
            "system_prompt": CARDIOLOGY_DOCTOR_SYSTEM_PROMPT,
            "evaluation_prompt": CARDIOLOGY_EVALUATION_PROMPT,
            "knowledge_department": "cardiology",
            "is_cardiology": True,
            "llm_provider": os.getenv("LLM_PROVIDER", "nvidia").strip().lower() or "nvidia",
            "llm_model": os.getenv("NVIDIA_MODEL", "meta/llama-3.1-8b-instruct").strip() or "meta/llama-3.1-8b-instruct",
        }

    return {
        "department": "general",
        "doctor_id": get_default_doctor_id(),
        "doctor_name": get_default_doctor_name() or DOCTOR_NAME,
        "system_prompt": DOCTOR_SYSTEM_PROMPT,
        "evaluation_prompt": EVALUATION_PROMPT,
        "knowledge_department": "general",
        "is_cardiology": False,
    }
