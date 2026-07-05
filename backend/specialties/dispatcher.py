from __future__ import annotations

from typing import Any

from backend.models.intake import ConsultationContext
from backend.specialties.base import BaseSpecialty
from backend.specialties.registry import SpecialtyRegistry, get_specialty_registry


class SpecialtyDispatcher:
    """Resolve a consultation context to the matching specialty implementation."""

    def __init__(self, registry: SpecialtyRegistry | None = None) -> None:
        self._registry = registry or get_specialty_registry()

    def dispatch(self, consultation_context: Any) -> BaseSpecialty:
        department = self._extract_department(consultation_context)
        if not department:
            raise KeyError("Consultation context does not include a department")
        specialty_cls = self._registry.get(department)
        return specialty_cls()

    def _extract_department(self, consultation_context: Any) -> str | None:
        if consultation_context is None:
            return None

        if isinstance(consultation_context, dict):
            department = consultation_context.get("selected_department") or consultation_context.get("department")
            if department:
                return str(department)
            intake = consultation_context.get("clinical_intake_record") or {}
            if isinstance(intake, dict):
                mapped = intake.get("recommended_department") or intake.get("department")
                if mapped:
                    return str(mapped)
            return None

        for attr in ("selected_department", "department"):
            value = getattr(consultation_context, attr, None)
            if value:
                return str(value)

        clinical_intake_record = getattr(consultation_context, "clinical_intake_record", None)
        if clinical_intake_record is not None:
            if isinstance(clinical_intake_record, ConsultationContext):
                return clinical_intake_record.selected_department or clinical_intake_record.recommended_department
            if isinstance(clinical_intake_record, dict):
                mapped = clinical_intake_record.get("recommended_department") or clinical_intake_record.get("department")
                if mapped:
                    return str(mapped)

        return None


def resolve_specialty(consultation_context: Any, registry: SpecialtyRegistry | None = None) -> BaseSpecialty:
    return SpecialtyDispatcher(registry=registry).dispatch(consultation_context)
