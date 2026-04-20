import sys
import subprocess
import importlib
from curl_cffi import requests
from pathlib import Path

# Path to the phase2 bootstrap script
BOOTSTRAP_PATH = Path(__file__).resolve().parent.parent.parent / "phase2" / "auth" / "bootstrap.py"


def _trigger_refresh():
    """
    Runs the Phase 2 bootstrap script to get fresh tokens.
    Blocks until the browser session is complete and config.py is updated.
    """
    print("\n[UpworkClient] Triggering Phase 2 token refresh...")
    print("[UpworkClient] A browser window will open - please wait.\n")

    result = subprocess.run(
        [sys.executable, str(BOOTSTRAP_PATH)],
        check=False
    )

    if result.returncode != 0:
        print("[UpworkClient] [!] Bootstrap script exited with an error. Check the browser.")
    else:
        print("[UpworkClient] [OK] Token refresh complete. Reloading config...")

    # Reload config.py so the new tokens are picked up without restarting
    import scraper.config as config_module
    importlib.reload(config_module)
    from scraper.config import HEADERS, COOKIES
    return HEADERS, COOKIES


class UpworkClient:
    def __init__(self, headers, cookies):
        self.session = requests.Session(impersonate="chrome110")
        self.headers = headers
        self.cookies = cookies

    def fetch_jobs(self, payload, retry_on_403: bool = True):
        response = self.session.post(
            "https://www.upwork.com/api/graphql/v1?alias=visitorJobSearch",
            headers=self.headers,
            cookies=self.cookies,
            json=payload
        )

        # Auto-refresh on Cloudflare block
        if response.status_code == 403 and retry_on_403:
            print(f"\n[UpworkClient] 403 Forbidden detected. Initiating auto-refresh...")
            new_headers, new_cookies = _trigger_refresh()
            self.headers = new_headers
            self.cookies = new_cookies

            # Retry ONCE with fresh tokens (no infinite loop)
            response = self.fetch_jobs(payload, retry_on_403=False)

        return response
