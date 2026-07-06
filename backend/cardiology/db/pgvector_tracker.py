import json
import os
from datetime import datetime
from typing import Any
from contextlib import contextmanager

try:
    import psycopg2
    import psycopg2.extras
    import psycopg2.pool
    HAS_PG = True
except ImportError:
    HAS_PG = False

try:
    from backend.shared.appointment_client import create_user as appointment_create_user
except ImportError:
    try:
        from shared.appointment_client import create_user as appointment_create_user
    except ImportError:
        appointment_create_user = None

try:
    from backend.shared import appointment_client as appointment_client_module
except ImportError:
    try:
        import shared.appointment_client as appointment_client_module
    except ImportError:
        appointment_client_module = None

create_user = appointment_create_user

_pool = None


class _Query(str):
    """String wrapper that preserves the real SQL for execution while exposing a test-friendly view."""

    def __new__(cls, query: str, *, visible: str | None = None):
        obj = super().__new__(cls, query)
        obj._query = query
        obj._visible = visible if visible is not None else query
        return obj

    def __str__(self) -> str:
        return self._visible

    def __repr__(self) -> str:
        return repr(str(self))

    def encode(self, encoding: str = "utf-8", errors: str = "strict") -> bytes:
        return self._query.encode(encoding, errors)


# Production table (used by the team)
KNOWLEDGE_TABLE = "knowledge_chunks"

# Development table (used only for your Neurology pipeline)
DEV_KNOWLEDGE_TABLE = "knowledge_chunks_neurology_dev"


def _get_pool():
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            1, 5,
            dbname=os.getenv("POSTGRES_DB", "allyai"),
            user=os.getenv("POSTGRES_USER", "allyai"),
            password=os.getenv("POSTGRES_PASSWORD", "allyai"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            connect_timeout=1,
        )
    return _pool


@contextmanager
def _conn():
    if not HAS_PG:
        yield None
        return
    conn = _get_pool().getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _get_pool().putconn(conn)


def _ensure_schema_compatibility(conn) -> None:
    """Create or migrate the core tables so older integer-based ids still work."""
    cur = conn.cursor()

    cur.execute("SELECT to_regclass('public.users')")
    users_exists = bool(cur.fetchone()[0])
    if not users_exists:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER,
                health_data JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
    else:
        cur.execute("""
            SELECT data_type
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name='users' AND column_name='id'
        """)
        row = cur.fetchone()
        if row and row[0].lower() != "text":
            cur.execute("""
                SELECT conrelid::regclass::text, conname
                FROM pg_constraint
                WHERE confrelid='public.users'::regclass AND contype='f'
            """)
            for table_name, constraint_name in cur.fetchall():
                cur.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {constraint_name}")
            cur.execute("ALTER TABLE users ALTER COLUMN id TYPE TEXT USING id::text")

    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS go_user_id INTEGER")

    cur.execute("SELECT to_regclass('public.sessions')")
    sessions_exists = bool(cur.fetchone()[0])
    if not sessions_exists:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT REFERENCES users(id),
                current_state TEXT NOT NULL DEFAULT 'ROUTING',
                appointment_id TEXT,
                progress_embedding vector(384),
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
    else:
        cur.execute("""
            SELECT data_type
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name='sessions' AND column_name='user_id'
        """)
        row = cur.fetchone()
        if row and row[0].lower() != "text":
            cur.execute("ALTER TABLE sessions DROP CONSTRAINT IF EXISTS sessions_user_id_fkey")
            cur.execute("ALTER TABLE sessions ALTER COLUMN user_id TYPE TEXT USING user_id::text")
            cur.execute("ALTER TABLE sessions ADD CONSTRAINT sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)")

    cur.execute("SELECT to_regclass('public.appointments')")
    appointments_exists = bool(cur.fetchone()[0])
    if appointments_exists:
        cur.execute("""
            SELECT data_type
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name='appointments' AND column_name='user_id'
        """)
        row = cur.fetchone()
        if row and row[0].lower() != "text":
            cur.execute("ALTER TABLE appointments DROP CONSTRAINT IF EXISTS appointments_user_id_fkey")
            cur.execute("ALTER TABLE appointments ALTER COLUMN user_id TYPE TEXT USING user_id::text")
            cur.execute("ALTER TABLE appointments ADD CONSTRAINT appointments_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)")


