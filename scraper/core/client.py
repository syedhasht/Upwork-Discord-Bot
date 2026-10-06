import os
import re
import sys
import json
import time
import sqlite3
import logging
import datetime
import threading
import subprocess
from curl_cffi import requests
from curl_cffi.requests import BrowserType
from pathlib import Path

logger = logging.getLogger("jobhunt")

# Path to the Cloudflare solver script, session storage and the bot database
CORE_DIR = Path(__file__).resolve().parent
BOOTSTRAP_PATH = CORE_DIR.parent.parent / "cloudflare" / "bypass" / "solver.py"
SESSION_PATH = CORE_DIR / "session.json"
DB_PATH = CORE_DIR.parent.parent / "Database" / "jobs.db"

# Tokens minted less than this long ago are "fresh". If Upwork still rejects them they did
# not expire, so running the solver again cannot help (it only adds noise to a block).
TOKEN_FRESH_SECS = 90
# Consecutive rejections of fresh tokens before all fetching and solver launches pause.
BLOCK_THRESHOLD = 3
# Cooldown once paused. Doubles on every consecutive trip, capped at the max.
BACKOFF_BASE_SECS = 300
BACKOFF_MAX_SECS = 1800
# TLS profile used when the solver's Chrome version is unknown.
DEFAULT_IMPERSONATE = "chrome110"

_refresh_lock = threading.Lock()

# Circuit breaker state, guarded by _state_lock.
_state_lock = threading.Lock()
_blocked_until = 0.0
_block_trips = 0
_fresh_rejections = 0


def blocked_for() -> float:
    """Seconds left on the block cooldown. 0 means requests are allowed."""
    return max(0.0, _blocked_until - time.time())


def _trip_breaker(reason: str):
    """Pauses every Upwork request and solver launch for a growing cooldown."""
    global _blocked_until, _block_trips, _fresh_rejections
    with _state_lock:
        _block_trips += 1
        _fresh_rejections = 0
        wait = min(BACKOFF_BASE_SECS * 2 ** min(_block_trips - 1, 10), BACKOFF_MAX_SECS)
        _blocked_until = time.time() + wait
        trips, until = _block_trips, _blocked_until
    resume = datetime.datetime.fromtimestamp(until).strftime("%H:%M:%S")
    logger.error(f"{reason} Pausing all Upwork requests and solver launches for {wait / 60:.0f} min (until {resume}, trip #{trips}).")


def _note_success():
    """A good response ends any block: reset the failure counters and the backoff."""
    global _block_trips, _fresh_rejections
    with _state_lock:
        recovered = _block_trips > 0
        _block_trips = 0
        _fresh_rejections = 0
    if recovered:
        logger.info("Upwork is accepting requests again. Block cooldown reset.")


def _note_fresh_rejection():
    """Counts a rejection of just-minted tokens and trips the breaker once it is a pattern."""
    global _fresh_rejections
    with _state_lock:
        _fresh_rejections += 1
        # After a cooldown (_block_trips > 0) the first failed probe trips again immediately.
        trip = _fresh_rejections >= BLOCK_THRESHOLD or _block_trips > 0
    if trip:
        _trip_breaker("Upwork keeps rejecting freshly minted tokens.")


def _session_mtime() -> float:
    try:
        return SESSION_PATH.stat().st_mtime
    except OSError:
        return 0.0


def _tokens_age() -> float:
    """Seconds since the solver last wrote session.json (the age of the current tokens)."""
    return time.time() - _session_mtime()


def _describe_response(response) -> str:
    """One-line summary of a rejected response, to tell a Cloudflare challenge from an Upwork API refusal."""
    h = response.headers
    try:
        body = " ".join((response.text or "")[:200].split())
    except Exception:
        body = "<unreadable>"
    return (f"[status={response.status_code} server={h.get('server')} cf-mitigated={h.get('cf-mitigated')} "
            f"cf-ray={h.get('cf-ray')} content-type={h.get('content-type')} body={body!r}]")


def _pick_impersonation(user_agent: str) -> str:
    """
    Picks the curl_cffi TLS profile closest to (and not newer than) the Chrome version of the
    solver's browser, so the TLS handshake, headers and cf_clearance cookie tell one story.
    UPWORK_IMPERSONATE in the environment overrides the choice.
    """
    override = os.getenv("UPWORK_IMPERSONATE")
    if override:
        return override

    match = re.search(r"Chrome/(\d+)", user_agent or "")
    if not match:
        return DEFAULT_IMPERSONATE
    major = int(match.group(1))

    versions = []
    for browser in BrowserType:
        m = re.fullmatch(r"chrome(\d+)a?", browser.value)
        if m and int(m.group(1)) <= major:
            versions.append((int(m.group(1)), browser.value))
    return max(versions)[1] if versions else DEFAULT_IMPERSONATE


