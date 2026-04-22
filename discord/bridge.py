import sys
from pathlib import Path

# Add the scraper/ folder to the import path so runner.py is importable
SCRAPER_DIR = Path(__file__).resolve().parent.parent / "scraper"
if str(SCRAPER_DIR) not in sys.path:
    sys.path.insert(0, str(SCRAPER_DIR))

import runner as scraper_runner


def get_jobs(keyword: str = "python", count: int = 10) -> list:
    """
    Bridge between the Discord bot and the Upwork scraper.
    Calls scraper/runner.py and returns a clean list of job dicts.
    """
    return scraper_runner.run_scraper(keyword=keyword, count=count)