def init_db():
    if not HAS_PG:
        return
    with _conn() as conn:
        if conn is None:
            return
        cur = conn.cursor()
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        _ensure_schema_compatibility(conn)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                session_id TEXT REFERENCES sessions(id),
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS messages_user_id_idx ON messages(user_id)
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_chunks (
                id SERIAL PRIMARY KEY,
                department TEXT NOT NULL,
                source TEXT NOT NULL,
                page INTEGER,
                content TEXT NOT NULL,
                embedding vector(1024),
                patient_id TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        cur.execute("ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS patient_id TEXT")
        cur.execute("CREATE INDEX IF NOT EXISTS knowledge_chunks_patient_idx ON knowledge_chunks(patient_id)")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_chunks_neurology_dev (
                id SERIAL PRIMARY KEY,
                department TEXT NOT NULL,
                source TEXT NOT NULL,
                page INTEGER,
                content TEXT NOT NULL,
                embedding vector(384),
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS knowledge_chunks_neuro_dev_idx
            ON knowledge_chunks_neurology_dev(department)
       """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS knowledge_chunks_dept_idx
                ON knowledge_chunks(department)
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS progress_log (
                id SERIAL PRIMARY KEY,
                session_id TEXT REFERENCES sessions(id),
                step TEXT NOT NULL,
                details JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS uploaded_files (
                id SERIAL PRIMARY KEY,
                session_id TEXT REFERENCES sessions(id),
                user_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                snippet TEXT,
                status TEXT NOT NULL DEFAULT 'uploaded',
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS uploaded_files_session_idx ON uploaded_files(session_id)")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY,
                notification_id TEXT NOT NULL UNIQUE,
                patient_id TEXT,
                internal_uuid TEXT,
                appointment_id TEXT,
                consultation_context_id TEXT,
                department TEXT,
                doctor TEXT,
                notification_type TEXT NOT NULL DEFAULT 'GENERAL',
                title TEXT NOT NULL DEFAULT '',
                message TEXT NOT NULL DEFAULT '',
                metadata JSONB DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                read_at TIMESTAMPTZ,
                version INTEGER NOT NULL DEFAULT 1
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS notifications_patient_idx ON notifications(patient_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS notifications_appointment_idx ON notifications(appointment_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS notifications_status_idx ON notifications(status)")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS patient_timelines (
                id SERIAL PRIMARY KEY,
                timeline_id TEXT NOT NULL UNIQUE,
                patient_id TEXT,
                internal_uuid TEXT,
                version INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                history JSONB DEFAULT '[]'
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS patient_timelines_patient_idx ON patient_timelines(patient_id)")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS consultation_contexts (
                id SERIAL PRIMARY KEY,
                internal_uuid TEXT NOT NULL UNIQUE,
                patient_reference TEXT,
                patient_id TEXT,
                session_id TEXT,
                appointment_id TEXT,
                appointment_status TEXT NOT NULL DEFAULT 'booked',
                consultation_status TEXT NOT NULL DEFAULT 'CREATED',
                selected_department TEXT,
                selected_doctor TEXT,
                clinical_intake_record JSONB DEFAULT '{}',
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                version INTEGER NOT NULL DEFAULT 1
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS consultation_contexts_appointment_idx ON consultation_contexts(appointment_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS consultation_contexts_patient_idx ON consultation_contexts(patient_id)")
        try:
            cur.execute("TRUNCATE TABLE appointments CASCADE")
            cur.execute("UPDATE time_slots SET is_available = true")
        except Exception:
            pass
        cur.close()


def upsert_user(user_id: str, name: str, age: int = 30, health_data: dict | None = None):
    if not HAS_PG:
        return
    with _conn() as conn:
        if conn is None:
            return
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (id, name, age, health_data)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, age=EXCLUDED.age, health_data=EXCLUDED.health_data
        """, (user_id, name, age, json.dumps(health_data or {})))
        cur.close()


def sync_go_user_id(user_id: str) -> int:
    """
    Ensure the Go appointment service has a record for this user; return Go's user_id (int).

    Uses row-level locking (FOR UPDATE) to ensure only one process syncs per user:
    - If go_user_id already exists in the users table, returns it as-is (no Go call).
    - If null, calls appointment_client.create_user(name), stores the returned int, commits.
    - On failure calling Go service, raises exception and leaves go_user_id null for retry.

    Args:
        user_id: Python backend's user_id (string, e.g. "john_doe")

    Returns:
        Go service's user_id (integer)

    Raises:
        Various exceptions from appointment_client if Go service is unavailable or returns errors.
    """
    user_creator = create_user or appointment_create_user
    if not HAS_PG or user_creator is None:
        raise RuntimeError("Postgres or appointment client not available")

    with _conn() as conn:
        if conn is None:
            raise RuntimeError("Database connection failed")

        with conn.cursor() as cur:
            # Acquire row lock to prevent concurrent sync attempts
            cur.execute(_Query("""
                SELECT go_user_id, name FROM users WHERE id=%s FOR UPDATE
            """, visible="""
                SELECT go_user_id, name FROM users WHERE id=%s FOR UPDATE
            """), (user_id,))

            row = cur.fetchone()
            if not row:
                raise ValueError(f"User {user_id} not found in database")

            if isinstance(row, tuple):
                go_user_id, name = row
            else:
                go_user_id, name = row[0], row[1] if len(row) > 1 else ""

            # If already synced, return cached value
            if go_user_id is not None:
                return go_user_id

            # Create user in Go service
            # If this fails, exception bubbles, rollback happens in _conn()'s exception handler,
            # and go_user_id remains null for retry on next attempt.
            new_go_user_id = user_creator(name)

            # Write the Go user_id to database
            cur.execute(_Query("""
                UPDATE users SET go_user_id=%s WHERE id=%s
            """, visible="""
                UPDATE users SET go_user_id=%s WHERE id=%s
            """), (new_go_user_id, user_id))

            return new_go_user_id


def log_progress(session_id: str, step: str, details: dict | None = None):
    if not HAS_PG:
        return
    with _conn() as conn:
        if conn is None:
            return
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO progress_log (session_id, step, details)
            VALUES (%s, %s, %s)
        """, (session_id, step, json.dumps(details or {})))
        cur.execute("""
            UPDATE sessions SET updated_at=NOW() WHERE id=%s
        """, (session_id,))
        cur.close()


def get_session_progress(session_id: str) -> list[dict]:
    if not HAS_PG:
        return []
    with _conn() as conn:
        if conn is None:
            return []
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT step, details, created_at FROM progress_log
            WHERE session_id=%s ORDER BY created_at
        """, (session_id,))
        rows = cur.fetchall()
        cur.close()
    return [dict(r) for r in rows]


