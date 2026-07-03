-- Go service tables: departments, doctors, time_slots, appointments, lab_tests, reports, inbox

CREATE TABLE IF NOT EXISTS departments (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS doctors (
    id SERIAL PRIMARY KEY,
    department_id INTEGER NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    specialty TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS time_slots (
    id SERIAL PRIMARY KEY,
    doctor_id INTEGER NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    is_available BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS appointments (
    id SERIAL PRIMARY KEY,
    doctor_id INTEGER NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL,
    time_slot_id INTEGER NOT NULL REFERENCES time_slots(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'scheduled',
    booked_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS lab_tests (
    id SERIAL PRIMARY KEY,
    appointment_id INTEGER NOT NULL REFERENCES appointments(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL,
    test_name TEXT NOT NULL,
    reason TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    result JSONB,
    remarks TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS reports (
    id SERIAL PRIMARY KEY,
    appointment_id INTEGER NOT NULL REFERENCES appointments(id) ON DELETE CASCADE,
    report_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS inbox (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS lab_reports (
    id SERIAL PRIMARY KEY,

    appointment_id INTEGER NOT NULL
        REFERENCES appointments(id) ON DELETE CASCADE,

    user_id INTEGER NOT NULL,

    pdf_name TEXT NOT NULL,

    pdf_path TEXT NOT NULL,

    status TEXT NOT NULL DEFAULT 'generated',

    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);