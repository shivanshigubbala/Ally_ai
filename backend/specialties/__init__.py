from backend.specialties.base import BaseSpecialty
from backend.specialties.dispatcher import SpecialtyDispatcher, resolve_specialty
from backend.specialties.registry import (
    SpecialtyRegistry,
    get_specialty_for_department,
    get_specialty_registry,
)

__all__ = [
    "BaseSpecialty",
    "SpecialtyDispatcher",
    "SpecialtyRegistry",
    "get_specialty_for_department",
    "get_specialty_registry",
    "resolve_specialty",
]
