from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseSpecialty(ABC):
    """Shared contract that every specialty module must implement."""

    department: str = "general"

    @abstractmethod
    def initialize_consultation(self, patient_id: str | None = None, appointment_id: str | None = None, **kwargs: Any) -> Any:
        """Initialize consultation state for a specialty workflow."""

    @abstractmethod
    def load_consultation_context(self, appointment_id: str | None = None, **kwargs: Any) -> Any:
        """Load the shared consultation context for the appointment."""

    @abstractmethod
    def load_patient_history(self, patient_id: str | None = None, **kwargs: Any) -> Any:
        """Load the patient's longitudinal history."""

    @abstractmethod
    def load_patient_documents(self, patient_id: str | None = None, appointment_id: str | None = None, **kwargs: Any) -> Any:
        """Load patient documents for the consultation workflow."""

    @abstractmethod
    def run_consultation(self, user_id: str, appointment_id: str, user_message: str | None = None, pending_event: dict | None = None, **kwargs: Any) -> Any:
        """Run the specialty consultation workflow."""

    @abstractmethod
    def generate_summary(self, state: Any, **kwargs: Any) -> Any:
        """Generate a structured consultation summary for persistence."""

    @abstractmethod
    def recommend_labs(self, state: Any, **kwargs: Any) -> Any:
        """Return recommended tests or lab guidance for the consultation."""

    @abstractmethod
    def complete_consultation(self, state: Any, **kwargs: Any) -> Any:
        """Finalize the consultation and prepare downstream artifacts."""
