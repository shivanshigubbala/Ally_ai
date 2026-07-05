"""
HTTP client for the Go appointment microservice.

Provides a thin, department-agnostic wrapper around the appointment booking API.
Base URL is configured via APPOINTMENT_SERVICE_URL environment variable.

No auth, no caching, no retry logic — simple synchronous calls only.
"""
from __future__ import annotations

import os
import requests
from typing import Any


# ---- Custom Exceptions -------------------------------------------------------

class AppointmentServiceError(Exception):
    """Base exception for appointment service errors."""
    pass


class AppointmentServiceUnavailable(AppointmentServiceError):
    """Raised when the service cannot be reached (connection error, timeout, etc.)"""
    pass


class AppointmentNotFound(AppointmentServiceError):
    """Raised when a requested resource (appointment, doctor, slot, user) is not found (404)."""
    pass


class SlotAlreadyBooked(AppointmentServiceError):
    """Raised when attempting to book a slot that is already taken (409)."""
    pass


# ---- Configuration -----------------------------------------------------------

APPOINTMENT_SERVICE_URL = os.getenv("APPOINTMENT_SERVICE_URL", "http://appointment:8081").rstrip("/")
REQUEST_TIMEOUT = 5  # seconds


# ---- Helper -------------------------------------------------------------------

def _safe_request(method: str, endpoint: str, json_data: dict | None = None, params: dict | None = None) -> dict | list:
    """
    Make a request to the appointment service and map HTTP errors to custom exceptions.
    
    Args:
        method: HTTP method ("GET", "POST", "PATCH", etc.)
        endpoint: path relative to base URL (e.g., "/departments")
        json_data: JSON body for POST/PATCH
        params: query parameters
    
    Returns:
        Parsed JSON response (dict or list)
    
    Raises:
        AppointmentServiceUnavailable: on connection error, timeout, or 5xx
        AppointmentNotFound: on 404
        SlotAlreadyBooked: on 409
        AppointmentServiceError: on other 4xx errors
    """
    url = f"{APPOINTMENT_SERVICE_URL}{endpoint}"
    try:
        if method == "GET":
            resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        elif method == "POST":
            resp = requests.post(url, json=json_data, params=params, timeout=REQUEST_TIMEOUT)
        elif method == "PATCH":
            resp = requests.patch(url, json=json_data, params=params, timeout=REQUEST_TIMEOUT)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
    except (requests.ConnectionError, requests.Timeout) as exc:
        raise AppointmentServiceUnavailable(f"Connection to appointment service failed: {exc}") from exc
    except requests.RequestException as exc:
        raise AppointmentServiceUnavailable(f"Request to appointment service failed: {exc}") from exc

    if resp.status_code == 404:
        raise AppointmentNotFound(f"Resource not found: {endpoint}")
    elif resp.status_code == 409:
        raise SlotAlreadyBooked(f"Conflict: slot already booked or resource conflict at {endpoint}")
    elif resp.status_code >= 500:
        raise AppointmentServiceUnavailable(f"Appointment service error {resp.status_code}: {resp.text}")
    elif resp.status_code >= 400:
        raise AppointmentServiceError(f"Appointment service error {resp.status_code}: {resp.text}")

    return resp.json()


# ---- Public API ---------------------------------------------------------------

def list_departments() -> list[dict]:
    """
    List all available medical departments.
    
    Returns:
        List of department dicts: [{id, name}, ...]
    """
    return _safe_request("GET", "/departments")


def list_doctors(department_id: str | None = None) -> list[dict]:
    """
    List all doctors, optionally filtered by department.
    
    Args:
        department_id: optional department ID to filter by
    
    Returns:
        List of doctor dicts: [{id, name, department_id, specialty}, ...]
    """
    params = {}
    if department_id:
        params["department_id"] = department_id
    return _safe_request("GET", "/doctors", params=params)


def list_slots(doctor_id: str | None = None) -> list[dict]:
    """
    List available appointment slots, optionally filtered by doctor.
    
    Args:
        doctor_id: optional doctor ID to filter by
    
    Returns:
        List of slot dicts: [{id, doctor_id, start_time, end_time, is_available}, ...]
    """
    params = {}
    if doctor_id:
        params["doctor_id"] = doctor_id
    return _safe_request("GET", "/slots", params=params)


def create_user(name: str) -> int:
    """
    Create a user record in the Go service.
    
    Args:
        name: user's full name
    
    Returns:
        Go service's user ID (integer)
    
    Raises:
        AppointmentServiceUnavailable: on connection/service errors
        AppointmentServiceError: on other errors
    """
    resp = _safe_request("POST", "/users", json_data={"name": name})
    return resp["id"]


def book(doctor_id: str, go_user_id: int, time_slot_id: str) -> dict:
    """
    Book an appointment for a user with a doctor at a specific time slot.
    
    Args:
        doctor_id: Go service doctor ID
        go_user_id: Go service user ID (returned by create_user)
        time_slot_id: Go service time slot ID
    
    Returns:
        Appointment dict: {id, doctor_id, user_id, time_slot_id, status, booked_at}
    
    Raises:
        AppointmentNotFound: if doctor_id, user_id, or slot_id not found (404)
        SlotAlreadyBooked: if slot is already booked (409)
        AppointmentServiceUnavailable: on connection/service errors
    """
    resp = _safe_request(
        "POST",
        "/appointments",
        json_data={
            "doctor_id": doctor_id,
            "user_id": go_user_id,
            "time_slot_id": time_slot_id,
        }
    )
    return resp


def get_appointments(user_id: str | None = None) -> list[dict]:
    """
    Get all appointments, optionally filtered by user.
    
    Args:
        user_id: optional Go service user ID to filter by
    
    Returns:
        List of appointment dicts: [{id, doctor_id, user_id, time_slot_id, status, booked_at}, ...]
    """
    params = {}
    if user_id:
        params["user_id"] = user_id
    return _safe_request("GET", "/appointments", params=params)


def update_status(appointment_id: str, status: str) -> dict:
    """
    Update the status of an appointment (e.g., from "booked" to "completed").
    
    Args:
        appointment_id: Go service appointment ID
        status: new status (e.g., "completed", "cancelled")
    
    Returns:
        Updated appointment dict: {id, doctor_id, user_id, time_slot_id, status, booked_at}
    
    Raises:
        AppointmentNotFound: if appointment_id not found (404)
        AppointmentServiceUnavailable: on connection/service errors
    """
    resp = _safe_request(
        "PATCH",
        f"/appointments/{appointment_id}/status",
        json_data={"status": status}
    )
    return resp