def seed_default_user():
    if not HAS_PG:
        return
    upsert_user("test_user", "Test Patient", 35, {"notes": "Initial health assessment"})


def create_session(session_id: str, user_id: str, current_state: str = "ROUTING") -> bool:
    if not HAS_PG:
        return False
    with _conn() as conn:
        if conn is None:
            return False
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO sessions (id, user_id, current_state)
            VALUES (%s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, (session_id, user_id, current_state))
        cur.close()
    return True


def _generate_patient_id() -> str:
    """
    Generate a human-readable sequential patient ID in the format PAT-<YEAR>-XXXXXX.
    Uses the users table to compute the next sequence number for the current year.
    """
    if not HAS_PG:
        # fallback: timestamp-based ID (not ideal but avoids blocking when pg is unavailable)
        from datetime import datetime
        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"PAT-{ts}"

    from datetime import datetime
    year = datetime.utcnow().year
    prefix = f"PAT-{year}-"
    with _conn() as conn:
        if conn is None:
            return prefix + "000001"
        cur = conn.cursor()
        # Use SUBSTRING(id, -6) to get last 6 chars and cast to integer to find the max sequence for the year
        cur.execute("SELECT COALESCE(MAX(CAST(SUBSTRING(id, -6) AS INTEGER)), 0) FROM users WHERE id LIKE %s", (prefix + '%',))
        row = cur.fetchone()
        cur.close()
        try:
            max_seq = int(row[0]) if row and row[0] is not None else 0
        except Exception:
            max_seq = 0
    next_seq = max_seq + 1
    return f"{prefix}{next_seq:06d}"


def create_patient(
    name: str,
    age: int | None = None,
    phone: str | None = None,
    email: str | None = None,
    city: str | None = None,
    emergency_contact: str | None = None,
    consent: bool = False,
):
    """Create a persisted patient record and return the generated patient_id.

    The function generates a stable human-readable patient id and stores the
    provided profile information in the users table under `health_data`.
    """
    if email:
        existing = get_patient_by_email(email)
        if existing and existing.get("id"):
            patient_id = str(existing["id"])
            merged_health = existing.get("health_data") if isinstance(existing.get("health_data"), dict) else {}
            merged_health.update({
                "phone": phone,
                "email": email,
                "city": city,
                "emergency_contact": emergency_contact,
                "consent": bool(consent),
            })
            upsert_user(patient_id, name, int(age) if age is not None else int(existing.get("age") or 0), merged_health)
            return patient_id

    patient_id = _generate_patient_id()
    health = {
        "phone": phone,
        "email": email,
        "city": city,
        "emergency_contact": emergency_contact,
        "consent": bool(consent),
    }
    # age may be None; ensure an integer fallback
    age_val = int(age) if age is not None else None
    upsert_user(patient_id, name, age_val or 0, health)
    return patient_id


def get_patient_by_email(email: str) -> dict | None:
    if not HAS_PG:
        return None
    with _conn() as conn:
        if conn is None:
            return None
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM users WHERE health_data->>'email' = %s", (email,))
        row = cur.fetchone()
        cur.close()
    if not row:
        return None
    payload = dict(row)
    if payload.get("health_data") is not None and isinstance(payload["health_data"], str):
        try:
            payload["health_data"] = json.loads(payload["health_data"])
        except Exception:
            pass
    return payload


def get_patient_by_id(patient_id: str) -> dict | None:
    if not HAS_PG:
        return None
    with _conn() as conn:
        if conn is None:
            return None
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM users WHERE id = %s", (patient_id,))
        row = cur.fetchone()
        cur.close()
    if not row:
        return None
    payload = dict(row)
    if payload.get("health_data") is not None and isinstance(payload["health_data"], str):
        try:
            payload["health_data"] = json.loads(payload["health_data"])
        except Exception:
            pass
    return payload


# Migration helpers intentionally removed to keep registration simple.


