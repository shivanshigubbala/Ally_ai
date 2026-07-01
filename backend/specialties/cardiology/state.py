from dataclasses import dataclass, field
from typing import List


@dataclass
class CardiologyState:

    patient_name: str = ""

    chief_complaint: str = ""

    symptoms: List[str] = field(default_factory=list)

    duration: str = ""

    pain_location: str = ""

    pain_radiation: str = ""

    severity: str = ""

    associated_symptoms: List[str] = field(default_factory=list)

    medical_history: List[str] = field(default_factory=list)

    medications: List[str] = field(default_factory=list)

    allergies: List[str] = field(default_factory=list)

    smoking: bool = False

    diabetes: bool = False

    hypertension: bool = False

    family_history: bool = False

    questions_asked: List[str] = field(default_factory=list)

    recommended_tests: List[str] = field(default_factory=list)

    risk_level: str = "Unknown"

    emergency: bool = False

    consultation_complete: bool = False

    summary: str = ""