"""
PostgreSQL Database management for Telegram Bot System
"""
import psycopg2
import psycopg2.extras
import logging
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import asyncio
import asyncpg

logger = logging.getLogger(__name__)

class PostgreSQLDatabase:
    def __init__(self, connection_string: str = None):
        """Initialize PostgreSQL database connection"""
        if connection_string:
            self.connection_string = connection_string
        else:
            # Default connection string
            self.connection_string = os.getenv(
                'DATABASE_URL',
                'postgresql://telegram_bot_user:your_secure_password@localhost:5432/telegram_bot_db'
            )
        self.init_database()

    def get_connection(self):
        """Get PostgreSQL database connection"""
        conn = psycopg2.connect(self.connection_string)
        return conn

    async def get_async_connection(self):
        """Get async PostgreSQL database connection"""
        conn = await asyncpg.connect(self.connection_string)
        return conn

    def init_database(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Tasks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    task_name TEXT DEFAULT 'مهمة توجيه',
                    source_chat_id TEXT NOT NULL,
                    source_chat_name TEXT,
                    target_chat_id TEXT NOT NULL,
                    target_chat_name TEXT,
                    forward_mode TEXT DEFAULT 'forward',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Task Sources table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_sources (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    chat_id TEXT NOT NULL,
                    chat_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Task Targets table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_targets (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    chat_id TEXT NOT NULL,
                    chat_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # User settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id BIGINT PRIMARY KEY,
                    timezone TEXT DEFAULT 'Asia/Riyadh',
                    language TEXT DEFAULT 'ar',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # User sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    user_id BIGINT PRIMARY KEY,
                    phone_number TEXT,
                    session_string TEXT,
                    is_authenticated BOOLEAN DEFAULT FALSE,
                    is_healthy BOOLEAN DEFAULT TRUE,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    connection_errors INTEGER DEFAULT 0,
                    last_error_time TIMESTAMP,
                    last_error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Conversation states table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversation_states (
                    user_id BIGINT PRIMARY KEY,
                    state TEXT NOT NULL,
                    data JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Task media filters table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_media_filters (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    media_types TEXT[] DEFAULT '{}',
                    min_file_size INTEGER DEFAULT 0,
                    max_file_size INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Task word filters table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_word_filters (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    filter_type TEXT DEFAULT 'block',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Word filter entries table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS word_filter_entries (
                    id SERIAL PRIMARY KEY,
                    filter_id INTEGER NOT NULL,
                    word TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (filter_id) REFERENCES task_word_filters (id) ON DELETE CASCADE
                )
            ''')

            # Task text replacements table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_text_replacements (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Text replacement entries table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS text_replacement_entries (
                    id SERIAL PRIMARY KEY,
                    replacement_id INTEGER NOT NULL,
                    old_text TEXT NOT NULL,
                    new_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (replacement_id) REFERENCES task_text_replacements (id) ON DELETE CASCADE
                )
            ''')

            # Task headers table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_headers (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    header_text TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Task footers table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_footers (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    footer_text TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Task inline buttons table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_inline_buttons (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    button_text TEXT NOT NULL,
                    button_url TEXT,
                    button_callback TEXT,
                    button_order INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Task message settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_message_settings (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    preserve_media BOOLEAN DEFAULT TRUE,
                    preserve_caption BOOLEAN DEFAULT TRUE,
                    preserve_buttons BOOLEAN DEFAULT TRUE,
                    preserve_links BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Task forwarding settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_forwarding_settings (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    forward_mode TEXT DEFAULT 'forward',
                    preserve_original BOOLEAN DEFAULT FALSE,
                    add_watermark BOOLEAN DEFAULT FALSE,
                    watermark_text TEXT,
                    watermark_position TEXT DEFAULT 'bottom-right',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Message mappings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS message_mappings (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    source_message_id BIGINT NOT NULL,
                    target_message_id BIGINT NOT NULL,
                    source_chat_id TEXT NOT NULL,
                    target_chat_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Pending messages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pending_messages (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    message_id BIGINT NOT NULL,
                    chat_id TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    message_data JSONB NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    next_retry TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Recurring posts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS recurring_posts (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    name TEXT DEFAULT 'منشور متكرر',
                    enabled BOOLEAN DEFAULT TRUE,
                    source_chat_id TEXT NOT NULL,
                    source_message_id BIGINT NOT NULL,
                    interval_seconds INTEGER NOT NULL,
                    delete_previous BOOLEAN DEFAULT FALSE,
                    preserve_original_buttons BOOLEAN DEFAULT TRUE,
                    next_run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Deliveries table for recurring posts
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS recurring_post_deliveries (
                    id SERIAL PRIMARY KEY,
                    recurring_post_id INTEGER NOT NULL,
                    target_chat_id TEXT NOT NULL,
                    last_message_id BIGINT,
                    last_posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (recurring_post_id) REFERENCES recurring_posts (id) ON DELETE CASCADE,
                    UNIQUE(recurring_post_id, target_chat_id)
                )
            ''')

            # Task advanced filters table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_advanced_filters (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    filter_type TEXT NOT NULL,
                    filter_value TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Task day filters table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_day_filters (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    day_of_week INTEGER NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Task working hours table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_working_hours (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    is_enabled BOOLEAN DEFAULT FALSE,
                    timezone TEXT DEFAULT 'Asia/Riyadh',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Task working hours schedule table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_working_hours_schedule (
                    id SERIAL PRIMARY KEY,
                    working_hours_id INTEGER NOT NULL,
                    day_of_week INTEGER NOT NULL,
                    start_time TIME NOT NULL,
                    end_time TIME NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (working_hours_id) REFERENCES task_working_hours (id) ON DELETE CASCADE
                )
            ''')

            # Task language filters table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_language_filters (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    language_code TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Task admin filters table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_admin_filters (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    admin_user_id BIGINT NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Task duplicate settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_duplicate_settings (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    check_duplicates BOOLEAN DEFAULT FALSE,
                    duplicate_window_hours INTEGER DEFAULT 24,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Forwarded messages log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS forwarded_messages_log (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    source_message_id BIGINT NOT NULL,
                    target_message_id BIGINT NOT NULL,
                    source_chat_id TEXT NOT NULL,
                    target_chat_id TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    forward_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processing_time_ms INTEGER,
                    status TEXT DEFAULT 'success',
                    error_message TEXT,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Task inline button filters table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_inline_button_filters (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    filter_type TEXT DEFAULT 'preserve',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Task forwarded message filters table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_forwarded_message_filters (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    filter_type TEXT DEFAULT 'allow',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Task text cleaning settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_text_cleaning_settings (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    clean_links BOOLEAN DEFAULT FALSE,
                    clean_mentions BOOLEAN DEFAULT FALSE,
                    clean_hashtags BOOLEAN DEFAULT FALSE,
                    clean_emojis BOOLEAN DEFAULT FALSE,
                    clean_extra_spaces BOOLEAN DEFAULT FALSE,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Task text cleaning keywords table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_text_cleaning_keywords (
                    id SERIAL PRIMARY KEY,
                    cleaning_settings_id INTEGER NOT NULL,
                    keyword TEXT NOT NULL,
                    replacement TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cleaning_settings_id) REFERENCES task_text_cleaning_settings (id) ON DELETE CASCADE
                )
            ''')

            # Task text formatting settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_text_formatting_settings (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    bold_links BOOLEAN DEFAULT FALSE,
                    italic_mentions BOOLEAN DEFAULT FALSE,
                    underline_hashtags BOOLEAN DEFAULT FALSE,
                    strikethrough_spoilers BOOLEAN DEFAULT FALSE,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Task translation settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_translation_settings (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    translate_text BOOLEAN DEFAULT FALSE,
                    source_language TEXT DEFAULT 'auto',
                    target_language TEXT DEFAULT 'ar',
                    translation_service TEXT DEFAULT 'google',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Task watermark settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_watermark_settings (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    add_watermark BOOLEAN DEFAULT FALSE,
                    watermark_text TEXT,
                    watermark_image_path TEXT,
                    watermark_position TEXT DEFAULT 'bottom-right',
                    watermark_opacity REAL DEFAULT 0.7,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Task audio metadata settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_audio_metadata_settings (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    enabled BOOLEAN DEFAULT FALSE,
                    template TEXT DEFAULT 'default',
                    preserve_quality BOOLEAN DEFAULT TRUE,
                    convert_to_mp3 BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Task character limit settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_character_limit_settings (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    enabled BOOLEAN DEFAULT FALSE,
                    mode TEXT DEFAULT 'block',
                    length_mode TEXT DEFAULT 'range',
                    min_chars INTEGER DEFAULT 0,
                    max_chars INTEGER DEFAULT 4096,
                    use_range BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Task rate limit settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_rate_limit_settings (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    enabled BOOLEAN DEFAULT FALSE,
                    max_messages_per_hour INTEGER DEFAULT 100,
                    max_messages_per_day INTEGER DEFAULT 1000,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Task forwarding delay settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_forwarding_delay_settings (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    enabled BOOLEAN DEFAULT FALSE,
                    delay_seconds INTEGER DEFAULT 0,
                    random_delay BOOLEAN DEFAULT FALSE,
                    min_delay INTEGER DEFAULT 0,
                    max_delay INTEGER DEFAULT 60,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Task sending interval settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_sending_interval_settings (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    enabled BOOLEAN DEFAULT FALSE,
                    interval_seconds INTEGER DEFAULT 1,
                    random_interval BOOLEAN DEFAULT FALSE,
                    min_interval INTEGER DEFAULT 1,
                    max_interval INTEGER DEFAULT 10,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Rate limit tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS rate_limit_tracking (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    message_count INTEGER DEFAULT 0,
                    hour_count INTEGER DEFAULT 0,
                    day_count INTEGER DEFAULT 0,
                    last_reset_hour TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_reset_day TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Task audio template settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_audio_template_settings (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    title_template TEXT DEFAULT '$title',
                    artist_template TEXT DEFAULT '$artist',
                    album_artist_template TEXT DEFAULT '$album_artist',
                    album_template TEXT DEFAULT '$album',
                    year_template TEXT DEFAULT '$year',
                    genre_template TEXT DEFAULT '$genre',
                    composer_template TEXT DEFAULT '$composer',
                    comment_template TEXT DEFAULT '$comment',
                    track_template TEXT DEFAULT '$track',
                    length_template TEXT DEFAULT '$length',
                    lyrics_template TEXT DEFAULT '$lyrics',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Message duplicates table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS message_duplicates (
                    id SERIAL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    message_hash TEXT NOT NULL,
                    message_id BIGINT NOT NULL,
                    chat_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # User channels table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_channels (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    channel_id TEXT NOT NULL,
                    channel_name TEXT,
                    channel_username TEXT,
                    is_admin BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_sources_task_id ON task_sources(task_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_targets_task_id ON task_targets(task_id)')
            cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS uq_user_sessions_user_id ON user_sessions(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversation_states_user_id ON conversation_states(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_message_mappings_task_id ON message_mappings(task_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_pending_messages_task_id ON pending_messages(task_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_forwarded_messages_log_task_id ON forwarded_messages_log(task_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_message_duplicates_task_id ON message_duplicates(task_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_channels_user_id ON user_channels(user_id)')

            conn.commit()

            # ===== Schema safety: ensure required columns exist (for upgraded databases) =====
            try:
                cursor.execute("ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS is_authenticated BOOLEAN DEFAULT FALSE")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS is_healthy BOOLEAN DEFAULT TRUE")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS connection_errors INTEGER DEFAULT 0")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS last_error_time TIMESTAMP")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS last_error_message TEXT")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS session_string TEXT")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS phone_number TEXT")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE user_sessions ALTER COLUMN created_at TYPE TIMESTAMP USING created_at::timestamp")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE user_sessions ALTER COLUMN updated_at TYPE TIMESTAMP USING updated_at::timestamp")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE user_sessions ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP")
            except Exception:
                pass
            try:
                cursor.execute("UPDATE user_sessions SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE user_sessions ALTER COLUMN updated_at SET DEFAULT CURRENT_TIMESTAMP")
            except Exception:
                pass

            try:
                cursor.execute("ALTER TABLE user_sessions ALTER COLUMN user_id TYPE BIGINT USING user_id::bigint")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE user_sessions DROP CONSTRAINT IF EXISTS user_sessions_user_id_fkey")
            except Exception:
                pass
            try:
                cursor.execute("""
DO $$
DECLARE
    r record;
BEGIN
    FOR r IN
        SELECT conname
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        WHERE t.relname = 'user_sessions' AND c.contype = 'f'
    LOOP
        EXECUTE format('ALTER TABLE user_sessions DROP CONSTRAINT %I', r.conname);
    END LOOP;
END$$;
""")
            except Exception:
                pass
            
            try:
                cursor.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS task_name TEXT DEFAULT 'مهمة توجيه'")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS source_chat_id TEXT")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS source_chat_name TEXT")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS target_chat_id TEXT")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS target_chat_name TEXT")
            except Exception:
                pass

            try:
                cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_user_channels_user_channel ON user_channels(user_id, channel_id)")
            except Exception:
                pass

            # Compatibility columns for message settings / inline buttons / duplicates
            try:
                cursor.execute("ALTER TABLE task_message_settings ADD COLUMN IF NOT EXISTS header_enabled BOOLEAN DEFAULT FALSE")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE task_message_settings ADD COLUMN IF NOT EXISTS header_text TEXT DEFAULT ''")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE task_message_settings ADD COLUMN IF NOT EXISTS footer_enabled BOOLEAN DEFAULT FALSE")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE task_message_settings ADD COLUMN IF NOT EXISTS footer_text TEXT DEFAULT ''")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE task_message_settings ADD COLUMN IF NOT EXISTS inline_buttons_enabled BOOLEAN DEFAULT FALSE")
            except Exception:
                pass

            try:
                cursor.execute("ALTER TABLE task_inline_buttons ADD COLUMN IF NOT EXISTS row_position INTEGER DEFAULT 0")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE task_inline_buttons ADD COLUMN IF NOT EXISTS col_position INTEGER DEFAULT 0")
            except Exception:
                pass

            try:
                cursor.execute("ALTER TABLE task_duplicate_settings ADD COLUMN IF NOT EXISTS similarity_threshold REAL DEFAULT 0.85")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE task_duplicate_settings ADD COLUMN IF NOT EXISTS check_text BOOLEAN DEFAULT TRUE")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE task_duplicate_settings ADD COLUMN IF NOT EXISTS check_media BOOLEAN DEFAULT TRUE")
            except Exception:
                pass

            conn.commit()

    # User session methods
    def save_user_session(self, user_id: int, phone_number: str, session_string: str) -> bool:
        """Save user session to database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO user_sessions (user_id, phone_number, session_string, is_authenticated, created_at, updated_at)
                    VALUES (%s, %s, %s, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET 
                        phone_number = EXCLUDED.phone_number,
                        session_string = EXCLUDED.session_string,
                        is_authenticated = TRUE,
                        updated_at = CURRENT_TIMESTAMP
                ''', (user_id, phone_number, session_string))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving user session: {e}")
            return False

    def get_user_session(self, user_id: int) -> Optional[Dict]:
        """Get user session from database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute('''
                    SELECT * FROM user_sessions WHERE user_id = %s
                ''', (user_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting user session: {e}")
            return None

    def is_user_authenticated(self, user_id: int) -> bool:
        """Check if user is authenticated"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT is_authenticated FROM user_sessions WHERE user_id = %s
                ''', (user_id,))
                result = cursor.fetchone()
                return result[0] if result else False
        except Exception as e:
            logger.error(f"Error checking user authentication: {e}")
            return False

    # Task methods
    def create_task(self, user_id: int, task_name: str, source_chat_id: str, target_chat_id: str, **kwargs) -> int:
        """Create a new task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO tasks (user_id, task_name, source_chat_id, target_chat_id, forward_mode)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                ''', (user_id, task_name, source_chat_id, target_chat_id, kwargs.get('forward_mode', 'forward')))
                task_id = cursor.fetchone()[0]
                conn.commit()
                return task_id
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return None

    def get_task(self, task_id: int, user_id: int = None) -> Optional[Dict]:
        """Get task by ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                if user_id:
                    cursor.execute('''
                        SELECT * FROM tasks WHERE id = %s AND user_id = %s
                    ''', (task_id, user_id))
                else:
                    cursor.execute('''
                        SELECT * FROM tasks WHERE id = %s
                    ''', (task_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting task: {e}")
            return None

    def get_user_tasks(self, user_id: int) -> List[Dict]:
        """Get all tasks for a user"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute('''
                    SELECT * FROM tasks WHERE user_id = %s ORDER BY created_at DESC
                ''', (user_id,))
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error getting user tasks: {e}")
            return []

    # Audio metadata methods
    def get_audio_metadata_settings(self, task_id: int) -> Optional[Dict]:
        """Get audio metadata settings for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute('''
                    SELECT * FROM task_audio_metadata_settings WHERE task_id = %s
                ''', (task_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting audio metadata settings: {e}")
            return None

    def get_audio_template_settings(self, task_id: int) -> Optional[Dict]:
        """Get audio template settings for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute('''
                    SELECT * FROM task_audio_template_settings WHERE task_id = %s
                ''', (task_id,))
                result = cursor.fetchone()
                if result:
                    return dict(result)
                else:
                    # Create default settings if not exists
                    cursor.execute('''
                        INSERT INTO task_audio_template_settings (task_id)
                        VALUES (%s)
                        RETURNING *
                    ''', (task_id,))
                    result = cursor.fetchone()
                    conn.commit()
                    return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting audio template settings: {e}")
            return None

    def update_audio_template_setting(self, task_id: int, tag_name: str, template_value: str) -> bool:
        """Update a specific audio template setting for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if settings exist
                cursor.execute('''
                    SELECT id FROM task_audio_template_settings WHERE task_id = %s
                ''', (task_id,))
                
                if cursor.fetchone():
                    # Update existing settings
                    cursor.execute(f'''
                        UPDATE task_audio_template_settings 
                        SET {tag_name}_template = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE task_id = %s
                    ''', (template_value, task_id))
                else:
                    # Create new settings
                    cursor.execute(f'''
                        INSERT INTO task_audio_template_settings (task_id, {tag_name}_template)
                        VALUES (%s, %s)
                    ''', (task_id, template_value))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating audio template setting: {e}")
            return False

    def reset_audio_template_settings(self, task_id: int) -> bool:
        """Reset audio template settings to default values"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE task_audio_template_settings SET
                        title_template = '$title',
                        artist_template = '$artist',
                        album_artist_template = '$album_artist',
                        album_template = '$album',
                        year_template = '$year',
                        genre_template = '$genre',
                        composer_template = '$composer',
                        comment_template = '$comment',
                        track_template = '$track',
                        length_template = '$length',
                        lyrics_template = '$lyrics',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE task_id = %s
                ''', (task_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error resetting audio template settings: {e}")
            return False

    # Character limit methods
    def get_character_limit_settings(self, task_id: int) -> Optional[Dict]:
        """Get character limit settings for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute('''
                    SELECT enabled, mode, length_mode, min_chars, max_chars, use_range
                    FROM task_character_limit_settings WHERE task_id = %s
                ''', (task_id,))
                result = cursor.fetchone()
                if result:
                    return dict(result)
                else:
                    # Create defaults if missing
                    cursor.execute('''
                        INSERT INTO task_character_limit_settings (task_id, enabled, mode, length_mode, min_chars, max_chars, use_range)
                        VALUES (%s, FALSE, 'allow', 'range', 0, 4000, TRUE)
                        RETURNING enabled, mode, length_mode, min_chars, max_chars, use_range
                    ''', (task_id,))
                    result = cursor.fetchone()
                    conn.commit()
                    return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting character limit settings: {e}")
            return None

    def update_character_limit_settings(self, task_id: int, **kwargs) -> bool:
        """Update character limit settings for PostgreSQL"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Ensure row exists
                cursor.execute('''
                    INSERT INTO task_character_limit_settings (task_id)
                    VALUES (%s)
                    ON CONFLICT (task_id) DO NOTHING
                ''', (task_id,))
                if not kwargs:
                    return False
                updates = []
                params = []
                for key, value in kwargs.items():
                    if key in ['enabled', 'mode', 'min_chars', 'max_chars', 'use_range', 'length_mode']:
                        updates.append(f"{key} = %s")
                        params.append(value)
                if not updates:
                    return False
                params.append(task_id)
                cursor.execute(f'''
                    UPDATE task_character_limit_settings
                    SET {', '.join(updates)}
                    WHERE task_id = %s
                ''', params)
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating character limit settings: {e}")
            return False

    def toggle_character_limit(self, task_id: int) -> bool:
        """Toggle character limit enabled flag for PostgreSQL"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO task_character_limit_settings (task_id, enabled)
                    VALUES (%s, TRUE)
                    ON CONFLICT (task_id) DO UPDATE SET enabled = NOT task_character_limit_settings.enabled
                    RETURNING enabled
                ''', (task_id,))
                result = cursor.fetchone()
                conn.commit()
                return result[0] if result else False
        except Exception as e:
            logger.error(f"Error toggling character limit: {e}")
            return False

    def cycle_character_limit_mode(self, task_id: int) -> str:
        """Cycle allow/block mode for PostgreSQL"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO task_character_limit_settings (task_id, mode)
                    VALUES (%s, 'allow')
                    ON CONFLICT (task_id) DO NOTHING
                ''', (task_id,))
                cursor.execute('SELECT mode FROM task_character_limit_settings WHERE task_id = %s', (task_id,))
                current = cursor.fetchone()
                new_mode = 'block' if current and current[0] == 'allow' else 'allow'
                cursor.execute('UPDATE task_character_limit_settings SET mode = %s WHERE task_id = %s', (new_mode, task_id))
                conn.commit()
                return new_mode
        except Exception as e:
            logger.error(f"Error cycling character limit mode: {e}")
            return 'allow'

    def cycle_length_mode(self, task_id: int) -> str:
        """Cycle length_mode for PostgreSQL: max -> min -> range"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO task_character_limit_settings (task_id, length_mode)
                    VALUES (%s, 'range')
                    ON CONFLICT (task_id) DO NOTHING
                ''', (task_id,))
                cursor.execute('SELECT length_mode FROM task_character_limit_settings WHERE task_id = %s', (task_id,))
                current = cursor.fetchone()
                current_mode = current[0] if current else 'range'
                if current_mode == 'max':
                    new_mode = 'min'
                elif current_mode == 'min':
                    new_mode = 'range'
                else:
                    new_mode = 'max'
                cursor.execute('UPDATE task_character_limit_settings SET length_mode = %s WHERE task_id = %s', (new_mode, task_id))
                conn.commit()
                return new_mode
        except Exception as e:
            logger.error(f"Error cycling length mode: {e}")
            return 'range'

    # Rate limit methods
    def get_rate_limit_settings(self, task_id: int) -> Optional[Dict]:
        """Get rate limit settings for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute('''
                    SELECT * FROM task_rate_limit_settings WHERE task_id = %s
                ''', (task_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting rate limit settings: {e}")
            return None

    # Forwarding delay methods
    def get_forwarding_delay_settings(self, task_id: int) -> Optional[Dict]:
        """Get forwarding delay settings for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute('''
                    SELECT * FROM task_forwarding_delay_settings WHERE task_id = %s
                ''', (task_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting forwarding delay settings: {e}")
            return None

    # Sending interval methods
    def get_sending_interval_settings(self, task_id: int) -> Optional[Dict]:
        """Get sending interval settings for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute('''
                    SELECT * FROM task_sending_interval_settings WHERE task_id = %s
                ''', (task_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting sending interval settings: {e}")
            return None

    # ===== Recurring Posts CRUD =====
    def create_recurring_post(self, task_id: int, source_chat_id: str, source_message_id: int, interval_seconds: int,
                               name: str = 'منشور متكرر', enabled: bool = True,
                               delete_previous: bool = False, preserve_original_buttons: bool = True,
                               next_run_at: Optional[str] = None) -> Optional[int]:
        """Create a recurring post and return its ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO recurring_posts
                    (task_id, name, enabled, source_chat_id, source_message_id, interval_seconds,
                     delete_previous, preserve_original_buttons, next_run_at, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, CURRENT_TIMESTAMP), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    RETURNING id
                ''', (task_id, name, enabled, str(source_chat_id), int(source_message_id), int(interval_seconds),
                      bool(delete_previous), bool(preserve_original_buttons), next_run_at))
                new_id = cursor.fetchone()[0]
                conn.commit()
                return new_id
        except Exception as e:
            logger.error(f"Error creating recurring post: {e}")
            return None

    def update_recurring_post(self, recurring_id: int, **kwargs) -> bool:
        """Update fields of a recurring post"""
        try:
            if not kwargs:
                return False
            with self.get_connection() as conn:
                cursor = conn.cursor()
                allowed = {
                    'name', 'enabled', 'interval_seconds', 'delete_previous', 'preserve_original_buttons', 'next_run_at'
                }
                updates = []
                params = []
                for key, val in kwargs.items():
                    if key in allowed:
                        updates.append(f"{key} = %s")
                        params.append(val)
                if not updates:
                    return False
                params.append(recurring_id)
                cursor.execute(f'''
                    UPDATE recurring_posts
                    SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                ''', params)
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating recurring post: {e}")
            return False

    def delete_recurring_post(self, recurring_id: int) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM recurring_posts WHERE id = %s', (recurring_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting recurring post: {e}")
            return False

    def list_recurring_posts(self, task_id: int) -> List[Dict]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute('''
                    SELECT id, task_id, name, enabled, source_chat_id, source_message_id, interval_seconds,
                           delete_previous, preserve_original_buttons, next_run_at, created_at, updated_at
                    FROM recurring_posts WHERE task_id = %s ORDER BY id DESC
                ''', (task_id,))
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error listing recurring posts: {e}")
            return []

    def get_recurring_post(self, recurring_id: int) -> Optional[Dict]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute('''
                    SELECT id, task_id, name, enabled, source_chat_id, source_message_id, interval_seconds,
                           delete_previous, preserve_original_buttons, next_run_at, created_at, updated_at
                    FROM recurring_posts WHERE id = %s
                ''', (recurring_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting recurring post: {e}")
            return None

    def upsert_recurring_delivery(self, recurring_post_id: int, target_chat_id: str,
                                  last_message_id: Optional[int]) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO recurring_post_deliveries (recurring_post_id, target_chat_id, last_message_id, last_posted_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (recurring_post_id, target_chat_id)
                    DO UPDATE SET last_message_id = EXCLUDED.last_message_id, last_posted_at = CURRENT_TIMESTAMP
                ''', (recurring_post_id, str(target_chat_id), last_message_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error upserting recurring delivery: {e}")
            return False

    def get_recurring_delivery(self, recurring_post_id: int, target_chat_id: str) -> Optional[Dict]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute('''
                    SELECT id, recurring_post_id, target_chat_id, last_message_id, last_posted_at
                    FROM recurring_post_deliveries
                    WHERE recurring_post_id = %s AND target_chat_id = %s
                ''', (recurring_post_id, str(target_chat_id)))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting recurring delivery: {e}")
            return None

    # Message settings methods
    def get_message_settings(self, task_id: int) -> Optional[Dict]:
        """Get message settings for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute('''
                    SELECT * FROM task_message_settings WHERE task_id = %s
                ''', (task_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting message settings: {e}")
            return None

    # Working hours methods
    def toggle_working_hour(self, task_id: int, day_of_week: int, start_time: str, end_time: str) -> bool:
        """Toggle working hour for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if working hours enabled
                cursor.execute('''
                    SELECT id FROM task_working_hours WHERE task_id = %s
                ''', (task_id,))
                
                working_hours = cursor.fetchone()
                if not working_hours:
                    # Create working hours record
                    cursor.execute('''
                        INSERT INTO task_working_hours (task_id, is_enabled)
                        VALUES (%s, TRUE)
                        RETURNING id
                    ''', (task_id,))
                    working_hours_id = cursor.fetchone()[0]
                else:
                    working_hours_id = working_hours[0]
                
                # Check if schedule exists
                cursor.execute('''
                    SELECT id FROM task_working_hours_schedule 
                    WHERE working_hours_id = %s AND day_of_week = %s
                ''', (working_hours_id, day_of_week))
                
                schedule = cursor.fetchone()
                if schedule:
                    # Toggle existing schedule
                    cursor.execute('''
                        UPDATE task_working_hours_schedule 
                        SET is_active = NOT is_active
                        WHERE id = %s
                    ''', (schedule[0],))
                else:
                    # Create new schedule
                    cursor.execute('''
                        INSERT INTO task_working_hours_schedule 
                        (working_hours_id, day_of_week, start_time, end_time)
                        VALUES (%s, %s, %s, %s)
                    ''', (working_hours_id, day_of_week, start_time, end_time))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error toggling working hour: {e}")
            return False

    # Channel management methods
    def add_user_channel(self, user_id: int, channel_id: str, channel_name: str = None, channel_username: str = None, is_admin: bool = False) -> bool:
        """Add a channel for a user"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO user_channels (user_id, channel_id, channel_name, channel_username, is_admin)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, channel_id) 
                    DO UPDATE SET 
                        channel_name = EXCLUDED.channel_name,
                        channel_username = EXCLUDED.channel_username,
                        is_admin = EXCLUDED.is_admin,
                        updated_at = CURRENT_TIMESTAMP
                ''', (user_id, channel_id, channel_name, channel_username, is_admin))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error adding user channel: {e}")
            return False

    def get_user_channels(self, user_id: int) -> List[Dict]:
        """Get all channels for a user"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute('''
                    SELECT * FROM user_channels WHERE user_id = %s ORDER BY created_at DESC
                ''', (user_id,))
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error getting user channels: {e}")
            return []

    def delete_user_channel(self, user_id: int, channel_id: str) -> bool:
        """Delete a channel for a user"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM user_channels WHERE user_id = %s AND channel_id = %s
                ''', (user_id, channel_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting user channel: {e}")
            return False

    def update_user_channel(self, user_id: int, channel_id: str, **kwargs) -> bool:
        """Update a channel for a user"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build update query dynamically
                update_fields = []
                values = []
                
                for key, value in kwargs.items():
                    if key in ['channel_name', 'channel_username', 'is_admin']:
                        update_fields.append(f"{key} = %s")
                        values.append(value)
                
                if not update_fields:
                    return False
                
                values.extend([user_id, channel_id])
                
                query = f'''
                    UPDATE user_channels 
                    SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s AND channel_id = %s
                '''
                
                cursor.execute(query, values)
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating user channel: {e}")
            return False

    # ===== Conversation state methods (API parity with SQLite) =====
    def set_conversation_state(self, user_id: int, state: str, data: str = '') -> bool:
        try:
            import json
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Normalize data to JSONB
                try:
                    parsed = json.loads(data) if data else {}
                except Exception:
                    parsed = {"data": data} if data else {}
                cursor.execute('''
                    INSERT INTO conversation_states (user_id, state, data, created_at, updated_at)
                    VALUES (%s, %s, %s::jsonb, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id)
                    DO UPDATE SET state = EXCLUDED.state, data = EXCLUDED.data, updated_at = CURRENT_TIMESTAMP
                ''', (user_id, state, json.dumps(parsed)))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error setting conversation state: {e}")
            return False

    def get_conversation_state(self, user_id: int):
        try:
            import json
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT state, data FROM conversation_states WHERE user_id = %s', (user_id,))
                row = cursor.fetchone()
                if row:
                    state_val = row[0]
                    data_val = row[1]
                    try:
                        data_str = json.dumps(data_val) if not isinstance(data_val, str) else data_val
                    except Exception:
                        data_str = str(data_val) if data_val is not None else ''
                    return (state_val, data_str)
                return None
        except Exception as e:
            logger.error(f"Error getting conversation state: {e}")
            return None

    def clear_conversation_state(self, user_id: int) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM conversation_states WHERE user_id = %s', (user_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error clearing conversation state: {e}")
            return False

    # ===== Session helpers =====
    def update_session_health(self, user_id: int, is_healthy: bool, error_message: str = None) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if is_healthy:
                    cursor.execute('''
                        UPDATE user_sessions
                        SET is_healthy = TRUE, last_activity = CURRENT_TIMESTAMP, connection_errors = 0, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s
                    ''', (user_id,))
                else:
                    cursor.execute('''
                        UPDATE user_sessions
                        SET is_healthy = FALSE, connection_errors = COALESCE(connection_errors, 0) + 1,
                            last_error_time = CURRENT_TIMESTAMP, last_error_message = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s
                    ''', (error_message, user_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating session health: {e}")
            return False

    def get_user_session_string(self, user_id: int) -> str:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT session_string FROM user_sessions WHERE user_id = %s AND is_authenticated = TRUE', (user_id,))
                row = cursor.fetchone()
                return row[0] if row and row[0] else None
        except Exception as e:
            logger.error(f"Error getting session string: {e}")
            return None

    def get_all_authenticated_users(self):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, phone_number, session_string
                    FROM user_sessions
                    WHERE is_authenticated = TRUE AND session_string IS NOT NULL AND session_string <> ''
                ''')
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting authenticated users: {e}")
            return []

    def delete_user_session(self, user_id: int) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM user_sessions WHERE user_id = %s', (user_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting user session: {e}")
            return False

    # ===== Tasks and sources/targets =====
    def get_task_sources(self, task_id: int):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id, chat_id, chat_name FROM task_sources WHERE task_id = %s ORDER BY created_at', (task_id,))
                results = cursor.fetchall()
                return [{'id': r[0], 'chat_id': r[1], 'chat_name': r[2]} for r in results]
        except Exception as e:
            logger.error(f"Error getting task sources: {e}")
            return []

    def get_task_targets(self, task_id: int):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id, chat_id, chat_name FROM task_targets WHERE task_id = %s ORDER BY created_at', (task_id,))
                results = cursor.fetchall()
                return [{'id': r[0], 'chat_id': r[1], 'chat_name': r[2]} for r in results]
        except Exception as e:
            logger.error(f"Error getting task targets: {e}")
            return []

    def add_task_source(self, task_id: int, chat_id: str, chat_name: str = None):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO task_sources (task_id, chat_id, chat_name) VALUES (%s, %s, %s) RETURNING id', (task_id, chat_id, chat_name))
                new_id = cursor.fetchone()[0]
                conn.commit()
                return new_id
        except Exception as e:
            logger.error(f"Error adding task source: {e}")
            return None

    def add_task_target(self, task_id: int, chat_id: str, chat_name: str = None):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO task_targets (task_id, chat_id, chat_name) VALUES (%s, %s, %s) RETURNING id', (task_id, chat_id, chat_name))
                new_id = cursor.fetchone()[0]
                conn.commit()
                return new_id
        except Exception as e:
            logger.error(f"Error adding task target: {e}")
            return None

    def remove_task_source(self, source_id: int, task_id: int) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM task_sources WHERE id = %s AND task_id = %s', (source_id, task_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error removing task source: {e}")
            return False

    def remove_task_target(self, target_id: int, task_id: int) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM task_targets WHERE id = %s AND task_id = %s', (target_id, task_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error removing task target: {e}")
            return False

    def get_active_user_tasks(self, user_id: int):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, task_name, source_chat_id, source_chat_name, target_chat_id, target_chat_name, forward_mode
                    FROM tasks WHERE user_id = %s AND is_active = TRUE
                    ORDER BY created_at DESC
                ''', (user_id,))
                rows = cursor.fetchall()
                tasks = []
                for row in rows:
                    task_id = row[0]
                    # Expand sources/targets if present in new tables
                    sources = self.get_task_sources(task_id) or ([{'id': 0, 'chat_id': row[2], 'chat_name': row[3]}] if row[2] else [])
                    targets = self.get_task_targets(task_id) or ([{'id': 0, 'chat_id': row[4], 'chat_name': row[5]}] if row[4] else [])
                    for s in sources:
                        for t in targets:
                            tasks.append({
                                'id': task_id,
                                'task_name': row[1],
                                'source_chat_id': s['chat_id'],
                                'source_chat_name': s['chat_name'],
                                'target_chat_id': t['chat_id'],
                                'target_chat_name': t['chat_name'],
                                'forward_mode': row[6] or 'forward'
                            })
                return tasks
        except Exception as e:
            logger.error(f"Error getting active user tasks: {e}")
            return []

    def get_task_with_sources_targets(self, task_id: int, user_id: int = None):
        try:
            task = self.get_task(task_id, user_id)
            if not task:
                return None
            sources = self.get_task_sources(task_id) or ([{'id': 0, 'chat_id': task.get('source_chat_id'), 'chat_name': task.get('source_chat_name')}] if task.get('source_chat_id') else [])
            targets = self.get_task_targets(task_id) or ([{'id': 0, 'chat_id': task.get('target_chat_id'), 'chat_name': task.get('target_chat_name')}] if task.get('target_chat_id') else [])
            task['sources'] = sources
            task['targets'] = targets
            return task
        except Exception as e:
            logger.error(f"Error getting task with sources/targets: {e}")
            return None

    def migrate_task_to_new_structure(self, task_id: int) -> bool:
        try:
            task = self.get_task(task_id)
            if not task:
                return False
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM task_sources WHERE task_id = %s', (task_id,))
                sources_count = cursor.fetchone()[0]
                cursor.execute('SELECT COUNT(*) FROM task_targets WHERE task_id = %s', (task_id,))
                targets_count = cursor.fetchone()[0]
                if sources_count == 0 and task.get('source_chat_id'):
                    cursor.execute('INSERT INTO task_sources (task_id, chat_id, chat_name) VALUES (%s, %s, %s)', (task_id, task['source_chat_id'], task['source_chat_name']))
                if targets_count == 0 and task.get('target_chat_id'):
                    cursor.execute('INSERT INTO task_targets (task_id, chat_id, chat_name) VALUES (%s, %s, %s)', (task_id, task['target_chat_id'], task['target_chat_name']))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error migrating task: {e}")
            return False

    # ===== Message mappings =====
    def save_message_mapping(self, task_id: int, source_chat_id: str, source_message_id: int, target_chat_id: str, target_message_id: int) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO message_mappings (task_id, source_chat_id, source_message_id, target_chat_id, target_message_id, created_at)
                    VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ''', (task_id, str(source_chat_id), source_message_id, str(target_chat_id), target_message_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving message mapping: {e}")
            return False

    def get_message_mappings_by_source(self, task_id: int, source_chat_id: str, source_message_id: int):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, task_id, source_chat_id, source_message_id, target_chat_id, target_message_id
                    FROM message_mappings
                    WHERE task_id = %s AND source_chat_id = %s AND source_message_id = %s
                ''', (task_id, str(source_chat_id), source_message_id))
                rows = cursor.fetchall()
                return [{'id': r[0], 'task_id': r[1], 'source_chat_id': r[2], 'source_message_id': r[3], 'target_chat_id': r[4], 'target_message_id': r[5]} for r in rows]
        except Exception as e:
            logger.error(f"Error getting message mappings: {e}")
            return []

    def delete_message_mapping(self, mapping_id: int) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM message_mappings WHERE id = %s', (mapping_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting message mapping: {e}")
            return False

    # ===== Text cleaning / formatting / translation / watermark =====
    def get_text_cleaning_settings(self, task_id: int):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM task_text_cleaning_settings WHERE task_id = %s', (task_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting text cleaning settings: {e}")
            return None

    def get_text_cleaning_keywords(self, task_id: int):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT keyword FROM task_text_cleaning_keywords WHERE task_id = %s ORDER BY keyword', (task_id,))
                return [r[0] for r in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting cleaning keywords: {e}")
            return []

    def get_text_formatting_settings(self, task_id: int):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM task_text_formatting_settings WHERE task_id = %s', (task_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting text formatting settings: {e}")
            return None

    def get_translation_settings(self, task_id: int):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM task_translation_settings WHERE task_id = %s', (task_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting translation settings: {e}")
            return None

    def get_watermark_settings(self, task_id: int):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM task_watermark_settings WHERE task_id = %s', (task_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting watermark settings: {e}")
            return None

    # ===== Audio settings =====
    def update_audio_metadata_enabled(self, task_id: int, enabled: bool) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO task_audio_metadata_settings (task_id, enabled)
                    VALUES (%s, %s)
                    ON CONFLICT (task_id) DO UPDATE SET enabled = EXCLUDED.enabled, updated_at = CURRENT_TIMESTAMP
                ''', (task_id, enabled))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating audio metadata enabled: {e}")
            return False

    def update_audio_metadata_setting(self, task_id: int, key: str, value) -> bool:
        try:
            allowed = {
                'preserve_quality': 'preserve_quality',
                'convert_to_mp3': 'convert_to_mp3',
                'album_art_enabled': 'album_art_enabled',
                'album_art_path': 'album_art_path',
                'audio_merge_enabled': 'audio_merge_enabled',
                'intro_audio_path': 'intro_audio_path',
                'outro_audio_path': 'outro_audio_path',
                'intro_position': 'intro_position'
            }
            if key not in allowed:
                return False
            column = allowed[key]
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    INSERT INTO task_audio_metadata_settings (task_id, {column})
                    VALUES (%s, %s)
                    ON CONFLICT (task_id) DO UPDATE SET {column} = EXCLUDED.{column}, updated_at = CURRENT_TIMESTAMP
                ''', (task_id, value))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating audio metadata setting: {e}")
            return False

    def update_audio_metadata_template(self, task_id: int, template_name: str) -> bool:
        try:
            return self.update_audio_metadata_setting(task_id, 'template', template_name)
        except Exception as e:
            logger.error(f"Error updating audio metadata template: {e}")
            return False

    def set_album_art_settings(self, task_id: int, **kwargs) -> bool:
        try:
            # supported: enabled(bool), path(str), apply_to_all(bool)
            mapping = {
                'enabled': 'album_art_enabled',
                'path': 'album_art_path',
                'apply_to_all': 'apply_art_to_all'
            }
            with self.get_connection() as conn:
                cursor = conn.cursor()
                for k, v in kwargs.items():
                    if k in mapping:
                        col = mapping[k]
                        cursor.execute(f'''
                            INSERT INTO task_audio_metadata_settings (task_id, {col})
                            VALUES (%s, %s)
                            ON CONFLICT (task_id) DO UPDATE SET {col} = EXCLUDED.{col}, updated_at = CURRENT_TIMESTAMP
                        ''', (task_id, v))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error setting album art settings: {e}")
            return False

    def set_audio_merge_settings(self, task_id: int, **kwargs) -> bool:
        try:
            mapping = {
                'enabled': 'audio_merge_enabled',
                'intro_path': 'intro_audio_path',
                'outro_path': 'outro_audio_path',
                'intro_position': 'intro_position'
            }
            with self.get_connection() as conn:
                cursor = conn.cursor()
                for k, v in kwargs.items():
                    if k in mapping:
                        col = mapping[k]
                        cursor.execute(f'''
                            INSERT INTO task_audio_metadata_settings (task_id, {col})
                            VALUES (%s, %s)
                            ON CONFLICT (task_id) DO UPDATE SET {col} = EXCLUDED.{col}, updated_at = CURRENT_TIMESTAMP
                        ''', (task_id, v))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error setting audio merge settings: {e}")
            return False

    # ===== Message settings helpers =====
    def update_inline_buttons_enabled(self, task_id: int, enabled: bool) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO task_message_settings (task_id, inline_buttons_enabled)
                    VALUES (%s, %s)
                    ON CONFLICT (task_id) DO UPDATE SET inline_buttons_enabled = EXCLUDED.inline_buttons_enabled, updated_at = CURRENT_TIMESTAMP
                ''', (task_id, enabled))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating inline buttons enabled: {e}")
            return False

    # ===== Rate limiting =====
    def check_rate_limit(self, task_id: int) -> bool:
        try:
            settings = self.get_rate_limit_settings(task_id)
            if not settings or not settings.get('enabled'):
                return False
            max_per_hour = settings.get('max_messages_per_hour', 100)
            max_per_day = settings.get('max_messages_per_day', 1000)
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT message_count, hour_count, day_count, last_reset_hour, last_reset_day FROM rate_limit_tracking WHERE task_id = %s', (task_id,))
                row = cursor.fetchone()
                from datetime import datetime, timedelta
                now = datetime.utcnow()
                if not row:
                    return False
                message_count, hour_count, day_count, last_reset_hour, last_reset_day = row
                # reset windows
                if last_reset_hour is None or (now - last_reset_hour).total_seconds() >= 3600:
                    hour_count = 0
                if last_reset_day is None or (now - last_reset_day).total_seconds() >= 86400:
                    day_count = 0
                return (hour_count >= max_per_hour) or (day_count >= max_per_day)
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return False

    def track_message_for_rate_limit(self, task_id: int) -> bool:
        try:
            from datetime import datetime
            now = datetime.utcnow()
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id, hour_count, day_count, last_reset_hour, last_reset_day FROM rate_limit_tracking WHERE task_id = %s', (task_id,))
                row = cursor.fetchone()
                if not row:
                    cursor.execute('''
                        INSERT INTO rate_limit_tracking (task_id, message_count, hour_count, day_count, last_reset_hour, last_reset_day)
                        VALUES (%s, 1, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ''', (task_id,))
                else:
                    cursor.execute('''
                        UPDATE rate_limit_tracking
                        SET message_count = COALESCE(message_count,0) + 1,
                            hour_count = COALESCE(hour_count,0) + 1,
                            day_count = COALESCE(day_count,0) + 1
                        WHERE task_id = %s
                    ''', (task_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error tracking rate limit: {e}")
            return False

    # ===== Advanced filters =====
    def get_advanced_filters_settings(self, task_id: int):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM task_advanced_filters WHERE task_id = %s', (task_id,))
                row = cursor.fetchone()
                return dict(row) if row else {
                    'day_filter_enabled': False,
                    'working_hours_enabled': False,
                    'language_filter_enabled': False,
                    'admin_filter_enabled': False,
                    'duplicate_filter_enabled': False,
                    'inline_button_filter_enabled': False,
                    'forwarded_message_filter_enabled': False
                }
        except Exception as e:
            logger.error(f"Error getting advanced filters: {e}")
            return {}

    def get_forwarded_message_filter_setting(self, task_id: int):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM task_forwarded_message_filters WHERE task_id = %s', (task_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting forwarded message filter: {e}")
            return None

    def get_inline_button_filter_setting(self, task_id: int):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM task_inline_button_filters WHERE task_id = %s', (task_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting inline button filter: {e}")
            return None

    def get_day_filters(self, task_id: int):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT day_of_week, is_active FROM task_day_filters WHERE task_id = %s ORDER BY day_of_week', (task_id,))
                return [{'day_number': r[0], 'is_allowed': bool(r[1])} for r in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting day filters: {e}")
            return []

    def set_day_filter(self, task_id: int, day_number: int, is_allowed: bool) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO task_day_filters (task_id, day_of_week, is_active)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (task_id, day_of_week) DO UPDATE SET is_active = EXCLUDED.is_active
                ''', (task_id, day_number, is_allowed))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error setting day filter: {e}")
            return False

    def get_working_hours(self, task_id: int):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM task_working_hours WHERE task_id = %s', (task_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting working hours: {e}")
            return None

    def initialize_working_hours_schedule(self, task_id: int) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # create task_working_hours if missing
                cursor.execute('''
                    INSERT INTO task_working_hours (task_id, is_enabled)
                    VALUES (%s, TRUE)
                    ON CONFLICT (task_id) DO NOTHING
                ''', (task_id,))
                # populate schedule 0..23 disabled by default
                for hour in range(24):
                    cursor.execute('''
                        INSERT INTO task_working_hours_schedule (working_hours_id, day_of_week, start_time, end_time, is_active)
                        SELECT id, 0, '00:00', '00:00', FALSE FROM task_working_hours WHERE task_id = %s
                        ON CONFLICT DO NOTHING
                    ''', (task_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error initializing working hours schedule: {e}")
            return False

    def set_all_working_hours(self, task_id: int, enabled: bool) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE task_working_hours SET is_enabled = %s, updated_at = CURRENT_TIMESTAMP WHERE task_id = %s', (enabled, task_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error setting all working hours: {e}")
            return False

    # ===== Duplicates =====
    def get_duplicate_settings(self, task_id: int):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM task_duplicate_settings WHERE task_id = %s', (task_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting duplicate settings: {e}")
            return None

    def update_duplicate_setting(self, task_id: int, key: str, value) -> bool:
        try:
            allowed = {'similarity_threshold', 'time_window_hours', 'check_text', 'check_media'}
            if key not in allowed:
                return False
            column = 'duplicate_window_hours' if key == 'time_window_hours' else key
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    INSERT INTO task_duplicate_settings (task_id, {column})
                    VALUES (%s, %s)
                    ON CONFLICT (task_id) DO UPDATE SET {column} = EXCLUDED.{column}
                ''', (task_id, value))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating duplicate setting: {e}")
            return False

    def get_recent_messages_for_duplicate_check(self, task_id: int, cutoff_time) -> list:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, source_message_id, message_text, message_hash, media_type, media_hash, forward_time
                    FROM forwarded_messages_log
                    WHERE task_id = %s AND forward_time >= %s
                    ORDER BY forward_time DESC
                ''', (task_id, cutoff_time))
                rows = cursor.fetchall()
                return [{'id': r[0], 'source_message_id': r[1], 'message_text': r[2], 'message_hash': r[3], 'media_type': r[4], 'media_hash': r[5], 'forward_time': r[6]} for r in rows]
        except Exception as e:
            logger.error(f"Error getting recent messages: {e}")
            return []

    def update_message_timestamp_for_duplicate(self, row_id: int, new_time) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE forwarded_messages_log SET forward_time = %s WHERE id = %s', (new_time, row_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating message timestamp: {e}")
            return False

    def store_message_for_duplicate_check(self, task_id: int, source_chat_id: str, source_message_id: int, message_text: str, message_hash: str, media_type: str, media_hash: str) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO forwarded_messages_log (task_id, source_chat_id, source_message_id, message_text, message_hash, media_type, media_hash, forward_time)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ''', (task_id, str(source_chat_id), source_message_id, message_text, message_hash, media_type, media_hash))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error storing forwarded message: {e}")
            return False

    # ===== Language filters =====
    def get_language_filters(self, task_id: int):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT language_code, language_name, is_active FROM task_language_filters WHERE task_id = %s ORDER BY language_code', (task_id,))
                return [{'language_code': r[0], 'language_name': r[1], 'is_active': bool(r[2])} for r in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting language filters: {e}")
            return []

    def add_language_filter(self, task_id: int, language_code: str, language_name: str, is_active: bool) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO task_language_filters (task_id, language_code, language_name, is_active)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (task_id, language_code) DO UPDATE SET language_name = EXCLUDED.language_name, is_active = EXCLUDED.is_active
                ''', (task_id, language_code, language_name, is_active))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error adding language filter: {e}")
            return False

    def remove_language_filter(self, task_id: int, language_code: str) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM task_language_filters WHERE task_id = %s AND language_code = %s', (task_id, language_code))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error removing language filter: {e}")
            return False

    def toggle_language_filter(self, task_id: int, language_code: str) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE task_language_filters SET is_active = NOT is_active WHERE task_id = %s AND language_code = %s', (task_id, language_code))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error toggling language filter: {e}")
            return False

    def clear_language_filters(self, task_id: int) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM task_language_filters WHERE task_id = %s', (task_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error clearing language filters: {e}")
            return False

    # ===== Pending messages =====
    def get_pending_message_by_source(self, task_id: int, user_id: int, source_chat_id: str, source_message_id: int):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, task_id, user_id, source_chat_id, source_message_id, message_data, message_type, approval_message_id, status, created_at
                    FROM pending_messages
                    WHERE task_id = %s AND user_id = %s AND source_chat_id = %s AND source_message_id = %s
                ''', (task_id, user_id, str(source_chat_id), source_message_id))
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0], 'task_id': row[1], 'user_id': row[2], 'source_chat_id': row[3],
                        'source_message_id': row[4], 'message_data': row[5], 'message_type': row[6],
                        'approval_message_id': row[7], 'status': row[8], 'created_at': row[9]
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting pending message: {e}")
            return None

    def add_pending_message(self, task_id: int, user_id: int, source_chat_id: str, source_message_id: int, message_data: str, message_type: str, approval_message_id: int = None) -> int:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO pending_messages (task_id, user_id, source_chat_id, source_message_id, message_data, message_type, approval_message_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                ''', (task_id, user_id, str(source_chat_id), source_message_id, message_data, message_type, approval_message_id))
                new_id = cursor.fetchone()[0]
                conn.commit()
                return new_id
        except Exception as e:
            logger.error(f"Error adding pending message: {e}")
            return None

    def update_pending_message_status(self, pending_id: int, status: str, approval_message_id: int = None) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if approval_message_id is not None:
                    cursor.execute('UPDATE pending_messages SET status = %s, approval_message_id = %s WHERE id = %s', (status, approval_message_id, pending_id))
                else:
                    cursor.execute('UPDATE pending_messages SET status = %s WHERE id = %s', (status, pending_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating pending message status: {e}")
            return False

    # ===== Task update helpers =====
    def update_task_forward_mode(self, task_id: int, user_id: int, forward_mode: str) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE tasks SET forward_mode = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s AND user_id = %s', (forward_mode, task_id, user_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating task forward mode: {e}")
            return False