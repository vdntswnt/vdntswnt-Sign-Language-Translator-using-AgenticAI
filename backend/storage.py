import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory.db")


# ── Setup ─────────────────────────────────────────────────────────────────────

def init_db():
    """Create tables if they don't exist. Safe to call on every startup."""
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id  TEXT PRIMARY KEY,
                history     TEXT NOT NULL DEFAULT '[]',
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS feedback (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT NOT NULL,
                input_text  TEXT NOT NULL,
                gloss       TEXT NOT NULL,
                rating      INTEGER NOT NULL,  -- 1 = thumbs up, -1 = thumbs down
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS corrections (
                input_text  TEXT PRIMARY KEY,
                bad_gloss   TEXT NOT NULL,
                created_at  TEXT NOT NULL
            );
        """)
    print(f"[Memory] SQLite DB ready at {DB_PATH}")


def _conn():
    return sqlite3.connect(DB_PATH)


def _now():
    return datetime.utcnow().isoformat()


# ── Session memory ────────────────────────────────────────────────────────────

def load_session(session_id: str) -> list:
    """Load conversation history for a session. Returns [] if not found."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT history FROM sessions WHERE session_id = ?",
            (session_id,)
        ).fetchone()
        if row:
            return json.loads(row[0])
        return []


def save_session(session_id: str, history: list):
    """Save or update conversation history for a session."""
    now = _now()
    history_json = json.dumps(history)
    with _conn() as conn:
        conn.execute("""
            INSERT INTO sessions (session_id, history, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                history    = excluded.history,
                updated_at = excluded.updated_at
        """, (session_id, history_json, now, now))


def delete_session(session_id: str):
    """Delete a session's history."""
    with _conn() as conn:
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))


# ── Feedback ──────────────────────────────────────────────────────────────────

def save_feedback(session_id: str, input_text: str, gloss: str, rating: int):
    """
    Save user feedback.
    rating: 1 = thumbs up, -1 = thumbs down
    If thumbs down, also adds to corrections table so agent avoids this gloss.
    """
    with _conn() as conn:
        conn.execute("""
            INSERT INTO feedback (session_id, input_text, gloss, rating, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, input_text.strip().lower(), gloss, rating, _now()))

        # If thumbs down — remember this bad gloss to avoid it next time
        if rating == -1:
            conn.execute("""
                INSERT INTO corrections (input_text, bad_gloss, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(input_text) DO UPDATE SET
                    bad_gloss  = excluded.bad_gloss,
                    created_at = excluded.created_at
            """, (input_text.strip().lower(), gloss, _now()))
            print(f"[Memory] Correction saved: '{input_text}' → bad gloss: '{gloss}'")


def get_bad_gloss(input_text: str) -> str | None:
    """
    Returns the previously bad gloss for this input if it was thumbs-downed.
    Agent uses this to avoid repeating the same mistake.
    """
    with _conn() as conn:
        row = conn.execute(
            "SELECT bad_gloss FROM corrections WHERE input_text = ?",
            (input_text.strip().lower(),)
        ).fetchone()
        return row[0] if row else None


def get_feedback_stats() -> dict:
    """Returns overall feedback stats for the /health endpoint."""
    with _conn() as conn:
        total     = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
        thumbs_up = conn.execute("SELECT COUNT(*) FROM feedback WHERE rating = 1").fetchone()[0]
        thumbs_dn = conn.execute("SELECT COUNT(*) FROM feedback WHERE rating = -1").fetchone()[0]
        corrections = conn.execute("SELECT COUNT(*) FROM corrections").fetchone()[0]
        return {
            "total_feedback":   total,
            "thumbs_up":        thumbs_up,
            "thumbs_down":      thumbs_dn,
            "corrections_learned": corrections,
        }