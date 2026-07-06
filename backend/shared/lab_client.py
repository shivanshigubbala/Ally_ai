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
        "user_id": str(_parse_int(user_id, 0) or 0),
        "doctor_id": _parse_int(doctor_id, 0) or 0,
        "department": department or "",
        "tests": tests or [],
    }

    try:
        return _safe_request("POST", "/lab-tests", json_data=payload)
    except Exception:
        # Lab service unavailable — produce local mock PDF reports and return a
        # best-effort response so the rest of the system can continue.
        try:
            from fpdf import FPDF
        except Exception:
            FPDF = None

        from pathlib import Path
        reports_root = Path(__file__).resolve().parents[1] / "reports"
        dept = (department or "general") or "general"
        out_dir = reports_root / dept
        out_dir.mkdir(parents=True, exist_ok=True)

        reports: list[dict[str, Any]] = []
        tests_list = tests or []
        for idx, t in enumerate(tests_list, 1):
            name = t.get("name") if isinstance(t, dict) else str(t)
            safe_name = re.sub(r"[^A-Za-z0-9_\-]+", "_", str(name))[:80]
            filename = f"report_{appointment_id}_{idx}_{safe_name}.pdf"
            filepath = out_dir / filename

            if FPDF is not None:
                try:
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", size=12)
                    pdf.cell(0, 10, f"Lab Report", ln=True)
                    pdf.ln(4)
                    pdf.cell(0, 8, f"Appointment: {appointment_id}", ln=True)
                    pdf.cell(0, 8, f"Patient ID: {user_id}", ln=True)
                    pdf.cell(0, 8, f"Doctor: {doctor_id}", ln=True)
                    pdf.ln(6)
                    pdf.multi_cell(0, 8, f"Test: {name}")
                    reason = t.get("reason") if isinstance(t, dict) else ""
                    if reason:
                        pdf.ln(2)
                        pdf.multi_cell(0, 8, f"Reason: {reason}")
                    pdf.ln(6)
                    pdf.multi_cell(0, 8, "Result: This is a mock result generated locally. Please treat this as a placeholder.")
                    pdf.output(str(filepath))
                except Exception:
                    # fallback: write a small text file with .pdf extension
                    try:
                        filepath.write_text(f"Mock report for {name}\nReason: {t.get('reason','')}\nResult: MOCK\n")
                    except Exception:
                        pass
            else:
                try:
                    filepath.write_text(f"Mock report for {name}\nReason: {t.get('reason','')}\nResult: MOCK\n")
                except Exception:
                    pass

            reports.append({
                "test": name,
                "pdf_name": filename,
                "path": f"/reports/{dept}/{filename}",
            })

        # Best-effort: return a structured payload similar to the lab service.
        return {"status": "mocked", "reports": reports}
