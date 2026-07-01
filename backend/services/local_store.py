import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class Department:
    id: str
    name: str


@dataclass
class Doctor:
    id: str
    name: str
    department_id: str


@dataclass
class Slot:
    id: str
    doctor_id: str
    start_time: datetime
    booked: bool = False


@dataclass
class Appointment:
    id: str
    doctor_id: str
    slot_id: str
    patient: str
    reason: str
    department: str
    booked_at: datetime


class LocalStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._depts: dict[str, Department] = {}
        self._doctors: dict[str, Doctor] = {}
        self._slots: dict[str, Slot] = {}
        self._appointments: dict[str, Appointment] = {}
        self._seed()

    def _next_id(self, prefix: str, existing: dict) -> str:
        n = 0
        for k in existing:
            if k.startswith(prefix):
                try:
                    n = max(n, int(k[len(prefix):]))
                except ValueError:
                    pass
        return f"{prefix}{n + 1}"

    def _seed(self):
        depts = [
            Department("general", "General Practice"),
        ]
        for d in depts:
            self._depts[d.id] = d

        docs = [
            Doctor("d5", "Dr. Shankar", "general"),
            Doctor("d6", "Dr. Maya Patel", "general"),
            Doctor("d7", "Dr. Omar Khan", "general"),
        ]
        for d in docs:
            self._doctors[d.id] = d

        now = datetime.now().replace(microsecond=0, second=0, minute=0) + timedelta(hours=1)
        slot_idx = 0
        for doc in docs:
            for h in range(4):
                slot_idx += 1
                sid = f"s{slot_idx}"
                self._slots[sid] = Slot(sid, doc.id, now + timedelta(hours=h * 2))

    # --- public API (mirrors appointment_client) ---

    def list_departments(self) -> list[dict]:
        with self._lock:
            return sorted(
                [{"id": d.id, "name": d.name} for d in self._depts.values()],
                key=lambda x: x["id"],
            )

    def list_doctors(self, department: Optional[str] = None) -> list[dict]:
        with self._lock:
            out = []
            for d in self._doctors.values():
                if department and d.department_id != department:
                    continue
                out.append({
                    "id": d.id,
                    "name": d.name,
                    "department_id": d.department_id,
                })
            return sorted(out, key=lambda x: x["id"])

    def list_slots(self, doctor_id: Optional[str] = None) -> list[dict]:
        with self._lock:
            booked_ids = {a.slot_id for a in self._appointments.values()}
            out = []
            for s in self._slots.values():
                if doctor_id and s.doctor_id != doctor_id:
                    continue
                if s.id in booked_ids:
                    continue
                out.append({
                    "id": s.id,
                    "doctor_id": s.doctor_id,
                    "start_time": s.start_time.isoformat(),
                })
            return sorted(out, key=lambda x: x["start_time"])

    def book_appointment(self, doctor_id: str, slot_id: str, patient: str, reason: str) -> tuple[int, dict]:
        with self._lock:
            if doctor_id not in self._doctors:
                return 404, {"error": "doctor not found"}
            slot = self._slots.get(slot_id)
            if not slot or slot.doctor_id != doctor_id:
                return 404, {"error": "slot not found"}
            for a in self._appointments.values():
                if a.slot_id == slot_id:
                    return 409, {"error": "slot_taken"}
            aid = self._next_id("a", self._appointments)
            apt = Appointment(
                id=aid,
                doctor_id=doctor_id,
                slot_id=slot_id,
                patient=patient,
                reason=reason,
                department=self._doctors[doctor_id].department_id,
                booked_at=datetime.now(),
            )
            self._appointments[aid] = apt
            return 200, {"id": aid, "confirmed": True}


# Singleton
_store = LocalStore()


def list_departments() -> list[dict]:
    return _store.list_departments()


def list_doctors(department: Optional[str] = None) -> list[dict]:
    return _store.list_doctors(department)


def list_slots(doctor_id: Optional[str] = None) -> list[dict]:
    return _store.list_slots(doctor_id)


def book_appointment(doctor_id: str, slot_id: str, patient: str, reason: str) -> tuple[int, dict]:
    return _store.book_appointment(doctor_id, slot_id, patient, reason)
