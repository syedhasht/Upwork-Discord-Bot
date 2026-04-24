import logging
import config
import database
from bot import bot
from pathlib import Path

# ── Logging Setup ────────────────────────────────────────────────────────────
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "bot.log"

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)-8s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("jobhunt")

# ── Execution ─────────────────────────────────────────────────────────────────

def main():
    """Main entry point: Initialize DB and run the bot."""
    print(f"[Logger] Logging to: {LOG_FILE}")
    
    # Initialize SQLite database
    database.init_db()
    
    # Run Discord Bot
    if not config.BOT_TOKEN or config.BOT_TOKEN == "your_discord_bot_token_here":
        logger.error("BOT_TOKEN missing in .env!")
    else:
        logger.info("Initializing bot engine...")
        bot.run(config.BOT_TOKEN)

if __name__ == "__main__":
    main()
