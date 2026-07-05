import unittest
from unittest.mock import patch

from backend.cardiology.agent import GeneralPhysicianSpecialty
from backend.cardiology.models.session_state import DoctorState
from backend.specialties.dispatcher import SpecialtyDispatcher
from backend.specialties.registry import get_specialty_registry


class SpecialtyFrameworkTests(unittest.TestCase):
    def test_registry_returns_gp_specialty_for_general_departments(self) -> None:
        registry = get_specialty_registry()

        specialty_cls = registry.get("General Physician")
        self.assertEqual(specialty_cls.__name__, "GeneralPhysicianSpecialty")

        instance = specialty_cls()
        self.assertEqual(instance.department, "general")

    def test_dispatcher_resolves_general_physician_and_cardiology(self) -> None:
        dispatcher = SpecialtyDispatcher(registry=get_specialty_registry())

        gp_specialty = dispatcher.dispatch({"selected_department": "General Physician"})
        self.assertEqual(gp_specialty.__class__.__name__, "GeneralPhysicianSpecialty")

        cardiology_specialty = dispatcher.dispatch({"selected_department": "Cardiology"})
        self.assertEqual(cardiology_specialty.__class__.__name__, "CardiologySpecialty")

    def test_dispatcher_raises_for_unknown_department(self) -> None:
        dispatcher = SpecialtyDispatcher(registry=get_specialty_registry())

        with self.assertRaises(KeyError):
            dispatcher.dispatch({"selected_department": "Neurology"})

    def test_gp_specialty_uses_existing_consultation_runner(self) -> None:
        state = DoctorState(user_id="u1", appointment_id="a1", doctor_id="d1", department="general")
        with patch("backend.cardiology.agent.step", return_value=(state, [])) as step_mock:
            specialty = GeneralPhysicianSpecialty()
            result = specialty.run_consultation("u1", "a1", user_message="hello")

        self.assertEqual(result, (state, []))
        step_mock.assert_called_once_with("u1", "a1", "hello", None)

    def test_gp_specialty_generates_summary_from_state(self) -> None:
        state = DoctorState(user_id="u1", appointment_id="a1", doctor_id="d1", department="general")
        state.consultation_summary = {"assessment": "ok"}

        specialty = GeneralPhysicianSpecialty()
        summary = specialty.generate_summary(state)

        self.assertEqual(summary, {"assessment": "ok"})


if __name__ == "__main__":
    unittest.main()
