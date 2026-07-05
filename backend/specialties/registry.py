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
        from backend.cardiology.agent import CardiologySpecialty
    except Exception:
        CardiologySpecialty = None

    try:
        from backend.neurology.agent import NeurologySpecialty
    except Exception:
        NeurologySpecialty = None

    if GeneralPhysicianSpecialty is not None:
        registry.register("general physician", GeneralPhysicianSpecialty)
        registry.register("general", GeneralPhysicianSpecialty)
    if CardiologySpecialty is not None:
        registry.register("cardiology", CardiologySpecialty)
    if NeurologySpecialty is not None:
        registry.register("neurology", NeurologySpecialty)

    return registry


def get_specialty_for_department(department: str, **kwargs: Any) -> BaseSpecialty:
    registry = get_specialty_registry()
    return registry.create(department, **kwargs)
