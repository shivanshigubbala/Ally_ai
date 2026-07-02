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

_pool = None

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


def init_db():
    if not HAS_PG:
        return
    with _conn() as conn:
        if conn is None:
            return
        cur = conn.cursor()
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER,
                health_data JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
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
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
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
            INSERT INTO knowledge_chunks (department, source, page, content, embedding)
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
            SELECT content, page, source,
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
                SELECT content, page, source,
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