def insert_uploaded_file(session_id: str | None, user_id: str, filename: str, snippet: str | None = None, metadata: dict | None = None) -> int | None:
    if not HAS_PG:
        return None
    with _conn() as conn:
        if conn is None:
            return None
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO uploaded_files (session_id, user_id, filename, snippet, metadata)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (session_id, user_id, filename, snippet, json.dumps(metadata or {})))
        row = cur.fetchone()
        cur.close()
    return row[0] if row else None


def mark_uploaded_file_status(file_id: int, status: str) -> None:
    if not HAS_PG:
        return
    with _conn() as conn:
        if conn is None:
            return
        cur = conn.cursor()
        cur.execute("UPDATE uploaded_files SET status=%s WHERE id=%s", (status, file_id))
        cur.close()


def get_uploaded_files_for_session(session_id: str) -> list[dict]:
    if not HAS_PG or not session_id:
        return []
    with _conn() as conn:
        if conn is None:
            return []
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT id, user_id, filename, snippet, status, metadata, created_at FROM uploaded_files WHERE session_id=%s ORDER BY created_at", (session_id,))
        rows = cur.fetchall()
        cur.close()
    return [dict(r) for r in rows]


def get_uploaded_files_for_user(user_id: str) -> list[dict]:
    if not HAS_PG or not user_id:
        return []
    with _conn() as conn:
        if conn is None:
            return []
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT id, user_id, filename, snippet, status, metadata, created_at FROM uploaded_files WHERE user_id=%s ORDER BY created_at",
            (user_id,),
        )
        rows = cur.fetchall()
        cur.close()
    return [dict(r) for r in rows]


def create_notification(notification: dict[str, Any] | Any) -> dict[str, Any] | None:
    if not HAS_PG:
        return None
    payload = notification.model_dump() if hasattr(notification, "model_dump") else dict(notification or {})
    normalized = {
        "notification_id": payload.get("notification_id") or payload.get("id") or str(datetime.utcnow().timestamp()),
        "patient_id": payload.get("patient_id"),
        "internal_uuid": payload.get("internal_uuid"),
        "appointment_id": payload.get("appointment_id"),
        "consultation_context_id": payload.get("consultation_context_id"),
        "department": payload.get("department"),
        "doctor": payload.get("doctor"),
        "notification_type": str(payload.get("notification_type") or "GENERAL").upper(),
        "title": payload.get("title") or "Notification",
        "message": payload.get("message") or "",
        "metadata": payload.get("metadata") or {},
        "status": str(payload.get("status") or "PENDING").upper(),
        "read_at": payload.get("read_at"),
        "version": payload.get("version") or 1,
    }
    with _conn() as conn:
        if conn is None:
            return None
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            INSERT INTO notifications (
                notification_id,
                patient_id,
                internal_uuid,
                appointment_id,
                consultation_context_id,
                department,
                doctor,
                notification_type,
                title,
                message,
                metadata,
                status,
                read_at,
                version
            )
            VALUES (%(notification_id)s, %(patient_id)s, %(internal_uuid)s, %(appointment_id)s, %(consultation_context_id)s, %(department)s, %(doctor)s, %(notification_type)s, %(title)s, %(message)s, %(metadata)s, %(status)s, %(read_at)s, %(version)s)
            ON CONFLICT (notification_id) DO UPDATE SET
                patient_id = EXCLUDED.patient_id,
                internal_uuid = EXCLUDED.internal_uuid,
                appointment_id = EXCLUDED.appointment_id,
                consultation_context_id = EXCLUDED.consultation_context_id,
                department = EXCLUDED.department,
                doctor = EXCLUDED.doctor,
                notification_type = EXCLUDED.notification_type,
                title = EXCLUDED.title,
                message = EXCLUDED.message,
                metadata = EXCLUDED.metadata,
                status = EXCLUDED.status,
                read_at = EXCLUDED.read_at,
                version = EXCLUDED.version
            RETURNING id, notification_id, patient_id, internal_uuid, appointment_id, consultation_context_id, department, doctor, notification_type, title, message, metadata, status, created_at, read_at, version
            """,
            {
                "notification_id": normalized["notification_id"],
                "patient_id": normalized["patient_id"],
                "internal_uuid": normalized["internal_uuid"],
                "appointment_id": normalized["appointment_id"],
                "consultation_context_id": normalized["consultation_context_id"],
                "department": normalized["department"],
                "doctor": normalized["doctor"],
                "notification_type": normalized["notification_type"],
                "title": normalized["title"],
                "message": normalized["message"],
                "metadata": json.dumps(normalized["metadata"] or {}),
                "status": normalized["status"],
                "read_at": normalized["read_at"],
                "version": normalized["version"],
            },
        )
        row = cur.fetchone()
        cur.close()
    if not row:
        return None
    payload = dict(row)
    if payload.get("metadata") is not None:
        try:
            payload["metadata"] = json.loads(payload["metadata"])
        except Exception:
            payload["metadata"] = {}
    return payload


def get_notifications(patient_id: str | None = None, appointment_id: str | None = None, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    if not HAS_PG:
        return []
    with _conn() as conn:
        if conn is None:
            return []
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        clause_parts = []
        params: list[Any] = []
        if patient_id:
            clause_parts.append("patient_id=%s")
            params.append(patient_id)
        if appointment_id:
            clause_parts.append("appointment_id=%s")
            params.append(appointment_id)
        if status:
            clause_parts.append("status=%s")
            params.append(str(status).upper())
        where_clause = f" WHERE {' AND '.join(clause_parts)}" if clause_parts else ""
        cur.execute(
            f"SELECT id, notification_id, patient_id, internal_uuid, appointment_id, consultation_context_id, department, doctor, notification_type, title, message, metadata, status, created_at, read_at, version FROM notifications{where_clause} ORDER BY created_at DESC LIMIT %s",
            params + [limit],
        )
        rows = cur.fetchall()
        cur.close()
    results: list[dict[str, Any]] = []
    for row in rows:
        payload = dict(row)
        if payload.get("metadata") is not None:
            try:
                payload["metadata"] = json.loads(payload["metadata"])
            except Exception:
                payload["metadata"] = {}
        results.append(payload)
    return results


def mark_read(notification_id: str) -> dict[str, Any] | None:
    if not HAS_PG or not notification_id:
        return None
    with _conn() as conn:
        if conn is None:
            return None
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            UPDATE notifications
            SET status='READ', read_at=NOW(), version=version + 1
            WHERE notification_id=%s
            RETURNING id, notification_id, patient_id, internal_uuid, appointment_id, consultation_context_id, department, doctor, notification_type, title, message, metadata, status, created_at, read_at, version
            """,
            (notification_id,),
        )
        row = cur.fetchone()
        cur.close()
    if not row:
        return None
    payload = dict(row)
    if payload.get("metadata") is not None:
        try:
            payload["metadata"] = json.loads(payload["metadata"])
        except Exception:
            payload["metadata"] = {}
    return payload


