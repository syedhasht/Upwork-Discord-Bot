import storage

def is_new_job(job_id: str) -> bool:
    """
    Checks if a job has already been posted during the current runtime.
    If it's new, it registers it permanently to prevent future duplication.
    """
    if job_id in storage.seen_jobs:
        return False
        
    storage.seen_jobs.add(job_id)
    return True
