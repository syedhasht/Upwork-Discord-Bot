import sys
from pathlib import Path

# Ensure bot/ root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import database

def is_new_job(job: dict, keyword: str = None) -> str:
    """
    Checks if a job is new, updated, or a duplicate.
    Returns:
        "new"     -> If ID + keyword is not in DB.
        "updated" -> If ID + keyword is in DB but budget or description changed.
        None      -> If it's a perfect duplicate.
    """
    job_id = job.get("id")
    if not job_id:
        return None

    if keyword is None:
        keyword = job.get("keyword") or "unknown"

    # Ensure job dict has the correct keyword for database operations
    job["keyword"] = keyword

    existing = database.get_job_by_keyword(job_id, keyword)
    
    if not existing:
        # Check if a job with same Description/Budget already exists in DB
        content_match = database.get_job_by_content(job.get("description"), job.get("budget"), keyword)

        
        # Always save the job so its ID is recorded in the DB
        database.save_job(job)
        
        if content_match:
            # Content already exists in DB (duplicate posting or repost).
            # Do not post a duplicate notification to Discord.
            return None
        
        return "new"

    # Check for updates in budget or description
    # (Using .strip() and string conversion to avoid trivial mismatches)
    old_budget = str(existing.get("budget") or "").strip()
    new_budget = str(job.get("budget") or "").strip()
    
    old_desc = str(existing.get("description") or "").strip()
    new_desc = str(job.get("description") or "").strip()

    if old_budget != new_budget or old_desc != new_desc:
        database.save_job(job, is_update=True)
        return "updated"

    return None

