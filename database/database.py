"""
SQLite Database management for Telegram Bot System
"""
import sqlite3
import logging
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        """Initialize SQLite database connection"""
        self.db_path = 'telegram_bot.db'
        self.init_database()

    def get_connection(self):
        """Get SQLite database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Tasks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
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
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    chat_id TEXT NOT NULL,
                    chat_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # User sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    user_id INTEGER PRIMARY KEY,
                    phone_number TEXT,
                    session_string TEXT,
                    is_authenticated BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Conversation states table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversation_states (
                    user_id INTEGER PRIMARY KEY,
                    state TEXT,
                    data TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Task media filters table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_media_filters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    media_type TEXT NOT NULL,
                    is_allowed BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                    UNIQUE(task_id, media_type)
                )
            ''')

            # Task word filters table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_word_filters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    filter_type TEXT NOT NULL CHECK (filter_type IN ('whitelist', 'blacklist')),
                    is_enabled BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                    UNIQUE(task_id, filter_type)
                )
            ''')

            # Word filter entries table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS word_filter_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filter_id INTEGER NOT NULL,
                    word_or_phrase TEXT NOT NULL,
                    is_case_sensitive BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (filter_id) REFERENCES task_word_filters (id) ON DELETE CASCADE
                )
            ''')

            # Task text replacements table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_text_replacements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    is_enabled BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                    UNIQUE(task_id)
                )
            ''')

            # Text replacement entries table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS text_replacement_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    replacement_id INTEGER NOT NULL,
                    find_text TEXT NOT NULL,
                    replace_text TEXT NOT NULL,
                    is_case_sensitive BOOLEAN DEFAULT FALSE,
                    is_whole_word BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (replacement_id) REFERENCES task_text_replacements (id) ON DELETE CASCADE
                )
            ''')

            # Task headers table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_headers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    enabled BOOLEAN DEFAULT FALSE,
                    header_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                    UNIQUE(task_id)
                )
            ''')

            # Task footers table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_footers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    enabled BOOLEAN DEFAULT FALSE,
                    footer_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                    UNIQUE(task_id)
                )
            ''')

            # Task inline buttons table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_inline_buttons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    button_text TEXT NOT NULL,
                    button_url TEXT NOT NULL,
                    row_position INTEGER DEFAULT 0,
                    col_position INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Task message settings table - for controlling enabled/disabled status
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_message_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL UNIQUE,
                    header_enabled BOOLEAN DEFAULT FALSE,
                    header_text TEXT DEFAULT '',
                    footer_enabled BOOLEAN DEFAULT FALSE,
                    footer_text TEXT DEFAULT '',
                    inline_buttons_enabled BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Task forwarding settings table - for advanced forwarding options
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_forwarding_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL UNIQUE,
                    link_preview_enabled BOOLEAN DEFAULT TRUE,
                    pin_message_enabled BOOLEAN DEFAULT FALSE,
                    silent_notifications BOOLEAN DEFAULT FALSE,
                    auto_delete_enabled BOOLEAN DEFAULT FALSE,
                    auto_delete_time INTEGER DEFAULT 3600,
                    sync_edit_enabled BOOLEAN DEFAULT FALSE,
                    sync_delete_enabled BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Message mappings table - for tracking forwarded messages
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS message_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    source_chat_id TEXT NOT NULL,
                    source_message_id INTEGER NOT NULL,
                    target_chat_id TEXT NOT NULL,
                    target_message_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                    UNIQUE(task_id, source_chat_id, source_message_id, target_chat_id)
                )
            ''')

            # Advanced filters master table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_advanced_filters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL UNIQUE,
                    day_filter_enabled BOOLEAN DEFAULT FALSE,
                    working_hours_enabled BOOLEAN DEFAULT FALSE,
                    language_filter_enabled BOOLEAN DEFAULT FALSE,
                    admin_filter_enabled BOOLEAN DEFAULT FALSE,
                    duplicate_filter_enabled BOOLEAN DEFAULT FALSE,
                    inline_button_filter_enabled BOOLEAN DEFAULT FALSE,
                    forwarded_message_filter_enabled BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Day filters table - for specifying allowed/blocked days
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_day_filters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    day_number INTEGER NOT NULL CHECK (day_number >= 0 AND day_number <= 6),
                    is_allowed BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                    UNIQUE(task_id, day_number)
                )
            ''')

            # Working hours table - for time-based filtering
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_working_hours (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL UNIQUE,
                    start_hour INTEGER DEFAULT 0 CHECK (start_hour >= 0 AND start_hour <= 23),
                    start_minute INTEGER DEFAULT 0 CHECK (start_minute >= 0 AND start_minute <= 59),
                    end_hour INTEGER DEFAULT 23 CHECK (end_hour >= 0 AND end_hour <= 23),
                    end_minute INTEGER DEFAULT 59 CHECK (end_minute >= 0 AND end_minute <= 59),
                    timezone_offset INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Language filters table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_language_filters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    language_code TEXT NOT NULL,
                    language_name TEXT,
                    is_allowed BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                    UNIQUE(task_id, language_code)
                )
            ''')

            # Admin filters table - for filtering by admin users
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_admin_filters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    admin_user_id INTEGER NOT NULL,
                    admin_username TEXT,
                    admin_first_name TEXT,
                    is_allowed BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                    UNIQUE(task_id, admin_user_id)
                )
            ''')

            # Duplicate settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_duplicate_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL UNIQUE,
                    check_text_similarity BOOLEAN DEFAULT TRUE,
                    check_media_similarity BOOLEAN DEFAULT TRUE,
                    similarity_threshold REAL DEFAULT 0.85,
                    time_window_hours INTEGER DEFAULT 24,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Forwarded messages log - for duplicate detection
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS forwarded_messages_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    source_chat_id TEXT NOT NULL,
                    source_message_id INTEGER NOT NULL,
                    message_text TEXT,
                    message_hash TEXT,
                    media_type TEXT,
                    media_hash TEXT,
                    forwarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Create indexes for better performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_forwarded_messages_task_message_hash 
                ON forwarded_messages_log (task_id, message_hash)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_forwarded_messages_task_media_hash 
                ON forwarded_messages_log (task_id, media_hash)
            ''')

            # Inline button filter settings
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_inline_button_filters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL UNIQUE,
                    block_messages_with_buttons BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Forwarded message filter settings
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_forwarded_message_filters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL UNIQUE,
                    block_forwarded_messages BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Text cleaning settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_text_cleaning_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL UNIQUE,
                    remove_links BOOLEAN DEFAULT FALSE,
                    remove_emojis BOOLEAN DEFAULT FALSE,
                    remove_hashtags BOOLEAN DEFAULT FALSE,
                    remove_phone_numbers BOOLEAN DEFAULT FALSE,
                    remove_empty_lines BOOLEAN DEFAULT FALSE,
                    remove_lines_with_keywords BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Text cleaning keywords table (for removing lines containing specific words)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_text_cleaning_keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    keyword TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                    UNIQUE(task_id, keyword)
                )
            ''')

            # Text formatting settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_text_formatting_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL UNIQUE,
                    text_formatting_enabled BOOLEAN DEFAULT FALSE,
                    format_type TEXT DEFAULT 'regular' CHECK (format_type IN ('regular', 'bold', 'italic', 'underline', 'strikethrough', 'code', 'monospace', 'quote', 'spoiler', 'hyperlink')),
                    hyperlink_text TEXT,
                    hyperlink_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Add new columns for synchronization if they don't exist
            try:
                cursor.execute("ALTER TABLE task_forwarding_settings ADD COLUMN sync_edit_enabled BOOLEAN DEFAULT FALSE")
                logger.info("✅ تم إضافة عمود sync_edit_enabled")
            except Exception:
                pass  # Column already exists

            try:
                cursor.execute("ALTER TABLE task_forwarding_settings ADD COLUMN sync_delete_enabled BOOLEAN DEFAULT FALSE")
                logger.info("✅ تم إضافة عمود sync_delete_enabled")
            except Exception:
                pass  # Column already exists

            # Task character limit settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_character_limit_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    enabled BOOLEAN DEFAULT FALSE,
                    mode TEXT DEFAULT 'allow' CHECK (mode IN ('allow', 'block')),
                    min_chars INTEGER DEFAULT 0,
                    max_chars INTEGER DEFAULT 4000,
                    use_range BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                    UNIQUE(task_id)
                )
            ''')

            # Task message rate limit settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_rate_limit_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    enabled BOOLEAN DEFAULT FALSE,
                    message_count INTEGER DEFAULT 5,
                    time_period_seconds INTEGER DEFAULT 60,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                    UNIQUE(task_id)
                )
            ''')

            # Task forwarding delay settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_forwarding_delay_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    enabled BOOLEAN DEFAULT FALSE,
                    delay_seconds INTEGER DEFAULT 5,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                    UNIQUE(task_id)
                )
            ''')

            # Task sending interval settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_sending_interval_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    enabled BOOLEAN DEFAULT FALSE,
                    interval_seconds INTEGER DEFAULT 3,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                    UNIQUE(task_id)
                )
            ''')

            # Rate limit tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS rate_limit_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            conn.commit()
            logger.info("✅ تم تهيئة جداول SQLite بنجاح مع الفلاتر المتقدمة والميزات الجديدة")

    # User Session Management
    def save_user_session(self, user_id: int, phone_number: str, session_string: str):
        """Save user session"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO user_sessions 
                (user_id, phone_number, session_string, is_authenticated, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, phone_number, session_string, True))
            conn.commit()

    def get_user_session(self, user_id: int) -> Optional[Tuple[str, str, str]]:
        """Get user session"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT phone_number, session_string 
                FROM user_sessions 
                WHERE user_id = ? AND is_authenticated = TRUE
            ''', (user_id,))
            result = cursor.fetchone()
            if result:
                return (result['phone_number'], result['session_string'], result['session_string'])
            return None

    def is_user_authenticated(self, user_id: int) -> bool:
        """Check if user is authenticated"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 1 FROM user_sessions 
                WHERE user_id = ? AND is_authenticated = TRUE
            ''', (user_id,))
            return cursor.fetchone() is not None

    def delete_user_session(self, user_id: int):
        """Delete user session"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM user_sessions WHERE user_id = ?', (user_id,))
            conn.commit()

    def get_all_authenticated_users(self):
        """Get all authenticated users with their sessions"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, phone_number, session_string 
                FROM user_sessions 
                WHERE is_authenticated = TRUE AND session_string IS NOT NULL
            ''')
            return cursor.fetchall()

    # Task Management
    def create_task(self, user_id: int, source_chat_id: str, source_chat_name: str,
                   target_chat_id: str, target_chat_name: str) -> int:
        """Create new forwarding task - simplified version for single source/target"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO tasks 
                (user_id, source_chat_id, source_chat_name, target_chat_id, target_chat_name)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, source_chat_id, source_chat_name, target_chat_id, target_chat_name))

            task_id = cursor.lastrowid
            conn.commit()
            return task_id

    def create_task_with_multiple_sources_targets(self, user_id: int, task_name: str, 
                                                 source_chat_ids: list, source_chat_names: list,
                                                 target_chat_ids: list, target_chat_names: list) -> int:
        """Create new forwarding task with multiple sources and targets"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Create main task with the first source and target
            first_source_id = source_chat_ids[0] if source_chat_ids else ''
            first_source_name = source_chat_names[0] if source_chat_names else first_source_id
            first_target_id = target_chat_ids[0] if target_chat_ids else ''
            first_target_name = target_chat_names[0] if target_chat_names else first_target_id

            cursor.execute('''
                INSERT INTO tasks 
                (user_id, task_name, source_chat_id, source_chat_name, target_chat_id, target_chat_name)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, task_name, first_source_id, first_source_name, first_target_id, first_target_name))

            task_id = cursor.lastrowid

            # Add all sources to task_sources table
            for i, source_id in enumerate(source_chat_ids):
                source_name = source_chat_names[i] if source_chat_names and i < len(source_chat_names) else source_id
                cursor.execute('''
                    INSERT INTO task_sources (task_id, chat_id, chat_name)
                    VALUES (?, ?, ?)
                ''', (task_id, source_id, source_name))

            # Add all targets to task_targets table
            for i, target_id in enumerate(target_chat_ids):
                target_name = target_chat_names[i] if target_chat_names and i < len(target_chat_names) else target_id
                cursor.execute('''
                    INSERT INTO task_targets (task_id, chat_id, chat_name)
                    VALUES (?, ?, ?)
                ''', (task_id, target_id, target_name))

            conn.commit()
            return task_id

    def get_user_tasks(self, user_id: int):
        """Get all tasks for a user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, task_name, source_chat_id, source_chat_name, target_chat_id, 
                       target_chat_name, forward_mode, is_active, created_at
                FROM tasks 
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))

            tasks = []
            for row in cursor.fetchall():
                tasks.append({
                    'id': row['id'],
                    'task_name': row['task_name'],
                    'source_chat_id': row['source_chat_id'],
                    'source_chat_name': row['source_chat_name'],
                    'target_chat_id': row['target_chat_id'],
                    'target_chat_name': row['target_chat_name'],
                    'forward_mode': row['forward_mode'] or 'forward',
                    'is_active': bool(row['is_active']),
                    'created_at': str(row['created_at'])
                })
            return tasks

    def get_task(self, task_id: int, user_id: int = None) -> Optional[Dict]:
        """Get a specific task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute("""
                    SELECT id, task_name, source_chat_id, source_chat_name, target_chat_id, 
                           target_chat_name, forward_mode, is_active, created_at
                    FROM tasks 
                    WHERE id = ? AND user_id = ?
                """, (task_id, user_id))
            else:
                cursor.execute("""
                    SELECT id, task_name, source_chat_id, source_chat_name, target_chat_id, 
                           target_chat_name, forward_mode, is_active, created_at
                    FROM tasks 
                    WHERE id = ?
                """, (task_id,))

            row = cursor.fetchone()
            if row:
                return {
                    'id': row['id'],
                    'task_name': row['task_name'],
                    'source_chat_id': row['source_chat_id'],
                    'source_chat_name': row['source_chat_name'],
                    'target_chat_id': row['target_chat_id'],
                    'target_chat_name': row['target_chat_name'],
                    'forward_mode': row['forward_mode'] or 'forward',
                    'is_active': bool(row['is_active']),
                    'created_at': str(row['created_at'])
                }
            return None

    def update_task_status(self, task_id: int, user_id: int, is_active: bool):
        """Update task status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE tasks SET is_active = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
            ''', (is_active, task_id, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def delete_task(self, task_id: int, user_id: int):
        """Delete task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM tasks WHERE id = ? AND user_id = ?', 
                         (task_id, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_active_tasks(self, user_id: int) -> List[Dict]:
        """Get active tasks for user with all sources and targets"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, task_name, source_chat_id, source_chat_name, target_chat_id, target_chat_name, forward_mode
                FROM tasks 
                WHERE user_id = ? AND is_active = TRUE
            ''', (user_id,))

            tasks = []
            for row in cursor.fetchall():
                task_id = row['id']

                # Get all sources for this task
                sources = self.get_task_sources(task_id)
                if not sources:
                    # Fallback to legacy data
                    sources = [{
                        'id': 0,
                        'chat_id': row['source_chat_id'],
                        'chat_name': row['source_chat_name']
                    }] if row['source_chat_id'] else []

                # Get all targets for this task  
                targets = self.get_task_targets(task_id)
                if not targets:
                    # Fallback to legacy data
                    targets = [{
                        'id': 0,
                        'chat_id': row['target_chat_id'],
                        'chat_name': row['target_chat_name']
                    }] if row['target_chat_id'] else []

                # Create individual task entries for each source-target combination
                for source in sources:
                    for target in targets:
                        tasks.append({
                            'id': row['id'],
                            'task_name': row['task_name'],
                            'source_chat_id': source['chat_id'],
                            'source_chat_name': source['chat_name'],
                            'target_chat_id': target['chat_id'],
                            'target_chat_name': target['chat_name'],
                            'forward_mode': row['forward_mode'] or 'forward'
                        })
            return tasks

    def get_all_active_tasks(self):
        """Get all active tasks for userbot"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, task_name, source_chat_id, source_chat_name, target_chat_id, target_chat_name, forward_mode
                FROM tasks 
                WHERE is_active = TRUE
            """)

            tasks = []
            for row in cursor.fetchall():
                tasks.append({
                    'id': row['id'],
                    'task_name': row['task_name'],
                    'source_chat_id': row['source_chat_id'],
                    'source_chat_name': row['source_chat_name'],
                    'target_chat_id': row['target_chat_id'],
                    'target_chat_name': row['target_chat_name'],
                    'forward_mode': row['forward_mode'] or 'forward'
                })
            return tasks

    # Conversation State Management
    def set_conversation_state(self, user_id: int, state: str, data: str = ''):
        """Set conversation state for user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO conversation_states 
                (user_id, state, data, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, state, data))
            conn.commit()

    def get_conversation_state(self, user_id: int) -> Optional[Tuple[str, str]]:
        """Get conversation state for user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT state, data FROM conversation_states 
                WHERE user_id = ?
            ''', (user_id,))
            result = cursor.fetchone()
            if result:
                return (result['state'], result['data'])
            return None

    def clear_conversation_state(self, user_id: int):
        """Clear conversation state for user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM conversation_states WHERE user_id = ?', (user_id,))
            conn.commit()

    # Advanced Task Management Functions
    def update_task_forward_mode(self, task_id: int, user_id: int, forward_mode: str):
        """Update task forward mode (copy/forward)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE tasks SET forward_mode = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
            ''', (forward_mode, task_id, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def add_task_source(self, task_id: int, chat_id: str, chat_name: str = None):
        """Add source to task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO task_sources (task_id, chat_id, chat_name)
                VALUES (?, ?, ?)
            ''', (task_id, chat_id, chat_name))
            conn.commit()
            return cursor.lastrowid

    def add_task_target(self, task_id: int, chat_id: str, chat_name: str = None):
        """Add target to task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO task_targets (task_id, chat_id, chat_name)
                VALUES (?, ?, ?)
            ''', (task_id, chat_id, chat_name))
            conn.commit()
            return cursor.lastrowid

    def get_task_sources(self, task_id: int):
        """Get all sources for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, chat_id, chat_name FROM task_sources
                WHERE task_id = ?
                ORDER BY created_at
            ''', (task_id,))

            sources = []
            for row in cursor.fetchall():
                sources.append({
                    'id': row['id'],
                    'chat_id': row['chat_id'], 
                    'chat_name': row['chat_name']
                })
            return sources

    def get_task_targets(self, task_id: int):
        """Get all targets for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, chat_id, chat_name FROM task_targets
                WHERE task_id = ?
                ORDER BY created_at
            ''', (task_id,))

            targets = []
            for row in cursor.fetchall():
                targets.append({
                    'id': row['id'],
                    'chat_id': row['chat_id'],
                    'chat_name': row['chat_name']
                })
            return targets

    def remove_task_source(self, source_id: int, task_id: int):
        """Remove source from task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM task_sources 
                WHERE id = ? AND task_id = ?
            ''', (source_id, task_id))
            conn.commit()
            return cursor.rowcount > 0

    def remove_task_target(self, target_id: int, task_id: int):
        """Remove target from task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM task_targets 
                WHERE id = ? AND task_id = ?
            ''', (target_id, task_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_task_with_sources_targets(self, task_id: int, user_id: int = None):
        """Get task with all sources and targets"""
        task = self.get_task(task_id, user_id)
        if not task:
            return None

        # Get sources and targets from new tables
        sources = self.get_task_sources(task_id)
        targets = self.get_task_targets(task_id)

        # If no sources/targets in new tables, use legacy data
        if not sources and task.get('source_chat_id'):
            sources = [{
                'id': 0,
                'chat_id': task['source_chat_id'],
                'chat_name': task['source_chat_name']
            }]

        if not targets and task.get('target_chat_id'):
            targets = [{
                'id': 0,
                'chat_id': task['target_chat_id'],
                'chat_name': task['target_chat_name']
            }]

        task['sources'] = sources
        task['targets'] = targets

        return task

    def migrate_task_to_new_structure(self, task_id: int):
        """Migrate existing task to new structure"""
        task = self.get_task(task_id)
        if not task:
            logger.error(f"❌ لا يمكن العثور على المهمة {task_id} للتهجير")
            return False

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Check if already migrated
            cursor.execute('SELECT COUNT(*) FROM task_sources WHERE task_id = ?', (task_id,))
            sources_count = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM task_targets WHERE task_id = ?', (task_id,))
            targets_count = cursor.fetchone()[0]

            if sources_count > 0 and targets_count > 0:
                logger.info(f"✅ المهمة {task_id} مهاجرة بالفعل ({sources_count} مصادر, {targets_count} أهداف)")
                return True  # Already migrated

            logger.info(f"🔄 بدء تهجير المهمة {task_id} إلى البنية الجديدة")

            # Migrate source if not exists
            if sources_count == 0 and task.get('source_chat_id'):
                cursor.execute('''
                    INSERT INTO task_sources (task_id, chat_id, chat_name)
                    VALUES (?, ?, ?)
                ''', (task_id, task['source_chat_id'], task['source_chat_name']))
                logger.info(f"➕ أضيف مصدر: {task['source_chat_id']}")

            # Migrate target if not exists
            if targets_count == 0 and task.get('target_chat_id'):
                cursor.execute('''
                    INSERT INTO task_targets (task_id, chat_id, chat_name)
                    VALUES (?, ?, ?)
                ''', (task_id, task['target_chat_id'], task['target_chat_name']))
                logger.info(f"➕ أضيف هدف: {task['target_chat_id']}")

            conn.commit()
            logger.info(f"✅ تم تهجير المهمة {task_id} بنجاح")
            return True

    # Media Filters Management
    def get_task_media_filters(self, task_id: int):
        """Get media filters for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT media_type, is_allowed FROM task_media_filters
                WHERE task_id = ?
                ORDER BY media_type
            ''', (task_id,))

            filters = {}
            for row in cursor.fetchall():
                filters[row['media_type']] = bool(row['is_allowed'])

            # If no filters exist, return default (all allowed)
            if not filters:
                media_types = ['text', 'photo', 'video', 'audio', 'document', 'voice', 'video_note', 'sticker', 'animation', 'location', 'contact', 'poll']
                filters = {media_type: True for media_type in media_types}

            return filters

    def set_task_media_filter(self, task_id: int, media_type: str, is_allowed: bool):
        """Set media filter for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO task_media_filters 
                (task_id, media_type, is_allowed)
                VALUES (?, ?, ?)
            ''', (task_id, media_type, is_allowed))
            conn.commit()
            return cursor.rowcount > 0

    def set_all_media_filters(self, task_id: int, is_allowed: bool):
        """Set all media filters for a task (allow all or block all)"""
        media_types = ['text', 'photo', 'video', 'audio', 'document', 'voice', 'video_note', 'sticker', 'animation', 'location', 'contact', 'poll']

        with self.get_connection() as conn:
            cursor = conn.cursor()
            for media_type in media_types:
                cursor.execute('''
                    INSERT OR REPLACE INTO task_media_filters 
                    (task_id, media_type, is_allowed)
                    VALUES (?, ?, ?)
                ''', (task_id, media_type, is_allowed))
            conn.commit()
            return True

    def reset_task_media_filters(self, task_id: int):
        """Reset task media filters to default (all allowed)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM task_media_filters WHERE task_id = ?', (task_id,))
            conn.commit()
            return cursor.rowcount >= 0

    # Word Filters Management
    def get_task_word_filter_settings(self, task_id: int):
        """Get word filter settings for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT filter_type, is_enabled FROM task_word_filters
                WHERE task_id = ?
            ''', (task_id,))

            settings = {}
            for row in cursor.fetchall():
                settings[row['filter_type']] = {
                    'enabled': bool(row['is_enabled'])
                }

            # Set defaults if not exist
            if 'whitelist' not in settings:
                settings['whitelist'] = {'enabled': False}
            if 'blacklist' not in settings:
                settings['blacklist'] = {'enabled': False}

            return settings

    def set_word_filter_status(self, task_id: int, filter_type: str, is_enabled: bool):
        """Enable/disable word filter for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO task_word_filters 
                (task_id, filter_type, is_enabled, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (task_id, filter_type, is_enabled))
            conn.commit()
            return cursor.rowcount > 0

    def get_word_filter_id(self, task_id: int, filter_type: str):
        """Get word filter ID, create if doesn't exist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM task_word_filters
                WHERE task_id = ? AND filter_type = ?
            ''', (task_id, filter_type))

            result = cursor.fetchone()
            if result:
                return result['id']

            # Create new filter (enabled by default)
            cursor.execute('''
                INSERT INTO task_word_filters (task_id, filter_type, is_enabled)
                VALUES (?, ?, TRUE)
            ''', (task_id, filter_type))
            conn.commit()
            return cursor.lastrowid

    def add_word_to_filter(self, task_id: int, filter_type: str, word_or_phrase: str, is_case_sensitive: bool = False):
        """Add word/phrase to filter list"""
        filter_id = self.get_word_filter_id(task_id, filter_type)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Check if word already exists
            cursor.execute('''
                SELECT id FROM word_filter_entries
                WHERE filter_id = ? AND word_or_phrase = ?
            ''', (filter_id, word_or_phrase))

            if cursor.fetchone():
                return False  # Word already exists

            cursor.execute('''
                INSERT INTO word_filter_entries (filter_id, word_or_phrase, is_case_sensitive)
                VALUES (?, ?, ?)
            ''', (filter_id, word_or_phrase, is_case_sensitive))
            conn.commit()
            return cursor.lastrowid

    def remove_word_from_filter(self, task_id: int, filter_type: str, word_or_phrase: str):
        """Remove word/phrase from filter list"""
        filter_id = self.get_word_filter_id(task_id, filter_type)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM word_filter_entries
                WHERE filter_id = ? AND word_or_phrase = ?
            ''', (filter_id, word_or_phrase))
            conn.commit()
            return cursor.rowcount > 0

    def get_filter_words(self, task_id: int, filter_type: str):
        """Get all words/phrases for a filter - returns format compatible with bot functions"""
        filter_id = self.get_word_filter_id(task_id, filter_type)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, word_or_phrase, is_case_sensitive FROM word_filter_entries
                WHERE filter_id = ?
                ORDER BY word_or_phrase
            ''', (filter_id,))

            # Return tuples in format (id, filter_id, word_or_phrase, is_case_sensitive)
            # This includes case sensitivity info to avoid separate queries
            words = []
            for row in cursor.fetchall():
                words.append((row['id'], filter_id, row['word_or_phrase'], row['is_case_sensitive']))
            return words

    def get_word_id(self, task_id: int, filter_type: str, word: str):
        """Get word ID from filter"""
        filter_id = self.get_word_filter_id(task_id, filter_type)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM word_filter_entries
                WHERE filter_id = ? AND word_or_phrase = ?
            ''', (filter_id, word))

            result = cursor.fetchone()
            return result['id'] if result else None

    def is_word_filter_enabled(self, task_id: int, filter_type: str):
        """Check if word filter is enabled for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT is_enabled FROM task_word_filters
                WHERE task_id = ? AND filter_type = ?
            ''', (task_id, filter_type))

            result = cursor.fetchone()
            return bool(result['is_enabled']) if result else False

    def set_word_filter_enabled(self, task_id: int, filter_type: str, is_enabled: bool):
        """Enable/disable word filter for a task (alias for set_word_filter_status)"""
        return self.set_word_filter_status(task_id, filter_type, is_enabled)

    def get_word_by_id(self, word_id: int):
        """Get word by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT word_or_phrase FROM word_filter_entries
                WHERE id = ?
            ''', (word_id,))

            result = cursor.fetchone()
            return result['word_or_phrase'] if result else None

    def remove_word_from_filter_by_id(self, word_id: int):
        """Remove word from filter by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM word_filter_entries WHERE id = ?
            ''', (word_id,))
            conn.commit()
            return cursor.rowcount > 0

    def clear_filter_words(self, task_id: int, filter_type: str):
        """Clear all words from filter"""
        filter_id = self.get_word_filter_id(task_id, filter_type)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM word_filter_entries WHERE filter_id = ?', (filter_id,))
            conn.commit()
            return cursor.rowcount >= 0

    def is_message_allowed_by_word_filter(self, task_id: int, message_text: str):
        """Check if message is allowed by word filters"""
        if not message_text:
            return True  # No text to filter

        settings = self.get_task_word_filter_settings(task_id)

        # Check whitelist first (if enabled)
        if settings['whitelist']['enabled']:
            whitelist_words = self.get_filter_words(task_id, 'whitelist')
            if whitelist_words:  # If whitelist has words
                # Message must contain at least one whitelisted word/phrase
                message_lower = message_text.lower()
                found_match = False

                for word_data in whitelist_words:
                    word = word_data[2]  # word_or_phrase from tuple
                    is_case_sensitive = word_data[3]  # is_case_sensitive from tuple

                    if is_case_sensitive:
                        if word in message_text:
                            found_match = True
                            break
                    else:
                        if word.lower() in message_lower:
                            found_match = True
                            break

                if not found_match:
                    logger.info(f"🚫 الرسالة محظورة: لا تحتوي على كلمات من القائمة البيضاء")
                    return False

        # Check blacklist (if enabled)
        if settings['blacklist']['enabled']:
            blacklist_words = self.get_filter_words(task_id, 'blacklist')
            message_lower = message_text.lower()

            for word_data in blacklist_words:
                word = word_data[2]  # word_or_phrase from tuple
                is_case_sensitive = word_data[3]  # is_case_sensitive from tuple

                if is_case_sensitive:
                    if word in message_text:
                        logger.info(f"🚫 الرسالة محظورة: تحتوي على كلمة محظورة '{word}'")
                        return False
                else:
                    if word.lower() in message_lower:
                        logger.info(f"🚫 الرسالة محظورة: تحتوي على كلمة محظورة '{word}'")
                        return False

        return True  # Message is allowed

    def add_multiple_filter_words(self, task_id: int, filter_type: str, words_list: list):
        """Add multiple words to a filter"""
        filter_id = self.get_word_filter_id(task_id, filter_type)
        added_count = 0

        with self.get_connection() as conn:
            cursor = conn.cursor()
            for word in words_list:
                word = word.strip()
                if word:  # Only add non-empty words
                    # Check if word already exists
                    cursor.execute('''
                        SELECT id FROM word_filter_entries
                        WHERE filter_id = ? AND word_or_phrase = ?
                    ''', (filter_id, word))

                    if not cursor.fetchone():
                        cursor.execute('''
                            INSERT INTO word_filter_entries (filter_id, word_or_phrase, is_case_sensitive)
                            VALUES (?, ?, FALSE)
                        ''', (filter_id, word))
                        added_count += 1

            conn.commit()
            logger.info(f"✅ تم إضافة {added_count} كلمة إلى فلتر {filter_type} للمهمة {task_id}")
            return added_count

    # Text Replacement Management
    def get_text_replacement_id(self, task_id: int):
        """Get or create text replacement configuration for task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM task_text_replacements WHERE task_id = ?
            ''', (task_id,))

            result = cursor.fetchone()
            if result:
                return result['id']

            # Create new replacement configuration (enabled by default)
            cursor.execute('''
                INSERT INTO task_text_replacements (task_id, is_enabled)
                VALUES (?, TRUE)
            ''', (task_id,))
            conn.commit()
            return cursor.lastrowid

    def is_text_replacement_enabled(self, task_id: int):
        """Check if text replacement is enabled for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT is_enabled FROM task_text_replacements WHERE task_id = ?
            ''', (task_id,))

            result = cursor.fetchone()
            return bool(result['is_enabled']) if result else False

    def set_text_replacement_enabled(self, task_id: int, is_enabled: bool):
        """Enable/disable text replacement for a task"""
        replacement_id = self.get_text_replacement_id(task_id)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE task_text_replacements 
                SET is_enabled = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (is_enabled, replacement_id))
            conn.commit()
            return cursor.rowcount > 0

    def add_text_replacement(self, task_id: int, find_text: str, replace_text: str, 
                           is_case_sensitive: bool = False, is_whole_word: bool = False):
        """Add text replacement rule"""
        replacement_id = self.get_text_replacement_id(task_id)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO text_replacement_entries 
                (replacement_id, find_text, replace_text, is_case_sensitive, is_whole_word)
                VALUES (?, ?, ?, ?, ?)
            ''', (replacement_id, find_text, replace_text, is_case_sensitive, is_whole_word))
            conn.commit()
            return cursor.lastrowid

    def get_text_replacements(self, task_id: int):
        """Get all text replacements for a task"""
        replacement_id = self.get_text_replacement_id(task_id)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, find_text, replace_text, is_case_sensitive, is_whole_word
                FROM text_replacement_entries
                WHERE replacement_id = ?
                ORDER BY find_text
            ''', (replacement_id,))

            return cursor.fetchall()

    def remove_text_replacement(self, replacement_entry_id: int):
        """Remove text replacement rule by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM text_replacement_entries WHERE id = ?
            ''', (replacement_entry_id,))
            conn.commit()
            return cursor.rowcount > 0

    def clear_text_replacements(self, task_id: int):
        """Clear all text replacements for a task"""
        replacement_id = self.get_text_replacement_id(task_id)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM text_replacement_entries WHERE replacement_id = ?
            ''', (replacement_id,))
            conn.commit()
            return cursor.rowcount >= 0

    def add_multiple_text_replacements(self, task_id: int, replacements_list: list):
        """Add multiple text replacements at once
        replacements_list: List of tuples (find_text, replace_text, is_case_sensitive, is_whole_word)
        """
        replacement_id = self.get_text_replacement_id(task_id)
        added_count = 0

        with self.get_connection() as conn:
            cursor = conn.cursor()
            for replacement in replacements_list:
                if len(replacement) >= 2:
                    find_text = replacement[0].strip()
                    replace_text = replacement[1].strip()
                    is_case_sensitive = replacement[2] if len(replacement) > 2 else False
                    is_whole_word = replacement[3] if len(replacement) > 3 else False

                    if find_text:  # Only add non-empty find text
                        # Check if replacement already exists
                        cursor.execute('''
                            SELECT id FROM text_replacement_entries
                            WHERE replacement_id = ? AND find_text = ?
                        ''', (replacement_id, find_text))

                        if not cursor.fetchone():
                            cursor.execute('''
                                INSERT INTO text_replacement_entries 
                                (replacement_id, find_text, replace_text, is_case_sensitive, is_whole_word)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (replacement_id, find_text, replace_text, is_case_sensitive, is_whole_word))
                            added_count += 1

            conn.commit()
            logger.info(f"✅ تم إضافة {added_count} استبدال نصي للمهمة {task_id}")
            return added_count

    def apply_text_replacements(self, task_id: int, message_text: str):
        """Apply text replacements to message text"""
        if not message_text or not self.is_text_replacement_enabled(task_id):
            return message_text

        replacements = self.get_text_replacements(task_id)
        if not replacements:
            return message_text

        modified_text = message_text
        replacement_count = 0

        for replacement in replacements:
            find_text = replacement['find_text']
            replace_text = replacement['replace_text']
            is_case_sensitive = replacement['is_case_sensitive']
            is_whole_word = replacement['is_whole_word']

            if is_whole_word:
                # Use word boundary matching
                import re
                pattern = r'\b' + re.escape(find_text) + r'\b'
                flags = 0 if is_case_sensitive else re.IGNORECASE

                old_text = modified_text
                modified_text = re.sub(pattern, replace_text, modified_text, flags=flags)
                if old_text != modified_text:
                    replacement_count += 1
            else:
                # Simple text replacement
                if is_case_sensitive:
                    if find_text in modified_text:
                        modified_text = modified_text.replace(find_text, replace_text)
                        replacement_count += 1
                else:
                    # Case insensitive replacement
                    import re
                    pattern = re.escape(find_text)
                    old_text = modified_text
                    modified_text = re.sub(pattern, replace_text, modified_text, flags=re.IGNORECASE)
                    if old_text != modified_text:
                        replacement_count += 1

        if replacement_count > 0:
            logger.info(f"✅ تم تطبيق {replacement_count} استبدال على الرسالة للمهمة {task_id}")

        return modified_text

    def get_message_settings(self, task_id: int) -> dict:
        """Get message formatting settings for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Get header settings
                cursor.execute('''
                    SELECT enabled, header_text FROM task_headers 
                    WHERE task_id = ?
                ''', (task_id,))
                header_result = cursor.fetchone()

                # Get footer settings
                cursor.execute('''
                    SELECT enabled, footer_text FROM task_footers 
                    WHERE task_id = ?
                ''', (task_id,))
                footer_result = cursor.fetchone()

                # Get inline buttons enabled status from task_message_settings
                cursor.execute('''
                    SELECT inline_buttons_enabled FROM task_message_settings 
                    WHERE task_id = ?
                ''', (task_id,))
                settings_result = cursor.fetchone()

                if not settings_result:
                    # Create default settings if not exist
                    cursor.execute('''
                        INSERT INTO task_message_settings (task_id) VALUES (?)
                    ''', (task_id,))
                    conn.commit()
                    inline_buttons_enabled = False
                else:
                    inline_buttons_enabled = bool(settings_result['inline_buttons_enabled'])

                return {
                    'header_enabled': header_result['enabled'] if header_result else False,
                    'header_text': header_result['header_text'] if header_result else None,
                    'footer_enabled': footer_result['enabled'] if footer_result else False,
                    'footer_text': footer_result['footer_text'] if footer_result else None,
                    'inline_buttons_enabled': inline_buttons_enabled
                }
        except Exception as e:
            logger.error(f"خطأ في الحصول على إعدادات الرسالة: {e}")
            return {
                'header_enabled': False,
                'header_text': None,
                'footer_enabled': False,
                'footer_text': None,
                'inline_buttons_enabled': False
            }

    def update_header_settings(self, task_id: int, enabled: bool, header_text: str = None):
        """Update header settings for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Check if header exists
            cursor.execute('SELECT id FROM task_headers WHERE task_id = ?', (task_id,))
            existing = cursor.fetchone()

            if existing:
                # Update existing
                cursor.execute('''
                    UPDATE task_headers 
                    SET enabled = ?, header_text = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE task_id = ?
                ''', (enabled, header_text, task_id))
            else:
                # Create new
                cursor.execute('''
                    INSERT INTO task_headers (task_id, enabled, header_text)
                    VALUES (?, ?, ?)
                ''', (task_id, enabled, header_text))

            conn.commit()

    def update_footer_settings(self, task_id: int, enabled: bool, footer_text: str = None):
        """Update footer settings for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Check if footer exists
            cursor.execute('SELECT id FROM task_footers WHERE task_id = ?', (task_id,))
            existing = cursor.fetchone()

            if existing:
                # Update existing
                cursor.execute('''
                    UPDATE task_footers 
                    SET enabled = ?, footer_text = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE task_id = ?
                ''', (enabled, footer_text, task_id))
            else:
                # Create new
                cursor.execute('''
                    INSERT INTO task_footers (task_id, enabled, footer_text)
                    VALUES (?, ?, ?)
                ''', (task_id, enabled, footer_text))

            conn.commit()

    def update_inline_buttons_enabled(self, task_id: int, enabled: bool):
        """Update inline buttons enabled status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO task_message_settings 
                (task_id, header_enabled, header_text, footer_enabled, footer_text, inline_buttons_enabled)
                SELECT ?, 
                       COALESCE(header_enabled, FALSE),
                       COALESCE(header_text, ''),
                       COALESCE(footer_enabled, FALSE),
                       COALESCE(footer_text, ''),
                       ?
                FROM task_message_settings WHERE task_id = ?
                UNION SELECT ?, FALSE, '', FALSE, '', ? WHERE NOT EXISTS 
                (SELECT 1 FROM task_message_settings WHERE task_id = ?)
            ''', (task_id, enabled, task_id, task_id, enabled, task_id))
            conn.commit()

    def get_inline_buttons(self, task_id: int):
        """Get inline buttons for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, task_id, button_text, button_url, row_position, col_position
                FROM task_inline_buttons 
                WHERE task_id = ? 
                ORDER BY row_position, col_position
            ''', (task_id,))
            results = cursor.fetchall()

            return [{
                'id': row['id'],
                'task_id': row['task_id'],
                'button_text': row['button_text'],
                'button_url': row['button_url'],
                'row_position': row['row_position'],
                'col_position': row['col_position']
            } for row in results]

    def add_inline_button(self, task_id: int, button_text: str, button_url: str, row_pos: int = 0, col_pos: int = 0):
        """Add inline button"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO task_inline_buttons 
                (task_id, button_text, button_url, row_position, col_position)
                VALUES (?, ?, ?, ?, ?)
            ''', (task_id, button_text, button_url, row_pos, col_pos))

            # Auto-enable inline buttons when first button is added
            cursor.execute('''
                INSERT OR REPLACE INTO task_message_settings 
                (task_id, header_enabled, header_text, footer_enabled, footer_text, inline_buttons_enabled)
                SELECT ?, 
                       COALESCE(header_enabled, FALSE),
                       COALESCE(header_text, ''),
                       COALESCE(footer_enabled, FALSE),
                       COALESCE(footer_text, ''),
                       TRUE
                FROM task_message_settings WHERE task_id = ?
                UNION SELECT ?, FALSE, '', FALSE, '', TRUE WHERE NOT EXISTS 
                (SELECT 1 FROM task_message_settings WHERE task_id = ?)
            ''', (task_id, task_id, task_id, task_id))

            conn.commit()
            return cursor.lastrowid

    def clear_inline_buttons(self, task_id: int):
        """Clear all inline buttons for task and disable inline buttons"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM task_inline_buttons WHERE task_id = ?', (task_id,))
            deleted_count = cursor.rowcount

            # Disable inline buttons when all buttons are cleared
            if deleted_count > 0:
                cursor.execute('''
                    INSERT OR REPLACE INTO task_message_settings 
                    (task_id, header_enabled, header_text, footer_enabled, footer_text, inline_buttons_enabled)
                    SELECT ?, 
                           COALESCE(header_enabled, FALSE),
                           COALESCE(header_text, ''),
                           COALESCE(footer_enabled, FALSE),
                           COALESCE(footer_text, ''),
                           FALSE
                    FROM task_message_settings WHERE task_id = ?
                    UNION SELECT ?, FALSE, '', FALSE, '', FALSE WHERE NOT EXISTS 
                    (SELECT 1 FROM task_message_settings WHERE task_id = ?)
                ''', (task_id, task_id, task_id, task_id))

            conn.commit()
            return deleted_count

    # Forwarding Settings Management
    def get_forwarding_settings(self, task_id: int) -> dict:
        """Get forwarding settings for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT link_preview_enabled, pin_message_enabled, silent_notifications, 
                       auto_delete_enabled, auto_delete_time, sync_edit_enabled, sync_delete_enabled
                FROM task_forwarding_settings 
                WHERE task_id = ?
            ''', (task_id,))
            result = cursor.fetchone()

            if result:
                return {
                    'link_preview_enabled': result['link_preview_enabled'],
                    'pin_message_enabled': result['pin_message_enabled'],
                    'silent_notifications': result['silent_notifications'],
                    'auto_delete_enabled': result['auto_delete_enabled'],
                    'auto_delete_time': result['auto_delete_time'],
                    'sync_edit_enabled': result['sync_edit_enabled'],
                    'sync_delete_enabled': result['sync_delete_enabled']
                }
            else:
                # Return default settings
                return {
                    'link_preview_enabled': True,
                    'pin_message_enabled': False,
                    'silent_notifications': False,
                    'auto_delete_enabled': False,
                    'auto_delete_time': 3600,
                    'sync_edit_enabled': False,
                    'sync_delete_enabled': False
                }

    def update_forwarding_settings(self, task_id: int, **kwargs):
        """Update forwarding settings for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get current settings
            current_settings = self.get_forwarding_settings(task_id)

            # Update with new values
            current_settings.update(kwargs)

            cursor.execute('''
                INSERT OR REPLACE INTO task_forwarding_settings 
                (task_id, link_preview_enabled, pin_message_enabled, silent_notifications, 
                 auto_delete_enabled, auto_delete_time, sync_edit_enabled, sync_delete_enabled, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (task_id, current_settings['link_preview_enabled'], 
                  current_settings['pin_message_enabled'], current_settings['silent_notifications'],
                  current_settings['auto_delete_enabled'], current_settings['auto_delete_time'],
                  current_settings['sync_edit_enabled'], current_settings['sync_delete_enabled']))

            conn.commit()

    def toggle_link_preview(self, task_id: int) -> bool:
        """Toggle link preview setting"""
        current_settings = self.get_forwarding_settings(task_id)
        new_state = not current_settings['link_preview_enabled']
        self.update_forwarding_settings(task_id, link_preview_enabled=new_state)
        return new_state

    def toggle_pin_message(self, task_id: int) -> bool:
        """Toggle pin message setting"""
        current_settings = self.get_forwarding_settings(task_id)
        new_state = not current_settings['pin_message_enabled']
        self.update_forwarding_settings(task_id, pin_message_enabled=new_state)
        return new_state

    def toggle_silent_notifications(self, task_id: int) -> bool:
        """Toggle silent notifications setting"""
        current_settings = self.get_forwarding_settings(task_id)
        new_state = not current_settings['silent_notifications']
        self.update_forwarding_settings(task_id, silent_notifications=new_state)
        return new_state

    def toggle_auto_delete(self, task_id: int) -> bool:
        """Toggle auto delete setting"""
        current_settings = self.get_forwarding_settings(task_id)
        new_state = not current_settings['auto_delete_enabled']
        self.update_forwarding_settings(task_id, auto_delete_enabled=new_state)
        return new_state

    def toggle_sync_edit(self, task_id: int) -> bool:
        """Toggle sync edit setting"""
        current_settings = self.get_forwarding_settings(task_id)
        new_state = not current_settings['sync_edit_enabled']
        self.update_forwarding_settings(task_id, sync_edit_enabled=new_state)
        return new_state

    def toggle_sync_delete(self, task_id: int) -> bool:
        """Toggle sync delete setting"""
        current_settings = self.get_forwarding_settings(task_id)
        new_state = not current_settings['sync_delete_enabled']
        self.update_forwarding_settings(task_id, sync_delete_enabled=new_state)
        return new_state

    def set_auto_delete_time(self, task_id: int, seconds: int):
        """Set auto delete time in seconds"""
        self.update_forwarding_settings(task_id, auto_delete_time=seconds)

    # Message Mapping Methods for Synchronization
    def save_message_mapping(self, task_id: int, source_chat_id: str, source_message_id: int, target_chat_id: str, target_message_id: int):
        """Save message mapping for synchronization"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO message_mappings 
                (task_id, source_chat_id, source_message_id, target_chat_id, target_message_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (task_id, source_chat_id, source_message_id, target_chat_id, target_message_id))
            conn.commit()

    def get_message_mappings_by_source(self, task_id: int, source_chat_id: str, source_message_id: int) -> List[Dict]:
        """Get all target message mappings for a source message"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, target_chat_id, target_message_id 
                FROM message_mappings 
                WHERE task_id = ? AND source_chat_id = ? AND source_message_id = ?
            ''', (task_id, source_chat_id, source_message_id))
            results = cursor.fetchall()
            return [{
                'id': row['id'],
                'target_chat_id': row['target_chat_id'],
                'target_message_id': row['target_message_id']
            } for row in results]

    def delete_message_mapping(self, mapping_id: int):
        """Delete a message mapping"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM message_mappings WHERE id = ?', (mapping_id,))
            conn.commit()

    # ===== Advanced Filters Management =====

    def get_advanced_filters_settings(self, task_id: int) -> Dict:
        """Get advanced filters settings for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM task_advanced_filters WHERE task_id = ?
            ''', (task_id,))
            result = cursor.fetchone()

            if result:
                return {
                    'day_filter_enabled': bool(result['day_filter_enabled']),
                    'working_hours_enabled': bool(result['working_hours_enabled']),
                    'language_filter_enabled': bool(result['language_filter_enabled']),
                    'admin_filter_enabled': bool(result['admin_filter_enabled']),
                    'duplicate_filter_enabled': bool(result['duplicate_filter_enabled']),
                    'inline_button_filter_enabled': bool(result['inline_button_filter_enabled']),
                    'forwarded_message_filter_enabled': bool(result['forwarded_message_filter_enabled'])
                }
            else:
                # Create default settings
                self.create_default_advanced_filters_settings(task_id)
                return {
                    'day_filter_enabled': False,
                    'working_hours_enabled': False,
                    'language_filter_enabled': False,
                    'admin_filter_enabled': False,
                    'duplicate_filter_enabled': False,
                    'inline_button_filter_enabled': False,
                    'forwarded_message_filter_enabled': False
                }

    def create_default_advanced_filters_settings(self, task_id: int):
        """Create default advanced filters settings for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO task_advanced_filters (task_id)
                VALUES (?)
            ''', (task_id,))
            conn.commit()

    def update_advanced_filter_setting(self, task_id: int, filter_type: str, enabled: bool):
        """Update a specific advanced filter setting"""
        valid_filters = {
            'day_filter': 'day_filter_enabled',
            'working_hours': 'working_hours_enabled', 
            'language_filter': 'language_filter_enabled',
            'admin_filter': 'admin_filter_enabled',
            'duplicate_filter': 'duplicate_filter_enabled',
            'inline_button_filter': 'inline_button_filter_enabled',
            'forwarded_message_filter': 'forwarded_message_filter_enabled',
            # Additional variations for consistency
            'day': 'day_filter_enabled',
            'admin': 'admin_filter_enabled',
            'language': 'language_filter_enabled',
            'duplicate': 'duplicate_filter_enabled',
            'inline_button': 'inline_button_filter_enabled',
            'forwarded_message': 'forwarded_message_filter_enabled'
        }

        if filter_type not in valid_filters:
            logger.error(f"نوع فلتر غير صالح: {filter_type}. الأنواع المتاحة: {list(valid_filters.keys())}")
            return False

        column_name = valid_filters[filter_type]

        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Create record if doesn't exist
            cursor.execute('''
                INSERT OR IGNORE INTO task_advanced_filters (task_id)
                VALUES (?)
            ''', (task_id,))

            # Update the specific filter
            cursor.execute(f'''
                UPDATE task_advanced_filters 
                SET {column_name} = ?, updated_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
            ''', (enabled, task_id))

            conn.commit()
            return cursor.rowcount > 0

    # ===== Day Filters Management =====

    def get_day_filters(self, task_id: int) -> List[Dict]:
        """Get day filters for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT day_number, is_allowed FROM task_day_filters
                WHERE task_id = ?
                ORDER BY day_number
            ''', (task_id,))

            # Create a dict for all days (0=Monday to 6=Sunday)
            day_names = ['الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد']
            day_filters = {}

            # Get existing filters
            for row in cursor.fetchall():
                day_filters[row['day_number']] = bool(row['is_allowed'])

            # Fill in missing days with default (allowed)
            result = []
            for day_num in range(7):
                result.append({
                    'day_number': day_num,
                    'day_name': day_names[day_num],
                    'is_allowed': day_filters.get(day_num, True)
                })

            return result

    def set_day_filter(self, task_id: int, day_number: int, is_allowed: bool):
        """Set day filter for a specific day"""
        if day_number < 0 or day_number > 6:
            logger.error(f"رقم يوم غير صالح: {day_number}")
            return False

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO task_day_filters 
                (task_id, day_number, is_allowed)
                VALUES (?, ?, ?)
            ''', (task_id, day_number, is_allowed))
            conn.commit()
            return True

    def set_all_day_filters(self, task_id: int, is_allowed: bool):
        """Set all day filters (select all/none)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for day_num in range(7):
                cursor.execute('''
                    INSERT OR REPLACE INTO task_day_filters 
                    (task_id, day_number, is_allowed)
                    VALUES (?, ?, ?)
                ''', (task_id, day_num, is_allowed))
            conn.commit()
            return True

    # ===== Working Hours Management =====

    def get_working_hours(self, task_id: int) -> Optional[Dict]:
        """Get working hours for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT start_hour, start_minute, end_hour, end_minute, timezone_offset
                FROM task_working_hours WHERE task_id = ?
            ''', (task_id,))
            result = cursor.fetchone()

            if result:
                return {
                    'start_hour': result['start_hour'],
                    'start_minute': result['start_minute'], 
                    'end_hour': result['end_hour'],
                    'end_minute': result['end_minute'],
                    'timezone_offset': result['timezone_offset']
                }
            return None

    def set_working_hours(self, task_id: int, start_hour: int, start_minute: int, 
                         end_hour: int, end_minute: int, timezone_offset: int = 0):
        """Set working hours for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO task_working_hours 
                (task_id, start_hour, start_minute, end_hour, end_minute, timezone_offset)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (task_id, start_hour, start_minute, end_hour, end_minute, timezone_offset))
            conn.commit()
            return True

    # ===== Language Filters Management =====

    def get_language_filters(self, task_id: int) -> List[Dict]:
        """Get language filters for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT language_code, language_name, is_allowed
                FROM task_language_filters WHERE task_id = ?
                ORDER BY language_name
            ''', (task_id,))

            filters = []
            for row in cursor.fetchall():
                filters.append({
                    'language_code': row['language_code'],
                    'language_name': row['language_name'],
                    'is_allowed': bool(row['is_allowed'])
                })
            return filters

    def add_language_filter(self, task_id: int, language_code: str, language_name: str, is_allowed: bool = True):
        """Add language filter"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO task_language_filters 
                (task_id, language_code, language_name, is_allowed)
                VALUES (?, ?, ?, ?)
            ''', (task_id, language_code, language_name, is_allowed))
            conn.commit()
            return True

    def toggle_language_filter(self, task_id: int, language_code: str):
        """Toggle language filter status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE task_language_filters 
                SET is_allowed = NOT is_allowed
                WHERE task_id = ? AND language_code = ?
            ''', (task_id, language_code))
            conn.commit()
            return cursor.rowcount > 0

    def remove_language_filter(self, task_id: int, language_code: str):
        """Remove language filter"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM task_language_filters 
                WHERE task_id = ? AND language_code = ?
            ''', (task_id, language_code))
            conn.commit()
            return cursor.rowcount > 0

    # ===== Admin Filters Management =====

    def get_admin_filters(self, task_id: int) -> List[Dict]:
        """Get admin filters for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT admin_user_id, admin_username, admin_first_name, is_allowed
                FROM task_admin_filters WHERE task_id = ?
                ORDER BY admin_first_name, admin_username
            ''', (task_id,))

            filters = []
            for row in cursor.fetchall():
                filters.append({
                    'admin_user_id': row['admin_user_id'],
                    'admin_username': row['admin_username'],
                    'admin_first_name': row['admin_first_name'],
                    'is_allowed': bool(row['is_allowed'])
                })
            return filters

    def add_admin_filter(self, task_id: int, admin_user_id: int, admin_username: str = None, 
                        admin_first_name: str = None, is_allowed: bool = True):
        """Add admin filter"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO task_admin_filters 
                (task_id, admin_user_id, admin_username, admin_first_name, is_allowed)
                VALUES (?, ?, ?, ?, ?)
            ''', (task_id, admin_user_id, admin_username, admin_first_name, is_allowed))
            conn.commit()
            return True

    def toggle_admin_filter(self, task_id: int, admin_user_id: int):
        """Toggle admin filter status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE task_admin_filters 
                SET is_allowed = NOT is_allowed, updated_at = CURRENT_TIMESTAMP
                WHERE task_id = ? AND admin_user_id = ?
            ''', (task_id, admin_user_id))
            conn.commit()
            return cursor.rowcount > 0

    def remove_admin_filter(self, task_id: int, admin_user_id: int):
        """Remove admin filter"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM task_admin_filters 
                WHERE task_id = ? AND admin_user_id = ?
            ''', (task_id, admin_user_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_admin_filters_for_source(self, task_id: int, source_chat_id: str) -> List[Dict]:
        """Get admin filters for a specific source channel"""
        # For now, return all admin filters for the task since we don't track source-specific admins yet
        # In the future, we can enhance the schema to track which source each admin belongs to
        return self.get_admin_filters(task_id)

    def clear_admin_filters_for_source(self, task_id: int, source_chat_id: str):
        """Clear admin filters for a specific source (for now clears all for the task)"""
        # For now, we'll clear all admins for the task when refreshing any source
        # In the future, we can enhance to track source-specific admins
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM task_admin_filters WHERE task_id = ?
            ''', (task_id,))
            conn.commit()
            return cursor.rowcount

    def get_admin_previous_permissions(self, task_id: int) -> Dict[int, bool]:
        """Get previous admin permissions before refresh"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT admin_user_id, is_allowed FROM task_admin_filters WHERE task_id = ?
            ''', (task_id,))

            permissions = {}
            for row in cursor.fetchall():
                permissions[row['admin_user_id']] = bool(row['is_allowed'])
            return permissions

    def add_admin_filter_with_previous_permission(self, task_id: int, admin_user_id: int, 
                                                 admin_username: str = None, admin_first_name: str = None, 
                                                 previous_permissions: Dict[int, bool] = None):
        """Add admin filter while preserving previous permissions if they exist"""
        # Check if this admin had previous permissions
        if previous_permissions and admin_user_id in previous_permissions:
            is_allowed = previous_permissions[admin_user_id]
            logger.info(f"🔄 الحفاظ على إذن سابق للمشرف {admin_user_id}: {is_allowed}")
        else:
            is_allowed = True  # Default for new admins
            logger.info(f"✅ مشرف جديد {admin_user_id}: إذن افتراضي = True")

        return self.add_admin_filter(task_id, admin_user_id, admin_username, admin_first_name, is_allowed)

    def is_advanced_filter_enabled(self, task_id: int, filter_type: str) -> bool:
        """Check if an advanced filter is enabled for a task"""
        try:
            settings = self.get_advanced_filters_settings(task_id)

            filter_mapping = {
                'admin': 'admin_filter_enabled',
                'admin_filter': 'admin_filter_enabled',
                'day': 'day_filter_enabled',
                'day_filter': 'day_filter_enabled',
                'working_hours': 'working_hours_enabled',
                'language': 'language_filter_enabled',
                'language_filter': 'language_filter_enabled',
                'duplicate': 'duplicate_filter_enabled',
                'duplicate_filter': 'duplicate_filter_enabled',
                'inline_button': 'inline_button_filter_enabled',
                'inline_button_filter': 'inline_button_filter_enabled',
                'forwarded_message': 'forwarded_message_filter_enabled',
                'forwarded_message_filter': 'forwarded_message_filter_enabled'
            }

            setting_key = filter_mapping.get(filter_type.lower())
            if setting_key:
                return settings.get(setting_key, False)
            else:
                logger.error(f"نوع فلتر غير معروف: {filter_type}")
                return False
        except Exception as e:
            logger.error(f"خطأ في فحص حالة الفلتر المتقدم: {e}")
            return False

    def get_task_allowed_admins(self, task_id: int) -> List[int]:
        """Get list of allowed admin user IDs for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT admin_user_id FROM task_admin_filters 
                    WHERE task_id = ? AND is_allowed = TRUE
                ''', (task_id,))

                allowed_admins = [row['admin_user_id'] for row in cursor.fetchall()]
                logger.info(f"المشرفين المسموحين للمهمة {task_id}: {allowed_admins}")
                return allowed_admins
        except Exception as e:
            logger.error(f"خطأ في جلب المشرفين المسموحين للمهمة {task_id}: {e}")
            return []

    def is_admin_allowed(self, task_id: int, user_id: int) -> bool:
        """Check if a user is allowed by admin filters for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT is_allowed FROM task_admin_filters 
                    WHERE task_id = ? AND admin_user_id = ?
                ''', (task_id, user_id))

                result = cursor.fetchone()
                if result:
                    is_allowed = bool(result['is_allowed'])
                    logger.info(f"فحص المشرف {user_id} للمهمة {task_id}: مسموح={is_allowed}")
                    return is_allowed
                else:
                    logger.info(f"المشرف {user_id} غير موجود في قائمة المهمة {task_id} - غير مسموح")
                    return False
        except Exception as e:
            logger.error(f"خطأ في فحص إذن المشرف {user_id} للمهمة {task_id}: {e}")
            return False

    # ===== Text Cleaning Management =====

    def get_text_cleaning_settings(self, task_id: int) -> Dict:
        """Get text cleaning settings for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT remove_links, remove_emojis, remove_hashtags, remove_phone_numbers,
                       remove_empty_lines, remove_lines_with_keywords
                FROM task_text_cleaning_settings WHERE task_id = ?
            ''', (task_id,))
            result = cursor.fetchone()

            if result:
                return {
                    'remove_links': bool(result['remove_links']),
                    'remove_emojis': bool(result['remove_emojis']),
                    'remove_hashtags': bool(result['remove_hashtags']),
                    'remove_phone_numbers': bool(result['remove_phone_numbers']),
                    'remove_empty_lines': bool(result['remove_empty_lines']),
                    'remove_lines_with_keywords': bool(result['remove_lines_with_keywords'])
                }
            else:
                # Create default settings
                self.create_default_text_cleaning_settings(task_id)
                return {
                    'remove_links': False,
                    'remove_emojis': False,
                    'remove_hashtags': False,
                    'remove_phone_numbers': False,
                    'remove_empty_lines': False,
                    'remove_lines_with_keywords': False
                }

    def create_default_text_cleaning_settings(self, task_id: int):
        """Create default text cleaning settings for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO task_text_cleaning_settings (task_id)
                VALUES (?)
            ''', (task_id,))
            conn.commit()

    def update_text_cleaning_setting(self, task_id: int, setting_type: str, enabled: bool):
        """Update a specific text cleaning setting"""
        valid_settings = {
            'remove_links': 'remove_links',
            'remove_emojis': 'remove_emojis',
            'remove_hashtags': 'remove_hashtags',
            'remove_phone_numbers': 'remove_phone_numbers',
            'remove_empty_lines': 'remove_empty_lines',
            'remove_lines_with_keywords': 'remove_lines_with_keywords'
        }

        if setting_type not in valid_settings:
            logger.error(f"نوع إعداد تنظيف النص غير صالح: {setting_type}")
            return False

        column_name = valid_settings[setting_type]

        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Create record if doesn't exist
            cursor.execute('''
                INSERT OR IGNORE INTO task_text_cleaning_settings (task_id)
                VALUES (?)
            ''', (task_id,))

            # Update the specific setting
            cursor.execute(f'''
                UPDATE task_text_cleaning_settings 
                SET {column_name} = ?, updated_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
            ''', (enabled, task_id))

            conn.commit()
            return cursor.rowcount > 0

    def get_text_cleaning_keywords(self, task_id: int) -> List[str]:
        """Get text cleaning keywords for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT keyword FROM task_text_cleaning_keywords 
                WHERE task_id = ? ORDER BY keyword
            ''', (task_id,))

            return [row['keyword'] for row in cursor.fetchall()]

    def add_text_cleaning_keyword(self, task_id: int, keyword: str):
        """Add a text cleaning keyword"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO task_text_cleaning_keywords (task_id, keyword)
                VALUES (?, ?)
            ''', (task_id, keyword.strip()))
            conn.commit()
            return cursor.rowcount > 0

    def remove_text_cleaning_keyword(self, task_id: int, keyword: str):
        """Remove a text cleaning keyword"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM task_text_cleaning_keywords 
                WHERE task_id = ? AND keyword = ?
            ''', (task_id, keyword))
            conn.commit()
            return cursor.rowcount > 0

    def clear_text_cleaning_keywords(self, task_id: int):
        """Clear all text cleaning keywords for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM task_text_cleaning_keywords WHERE task_id = ?
            ''', (task_id,))
            conn.commit()
            return cursor.rowcount

    def add_multiple_text_cleaning_keywords(self, task_id: int, keywords: List[str]) -> int:
        """Add multiple text cleaning keywords"""
        added_count = 0
        for keyword in keywords:
            keyword = keyword.strip()
            if keyword and self.add_text_cleaning_keyword(task_id, keyword):
                added_count += 1
        return added_count

    # ===== Duplicate Detection Management =====

    def get_duplicate_settings(self, task_id: int) -> Dict:
        """Get duplicate detection settings"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT check_text_similarity, check_media_similarity, 
                       similarity_threshold, time_window_hours
                FROM task_duplicate_settings WHERE task_id = ?
            ''', (task_id,))
            result = cursor.fetchone()

            if result:
                return {
                    'check_text_similarity': bool(result['check_text_similarity']),
                    'check_media_similarity': bool(result['check_media_similarity']),
                    'similarity_threshold': float(result['similarity_threshold']),
                    'time_window_hours': int(result['time_window_hours'])
                }
            else:
                # Create default settings
                self.create_default_duplicate_settings(task_id)
                return {
                    'check_text_similarity': True,
                    'check_media_similarity': True,
                    'similarity_threshold': 0.85,
                    'time_window_hours': 24
                }

    def create_default_duplicate_settings(self, task_id: int):
        """Create default duplicate detection settings"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO task_duplicate_settings (task_id)
                VALUES (?)
            ''', (task_id,))
            conn.commit()

    def update_duplicate_settings(self, task_id: int, check_text: bool = True, 
                                 check_media: bool = True, threshold: float = 0.85, 
                                 time_window: int = 24):
        """Update duplicate detection settings"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO task_duplicate_settings 
                (task_id, check_text_similarity, check_media_similarity, similarity_threshold, time_window_hours)
                VALUES (?, ?, ?, ?, ?)
            ''', (task_id, check_text, check_media, threshold, time_window))
            conn.commit()
            return True

    def log_forwarded_message(self, task_id: int, source_chat_id: str, source_message_id: int,
                             message_text: str = None, message_hash: str = None, 
                             media_type: str = None, media_hash: str = None):
        """Log forwarded message for duplicate detection"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO forwarded_messages_log 
                (task_id, source_chat_id, source_message_id, message_text, message_hash, media_type, media_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (task_id, source_chat_id, source_message_id, message_text, message_hash, media_type, media_hash))
            conn.commit()
            return cursor.lastrowid

    def check_duplicate_message(self, task_id: int, message_hash: str = None, media_hash: str = None,
                               time_window_hours: int = 24) -> bool:
        """Check if message is duplicate within time window"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Check for duplicates within time window
            if message_hash:
                cursor.execute('''
                    SELECT COUNT(*) as count FROM forwarded_messages_log
                    WHERE task_id = ? AND message_hash = ?
                    AND datetime(forwarded_at) > datetime('now', '-{} hours')
                '''.format(time_window_hours), (task_id, message_hash))

                if cursor.fetchone()['count'] > 0:
                    return True

            if media_hash:
                cursor.execute('''
                    SELECT COUNT(*) as count FROM forwarded_messages_log
                    WHERE task_id = ? AND media_hash = ?
                    AND datetime(forwarded_at) > datetime('now', '-{} hours')
                '''.format(time_window_hours), (task_id, media_hash))

                if cursor.fetchone()['count'] > 0:
                    return True

            return False

    # ===== Inline Button and Forwarded Message Filters =====

    def get_inline_button_filter_setting(self, task_id: int) -> bool:
        """Get inline button filter setting"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT block_messages_with_buttons FROM task_inline_button_filters 
                WHERE task_id = ?
            ''', (task_id,))
            result = cursor.fetchone()
            return bool(result['block_messages_with_buttons']) if result else False

    def set_inline_button_filter(self, task_id: int, block_buttons: bool):
        """Set inline button filter"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO task_inline_button_filters 
                (task_id, block_messages_with_buttons)
                VALUES (?, ?)
            ''', (task_id, block_buttons))
            conn.commit()
            return True

    def get_forwarded_message_filter_setting(self, task_id: int) -> bool:
        """Get forwarded message filter setting"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT block_forwarded_messages FROM task_forwarded_message_filters 
                WHERE task_id = ?
            ''', (task_id,))
            result = cursor.fetchone()
            return bool(result['block_forwarded_messages']) if result else False

    def set_forwarded_message_filter(self, task_id: int, block_forwarded: bool):
        """Set forwarded message filter"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO task_forwarded_message_filters 
                (task_id, block_forwarded_messages)
                VALUES (?, ?)
            ''', (task_id, block_forwarded))
            conn.commit()
            return True

    # ===== Text Cleaning Functions =====

    def get_text_cleaning_keywords(self, task_id):
        """Get text cleaning keywords for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT keyword FROM task_text_cleaning_keywords
                WHERE task_id = ?
                ORDER BY keyword
            """, (task_id,))

            results = cursor.fetchall()
            return [row[0] for row in results]

    def add_text_cleaning_keywords(self, task_id, keywords):
        """Add text cleaning keywords for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            added_count = 0

            for keyword in keywords:
                keyword = keyword.strip()
                if keyword:
                    # Check if keyword already exists
                    cursor.execute("""
                        SELECT keyword FROM task_text_cleaning_keywords
                        WHERE task_id = ? AND keyword = ?
                    """, (task_id, keyword))

                    if not cursor.fetchone():
                        # Add new keyword
                        cursor.execute("""
                            INSERT INTO task_text_cleaning_keywords (task_id, keyword)
                            VALUES (?, ?)
                        """, (task_id, keyword))
                        added_count += 1

            conn.commit()
            return added_count

    def remove_text_cleaning_keyword(self, task_id, keyword):
        """Remove a text cleaning keyword"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM task_text_cleaning_keywords
                WHERE task_id = ? AND keyword = ?
            """, (task_id, keyword))

            conn.commit()
            return cursor.rowcount > 0

    def clear_text_cleaning_keywords(self, task_id):
        """Clear all text cleaning keywords for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM task_text_cleaning_keywords
                WHERE task_id = ?
            """, (task_id,))

            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count

    # ===== Text Formatting Settings =====

    def get_text_formatting_settings(self, task_id: int) -> Dict:
        """Get text formatting settings for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT text_formatting_enabled, format_type, hyperlink_text, hyperlink_url
                FROM task_text_formatting_settings WHERE task_id = ?
            ''', (task_id,))

            result = cursor.fetchone()
            if result:
                return {
                    'text_formatting_enabled': bool(result['text_formatting_enabled']),
                    'format_type': result['format_type'],
                    'hyperlink_text': result['hyperlink_text'],
                    'hyperlink_url': result['hyperlink_url']
                }
            return {
                'text_formatting_enabled': False,
                'format_type': 'regular',
                'hyperlink_text': None,
                'hyperlink_url': None
            }

    def update_text_formatting_settings(self, task_id: int, text_formatting_enabled: bool = None,
                                      format_type: str = None, hyperlink_text: str = None, 
                                      hyperlink_url: str = None) -> bool:
        """Update text formatting settings for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Build update query dynamically
                updates = []
                params = []

                if format_type is not None:
                    updates.append("format_type = ?")
                    params.append(format_type)

                if text_formatting_enabled is not None:
                    updates.append("text_formatting_enabled = ?")
                    params.append(text_formatting_enabled)

                if hyperlink_text is not None:
                    updates.append("hyperlink_text = ?")
                    params.append(hyperlink_text)

                if hyperlink_url is not None:
                    updates.append("hyperlink_url = ?")
                    params.append(hyperlink_url)

                if not updates:
                    return False

                params.append(task_id)

                cursor.execute(f'''
                    UPDATE task_text_formatting_settings 
                    SET {', '.join(updates)}
                    WHERE task_id = ?
                ''', params)

                conn.commit()
                return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"خطأ في تحديث إعدادات تنسيق النص: {e}")
            return False

    def toggle_text_formatting(self, task_id: int) -> bool:
        """Toggle text formatting on/off for a task"""
        current_settings = self.get_text_formatting_settings(task_id)
        new_enabled = not current_settings['text_formatting_enabled']
        self.update_text_formatting_settings(task_id, text_formatting_enabled=new_enabled)
        return new_enabled

    # ===== Cleanup Functions =====

    def cleanup_old_forwarded_messages_log(self, days_old: int = 7):
        """Clean up old forwarded messages log for duplicate detection"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM forwarded_messages_log 
                WHERE forwarded_at < datetime('now', '-{} days')
            '''.format(days_old))
            deleted_count = cursor.rowcount
            conn.commit()
            if deleted_count > 0:
                logger.info(f"🧹 تم حذف {deleted_count} سجل رسالة قديم من سجل التكرار (أكثر من {days_old} أيام)")
            return deleted_count

    # ===== Character Limit Settings =====
    
    def save_character_limit_settings(self, task_id: int, enabled: bool = False, mode: str = 'allow',
                                    min_chars: int = 0, max_chars: int = 4000, use_range: bool = True) -> bool:
        """Save character limit settings for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO task_character_limit_settings 
                    (task_id, enabled, mode, min_chars, max_chars, use_range, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (task_id, enabled, mode, min_chars, max_chars, use_range))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في حفظ إعدادات حد الأحرف: {e}")
            return False

    def get_character_limit_settings(self, task_id: int) -> Dict:
        """Get character limit settings for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT enabled, mode, min_chars, max_chars, use_range
                FROM task_character_limit_settings 
                WHERE task_id = ?
            ''', (task_id,))
            result = cursor.fetchone()
            if result:
                return {
                    'enabled': bool(result['enabled']),
                    'mode': result['mode'],
                    'min_chars': result['min_chars'],
                    'max_chars': result['max_chars'],
                    'use_range': bool(result['use_range'])
                }
            return {
                'enabled': False,
                'mode': 'allow',
                'min_chars': 0,
                'max_chars': 4000,
                'use_range': True
            }

    def update_character_limit_settings(self, task_id: int, **kwargs) -> bool:
        """Update character limit settings for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                updates = []
                params = []
                
                for key, value in kwargs.items():
                    if key in ['enabled', 'mode', 'min_chars', 'max_chars', 'use_range']:
                        updates.append(f"{key} = ?")
                        params.append(value)
                
                if not updates:
                    return False
                
                params.append(task_id)
                cursor.execute(f'''
                    UPDATE task_character_limit_settings 
                    SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
                    WHERE task_id = ?
                ''', params)
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"خطأ في تحديث إعدادات حد الأحرف: {e}")
            return False

    # ===== Rate Limit Settings =====
    
    def save_rate_limit_settings(self, task_id: int, enabled: bool = False, 
                               message_count: int = 5, time_period_seconds: int = 60) -> bool:
        """Save rate limit settings for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO task_rate_limit_settings 
                    (task_id, enabled, message_count, time_period_seconds, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (task_id, enabled, message_count, time_period_seconds))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في حفظ إعدادات حد الرسائل: {e}")
            return False

    def get_rate_limit_settings(self, task_id: int) -> Dict:
        """Get rate limit settings for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT enabled, message_count, time_period_seconds
                FROM task_rate_limit_settings 
                WHERE task_id = ?
            ''', (task_id,))
            result = cursor.fetchone()
            if result:
                return {
                    'enabled': bool(result['enabled']),
                    'message_count': result['message_count'],
                    'time_period_seconds': result['time_period_seconds']
                }
            return {
                'enabled': False,
                'message_count': 5,
                'time_period_seconds': 60
            }

    def update_rate_limit_settings(self, task_id: int, **kwargs) -> bool:
        """Update rate limit settings for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                updates = []
                params = []
                
                for key, value in kwargs.items():
                    if key in ['enabled', 'message_count', 'time_period_seconds']:
                        updates.append(f"{key} = ?")
                        params.append(value)
                
                if not updates:
                    return False
                
                params.append(task_id)
                cursor.execute(f'''
                    UPDATE task_rate_limit_settings 
                    SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
                    WHERE task_id = ?
                ''', params)
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"خطأ في تحديث إعدادات حد الرسائل: {e}")
            return False

    def track_message_for_rate_limit(self, task_id: int) -> bool:
        """Track a message for rate limiting"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO rate_limit_tracking (task_id)
                    VALUES (?)
                ''', (task_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في تتبع الرسالة لحد الرسائل: {e}")
            return False

    def check_rate_limit(self, task_id: int) -> bool:
        """Check if task has exceeded rate limit"""
        settings = self.get_rate_limit_settings(task_id)
        if not settings['enabled']:
            return False  # No rate limit enabled
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) as count
                    FROM rate_limit_tracking 
                    WHERE task_id = ? 
                    AND timestamp > datetime('now', '-{} seconds')
                '''.format(settings['time_period_seconds']), (task_id,))
                result = cursor.fetchone()
                current_count = result['count'] if result else 0
                return current_count >= settings['message_count']
        except Exception as e:
            logger.error(f"خطأ في فحص حد الرسائل: {e}")
            return False

    def cleanup_old_rate_limit_tracking(self, hours_old: int = 24):
        """Clean up old rate limit tracking records"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM rate_limit_tracking 
                    WHERE timestamp < datetime('now', '-{} hours')
                '''.format(hours_old))
                deleted_count = cursor.rowcount
                conn.commit()
                if deleted_count > 0:
                    logger.info(f"🧹 تم حذف {deleted_count} سجل قديم من تتبع حد الرسائل")
                return deleted_count
        except Exception as e:
            logger.error(f"خطأ في تنظيف سجلات حد الرسائل: {e}")
            return 0

    # ===== Forwarding Delay Settings =====
    
    def save_forwarding_delay_settings(self, task_id: int, enabled: bool = False, delay_seconds: int = 5) -> bool:
        """Save forwarding delay settings for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO task_forwarding_delay_settings 
                    (task_id, enabled, delay_seconds, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', (task_id, enabled, delay_seconds))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في حفظ إعدادات تأخير التوجيه: {e}")
            return False

    def get_forwarding_delay_settings(self, task_id: int) -> Dict:
        """Get forwarding delay settings for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT enabled, delay_seconds
                FROM task_forwarding_delay_settings 
                WHERE task_id = ?
            ''', (task_id,))
            result = cursor.fetchone()
            if result:
                return {
                    'enabled': bool(result['enabled']),
                    'delay_seconds': result['delay_seconds']
                }
            return {
                'enabled': False,
                'delay_seconds': 5
            }

    def update_forwarding_delay_settings(self, task_id: int, **kwargs) -> bool:
        """Update forwarding delay settings for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                updates = []
                params = []
                
                for key, value in kwargs.items():
                    if key in ['enabled', 'delay_seconds']:
                        updates.append(f"{key} = ?")
                        params.append(value)
                
                if not updates:
                    return False
                
                params.append(task_id)
                cursor.execute(f'''
                    UPDATE task_forwarding_delay_settings 
                    SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
                    WHERE task_id = ?
                ''', params)
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"خطأ في تحديث إعدادات تأخير التوجيه: {e}")
            return False

    # ===== Sending Interval Settings =====
    
    def save_sending_interval_settings(self, task_id: int, enabled: bool = False, interval_seconds: int = 3) -> bool:
        """Save sending interval settings for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO task_sending_interval_settings 
                    (task_id, enabled, interval_seconds, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', (task_id, enabled, interval_seconds))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في حفظ إعدادات فاصل الإرسال: {e}")
            return False

    def get_sending_interval_settings(self, task_id: int) -> Dict:
        """Get sending interval settings for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT enabled, interval_seconds
                FROM task_sending_interval_settings 
                WHERE task_id = ?
            ''', (task_id,))
            result = cursor.fetchone()
            if result:
                return {
                    'enabled': bool(result['enabled']),
                    'interval_seconds': result['interval_seconds']
                }
            return {
                'enabled': False,
                'interval_seconds': 3
            }

    def update_sending_interval_settings(self, task_id: int, **kwargs) -> bool:
        """Update sending interval settings for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                updates = []
                params = []
                
                for key, value in kwargs.items():
                    if key in ['enabled', 'interval_seconds']:
                        updates.append(f"{key} = ?")
                        params.append(value)
                
                if not updates:
                    return False
                
                params.append(task_id)
                cursor.execute(f'''
                    UPDATE task_sending_interval_settings 
                    SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
                    WHERE task_id = ?
                ''', params)
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"خطأ في تحديث إعدادات فاصل الإرسال: {e}")
            return False

    # ===== Advanced Features Toggle Functions =====
    
    def toggle_character_limit(self, task_id: int) -> bool:
        """Toggle character limit on/off for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get current status
                cursor.execute('SELECT enabled FROM task_character_limit_settings WHERE task_id = ?', (task_id,))
                result = cursor.fetchone()
                
                if result:
                    new_enabled = not result[0]
                    cursor.execute('''
                        UPDATE task_character_limit_settings 
                        SET enabled = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE task_id = ?
                    ''', (new_enabled, task_id))
                else:
                    # Create default settings if not exists
                    new_enabled = True
                    cursor.execute('''
                        INSERT INTO task_character_limit_settings 
                        (task_id, enabled, mode, min_chars, max_chars)
                        VALUES (?, ?, 'allow', 10, 1000)
                    ''', (task_id, new_enabled))
                
                conn.commit()
                return new_enabled
        except Exception as e:
            logger.error(f"خطأ في تبديل حد الأحرف: {e}")
            return False

    def toggle_character_limit_mode(self, task_id: int) -> str:
        """Toggle character limit mode between allow/block"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get current mode
                cursor.execute('SELECT mode FROM task_character_limit_settings WHERE task_id = ?', (task_id,))
                result = cursor.fetchone()
                
                if result:
                    new_mode = 'block' if result[0] == 'allow' else 'allow'
                    cursor.execute('''
                        UPDATE task_character_limit_settings 
                        SET mode = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE task_id = ?
                    ''', (new_mode, task_id))
                    conn.commit()
                    return new_mode
                else:
                    # Create default if not exists
                    cursor.execute('''
                        INSERT INTO task_character_limit_settings 
                        (task_id, enabled, mode, min_chars, max_chars)
                        VALUES (?, 1, 'allow', 10, 1000)
                    ''', (task_id,))
                    conn.commit()
                    return 'allow'
        except Exception as e:
            logger.error(f"خطأ في تبديل وضع حد الأحرف: {e}")
            return 'allow'

    def toggle_rate_limit(self, task_id: int) -> bool:
        """Toggle rate limit on/off for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get current status
                cursor.execute('SELECT enabled FROM task_rate_limit_settings WHERE task_id = ?', (task_id,))
                result = cursor.fetchone()
                
                if result:
                    new_enabled = not result[0]
                    cursor.execute('''
                        UPDATE task_rate_limit_settings 
                        SET enabled = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE task_id = ?
                    ''', (new_enabled, task_id))
                else:
                    # Create default settings if not exists
                    new_enabled = True
                    cursor.execute('''
                        INSERT INTO task_rate_limit_settings 
                        (task_id, enabled, message_count, time_period_seconds)
                        VALUES (?, ?, 10, 60)
                    ''', (task_id, new_enabled))
                
                conn.commit()
                return new_enabled
        except Exception as e:
            logger.error(f"خطأ في تبديل حد الرسائل: {e}")
            return False

    def toggle_forwarding_delay(self, task_id: int) -> bool:
        """Toggle forwarding delay on/off for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get current status
                cursor.execute('SELECT enabled FROM task_forwarding_delay_settings WHERE task_id = ?', (task_id,))
                result = cursor.fetchone()
                
                if result:
                    new_enabled = not result[0]
                    cursor.execute('''
                        UPDATE task_forwarding_delay_settings 
                        SET enabled = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE task_id = ?
                    ''', (new_enabled, task_id))
                else:
                    # Create default settings if not exists
                    new_enabled = True
                    cursor.execute('''
                        INSERT INTO task_forwarding_delay_settings 
                        (task_id, enabled, delay_seconds)
                        VALUES (?, ?, 2)
                    ''', (task_id, new_enabled))
                
                conn.commit()
                return new_enabled
        except Exception as e:
            logger.error(f"خطأ في تبديل تأخير التوجيه: {e}")
            return False

    def toggle_sending_interval(self, task_id: int) -> bool:
        """Toggle sending interval on/off for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get current status
                cursor.execute('SELECT enabled FROM task_sending_interval_settings WHERE task_id = ?', (task_id,))
                result = cursor.fetchone()
                
                if result:
                    new_enabled = not result[0]
                    cursor.execute('''
                        UPDATE task_sending_interval_settings 
                        SET enabled = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE task_id = ?
                    ''', (new_enabled, task_id))
                else:
                    # Create default settings if not exists
                    new_enabled = True
                    cursor.execute('''
                        INSERT INTO task_sending_interval_settings 
                        (task_id, enabled, interval_seconds)
                        VALUES (?, ?, 3)
                    ''', (task_id, new_enabled))
                
                conn.commit()
                return new_enabled
        except Exception as e:
            logger.error(f"خطأ في تبديل فاصل الإرسال: {e}")
            return False