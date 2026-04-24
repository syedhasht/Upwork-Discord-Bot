import sys
import subprocess
import importlib
import logging
import datetime
from curl_cffi import requests
from pathlib import Path

logger = logging.getLogger("jobhunt")

import json
# Path to the Cloudflare solver script and session storage
CORE_DIR = Path(__file__).resolve().parent
BOOTSTRAP_PATH = CORE_DIR.parent.parent / "cloudflare" / "bypass" / "solver.py"
SESSION_PATH = CORE_DIR / "session.json"


import threading
import time

_refresh_lock = threading.Lock()
_last_refresh_local_time = 0.0

def _trigger_refresh():
    """
    Runs the Cloudflare bypass solver to get fresh tokens.
    Blocks until the browser session completes and scraper/core/config.py is updated.
    Uses a mutex to prevent duplicate simultaneous executions.
    """
    global _last_refresh_local_time
    
    with _refresh_lock:
        # Check if another thread already refreshed while we were waiting for the lock
        # If it was refreshed in the last 60 seconds, skip running the solver again
        if time.time() - _last_refresh_local_time < 60:
            logger.info("Token was just refreshed by another thread. Using new tokens instead of triggering solver again.")
            h, c = load_session()
            if h and c:
                return h, c
            # If load_session failed, continue and trigger a fresh solve anyway
            logger.warning("Failed to load session from another thread's refresh. Triggering own solver...")
            
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.warning(f"[{timestamp}] Token expired or Cloudflare block detected. Triggering solver...")
        logger.info("SeleniumBase UC solver starting. Please wait...")

        try:
            result = subprocess.run(
                [sys.executable, str(BOOTSTRAP_PATH)],
                check=False,
                timeout=120  # 120 seconds max to allow solver script retries
            )

            if result.returncode != 0:
                logger.error("Solver script exited with an error. Token refresh may have failed.")
            else:
                refresh_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logger.info(f"[{refresh_time}] Token refresh complete. New tokens written to scraper/core/config.py")
                _last_refresh_local_time = time.time()
        except subprocess.TimeoutExpired:
            logger.error("Solver script timed out after 120 seconds. Proceeding anyway...")

        import core.config as config_module
        importlib.reload(config_module)
        headers = getattr(config_module, "HEADERS", {})
        cookies = getattr(config_module, "COOKIES", {})
        logger.info(f"New tokens loaded. Authorization present: {'authorization' in headers and bool(headers.get('authorization'))}")
    
    # Update refresh timestamp in database
    try:
        import sqlite3
        db_path = Path(__file__).resolve().parent.parent.parent / "Database" / "jobs.db"
        if db_path.exists():
            with sqlite3.connect(db_path) as conn:
                now = datetime.datetime.now().astimezone()
                date_str = now.strftime("%Y-%m-%d")
                time_str = now.strftime("%H:%M:%S")
                conn.execute("INSERT INTO token_refresh_history (date, time) VALUES (?, ?)", (date_str, time_str))
                conn.commit()
    except Exception as e:
        logger.error(f"Failed to update refresh metadata: {e}")

    # Final return of fresh tokens
    tokens = load_session()
    return tokens if tokens else ({}, {})

def load_session():
    """Loads session headers and cookies from session.json with retries."""
    for _ in range(3):  # Try 3 times in case of file locks
        if SESSION_PATH.exists():
            try:
                with open(SESSION_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    h = data.get("headers", {})
                    c = data.get("cookies", {})
                    if h and c:
                        return h, c
            except Exception as e:
                logger.error(f"Error loading session.json (retrying): {e}")
                time.sleep(1)
    return {}, {}


class UpworkClient:
    def __init__(self, headers=None, cookies=None):
        self.session = requests.Session(impersonate="chrome110")
        
        # Load from provided args or fall back to JSON
        json_headers, json_cookies = load_session()
        self.headers = headers if headers else json_headers
        self.cookies = cookies if cookies else json_cookies

    def fetch_jobs(self, payload, retry_count: int = 0, force_refresh: bool = False):
        """
        Fetches jobs with robust error handling, retries, and auto-refresh logic.
        """
        MAX_RETRIES = 2
        
        if force_refresh or not self.headers or not self.headers.get("authorization"):
            logger.info("Session missing or force refresh requested. Triggering solver...")
            res = _trigger_refresh()
            if res and len(res) == 2:
                self.headers, self.cookies = res
            else:
                self.headers, self.cookies = {}, {}

        try:
            response = self.session.post(
                "https://www.upwork.com/api/graphql/v1?alias=visitorJobSearch",
                headers=self.headers,
                cookies=self.cookies,
                json=payload,
                timeout=30
            )
        except Exception as e:
            logger.error(f"Network error during fetch: {e}")
            if retry_count < MAX_RETRIES:
                time.sleep(5)
                return self.fetch_jobs(payload, retry_count + 1)
            return None

        if response is None:
            return None

        status = response.status_code
        content_type = response.headers.get("Content-Type", "")

        # 1. Handle Rate Limiting (429)
        if status == 429:
            wait_time = (retry_count + 1) * 30
            logger.warning(f"Rate limited (429). Sleeping for {wait_time}s...")
            time.sleep(wait_time)
            if retry_count < MAX_RETRIES:
                return self.fetch_jobs(payload, retry_count + 1)
            return response

        # 2. Handle Server Errors (5xx)
        if status >= 500:
            logger.warning(f"Upwork server error ({status}). Retrying in 10s...")
            time.sleep(10)
            if retry_count < MAX_RETRIES:
                return self.fetch_jobs(payload, retry_count + 1)
            return response

        # 3. Handle Auth Errors (401, 403) or Cloudflare HTML Challenges
        is_html = "text/html" in content_type
        is_cf_challenge = is_html and ("challenge-platform" in response.text or "Just a moment..." in response.text)
        
        if status in [401, 403] or is_cf_challenge:
            reason = "Auth expired" if status in [401, 403] else "Cloudflare HTML challenge"
            logger.warning(f"{reason} detected. Initiating auto token refresh...")
            
            new_headers, new_cookies = _trigger_refresh()
            self.headers = new_headers
            self.cookies = new_cookies

            if retry_count < MAX_RETRIES:
                logger.info("Retrying request with fresh tokens...")
                return self.fetch_jobs(payload, retry_count + 1)
            return response

        # 4. Validate JSON Response
        if "application/json" in content_type:
            try:
                data = response.json()
                # Detect "Soft Block" (Successful status but missing core data)
                if "data" not in data and "errors" not in data:
                    logger.warning("Soft block detected (empty JSON response). Refreshing tokens...")
                    _trigger_refresh() # Just refresh, next poll will pick it up
            except Exception as e:
                logger.error(f"Failed to parse JSON response: {e}")
        
        return response
