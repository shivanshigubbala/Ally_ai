import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg2://allyai:allyai@localhost:5432/allyai",
)

print(DATABASE_URL)

engine = create_engine(DATABASE_URL, future=True)

USERS = [
    {"id": 1, "name": "Aravind"},
    {"id": 2, "name": "Test Patient"},
]

DEPARTMENTS = [
    {"id": 1, "name": "General Practice"},
    {"id": 2, "name": "Cardiology"},
    {"id": 3, "name": "Neurology"},
    {"id": 4, "name": "Endocrinology"},
]

DOCTORS = [
    {"id": 1, "name": "Dr. Shankar", "department_id": 1, "specialty": "General Practice"},
    {"id": 2, "name": "Dr. Aravind", "department_id": 2, "specialty": "Cardiology"},
    {"id": 3, "name": "Dr. Nisha", "department_id": 3, "specialty": "Neurology"},
    {"id": 4, "name": "Dr. Leena", "department_id": 4, "specialty": "Endocrinology"},
]

SLOT_DURATION_MINUTES = 30
SLOTS_PER_DOCTOR = 5


def seed_users(conn):
    for user in USERS:
        conn.execute(
            text(
                """
                INSERT INTO users (id, name)
                VALUES (:id, :name)
                ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name
                """
            ),
            user,
        )
    conn.execute(text("SELECT setval(pg_get_serial_sequence('users', 'id'), (SELECT MAX(id) FROM users))"))


def seed_departments(conn):
    for department in DEPARTMENTS:
        conn.execute(
            text(
                """
                INSERT INTO departments (id, name)
                VALUES (:id, :name)
                ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name
                """
            ),
            department,
        )
    conn.execute(text("SELECT setval(pg_get_serial_sequence('departments', 'id'), (SELECT MAX(id) FROM departments))"))


def seed_doctors(conn):
    for doctor in DOCTORS:
        conn.execute(
            text(
                """
                INSERT INTO doctors (id, name, department_id, specialty)
                VALUES (:id, :name, :department_id, :specialty)
                ON CONFLICT (id) DO UPDATE
                SET name = EXCLUDED.name,
                    department_id = EXCLUDED.department_id,
                    specialty = EXCLUDED.specialty
                """
            ),
            doctor,
        )
    conn.execute(text("SELECT setval(pg_get_serial_sequence('doctors', 'id'), (SELECT MAX(id) FROM doctors))"))


def seed_time_slots(conn):
    start_time = datetime.now(tz=timezone.utc).replace(
        minute=0,
        second=0,
        microsecond=0,
    ) + timedelta(days=1, hours=9)

    inserted = 0
    for doctor_index, doctor in enumerate(DOCTORS):
        doctor_start = start_time + timedelta(hours=doctor_index * 2)
        for slot_index in range(SLOTS_PER_DOCTOR):
            slot_start = doctor_start + timedelta(
                minutes=slot_index * (SLOT_DURATION_MINUTES + 15)
            )
            slot_end = slot_start + timedelta(minutes=SLOT_DURATION_MINUTES)
            slot_id = (doctor["id"] - 1) * SLOTS_PER_DOCTOR + slot_index + 1
            result = conn.execute(
                text(
                    """
                    INSERT INTO time_slots (id, doctor_id, start_time, end_time, is_available)
                    VALUES (:id, :doctor_id, :start_time, :end_time, true)
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {
                    "id": slot_id,
                    "doctor_id": doctor["id"],
                    "start_time": slot_start,
                    "end_time": slot_end,
                },
            )
            inserted += result.rowcount or 0

    conn.execute(text("SELECT setval(pg_get_serial_sequence('time_slots', 'id'), (SELECT MAX(id) FROM time_slots))"))
    return inserted


def main():
    with engine.begin() as conn:
        seed_users(conn)
        seed_departments(conn)
        seed_doctors(conn)
        total_slots = seed_time_slots(conn)

    print("Seed completed:")
    print(f"  users seeded/verified: {len(USERS)}")
    print(f"  departments seeded/verified: {len(DEPARTMENTS)}")
    print(f"  doctors seeded/verified: {len(DOCTORS)}")
    print(f"  time slots inserted: {total_slots}")
    print("Run with DATABASE_URL set if your Postgres URL differs.")


if __name__ == "__main__":
    main()
