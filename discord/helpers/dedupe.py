import sys
from pathlib import Path

# Ensure bot/ root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import database

def is_new_job(job: dict, keyword: str = None) -> str:
    """
    Checks if a job is new, updated, or a duplicate.
    Rule: A job (by job_id) can ONLY belong to one category.
    If it already exists in another category, it will NOT be posted to any other category.
    Returns:
        "new"     -> If job_id is NOT in DB anywhere.
        "updated" -> If job_id is in DB under THIS SAME category and budget or description changed.
        None      -> If job_id already belongs to another category, or is a duplicate within this category.
    """
    job_id = job.get("id")
    if not job_id:
        return None

    if keyword is None:
        keyword = job.get("keyword") or "unknown"

    # Ensure job dict has the correct keyword for database operations
    job["keyword"] = keyword

    # 1. Check if job_id already exists anywhere in the database (any category)
    existing = database.get_job(job_id)
    
    if existing:
        existing_kw = (existing.get("keyword") or "").lower()
        current_kw = keyword.lower()

        # If already claimed by another category, strictly do not post in this category!
        if existing_kw != current_kw:
            return None

        # If it belongs to this same category, check for updates in budget or description
        old_budget = str(existing.get("budget") or "").strip()
        new_budget = str(job.get("budget") or "").strip()
        
        old_desc = str(existing.get("description") or "").strip()
        new_desc = str(job.get("description") or "").strip()

        if old_budget != new_budget or old_desc != new_desc:
            database.save_job(job, is_update=True)
            return "updated"

        return None

    # 2. Job ID is completely new to the system:
    # Check if a job with same Description/Budget already exists in DB
    content_match = database.get_job_by_content(job.get("description"), job.get("budget"))
    
    # Save the job so its ID and category are recorded in the DB
    database.save_job(job)
    
    if content_match:
        # Content already exists in DB (repost under new ID). Do not post duplicate.
        return None
    
    return "new"

