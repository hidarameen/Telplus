"""
Configuration for Telegram Bot System
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', 'your_bot_token_here')
API_ID = int(os.getenv('API_ID', '24343527'))
API_HASH = os.getenv('API_HASH', 'your_api_hash_here')

# Database Configuration  
DATABASE_FILE = 'telegram_bot.db'

# Session Configuration
SESSION_FILE = 'userbot_session'

# Other Settings
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'