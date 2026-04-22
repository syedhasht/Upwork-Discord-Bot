import sqlite3
from pathlib import Path
import datetime

# Database lives centrally in the root Database folder
DB_PATH = Path(__file__).resolve().parent.parent / "Database" / "jobs.db"


def _get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    """
    Creates all required tables if they don't already exist.
    Called once at bot startup.
    """
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS posted_jobs (
                job_id    TEXT PRIMARY KEY,
                title     TEXT,
                budget    TEXT,
                link      TEXT,
                keyword   TEXT,
                posted_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tracked_keywords (
                keyword    TEXT PRIMARY KEY,
                channel_id INTEGER,
                guild_id   INTEGER,
                created_at TEXT
            )
        """)
        conn.commit()
    print(f"[DB] Database initialized at {DB_PATH}")


def is_new_job(job_id: str) -> bool:
    """
    Returns True if the job has NOT been seen before.
    Returns False (duplicate) if it already exists in the database.
    """
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM posted_jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
    return row is None


def save_job(job: dict):
    """
    Permanently saves a job record to the database.
    """
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO posted_jobs (job_id, title, budget, link, posted_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                job.get("id"),
                job.get("title"),
                job.get("budget"),
                job.get("link"),
                datetime.datetime.now().isoformat()
            )
        )
        conn.commit()


def get_all_jobs() -> list:
    """
    Optional utility: returns all jobs ever posted (for debugging or !history command).
    """
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT job_id, title, budget, link, posted_at FROM posted_jobs ORDER BY posted_at DESC"
        ).fetchall()
    return [
        {"id": r[0], "title": r[1], "budget": r[2], "link": r[3], "posted_at": r[4]}
        for r in rows
    ]


# ── Tracker CRUD ──────────────────────────────────────────────────────────────

def add_tracker(keyword: str, channel_id: int, guild_id: int):
    """Register a keyword tracker linked to a specific Discord channel."""
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO tracked_keywords (keyword, channel_id, guild_id, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (keyword.lower(), channel_id, guild_id, datetime.datetime.now().isoformat())
        )
        conn.commit()


def remove_tracker(keyword: str):
    """Delete a keyword tracker from the database."""
    with _get_connection() as conn:
        conn.execute(
            "DELETE FROM tracked_keywords WHERE keyword = ?", (keyword.lower(),)
        )
        conn.commit()


def get_all_trackers() -> list:
    """Return all tracked keywords with their bound channel and guild IDs."""
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT keyword, channel_id, guild_id FROM tracked_keywords"
        ).fetchall()
    return [{"keyword": r[0], "channel_id": r[1], "guild_id": r[2]} for r in rows]


def tracker_exists(keyword: str) -> bool:
    """Check if a keyword is already being tracked."""
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM tracked_keywords WHERE keyword = ?", (keyword.lower(),)
        ).fetchone()
    return row is not None
