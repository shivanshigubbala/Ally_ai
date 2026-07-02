import re

from backend.specialties.cardiology.state import CardiologyState


class PatientInformationExtractor:
    """
    Extracts structured medical information from the patient's latest message
    and updates the CardiologyState.
    """

    def update_state(
        self,
        state: CardiologyState,
        patient_message: str,
    ) -> CardiologyState:

        message = patient_message.lower()

        # --------------------------------------------------
        # Chief Complaint
        # --------------------------------------------------

        if not state.chief_complaint:
            state.chief_complaint = patient_message

        # --------------------------------------------------
        # Symptoms
        # --------------------------------------------------

        symptom_keywords = [
            "chest pain",
            "palpitations",
            "shortness of breath",
            "breathlessness",
            "dizziness",
            "fainting",
            "fatigue",
            "leg swelling",
            "high blood pressure",
            "hypertension",
            "irregular heartbeat",
            "rapid heartbeat",
            "slow heartbeat",
            "chest tightness",
            "pressure in chest",
        ]

        for symptom in symptom_keywords:
            if symptom in message:
                if symptom not in state.symptoms:
                    state.symptoms.append(symptom)

        # --------------------------------------------------
        # Pain Location
        # --------------------------------------------------

        if "left side" in message:
            state.pain_location = "Left Chest"

        elif "right side" in message:
            state.pain_location = "Right Chest"

        elif "center" in message or "middle" in message:
            state.pain_location = "Center Chest"

        # --------------------------------------------------
        # Pain Radiation
        # --------------------------------------------------

        if "left arm" in message:
            state.pain_radiation = "Left Arm"

        elif "right arm" in message:
            state.pain_radiation = "Right Arm"

        elif "jaw" in message:
            state.pain_radiation = "Jaw"

        elif "back" in message:
            state.pain_radiation = "Back"

        elif "shoulder" in message:
            state.pain_radiation = "Shoulder"

        # --------------------------------------------------
        # Duration
        # --------------------------------------------------

        duration_pattern = re.search(
            r"(\d+)\s*(minute|minutes|hour|hours|day|days|week|weeks)",
            message,
        )

        if duration_pattern:
            state.duration = duration_pattern.group()

        # --------------------------------------------------
        # Severity (Pain Score)
        # --------------------------------------------------

        severity_pattern = re.search(
            r"\b([1-9]|10)\b",
            message,
        )

        if severity_pattern:
            state.severity = severity_pattern.group(1)

        # --------------------------------------------------
        # Associated Symptoms
        # --------------------------------------------------

        associated = [
            "sweating",
            "nausea",
            "vomiting",
            "shortness of breath",
            "dizziness",
            "fainting",
            "fatigue",
        ]

        for symptom in associated:
            if symptom in message:
                if symptom not in state.associated_symptoms:
                    state.associated_symptoms.append(symptom)

        # --------------------------------------------------
        # Medical History
        # --------------------------------------------------

        history = [
            "heart attack",
            "heart disease",
            "stroke",
            "diabetes",
            "hypertension",
            "high blood pressure",
            "kidney disease",
            "cholesterol",
        ]

        for disease in history:
            if disease in message:
                if disease not in state.medical_history:
                    state.medical_history.append(disease)

        # --------------------------------------------------
        # Risk Factors
        # --------------------------------------------------

        if "diabetes" in message:
            state.diabetes = True

        if "hypertension" in message or "high blood pressure" in message:
            state.hypertension = True

        if (
            "smoker" in message
            or "smoking" in message
            or "i smoke" in message
        ):
            state.smoking = True

        if "family history" in message:
            state.family_history = True

        # --------------------------------------------------
        # Emergency Detection
        # --------------------------------------------------

        emergency_keywords = [
            "left arm pain",
            "jaw pain",
            "collapse",
            "fainted",
            "unable to breathe",
            "severe chest pain",
        ]

        for keyword in emergency_keywords:
            if keyword in message:
                state.emergency = True
                break

        return state