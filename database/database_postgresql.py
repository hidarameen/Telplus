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
                    min_length INTEGER DEFAULT 0,
                    max_length INTEGER DEFAULT 4096,
                    use_range BOOLEAN DEFAULT FALSE,
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
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id)')
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
                cursor.execute("ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            except Exception:
                pass

            try:
                cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_user_channels_user_channel ON user_channels(user_id, channel_id)")
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
                    INSERT INTO user_sessions (user_id, phone_number, session_string, is_authenticated)
                    VALUES (%s, %s, %s, TRUE)
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
                    SELECT * FROM task_character_limit_settings WHERE task_id = %s
                ''', (task_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting character limit settings: {e}")
            return None

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