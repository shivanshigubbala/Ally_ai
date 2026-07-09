import unittest
from unittest.mock import patch, MagicMock
import json
from backend.models.session_state import DoctorState
from backend.neurology.agent import session_complete, questioning

class TestNeurologyMemory(unittest.TestCase):
    @patch("backend.neurology.agent.upsert_clinical_profile")
    @patch("backend.neurology.agent._call_llm")
    def test_longitudinal_memory_neurology(self, mock_call_llm, mock_upsert_profile):
        # 1. Visit 1
        state_v1 = DoctorState(
            user_id="test_patient",
            patient_id="PAT-2026-000001",
            patient_name="John Doe",
            appointment_id="101",
            doctor_id="neurology_physician",
            consultation_context_id="ctx-101",
            doctor_name="Dr. Octopus",
            department="neurology",
            chief_complaint="frequent migraines",
            tests_list=[{"name": "Brain MRI", "reason": "Rule out lesions"}],
            lab_request_status="PENDING_LAB"
        )
        state_v1.consultation_summary = {
            "clinical_assessment": "Neurological review completed.",
            "possible_diagnosis": "Chronic migraines",
            "lab_recommendations": state_v1.tests_list
        }
        
        # Mock the extraction LLM call
        mock_call_llm.return_value = json.dumps({
            "chronic_conditions": ["Type 2 Diabetes"],
            "allergies": ["Penicillin"],
            "current_medications": ["Metformin 500mg"],
            "risk_factors": ["Smoker"]
        })
        
        # Complete visit 1
        mock_emit = MagicMock()
        session_complete(state_v1, mock_emit)
        
        # Assert that upsert_clinical_profile was called
        mock_upsert_profile.assert_called_once()
        args = mock_upsert_profile.call_args[0]
        patient_id_arg, updates_arg = args[0], args[1]
        
        self.assertEqual(patient_id_arg, "PAT-2026-000001")
        self.assertEqual(updates_arg["chronic_conditions"], ["Type 2 Diabetes"])
        self.assertEqual(updates_arg["allergies"], ["Penicillin"])
        self.assertEqual(updates_arg["current_medications"], ["Metformin 500mg"])
        self.assertEqual(updates_arg["risk_factors"], ["Smoker"])
        self.assertEqual(updates_arg["department"], "neurology")
        
        visit_entry = updates_arg["visit_entry"]
        self.assertEqual(visit_entry["appointment_id"], "101")
        self.assertEqual(visit_entry["doctor_name"], "Dr. Octopus")
        self.assertEqual(visit_entry["chief_complaint"], "frequent migraines")
        self.assertEqual(visit_entry["test_status"], "PENDING_LAB")
        
        # 2. Visit 2
        state_v2 = DoctorState(
            user_id="test_patient",
            patient_id="PAT-2026-000001",
            patient_name="John Doe",
            appointment_id="102",
            doctor_id="neurology_physician",
            consultation_context_id="ctx-102",
            doctor_name="Dr. Octopus",
            department="neurology",
            chief_complaint="migraine follow-up",
            conversation_history=[{"role": "user", "content": "Hello doctor"}]
        )
        
        # Mock get_clinical_profile for Visit 2
        mock_profile = {
            "chronic_conditions": ["Type 2 Diabetes"],
            "allergies": ["Penicillin"],
            "current_medications": ["Metformin 500mg"],
            "risk_factors": ["Smoker"],
            "last_visit_per_department": {
                "neurology": visit_entry
            }
        }
        
        with patch("backend.neurology.agent.get_clinical_profile", return_value=mock_profile) as mock_get_profile:
            with patch("backend.neurology.agent._stream_into_emit") as mock_stream:
                questioning(state_v2, mock_emit)
                
                # Verify that the system prompt passed to LLM contains memory details
                mock_stream.assert_called_once()
                messages_arg = mock_stream.call_args[0][0]
                system_prompt = messages_arg[0]["content"]
                
                self.assertIn("Known chronic conditions: Type 2 Diabetes", system_prompt)
                self.assertIn("Known allergies: Penicillin", system_prompt)
                self.assertIn("Current medications (patient-reported): Metformin 500mg", system_prompt)
                self.assertIn("Known risk factors: Smoker", system_prompt)
                self.assertIn("LAST VISIT WITH THIS DEPARTMENT (neurology)", system_prompt)
                self.assertIn("Tests recommended: Brain MRI (status: PENDING_LAB)", system_prompt)

if __name__ == "__main__":
    unittest.main()
