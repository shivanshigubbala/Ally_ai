from __future__ import annotations

from typing import Any, Callable, Dict, Type

from backend.specialties.base import BaseSpecialty


class SpecialtyRegistry:
    """Registry for department-to-specialty implementations."""

    def __init__(self) -> None:
        self._registry: Dict[str, Type[BaseSpecialty]] = {}

    def register(self, department: str, specialty_cls: Type[BaseSpecialty]) -> None:
        self._registry[department.lower()] = specialty_cls

    def get(self, department: str) -> Type[BaseSpecialty]:
        key = department.lower()
        if key not in self._registry:
            raise KeyError(f"No specialty registered for department: {department}")
        return self._registry[key]

    def create(self, department: str, **kwargs: Any) -> BaseSpecialty:
        specialty_cls = self.get(department)
        return specialty_cls(**kwargs)


def get_specialty_registry() -> SpecialtyRegistry:
    registry = SpecialtyRegistry()

    try:
        from backend.general_physician.agent import GeneralPhysicianSpecialty
    except Exception:
        GeneralPhysicianSpecialty = None

    try:
        from backend.specialties.cardiology.consultation_controller import CardiologySpecialty
    except Exception:
        CardiologySpecialty = None

    if GeneralPhysicianSpecialty is not None:
        registry.register("general physician", GeneralPhysicianSpecialty)
        registry.register("general", GeneralPhysicianSpecialty)
    if CardiologySpecialty is not None:
        registry.register("cardiology", CardiologySpecialty)

    return registry


def get_specialty_for_department(department: str, **kwargs: Any) -> BaseSpecialty:
    registry = get_specialty_registry()
    return registry.create(department, **kwargs)
