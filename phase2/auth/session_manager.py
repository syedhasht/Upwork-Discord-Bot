import json
import time
from pathlib import Path

# Paths
BASE_DIR        = Path(__file__).resolve().parent
COOKIES_PATH    = BASE_DIR / "cookies.json"
LOCAL_STORAGE_PATH = BASE_DIR / "local_storage.json"
CONFIG_PATH     = BASE_DIR.parent.parent / "phase1" / "scraper" / "config.py"

TOKEN_MAX_AGE_HOURS = 10

def is_session_fresh() -> bool:
    if not COOKIES_PATH.exists():
        return False
    age_seconds = time.time() - COOKIES_PATH.stat().st_mtime
    age_hours = age_seconds / 3600
    if age_hours > TOKEN_MAX_AGE_HOURS:
        return False
    return True

def needs_refresh(triggered_by_403: bool = False) -> bool:
    if triggered_by_403:
        return True
    if not is_session_fresh():
        return True
    return False