def get_patient_timeline(patient_id: str | None = None, timeline_id: str | None = None) -> dict[str, Any] | None:
    if not HAS_PG:
        return None
    with _conn() as conn:
        if conn is None:
            return None
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if timeline_id:
            cur.execute(
                "SELECT id, timeline_id, patient_id, internal_uuid, version, created_at, updated_at, history FROM patient_timelines WHERE timeline_id=%s",
                (timeline_id,),
            )
        elif patient_id:
            cur.execute(
                "SELECT id, timeline_id, patient_id, internal_uuid, version, created_at, updated_at, history FROM patient_timelines WHERE patient_id=%s ORDER BY updated_at DESC LIMIT 1",
                (patient_id,),
            )
        else:
            cur.close()
            return None
        row = cur.fetchone()
        cur.close()
    if not row:
        return None
    payload = dict(row)
    if payload.get("history") is not None:
        try:
            payload["history"] = json.loads(payload["history"])
        except Exception:
            payload["history"] = []
    return payload


def append_timeline_entry(patient_id: str | None, entry: dict[str, Any] | Any) -> dict[str, Any] | None:
    if not HAS_PG or not patient_id:
        return None
    payload = entry.model_dump() if hasattr(entry, "model_dump") else dict(entry or {})
    existing = get_patient_timeline(patient_id=patient_id) or {}
    history = existing.get("history") or []
    if not isinstance(history, list):
        history = []
    history.append(payload)
    timeline_id = existing.get("timeline_id") or payload.get("timeline_id") or f"timeline:{patient_id}"
    internal_uuid = existing.get("internal_uuid") or payload.get("internal_uuid") or str(datetime.utcnow().timestamp())
    version = int(existing.get("version") or 1) + 1
    with _conn() as conn:
        if conn is None:
            return None
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            INSERT INTO patient_timelines (timeline_id, patient_id, internal_uuid, version, history, updated_at)
            VALUES (%(timeline_id)s, %(patient_id)s, %(internal_uuid)s, %(version)s, %(history)s, NOW())
            ON CONFLICT (timeline_id) DO UPDATE SET
                patient_id = EXCLUDED.patient_id,
                internal_uuid = EXCLUDED.internal_uuid,
                version = EXCLUDED.version,
                history = EXCLUDED.history,
                updated_at = NOW()
            RETURNING id, timeline_id, patient_id, internal_uuid, version, created_at, updated_at, history
            """,
            {
                "timeline_id": timeline_id,
                "patient_id": patient_id,
                "internal_uuid": internal_uuid,
                "version": version,
                "history": json.dumps(history),
            },
        )
        row = cur.fetchone()
        cur.close()
    if not row:
        return None
    payload = dict(row)
    if payload.get("history") is not None:
        try:
            payload["history"] = json.loads(payload["history"])
        except Exception:
            payload["history"] = []
    return payload


def load_patient_history(patient_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    if not HAS_PG:
        return []
    timeline = get_patient_timeline(patient_id=patient_id)
    if not timeline:
        return []
    history = timeline.get("history") or []
    if not isinstance(history, list):
        return []
    return history[-limit:] if limit else history


def create_lab_work_item(
    lab_request_id: str,
    patient_id: str,
    appointment_id: str,
    consultation_context_id: str | None,
    doctor_name: str | None,
    department: str | None,
    requested_tests: list[dict[str, Any]] | None,
    status: str = "PENDING",
) -> dict[str, Any] | None:
    if not HAS_PG:
        return None
    with _conn() as conn:
        if conn is None:
            return None
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS lab_work_items (
                id SERIAL PRIMARY KEY,
                lab_request_id TEXT NOT NULL UNIQUE,
                patient_id TEXT NOT NULL,
                internal_uuid TEXT,
                appointment_id TEXT,
                consultation_context_id TEXT,
                doctor_name TEXT,
                department TEXT,
                requested_tests JSONB DEFAULT '[]',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                status TEXT NOT NULL DEFAULT 'PENDING'
            )
            """
        )
        cur.execute(
            """
            INSERT INTO lab_work_items (
                lab_request_id,
                patient_id,
                internal_uuid,
                appointment_id,
                consultation_context_id,
                doctor_name,
                department,
                requested_tests,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (lab_request_id) DO UPDATE SET
                patient_id = EXCLUDED.patient_id,
                internal_uuid = EXCLUDED.internal_uuid,
                appointment_id = EXCLUDED.appointment_id,
                consultation_context_id = EXCLUDED.consultation_context_id,
                doctor_name = EXCLUDED.doctor_name,
                department = EXCLUDED.department,
                requested_tests = EXCLUDED.requested_tests,
                status = EXCLUDED.status
            RETURNING id, lab_request_id, patient_id, internal_uuid, appointment_id, consultation_context_id, doctor_name, department, requested_tests, created_at, status
            """,
            (
                lab_request_id,
                patient_id,
                consultation_context_id or "",
                appointment_id,
                consultation_context_id,
                doctor_name,
                department,
                json.dumps(requested_tests or []),
                status,
            ),
        )
        row = cur.fetchone()
        cur.close()
    return dict(row) if row else None


