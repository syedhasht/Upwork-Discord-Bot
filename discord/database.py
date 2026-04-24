import sqlite3
from pathlib import Path
import datetime
import logging

logger = logging.getLogger("jobhunt")

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
                job_id      TEXT PRIMARY KEY,
                title       TEXT,
                budget      TEXT,
                description TEXT,
                raw_json    TEXT,
                is_updated  INTEGER DEFAULT 0,
                updated_at  TEXT,
                link        TEXT,
                keyword     TEXT,
                posted_at   TEXT
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS token_refresh_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                time TEXT
            )
        """)
        conn.commit()

    # Migration: Add columns if they don't exist
    for col in ["description", "raw_json", "is_updated", "updated_at", "keyword"]:
        try:
            with _get_connection() as conn:
                # SQLite doesn't support adding DEFAULT value to existing columns easily via ALTER, 
                # but we can just add the column.
                conn.execute(f"ALTER TABLE posted_jobs ADD COLUMN {col} TEXT")
                conn.commit()
        except sqlite3.OperationalError:
            pass # Column already exists

    logger.info(f"Database initialized at {DB_PATH}")


def get_job(job_id: str) -> dict:
    """
    Fetches a single job record from the database by its ID.
    """
    with _get_connection() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM posted_jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
    return dict(row) if row else None


def get_job_by_content(description: str, budget: str) -> dict:
    """
    Finds a job by its description and budget.
    Used for the 'Swap Rule' to detect reposts.
    """
    with _get_connection() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM posted_jobs WHERE description = ? AND budget = ?", 
            (description, budget)
        ).fetchone()
    return dict(row) if row else None


def delete_job(job_id: str):
    """Permanently deletes a job record."""
    with _get_connection() as conn:
        conn.execute("DELETE FROM posted_jobs WHERE job_id = ?", (job_id,))
        conn.commit()


def is_new_job(job_id: str) -> bool:
    """
    Returns True if the job has NOT been seen before.
    """
    return get_job(job_id) is None


def save_job(job: dict, is_update: bool = False):
    """
    Permanently saves or updates a job record in the database.
    """
    with _get_connection() as conn:
        now = datetime.datetime.now().isoformat()
        
        if is_update:
            conn.execute(
                """
                UPDATE posted_jobs 
                SET title = ?, budget = ?, description = ?, raw_json = ?, is_updated = 1, updated_at = ?, keyword = COALESCE(?, keyword)
                WHERE job_id = ?
                """,
                (
                    job.get("title"),
                    job.get("budget"),
                    job.get("description"),
                    job.get("raw_json"),
                    now,
                    job.get("keyword"),
                    job.get("id")
                )
            )
        else:
            conn.execute(
                """
                INSERT OR IGNORE INTO posted_jobs (job_id, title, budget, description, raw_json, is_updated, posted_at, link, keyword)
                VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?)
                """,
                (
                    job.get("id"),
                    job.get("title"),
                    job.get("budget"),
                    job.get("description"),
                    job.get("raw_json"),
                    now,
                    job.get("link"),
                    job.get("keyword")
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
        conn.execute(
            "DELETE FROM posted_jobs WHERE keyword = ?", (keyword.lower(),)
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


# ── Metadata ──────────────────────────────────────────────────────────────────

# (Metadata functions removed as they are no longer needed)


def add_token_refresh(dt: datetime.datetime = None):
    """Adds a new row to the token_refresh_history table."""
    if dt is None:
        dt = datetime.datetime.now().astimezone()
    date_str = dt.strftime("%Y-%m-%d")
    time_str = dt.strftime("%H:%M:%S")
    with _get_connection() as conn:
        conn.execute(
            "INSERT INTO token_refresh_history (date, time) VALUES (?, ?)",
            (date_str, time_str)
        )
        conn.commit()


def get_latest_token_refresh() -> datetime.datetime:
    """Returns the most recent token refresh as a datetime object, or None if empty."""
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT date, time FROM token_refresh_history ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if row:
        dt_str = f"{row[0]}T{row[1]}"
        return datetime.datetime.fromisoformat(dt_str).astimezone()
    return None


def prune_old_jobs(hours: int = 50):
    """Deletes jobs older than the specified number of hours."""
    with _get_connection() as conn:
        # Calculate the cutoff time (local time)
        cutoff = (datetime.datetime.now() - datetime.timedelta(hours=hours)).isoformat()
        cursor = conn.execute("DELETE FROM posted_jobs WHERE posted_at < ?", (cutoff,))
        count = cursor.rowcount
        conn.commit()
    return count