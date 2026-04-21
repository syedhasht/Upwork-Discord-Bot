import sys
from pathlib import Path

# Ensure bot/ root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import database


def is_new_job(job: dict) -> bool:
    """
    Checks if the job is new using the persistent SQLite database.
    If it is new, saves it immediately so it won't be re-posted on next loop.
    Returns True if new, False if duplicate.
    """
    job_id = job.get("id")
    if not job_id:
        return False

    if database.is_new_job(job_id):
        database.save_job(job)
        return True

    return False