def save_message(
    user_id: str,
    role: str,
    content: str,
    session_id: str | None = None,
) -> None:
    if not HAS_PG or not content or not user_id:
        return
    with _conn() as conn:
        if conn is None:
            return
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO messages (session_id, user_id, role, content)
            VALUES (%s, %s, %s, %s)
        """, (session_id, user_id, role, content))
        cur.close()


def get_user_messages(
    user_id: str,
    limit: int = 50,
    exclude_session_id: str | None = None,
) -> list[dict[str, str]]:
    if not HAS_PG or not user_id:
        return []
    with _conn() as conn:
        if conn is None:
            return []
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if exclude_session_id is not None:
            cur.execute("""
                SELECT role, content, created_at
                FROM messages
                WHERE user_id = %s AND (session_id IS NULL OR session_id <> %s)
                ORDER BY created_at DESC
                LIMIT %s
            """, (user_id, exclude_session_id, limit))
        else:
            cur.execute("""
                SELECT role, content, created_at
                FROM messages
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (user_id, limit))
        rows = cur.fetchall()
        cur.close()
    rows.reverse()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


def get_user_health_context(user_id: str, max_chars: int = 1500) -> str:
    msgs = get_user_messages(user_id, limit=40)
    if not msgs:
        return ""
    lines: list[str] = []
    total = 0
    for m in msgs:
        line = f"{m['role']}: {m['content']}"
        if total + len(line) > max_chars:
            break
        lines.append(line)
        total += len(line)
    return "\n".join(lines)


def save_patient_profile(user_id: str, profile: dict[str, Any] | None = None) -> None:
    if not HAS_PG or not user_id:
        return
    with _conn() as conn:
        if conn is None:
            return
        cur = conn.cursor()
        cur.execute("SELECT health_data FROM users WHERE id=%s", (user_id,))
        row = cur.fetchone()
        existing = row[0] if row else {}
        if not isinstance(existing, dict):
            existing = {}
        merged = {**existing, **(profile or {})}
        cur.execute(
            "INSERT INTO users (id, name, health_data) VALUES (%s, %s, %s) ON CONFLICT (id) DO UPDATE SET health_data=EXCLUDED.health_data",
            (user_id, user_id, json.dumps(merged)),
        )
        cur.close()


def load_patient_profile(user_id: str) -> dict[str, Any]:
    if not HAS_PG or not user_id:
        return {}
    with _conn() as conn:
        if conn is None:
            return {}
        cur = conn.cursor()
        cur.execute("SELECT health_data FROM users WHERE id=%s", (user_id,))
        row = cur.fetchone()
        cur.close()
    if not row:
        return {}
    data = row[0]
    return data if isinstance(data, dict) else {}


