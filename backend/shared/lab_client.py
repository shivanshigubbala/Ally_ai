from __future__ import annotations

import os
import re
from typing import Any

import requests

LAB_SERVICE_URL = os.getenv("LAB_SERVICE_URL", "http://lab:8082").rstrip("/")
REQUEST_TIMEOUT = 5  # seconds


class LabServiceError(Exception):
    pass


class LabServiceUnavailable(LabServiceError):
    pass


class LabServiceRequestError(LabServiceError):
    pass


def _safe_request(method: str, endpoint: str, json_data: dict | None = None, params: dict | None = None) -> dict | list:
    url = f"{LAB_SERVICE_URL}{endpoint}"
    try:
        if method == "GET":
            resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        elif method == "POST":
            resp = requests.post(url, json=json_data, params=params, timeout=REQUEST_TIMEOUT)
        elif method == "PATCH":
            resp = requests.patch(url, json=json_data, params=params, timeout=REQUEST_TIMEOUT)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
    except (requests.ConnectionError, requests.Timeout) as exc:
        raise LabServiceUnavailable(f"Connection to lab service failed: {exc}") from exc
    except requests.RequestException as exc:
        raise LabServiceUnavailable(f"Request to lab service failed: {exc}") from exc

    if resp.status_code >= 500:
        raise LabServiceUnavailable(f"Lab service error {resp.status_code}: {resp.text}")
    if resp.status_code >= 400:
        raise LabServiceRequestError(f"Lab service request error {resp.status_code}: {resp.text}")

    return resp.json()


def _parse_int(value: str | int | None, default: int | None = None) -> int | None:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    text = str(value)
    digits = "".join(ch for ch in text if ch.isdigit())
    if digits:
        return int(digits)
    try:
        return int(text)
    except ValueError:
        return default


def create_lab_tests(
    appointment_id: str | int,
    user_id: str | int,
    doctor_id: str | int,
    department: str | None,
    tests: list[dict[str, Any]] | None,
    session_id: str | None = None,
) -> dict | list:
    payload = {
        "session_id": session_id or "",
        "appointment_id": _parse_int(appointment_id, 0) or 0,
        "user_id": _parse_int(user_id, 0) or 0,
        "doctor_id": _parse_int(doctor_id, 0) or 0,
        "department": department or "",
        "tests": tests or [],
    }
    return _safe_request("POST", "/lab-tests", json_data=payload)
