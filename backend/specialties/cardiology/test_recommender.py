"""Cardiology test catalogue and name sanitization.

Keeps the list of diagnostic tests the cardiology agent is allowed to
recommend, plus a canonical-name mapper so free-text LLM output (e.g.
"echo", "2D echo") gets normalized before it's shown to the patient or
put on a lab report.
"""

from __future__ import annotations

import re

CARDIOLOGY_TESTS: list[dict[str, str]] = [
    {
        "name": "ECG",
        "reason": "Records the heart's electrical activity to check rhythm and detect signs of ischemia.",
    },
    {
        "name": "Troponin",
        "reason": "A blood test that detects heart muscle damage, used to rule out a heart attack.",
    },
    {
        "name": "Echocardiogram",
        "reason": "An ultrasound of the heart that evaluates pumping function and valve health.",
    },
    {
        "name": "Holter Monitor",
        "reason": "Continuous ECG recording over 24-48 hours to catch intermittent irregular rhythms.",
    },
    {
        "name": "Lipid Profile",
        "reason": "Measures cholesterol levels, a key modifiable cardiovascular risk factor.",
    },
    {
        "name": "BNP",
        "reason": "A blood marker that helps assess for heart failure.",
    },
    {
        "name": "Chest X-Ray",
        "reason": "Checks heart size and lung fields, useful when breathlessness or swelling is present.",
    },
    {
        "name": "Stress Test",
        "reason": "Evaluates how the heart performs under exertion, useful for suspected coronary disease.",
    },
    {
        "name": "Blood Pressure Monitoring",
        "reason": "Tracks blood pressure over time to confirm and characterize hypertension.",
    },
]

_ALLOWED_TEST_NAMES: dict[str, str] = {
    "ecg": "ECG",
    "ekg": "ECG",
    "electrocardiogram": "ECG",
    "troponin": "Troponin",
    "echo": "Echocardiogram",
    "2d echo": "Echocardiogram",
    "echocardiogram": "Echocardiogram",
    "holter": "Holter Monitor",
    "holter monitor": "Holter Monitor",
    "holter monitoring": "Holter Monitor",
    "lipid profile": "Lipid Profile",
    "lipid panel": "Lipid Profile",
    "cholesterol panel": "Lipid Profile",
    "bnp": "BNP",
    "nt-probnp": "BNP",
    "chest x-ray": "Chest X-Ray",
    "chest xray": "Chest X-Ray",
    "cxr": "Chest X-Ray",
    "stress test": "Stress Test",
    "treadmill test": "Stress Test",
    "exercise stress test": "Stress Test",
    "blood pressure monitoring": "Blood Pressure Monitoring",
    "bp monitoring": "Blood Pressure Monitoring",
    "ambulatory bp monitoring": "Blood Pressure Monitoring",
}

EMERGENCY_TESTS: list[dict[str, str]] = [
    t for t in CARDIOLOGY_TESTS if t["name"] in ("ECG", "Troponin")
]

DEFAULT_REPORT_RESULTS: dict[str, str] = {
    "ECG": "Normal sinus rhythm. No acute ST-T changes noted.",
    "Troponin": "Within normal limits. No evidence of myocardial injury.",
    "Echocardiogram": "Normal chamber size and systolic function. No significant valve disease.",
    "Holter Monitor": "No significant arrhythmia captured during the monitoring period.",
    "Lipid Profile": "Cholesterol levels within acceptable range.",
    "BNP": "Within normal limits.",
    "Chest X-Ray": "Heart size and lung fields appear normal.",
    "Stress Test": "No significant ischemic changes with exertion.",
    "Blood Pressure Monitoring": "Readings within target range across the monitoring period.",
}


def _canonical_test_name(name: str) -> str | None:
    normalized = re.sub(r"\s+", " ", name or "").strip().lower()
    return _ALLOWED_TEST_NAMES.get(normalized)


def sanitize_tests(raw_tests: list[dict[str, str]] | None) -> list[dict[str, str]]:
    """Keep only tests from the cardiology catalogue, with a canonical name/reason."""
    tests: list[dict[str, str]] = []
    if not raw_tests:
        return tests
    for item in raw_tests:
        if not isinstance(item, dict):
            continue
        canonical_name = _canonical_test_name(str(item.get("name", "")).strip())
        if not canonical_name:
            continue
        reason = str(item.get("reason", "")).strip()
        if not reason:
            reason = next(
                (t["reason"] for t in CARDIOLOGY_TESTS if t["name"] == canonical_name),
                "",
            )
        entry = {"name": canonical_name, "reason": reason}
        if entry not in tests:
            tests.append(entry)
    return tests
