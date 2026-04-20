import sys
from pathlib import Path

# Explicitly inject the phase1 directory into the path so we can import its modules cleanly
PHASE1_DIR = Path(__file__).resolve().parent.parent / "phase1"
if str(PHASE1_DIR) not in sys.path:
    sys.path.append(str(PHASE1_DIR))

import main as phase1_main

def get_jobs(keyword="python") -> list:
    """
    Hooks directly into the Phase 1 script.
    Executes the Upwork Cloudflare-bypassing routine and returns authenticated job dictionaries.
    """
    return phase1_main.run_scraper(keyword=keyword, count=10)
