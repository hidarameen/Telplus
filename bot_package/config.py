"""
Configuration for Telegram Bot System
"""
import os

# Telegram Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', 'your_bot_token_here')
API_ID = os.getenv('API_ID', 'your_api_id_here')
API_HASH = os.getenv('API_HASH', 'your_api_hash_here')

# Database Configuration  
DATABASE_FILE = 'telegram_bot.db'

# Session Configuration
SESSION_FILE = 'userbot_session'

# Other Settings
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'