from __future__ import annotations

import os
from typing import Optional

try:
    from backend.services import local_store as store
except Exception:
    from services import local_store as store  # type: ignore


def _find_by_name_fragment(fragment: str) -> Optional[dict]:
    try:
        docs = store.list_doctors("neurology")
    except Exception:
        return None
    frag = fragment.lower()
    for d in docs:
        if frag in (d.get("name") or "").lower():
            return d
    return docs[0] if docs else None


def get_default_doctor_id() -> str:
    env = os.getenv("ALLY_NEUROLOGY_DOCTOR_ID")
    if env:
        return env
    d = _find_by_name_fragment("octopus")
    if d:
        return d.get("id") or "d9"
    return "d9"


def get_default_doctor_name() -> str:
    env = os.getenv("ALLY_NEUROLOGY_DOCTOR_NAME")
    if env:
        return env
    d = _find_by_name_fragment("octopus")
    if d:
        return d.get("name") or "Dr. Octopus"
    return "Dr. Octopus"
