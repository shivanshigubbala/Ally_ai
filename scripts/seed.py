import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg2://allyai:allyai@localhost:5432/allyai",
)

print(DATABASE_URL)

engine = create_engine(DATABASE_URL, future=True)

DEPARTMENTS = [
    {'name': 'Cardiology'},
    {'name': 'Neurology'},
    {'name': 'Endocrinology'},
]

DOCTORS = [
    {'name': 'Dr. Aravind', 'specialty': 'Cardiology', 'department': 'Cardiology'},
    {'name': 'Dr. Nisha', 'specialty': 'Neurology', 'department': 'Neurology'},
    {'name': 'Dr. Leena', 'specialty': 'Endocrinology', 'department': 'Endocrinology'},
]

SLOT_DURATION_MINUTES = 30
SLOTS_PER_DOCTOR = 5


def get_or_create_department(conn, name):
    result = conn.execute(
        text('SELECT id FROM departments WHERE name = :name'),
        {'name': name},
    ).fetchone()
    if result:
        return result[0]

    result = conn.execute(
        text('INSERT INTO departments (name) VALUES (:name) RETURNING id'),
        {'name': name},
    ).fetchone()
    return result[0]


def get_or_create_doctor(conn, name, specialty, department_id):
    result = conn.execute(
        text(
            'SELECT id FROM doctors WHERE name = :name AND department_id = :department_id'
        ),
        {'name': name, 'department_id': department_id},
    ).fetchone()
    if result:
        return result[0]

    result = conn.execute(
        text(
            'INSERT INTO doctors (department_id, name, specialty) '
            'VALUES (:department_id, :name, :specialty) RETURNING id'
        ),
        {'department_id': department_id, 'name': name, 'specialty': specialty},
    ).fetchone()
    return result[0]


def create_time_slots(conn, doctor_id, start_time):
    existing = conn.execute(
        text('SELECT COUNT(1) FROM time_slots WHERE doctor_id = :doctor_id'),
        {'doctor_id': doctor_id},
    ).scalar_one()
    if existing >= SLOTS_PER_DOCTOR:
        return 0

    inserted = 0
    slot_start = start_time
    for _ in range(SLOTS_PER_DOCTOR):
        slot_end = slot_start + timedelta(minutes=SLOT_DURATION_MINUTES)
        conn.execute(
            text(
                'INSERT INTO time_slots (doctor_id, start_time, end_time, is_available) '
                'VALUES (:doctor_id, :start_time, :end_time, true)'
            ),
            {
                'doctor_id': doctor_id,
                'start_time': slot_start,
                'end_time': slot_end,
            },
        )
        slot_start = slot_end + timedelta(minutes=15)
        inserted += 1

    return inserted


def main():
    now = datetime.now(tz=timezone.utc).replace(minute=0, second=0, microsecond=0)
    start_time = now + timedelta(days=1, hours=9)

    with engine.begin() as conn:
        department_ids = {}
        for department in DEPARTMENTS:
            department_id = get_or_create_department(conn, department['name'])
            department_ids[department['name']] = department_id

        doctor_ids = {}
        for doctor in DOCTORS:
            doctor_id = get_or_create_doctor(
                conn,
                doctor['name'],
                doctor['specialty'],
                department_ids[doctor['department']],
            )
            doctor_ids[doctor['name']] = doctor_id

        total_slots = 0
        for index, doctor in enumerate(DOCTORS):
            slot_time = start_time + timedelta(hours=index * 2)
            total_slots += create_time_slots(
                conn,
                doctor_ids[doctor['name']],
                slot_time,
            )

    print('Seed completed:')
    print(f'  departments seeded/verified: {len(DEPARTMENTS)}')
    print(f'  doctors seeded/verified: {len(DOCTORS)}')
    print(f'  time slots inserted: {total_slots}')
    print('Run with DATABASE_URL set if your Postgres URL differs.')


if __name__ == '__main__':
    main()

