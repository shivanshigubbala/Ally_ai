from __future__ import annotations

import os
from typing import Optional

try:
    from backend.general_physician.services import local_store as store
except Exception:
    from services import local_store as store


def _find_by_name_fragment(fragment: str) -> Optional[dict]:
    try:
        docs = store.list_doctors(None)
    except Exception:
        return None
    frag = fragment.lower()
    for d in docs:
        if frag in (d.get("name") or "").lower():
            return d
    return docs[0] if docs else None


def get_default_doctor_id() -> str:
    # Honor explicit environment override first
    env = os.getenv("ALLY_GP_DOCTOR_ID")
    if env:
        return env
    d = _find_by_name_fragment("shankar")
    if d:
        return d.get("id") or "d5"
    return "d5"


def get_default_doctor_name() -> str:
    env = os.getenv("ALLY_GP_DOCTOR_NAME")
    if env:
        return env
    d = _find_by_name_fragment("shankar")
    if d:
        return d.get("name") or "Dr. Shankar"
    return "Dr. Shankar"