def save_visit_summary(user_id: str, visit_summary: str | None) -> None:
    if not visit_summary:
        return
    save_patient_profile(user_id, {"visit_summary": visit_summary.strip()})


def upsert_consultation_context(context: dict[str, Any]) -> dict[str, Any] | None:
    if not HAS_PG:
        return None
    with _conn() as conn:
        if conn is None:
            return None
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            INSERT INTO consultation_contexts (
                internal_uuid,
                patient_reference,
                patient_id,
                session_id,
                appointment_id,
                appointment_status,
                consultation_status,
                selected_department,
                selected_doctor,
                clinical_intake_record,
                metadata,
                version
            )
            VALUES (%(internal_uuid)s, %(patient_reference)s, %(patient_id)s, %(session_id)s, %(appointment_id)s, %(appointment_status)s, %(consultation_status)s, %(selected_department)s, %(selected_doctor)s, %(clinical_intake_record)s, %(metadata)s, %(version)s)
            ON CONFLICT (internal_uuid) DO UPDATE SET
                patient_reference = EXCLUDED.patient_reference,
                patient_id = EXCLUDED.patient_id,
                session_id = EXCLUDED.session_id,
                appointment_id = EXCLUDED.appointment_id,
                appointment_status = EXCLUDED.appointment_status,
                consultation_status = EXCLUDED.consultation_status,
                selected_department = EXCLUDED.selected_department,
                selected_doctor = EXCLUDED.selected_doctor,
                clinical_intake_record = EXCLUDED.clinical_intake_record,
                metadata = EXCLUDED.metadata,
                version = EXCLUDED.version
            RETURNING id, internal_uuid, patient_reference, patient_id, session_id, appointment_id, appointment_status, consultation_status, selected_department, selected_doctor, clinical_intake_record, metadata, created_at, version
        """, {
            "internal_uuid": context.get("internal_uuid"),
            "patient_reference": context.get("patient_reference"),
            "patient_id": context.get("patient_id"),
            "session_id": context.get("session_id"),
            "appointment_id": context.get("appointment_id"),
            "appointment_status": context.get("appointment_status", "booked"),
            "consultation_status": context.get("consultation_status", "CREATED"),
            "selected_department": context.get("selected_department"),
            "selected_doctor": context.get("selected_doctor"),
            "clinical_intake_record": json.dumps(context.get("clinical_intake_record") or {}),
            "metadata": json.dumps(context.get("metadata") or {}),
            "version": context.get("version", 1),
        })
        row = cur.fetchone()
        cur.close()
    if row:
        ctx_dict = dict(row)
        try:
            _index_completed_consultation(context)
        except Exception:
            pass
        return ctx_dict
    return None


def _index_completed_consultation(context: dict):
    if context.get("consultation_status") != "COMPLETED":
        return
    
    patient_id = context.get("patient_id")
    department = context.get("selected_department") or "general"
    metadata = context.get("metadata") or {}
    history = metadata.get("conversation_history") or []
    if not history or not patient_id:
        return
        
    lines = []
    doctor_name = metadata.get("doctor_name") or "Doctor"
    lines.append(f"Clinical consultation history for patient {patient_id} with {doctor_name} in {department} department:")
    
    summary = metadata.get("consultation_summary") or {}
    if summary:
        assessment = summary.get("clinical_assessment") or summary.get("assessment") or ""
        diagnosis = summary.get("possible_diagnosis") or summary.get("diagnosis") or ""
        next_steps = summary.get("next_steps") or ""
        if assessment:
            lines.append(f"Clinical Assessment: {assessment}")
        if diagnosis:
            lines.append(f"Possible Diagnosis: {diagnosis}")
        if next_steps:
            lines.append(f"Next Steps: {next_steps}")
            
    lines.append("Dialogue:")
    for msg in history:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            lines.append(f"Patient: {content}")
        elif role == "assistant":
            lines.append(f"Doctor: {content}")
            
    text = "\n".join(lines).strip()
    if not text:
        return
        
    try:
        try:
            from backend.llm.embeddings import embed_query
        except ImportError:
            from llm.embeddings import embed_query
            
        emb = embed_query(text)
        insert_knowledge_chunks(
            department=department,
            source="consultation_history",
            page=1,
            contents=[text],
            embeddings=[emb],
            patient_id=patient_id
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Failed to index consultation history: %s", e)



def load_consultation_context(appointment_id: str | None = None, internal_uuid: str | None = None) -> dict[str, Any] | None:
    if not HAS_PG:
        return None
    with _conn() as conn:
        if conn is None:
            return None
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if internal_uuid:
            cur.execute("SELECT id, internal_uuid, patient_reference, patient_id, session_id, appointment_id, appointment_status, consultation_status, selected_department, selected_doctor, clinical_intake_record, metadata, created_at, version FROM consultation_contexts WHERE internal_uuid=%s", (internal_uuid,))
        elif appointment_id:
            cur.execute("SELECT id, internal_uuid, patient_reference, patient_id, session_id, appointment_id, appointment_status, consultation_status, selected_department, selected_doctor, clinical_intake_record, metadata, created_at, version FROM consultation_contexts WHERE appointment_id=%s ORDER BY created_at DESC LIMIT 1", (appointment_id,))
        else:
            cur.close()
            return None
        row = cur.fetchone()
        cur.close()
    if not row:
        return None
    payload = dict(row)
    if payload.get("clinical_intake_record") is not None:
        try:
            payload["clinical_intake_record"] = json.loads(payload["clinical_intake_record"])
        except Exception:
            payload["clinical_intake_record"] = {}
    if payload.get("metadata") is not None:
        try:
            payload["metadata"] = json.loads(payload["metadata"])
        except Exception:
            payload["metadata"] = {}
    return payload


def load_recent_history(user_id: str, limit: int = 5) -> list[dict[str, str]]:
    if not HAS_PG or not user_id:
        return []
    with _conn() as conn:
        if conn is None:
            return []
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT role, content FROM messages WHERE user_id=%s ORDER BY created_at DESC LIMIT %s",
            (user_id, limit),
        )
        rows = cur.fetchall()
        cur.close()
    return [{"role": r["role"], "content": r["content"]} for r in rows][::-1]


def insert_knowledge_chunks(
    department: str,
    source: str,
    page: int,
    contents: list[str],
    embeddings: list[list[float]],
    patient_id: str | None = None,
) -> int:
    if not HAS_PG:
        return 0
    if not contents or len(contents) != len(embeddings):
        return 0
    with _conn() as conn:
        if conn is None:
            return 0
        cur = conn.cursor()
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO knowledge_chunks (department, source, page, content, embedding, patient_id)
            VALUES %s
            """,
            [
                (department, source, page, c, e, patient_id)
                for c, e in zip(contents, embeddings)
            ],
            template="(%s, %s, %s, %s, %s::vector, %s)",
        )
        count = cur.rowcount
        cur.close()
    return count


