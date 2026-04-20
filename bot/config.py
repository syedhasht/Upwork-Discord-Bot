import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Read configurations
BOT_TOKEN = os.getenv("BOT_TOKEN")

_channel_id_env = os.getenv("CHANNEL_ID")
CHANNEL_ID = int(_channel_id_env) if _channel_id_env and _channel_id_env.isdigit() else None