def _record_refresh_in_db():
    """Update refresh timestamp in database."""
    try:
        if DB_PATH.exists():
            with sqlite3.connect(DB_PATH) as conn:
                now = datetime.datetime.now().astimezone()
                date_str = now.strftime("%Y-%m-%d")
                time_str = now.strftime("%H:%M:%S")
                conn.execute("INSERT INTO token_refresh_history (date, time) VALUES (?, ?)", (date_str, time_str))
                conn.commit()
    except Exception as e:
        logger.error(f"Failed to update refresh metadata: {e}")


def _trigger_refresh():
    """
    Runs the Cloudflare bypass solver to get fresh tokens.
    Blocks until the browser session completes and session.json is updated.
    Uses a mutex to prevent duplicate simultaneous executions, and refuses to launch
    while the block cooldown is active.
    """
    with _refresh_lock:
        # Check if another thread already refreshed while we were waiting for the lock
        if _tokens_age() < TOKEN_FRESH_SECS:
            logger.info("Token was just refreshed by another thread. Using new tokens instead of triggering solver again.")
            h, c = load_session()
            if h and c:
                return h, c
            # If load_session failed, continue and trigger a fresh solve anyway
            logger.warning("Failed to load session from another thread's refresh. Triggering own solver...")

        if blocked_for() > 0:
            logger.info(f"Solver launch skipped: block cooldown active for another {blocked_for() / 60:.1f} min.")
            return load_session()

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.warning(f"[{timestamp}] Token expired or Cloudflare block detected. Triggering solver...")
        logger.info("SeleniumBase UC solver starting. Please wait...")

        succeeded = False
        try:
            result = subprocess.run(
                [sys.executable, str(BOOTSTRAP_PATH)],
                check=False,
                timeout=120  # 120 seconds max to allow solver script retries
            )

            if result.returncode != 0:
                logger.error("Solver script exited with an error. Token refresh may have failed.")
            else:
                succeeded = True
                refresh_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logger.info(f"[{refresh_time}] Token refresh complete. New tokens written to scraper/core/config.py")
        except subprocess.TimeoutExpired:
            logger.error("Solver script timed out after 120 seconds.")

        if not succeeded:
            _trip_breaker("The Cloudflare solver failed.")

        headers, _ = load_session()
        logger.info(f"New tokens loaded. Authorization present: {bool(headers.get('authorization'))}")

    if succeeded:
        _record_refresh_in_db()

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
        self.session = None
        self._load()

        # Provided args win over session.json
        if headers or cookies:
            self.headers = headers or self.headers
            self.cookies = cookies or self.cookies
            self._reset_session()

    def _load(self):
        """(Re)loads tokens from session.json and rebuilds the HTTP session to match their browser."""
        mtime = _session_mtime()  # read first, so a refresh that lands mid-load is never mistaken for already loaded
        self.headers, self.cookies = load_session()
        self._loaded_mtime = mtime
        self._reset_session()

    def _reset_session(self):
        """Fresh HTTP session whose TLS profile matches the user-agent in use. Also resets dropped sockets."""
        if self.session is not None:
            try:
                self.session.close()
            except Exception:
                pass
        self.session = requests.Session(impersonate=_pick_impersonation(self.headers.get("user-agent")))

    def _recover_from_rejection(self) -> bool:
        """
        Called when Upwork rejected the tokens in use.
        Returns True when different tokens are now in hand and the request is worth retrying.
        """
        if _session_mtime() != self._loaded_mtime:
            # Another thread (or process) refreshed after we loaded our tokens.
            logger.info("Tokens were refreshed since this request was built. Loading them...")
            self._load()
            return True

        if _tokens_age() < TOKEN_FRESH_SECS:
            # Minted moments ago and still rejected: a block, not an expiry. Don't spin up
            # another browser or retry with the same tokens.
            _note_fresh_rejection()
            return False

        logger.warning("Initiating auto token refresh...")
        _trigger_refresh()
        self._load()
        return blocked_for() == 0 and bool(self.headers.get("authorization"))

    def fetch_jobs(self, payload, retry_count: int = 0, force_refresh: bool = False):
        """
        Fetches jobs with robust error handling, retries, and auto-refresh logic.
        Returns None without touching the network while the block cooldown is active.
        """
        MAX_RETRIES = 2

        if blocked_for() > 0:
            return None

        if force_refresh or not self.headers or not self.headers.get("authorization"):
            logger.info("Session missing or force refresh requested. Triggering solver...")
            _trigger_refresh()
            self._load()
            if not self.headers.get("authorization"):
                return None

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
                # Re-initialize session to reset any dropped sockets
                self._reset_session()
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
            reason = f"Request rejected (HTTP {status})" if status in [401, 403] else "Cloudflare HTML challenge"
            logger.warning(f"{reason}: {_describe_response(response)}")

            if self._recover_from_rejection() and retry_count < MAX_RETRIES:
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
                    self._recover_from_rejection() # Just refresh, next poll will pick it up
                elif "data" in data:
                    _note_success()
            except Exception as e:
                logger.error(f"Failed to parse JSON response: {e}")

        return response
