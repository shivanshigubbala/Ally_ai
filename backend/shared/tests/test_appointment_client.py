"""
Unit tests for backend.shared.appointment_client

Tests the HTTP wrapper functions and error mapping for the Go appointment service.
All HTTP calls are mocked via unittest.mock.patch to avoid requiring the service to be running.

Run inside Docker:
  docker compose -f docker-compose.checks.yml up --build --abort-on-container-exit --exit-code-from backend-checks
"""
import unittest
from unittest.mock import patch, MagicMock
import requests

from backend.shared import appointment_client
from backend.shared.appointment_client import (
    AppointmentServiceUnavailable,
    AppointmentNotFound,
    SlotAlreadyBooked,
    AppointmentServiceError,
)


class TestAppointmentClient(unittest.TestCase):
    """Test appointment_client module."""

    @patch('backend.shared.appointment_client.requests.get')
    def test_list_departments_success(self, mock_get):
        """Test successful list_departments call."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"id": "gen", "name": "General Physician"},
            {"id": "card", "name": "Cardiology"},
        ]
        mock_get.return_value = mock_resp

        result = appointment_client.list_departments()

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "gen")
        mock_get.assert_called_once()

    @patch('backend.shared.appointment_client.requests.get')
    def test_list_doctors_with_filter(self, mock_get):
        """Test list_doctors with department_id filter."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"id": "d1", "name": "Dr. Shankar", "department_id": "gen", "specialty": "GP"},
        ]
        mock_get.return_value = mock_resp

        result = appointment_client.list_doctors(department_id="gen")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Dr. Shankar")
        # Verify the query param was passed
        call_args = mock_get.call_args
        self.assertIn("params", call_args.kwargs)
        self.assertEqual(call_args.kwargs["params"]["department_id"], "gen")

    @patch('backend.shared.appointment_client.requests.get')
    def test_list_slots_success(self, mock_get):
        """Test successful list_slots call."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"id": "slot1", "doctor_id": "d1", "start_time": "2026-07-04T09:00:00", "end_time": "2026-07-04T09:30:00", "is_available": True},
        ]
        mock_get.return_value = mock_resp

        result = appointment_client.list_slots(doctor_id="d1")

        self.assertEqual(len(result), 1)
        self.assertTrue(result[0]["is_available"])

    @patch('backend.shared.appointment_client.requests.post')
    def test_create_user_success(self, mock_post):
        """Test successful create_user call."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": 42, "name": "John Doe"}
        mock_post.return_value = mock_resp

        result = appointment_client.create_user("John Doe")

        self.assertEqual(result, 42)
        mock_post.assert_called_once()

    @patch('backend.shared.appointment_client.requests.post')
    def test_book_success(self, mock_post):
        """Test successful book call."""
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {
            "id": "apt1",
            "doctor_id": "d1",
            "user_id": 42,
            "time_slot_id": "slot1",
            "status": "booked",
            "booked_at": "2026-07-03T10:00:00",
        }
        mock_post.return_value = mock_resp

        result = appointment_client.book("d1", 42, "slot1")

        self.assertEqual(result["id"], "apt1")
        self.assertEqual(result["status"], "booked")

    @patch('backend.shared.appointment_client.requests.patch')
    def test_update_status_success(self, mock_patch):
        """Test successful update_status call."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "id": "apt1",
            "doctor_id": "d1",
            "user_id": 42,
            "time_slot_id": "slot1",
            "status": "completed",
            "booked_at": "2026-07-03T10:00:00",
        }
        mock_patch.return_value = mock_resp

        result = appointment_client.update_status("apt1", "completed")

        self.assertEqual(result["status"], "completed")

    @patch('backend.shared.appointment_client.requests.get')
    def test_get_appointments_success(self, mock_get):
        """Test successful get_appointments call."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"id": "apt1", "doctor_id": "d1", "user_id": 42, "status": "booked"},
        ]
        mock_get.return_value = mock_resp

        result = appointment_client.get_appointments(user_id="42")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "apt1")

    # ---- Error Mapping Tests ----

    @patch('backend.shared.appointment_client.requests.get')
    def test_404_raises_appointment_not_found(self, mock_get):
        """Test that 404 is mapped to AppointmentNotFound."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        with self.assertRaises(AppointmentNotFound):
            appointment_client.list_doctors()

    @patch('backend.shared.appointment_client.requests.post')
    def test_409_raises_slot_already_booked(self, mock_post):
        """Test that 409 is mapped to SlotAlreadyBooked."""
        mock_resp = MagicMock()
        mock_resp.status_code = 409
        mock_post.return_value = mock_resp

        with self.assertRaises(SlotAlreadyBooked):
            appointment_client.book("d1", 42, "slot1")

    @patch('backend.shared.appointment_client.requests.post')
    def test_connection_error_raises_unavailable(self, mock_post):
        """Test that connection errors are mapped to AppointmentServiceUnavailable."""
        mock_post.side_effect = requests.ConnectionError("Network unreachable")

        with self.assertRaises(AppointmentServiceUnavailable):
            appointment_client.create_user("John Doe")

    @patch('backend.shared.appointment_client.requests.get')
    def test_timeout_raises_unavailable(self, mock_get):
        """Test that timeouts are mapped to AppointmentServiceUnavailable."""
        mock_get.side_effect = requests.Timeout("Request timed out")

        with self.assertRaises(AppointmentServiceUnavailable):
            appointment_client.list_departments()

    @patch('backend.shared.appointment_client.requests.get')
    def test_500_raises_unavailable(self, mock_get):
        """Test that 5xx errors are mapped to AppointmentServiceUnavailable."""
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_get.return_value = mock_resp

        with self.assertRaises(AppointmentServiceUnavailable):
            appointment_client.list_departments()

    @patch('backend.shared.appointment_client.requests.post')
    def test_400_raises_generic_error(self, mock_post):
        """Test that 4xx errors (other than 404, 409) are mapped to AppointmentServiceError."""
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = "Bad Request"
        mock_post.return_value = mock_resp

        with self.assertRaises(AppointmentServiceError):
            appointment_client.create_user("John Doe")


if __name__ == "__main__":
    unittest.main()
