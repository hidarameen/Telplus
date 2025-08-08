import os

# Telegram Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', 'your_bot_token_here')

# Telegram API Configuration for Userbot
API_ID = int(os.getenv('API_ID', '12345'))
API_HASH = os.getenv('API_HASH', 'your_api_hash_here')

# Flask Configuration
SECRET_KEY = os.getenv('SECRET_KEY', 'your_secret_key_here')
DATABASE_URL = 'sqlite:///telegram_bot.db'

# Session Configuration
SESSION_FILE = 'user_session'
