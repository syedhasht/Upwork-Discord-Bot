import sys
from pathlib import Path

# Ensure bot/ root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import database

def is_new_job(job: dict) -> str:
    """
    Checks if a job is new, updated, or a duplicate.
    Returns:
        "new"     -> If ID is not in DB.
        "updated" -> If ID is in DB but budget or description changed.
        None      -> If it's a perfect duplicate.
    """
    job_id = job.get("id")
    if not job_id:
        return None

    existing = database.get_job(job_id)
    
    if not existing:
        # SWAP RULE: Check if a job with same Description/Budget exists but with a different ID
        content_match = database.get_job_by_content(job.get("description"), job.get("budget"))
        if content_match:
            # Delete the old "dead" job record before saving the new "live" one
            database.delete_job(content_match["job_id"])
        
        database.save_job(job)
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
