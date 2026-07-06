import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Any

try:
    from backend.db.pgvector_tracker import _conn, HAS_PG
    import psycopg2.extras
except ImportError:
    try:
        from db.pgvector_tracker import _conn, HAS_PG
        import psycopg2.extras
    except ImportError:
        HAS_PG = False
        _conn = None


def coerce_doctor_id(doctor_id: str | int | None) -> int | None:
    if doctor_id is None:
        return None
    doc_str = str(doctor_id).lower()
    if "d5" in doc_str or "d7" in doc_str or doc_str == "1":
        return 1
    elif "d8" in doc_str or doc_str == "2":
        return 2
    elif "d9" in doc_str or doc_str == "3":
        return 3
    else:
        digits = "".join(c for c in doc_str if c.isdigit())
        return int(digits) if digits else 1


def map_db_doctor_id_to_d_id(db_id: int | str) -> str:
    val = str(db_id)
    if val == "1":
        return "d5"
    elif val == "2":
        return "d8"
    elif val == "3":
        return "d9"
    return f"d{val}"


def coerce_slot_id(slot_id: str | int | None) -> int | None:
    if slot_id is None:
        return None
    slot_str = str(slot_id).lower()
    digits = "".join(c for c in slot_str if c.isdigit())
    return int(digits) if digits else 1


def coerce_dept_id(dept: str | int | None) -> int | None:
    if dept is None:
        return None
    dept_str = str(dept).lower()
    if "general" in dept_str or dept_str == "1":
        return 1
    elif "cardiology" in dept_str or dept_str == "2":
        return 2
    elif "neurology" in dept_str or dept_str == "3":
        return 3
    else:
        digits = "".join(c for c in dept_str if c.isdigit())
        return int(digits) if digits else 1


class LocalStore:
    def __init__(self):
        self._lock = threading.Lock()

    def list_departments(self) -> list[dict]:
        if not HAS_PG:
            return []
        with _conn() as conn:
            if conn is None: return []
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("SELECT id::text, name FROM departments ORDER BY id")
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    def list_doctors(self, department: Optional[str] = None) -> list[dict]:
        if not HAS_PG:
            return []
        with _conn() as conn:
            if conn is None: return []
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            if department:
                dept_id = coerce_dept_id(department)
                cur.execute("SELECT id::text, name, department_id::text FROM doctors WHERE department_id = %s ORDER BY id", (dept_id,))
            else:
                cur.execute("SELECT id::text, name, department_id::text FROM doctors ORDER BY id")
            rows = cur.fetchall()
            out = []
            for r in rows:
                r_dict = dict(r)
                r_dict["id"] = map_db_doctor_id_to_d_id(r_dict["id"])
                r_dict["department_id"] = str(r_dict["department_id"])
                out.append(r_dict)
            return out

    def list_slots(self, doctor_id: Optional[str] = None) -> list[dict]:
        if not HAS_PG:
            return []
        with _conn() as conn:
            if conn is None: return []
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            if doctor_id:
                doc_id = coerce_doctor_id(doctor_id)
                cur.execute("SELECT id::text, doctor_id::text, start_time FROM time_slots WHERE is_available = true AND doctor_id = %s ORDER BY start_time", (doc_id,))
            else:
                cur.execute("SELECT id::text, doctor_id::text, start_time FROM time_slots WHERE is_available = true ORDER BY start_time")
            rows = cur.fetchall()
            out = []
            for r in rows:
                r_dict = dict(r)
                r_dict["doctor_id"] = map_db_doctor_id_to_d_id(r_dict["doctor_id"])
                if isinstance(r_dict["start_time"], datetime):
                    r_dict["start_time"] = r_dict["start_time"].isoformat()
                out.append(r_dict)
            return out

    def book_appointment(
        self,
        doctor_id: str,
        slot_id: str,
        patient: str,
        reason: str,
        patient_id: Optional[str] = None,
        session_id: Optional[str] = None,
        department: Optional[str] = None,
        consultation_context_id: Optional[str] = None,
        status: str = "booked",
    ) -> tuple[int, dict]:
        if not patient_id:
            return 422, {"error": "patient_id required"}
        if not HAS_PG:
            return 500, {"error": "DB unavailable"}
        
        doc_id = coerce_doctor_id(doctor_id)
        s_id = coerce_slot_id(slot_id)
        
        with self._lock:
            with _conn() as conn:
                if conn is None: return 500, {"error": "DB unavailable"}
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
                # Check doctor
                cur.execute("SELECT * FROM doctors WHERE id = %s", (doc_id,))
                doc = cur.fetchone()
                if not doc:
                    return 404, {"error": "doctor not found"}
                
                # Check slot
                cur.execute("SELECT * FROM time_slots WHERE id = %s AND doctor_id = %s", (s_id, doc_id))
                slot = cur.fetchone()
                if not slot:
                    return 404, {"error": "slot not found"}
                if not slot.get('is_available', True):
                    return 409, {"error": "slot_taken"}
                
                dept = coerce_dept_id(department) or doc['department_id']
                
                # Book
                cur.execute("""
                    INSERT INTO appointments (user_id, doctor_id, time_slot_id, department_id, reason, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (patient_id, doc_id, s_id, dept, reason, status))
                aid = cur.fetchone()['id']
                
                # Mark slot unavailable
                cur.execute("UPDATE time_slots SET is_available = false WHERE id = %s", (s_id,))
                
                return 200, {"id": str(aid), "confirmed": True}

    def get_appointment(self, appointment_id: str) -> Optional[dict]:
        if not HAS_PG: return None
        try:
            apt_id = int(appointment_id)
        except ValueError:
            return None
            
        with _conn() as conn:
            if conn is None: return None
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT a.id, a.doctor_id, a.time_slot_id as slot_id, a.user_id as patient_id, 
                       a.reason, a.department_id as department, a.status,
                       u.name as patient
                FROM appointments a
                LEFT JOIN users u ON u.id = a.user_id
                WHERE a.id = %s
            """, (apt_id,))
            row = cur.fetchone()
            if not row: return None
            
            res = dict(row)
            res["id"] = str(res["id"])
            res["doctor_id"] = map_db_doctor_id_to_d_id(res["doctor_id"])
            res["slot_id"] = str(res["slot_id"])
            res["department"] = str(res["department"])
            res["session_id"] = None
            res["consultation_context_id"] = None
            return res

_store = LocalStore()

def list_departments() -> list[dict]:
    return _store.list_departments()

def list_doctors(department: Optional[str] = None) -> list[dict]:
    return _store.list_doctors(department)

def list_slots(doctor_id: Optional[str] = None) -> list[dict]:
    return _store.list_slots(doctor_id)

def book_appointment(
    doctor_id: str,
    slot_id: str,
    patient: str,
    reason: str,
    patient_id: Optional[str] = None,
    session_id: Optional[str] = None,
    department: Optional[str] = None,
    consultation_context_id: Optional[str] = None,
    status: str = "booked",
) -> tuple[int, dict]:
    return _store.book_appointment(
        doctor_id,
        slot_id,
        patient,
        reason,
        patient_id=patient_id,
        session_id=session_id,
        department=department,
        consultation_context_id=consultation_context_id,
        status=status,
    )

def get_appointment(appointment_id: str) -> Optional[dict]:
    return _store.get_appointment(appointment_id)
