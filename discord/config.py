import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Read configurations
BOT_TOKEN = os.getenv("BOT_TOKEN")

_channel_id_env = os.getenv("CHANNEL_ID")
CHANNEL_ID = int(_channel_id_env) if _channel_id_env and _channel_id_env.isdigit() else None

# How often (in minutes) to poll Upwork for new jobs per tracked keyword
REFRESH_INTERVAL = 1

# Maximum job age in hours to consider (default: 1.0 hour)
_max_age_env = os.getenv("MAX_JOB_AGE_HOURS")
MAX_JOB_AGE_HOURS = float(_max_age_env) if _max_age_env else 1.0