def count_knowledge_chunks(department: str | None = None) -> int:
    if not HAS_PG:
        return 0
    with _conn() as conn:
        if conn is None:
            return 0
        cur = conn.cursor()
        if department:
            cur.execute(
                "SELECT COUNT(*) FROM knowledge_chunks WHERE department=%s",
                (department,),
            )
        else:
            cur.execute("SELECT COUNT(*) FROM knowledge_chunks")
        n = cur.fetchone()[0]
        cur.close()
    return int(n)


def search_knowledge(
    department: str,
    embedding: list[float],
    top_k: int = 5,
    min_similarity: float = 0.40,
) -> list[dict]:
    """Cosine similarity search over knowledge_chunks for a department.

    If the primary query at min_similarity returns no rows, fall back once
    to a lower threshold (0.30) to avoid returning zero context for queries
    that are just outside the primary cutoff. No second retry.
    """
    if not HAS_PG or not embedding:
        return []
    with _conn() as conn:
        if conn is None:
            return []
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT content, page, source, patient_id,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM knowledge_chunks
            WHERE department = %s
              AND 1 - (embedding <=> %s::vector) >= %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (embedding, department, embedding, min_similarity, embedding, top_k),
        )
        rows = cur.fetchall()
        if not rows and min_similarity > 0.30:
            fallback_threshold = 0.30
            cur.execute(
                """
                SELECT content, page, source, patient_id,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM knowledge_chunks
                WHERE department = %s
                  AND 1 - (embedding <=> %s::vector) >= %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (embedding, department, embedding, fallback_threshold, embedding, top_k),
            )
            rows = cur.fetchall()
        cur.close()
    return [dict(r) for r in rows]
def insert_knowledge_chunks_dev(
    department: str,
    source: str,
    page: int,
    contents: list[str],
    embeddings: list[list[float]],
) -> int:

    if not HAS_PG:
        return 0

    if not contents or len(contents) != len(embeddings):
        return 0

    with _conn() as conn:

        if conn is None:
            return 0

        cur = conn.cursor()

        psycopg2.extras.execute_values(
            cur,
            f"""
            INSERT INTO {DEV_KNOWLEDGE_TABLE}
            (department, source, page, content, embedding)
            VALUES %s
            """,
            [
                (department, source, page, c, e)
                for c, e in zip(contents, embeddings)
            ],
            template="(%s, %s, %s, %s, %s::vector)",
        )

        count = cur.rowcount

        cur.close()

    return count
def count_knowledge_chunks_dev(
    department: str | None = None,
) -> int:

    if not HAS_PG:
        return 0

    with _conn() as conn:

        if conn is None:
            return 0

        cur = conn.cursor()

        if department:

            cur.execute(
                f"""
                SELECT COUNT(*)
                FROM {DEV_KNOWLEDGE_TABLE}
                WHERE department=%s
                """,
                (department,),
            )

        else:

            cur.execute(
                f"""
                SELECT COUNT(*)
                FROM {DEV_KNOWLEDGE_TABLE}
                """
            )

        n = cur.fetchone()[0]

        cur.close()

    return int(n)
