import sys
from pathlib import Path
import json

# Set stdout to UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Ensure scraper/ and discord/ paths are importable
SCRAPER_DIR = Path(__file__).resolve().parent / "scraper"
DISCORD_DIR = Path(__file__).resolve().parent / "discord"
if str(SCRAPER_DIR) not in sys.path:
    sys.path.insert(0, str(SCRAPER_DIR))
if str(DISCORD_DIR) not in sys.path:
    sys.path.insert(0, str(DISCORD_DIR))

import runner as scraper_runner
import database
from helpers.filters import filter_jobs
from helpers.dedupe import is_new_job

def debug_n8n():
    keyword = "n8n"
    print(f"--- Debugging logic for keyword: '{keyword}' ---")
    
    # 1. Fetch raw jobs
    raw_jobs = scraper_runner.run_scraper(keyword=keyword, count=50)
    print(f"Fetched {len(raw_jobs)} raw jobs from Upwork.")
    
    # 2. Filter jobs
    filtered_jobs = filter_jobs(raw_jobs, min_budget=0, keyword=keyword)
    print(f"Filtered down to {len(filtered_jobs)} jobs.")
    
    # 3. Sort jobs
    filtered_jobs.sort(key=lambda x: x.get("created_at_raw") or "")
    
    # 4. Take to_post (last 10)
    to_post = filtered_jobs[-10:]
    print(f"Taking last 10 sorted jobs. List size: {len(to_post)}")
    
    # 5. Let's see what is_new_job returns for all filtered jobs, not just the last 10, to understand!
    print("\n--- Checking all filtered jobs (oldest to newest): ---")
    for idx, job in enumerate(filtered_jobs, 1):
        status = is_new_job(job)
        in_to_post = job in to_post
        print(f"[{idx}] ID: {job['id']}")
        print(f"    Title: {job['title']}")
        print(f"    Created At Raw: {job['created_at_raw']}")
        print(f"    In to_post: {in_to_post}")
        print(f"    is_new_job status: {status}")
        
        # Check if it exists in the database
        db_job = database.get_job(job['id'])
        print(f"    Exists in DB: {db_job is not None}")
        if db_job:
            print(f"    DB inserted_at (posted_at): {db_job.get('posted_at')}")
            
        print()

if __name__ == "__main__":
    debug_n8n()
