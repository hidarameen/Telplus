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
        # إصلاح صلاحيات الملف قبل الاتصال
        try:
            import os
            if os.path.exists(self.db_path):
                os.chmod(self.db_path, 0o666)
                logger.info(f"✅ تم تصحيح صلاحيات قاعدة البيانات: {self.db_path}")
        except Exception as e:
            logger.warning(f"تحذير في تصحيح صلاحيات قاعدة البيانات: {e}")
        
        conn = sqlite3.connect(self.db_path, timeout=120, check_same_thread=False, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            # Improve concurrency and reduce lock errors
            conn.execute('PRAGMA journal_mode=DELETE')  # Fixed: Use DELETE instead of WAL to prevent readonly errors
            conn.execute('PRAGMA synchronous=NORMAL')
            conn.execute('PRAGMA busy_timeout=120000')
            conn.execute('PRAGMA foreign_keys=ON')
            conn.execute('PRAGMA locking_mode=NORMAL')
            conn.execute('PRAGMA temp_store=memory')
            conn.execute('PRAGMA cache_size=2000')
            
            # التأكد من أن قاعدة البيانات قابلة للكتابة
            conn.execute('BEGIN IMMEDIATE')
            conn.execute('ROLLBACK')
            
            logger.info("✅ تم تطبيق إعدادات PRAGMA آمنة وتأكيد إمكانية الكتابة")
        except sqlite3.OperationalError as e:
            if "readonly database" in str(e).lower():
                logger.error(f"❌ مشكلة readonly في قاعدة البيانات: {e}")
                logger.error("🔧 محاولة إصلاح الصلاحيات...")
                try:
                    import os
                    os.chmod(self.db_path, 0o666)
                    logger.info("✅ تم إصلاح الصلاحيات، إعادة المحاولة...")
                    # إعادة إنشاء الاتصال
                    conn.close()
                    conn = sqlite3.connect(self.db_path, timeout=120, check_same_thread=False, isolation_level=None)
                    conn.row_factory = sqlite3.Row
                    conn.execute('PRAGMA journal_mode=DELETE')
                    conn.execute('PRAGMA synchronous=NORMAL')
                    conn.execute('PRAGMA busy_timeout=120000')
                    conn.execute('PRAGMA foreign_keys=ON')
                    conn.execute('PRAGMA locking_mode=NORMAL')
                    conn.execute('PRAGMA temp_store=memory')
                    conn.execute('PRAGMA cache_size=2000')
                    conn.execute('BEGIN IMMEDIATE')
                    conn.execute('ROLLBACK')
                    logger.info("✅ تم إصلاح قاعدة البيانات بنجاح")
                except Exception as fix_error:
                    logger.error(f"❌ فشل في إصلاح قاعدة البيانات: {fix_error}")
                    raise
            else:
                logger.error(f"❌ خطأ في قاعدة البيانات: {e}")
                raise
        except Exception:
            # Ignore pragma failures on some platforms
            pass
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

            # User settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id INTEGER PRIMARY KEY,
                    timezone TEXT DEFAULT 'Asia/Riyadh',
                    language TEXT DEFAULT 'ar',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # User sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    user_id INTEGER PRIMARY KEY,
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
            
            # Add new columns if they don't exist (for existing databases)
            try:
                cursor.execute('ALTER TABLE user_sessions ADD COLUMN is_healthy BOOLEAN DEFAULT TRUE')
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute('ALTER TABLE user_sessions ADD COLUMN last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute('ALTER TABLE user_sessions ADD COLUMN connection_errors INTEGER DEFAULT 0')
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute('ALTER TABLE user_sessions ADD COLUMN last_error_time TIMESTAMP')
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute('ALTER TABLE user_sessions ADD COLUMN last_error_message TEXT')
            except sqlite3.OperationalError:
                pass

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

            # Word filter entries table (with case sensitivity and whole-word support)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS word_filter_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filter_id INTEGER NOT NULL,
                    word_or_phrase TEXT NOT NULL,
                    is_case_sensitive BOOLEAN DEFAULT FALSE,
                    is_whole_word BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (filter_id) REFERENCES task_word_filters (id) ON DELETE CASCADE
                )
            ''')

            # Backfill missing columns for existing databases
            try:
                cursor.execute("ALTER TABLE word_filter_entries ADD COLUMN is_whole_word BOOLEAN DEFAULT FALSE")
            except sqlite3.OperationalError:
                pass

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
                    -- New scope flags for header/footer application
                    apply_header_to_texts BOOLEAN DEFAULT TRUE,
                    apply_header_to_media BOOLEAN DEFAULT TRUE,
                    apply_footer_to_texts BOOLEAN DEFAULT TRUE,
                    apply_footer_to_media BOOLEAN DEFAULT TRUE,
                    inline_buttons_enabled BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Backfill missing scope columns for existing databases
            try:
                cursor.execute("ALTER TABLE task_message_settings ADD COLUMN apply_header_to_texts BOOLEAN DEFAULT TRUE")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE task_message_settings ADD COLUMN apply_header_to_media BOOLEAN DEFAULT TRUE")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE task_message_settings ADD COLUMN apply_footer_to_texts BOOLEAN DEFAULT TRUE")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE task_message_settings ADD COLUMN apply_footer_to_media BOOLEAN DEFAULT TRUE")
            except sqlite3.OperationalError:
                pass

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
                    split_album_enabled BOOLEAN DEFAULT FALSE,
                    publishing_mode TEXT DEFAULT 'auto' CHECK (publishing_mode IN ('auto', 'manual')),
                    -- New settings
                    sync_pin_enabled BOOLEAN DEFAULT FALSE,
                    clear_pin_notification BOOLEAN DEFAULT FALSE,
                    pin_notification_clear_time INTEGER DEFAULT 0,
                    preserve_reply_enabled BOOLEAN DEFAULT TRUE,
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
            # Backfill new columns for existing databases (safe-guard)
            try:
                cursor.execute("ALTER TABLE task_forwarding_settings ADD COLUMN sync_pin_enabled BOOLEAN DEFAULT FALSE")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE task_forwarding_settings ADD COLUMN clear_pin_notification BOOLEAN DEFAULT FALSE")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE task_forwarding_settings ADD COLUMN pin_notification_clear_time INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE task_forwarding_settings ADD COLUMN preserve_reply_enabled BOOLEAN DEFAULT TRUE")
            except sqlite3.OperationalError:
                pass


            # Pending messages table - for manual approval workflow
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pending_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    source_chat_id TEXT NOT NULL,
                    source_message_id INTEGER NOT NULL,
                    message_data TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    approval_message_id INTEGER,
                    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'expired')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP DEFAULT (datetime('now', '+24 hours')),
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Recurring posts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS recurring_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    name TEXT DEFAULT 'منشور متكرر',
                    enabled BOOLEAN DEFAULT TRUE,
                    source_chat_id TEXT NOT NULL,
                    source_message_id INTEGER NOT NULL,
                    interval_seconds INTEGER NOT NULL,
                    delete_previous BOOLEAN DEFAULT FALSE,
                    preserve_original_buttons BOOLEAN DEFAULT TRUE,
                    next_run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Deliveries for recurring posts to track last message per target
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS recurring_post_deliveries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recurring_post_id INTEGER NOT NULL,
                    target_chat_id TEXT NOT NULL,
                    last_message_id INTEGER,
                    last_posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (recurring_post_id) REFERENCES recurring_posts (id) ON DELETE CASCADE,
                    UNIQUE(recurring_post_id, target_chat_id)
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

            # Working hours table - for time-based filtering with enhanced modes
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_working_hours (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL UNIQUE,
                    mode TEXT DEFAULT 'work_hours',
                    timezone_offset INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Working hours schedule table - for defining specific hours
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_working_hours_schedule (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    hour INTEGER NOT NULL CHECK (hour >= 0 AND hour <= 23),
                    is_enabled BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                    UNIQUE(task_id, hour)
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
                    remove_caption BOOLEAN DEFAULT FALSE,
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

            # Add new columns for album splitting and caption removal if they don't exist
            try:
                cursor.execute("ALTER TABLE task_forwarding_settings ADD COLUMN split_album_enabled BOOLEAN DEFAULT FALSE")
                logger.info("✅ تم إضافة عمود split_album_enabled")
            except Exception:
                pass  # Column already exists

            try:
                cursor.execute("ALTER TABLE task_text_cleaning_settings ADD COLUMN remove_caption BOOLEAN DEFAULT FALSE")
                logger.info("✅ تم إضافة عمود remove_caption")
            except Exception:
                pass  # Column already exists

            # إضافة عمود الحجم الافتراضي لجدول العلامة المائية
            try:
                cursor.execute("ALTER TABLE task_watermark_settings ADD COLUMN default_size INTEGER DEFAULT 50 CHECK (default_size >= 5 AND default_size <= 100)")
                logger.info("✅ تم إضافة عمود default_size للعلامة المائية")
            except Exception:
                pass  # Column already exists

            # إضافة أعمدة الإزاحة اليدوية لجدول العلامة المائية
            try:
                cursor.execute("ALTER TABLE task_watermark_settings ADD COLUMN offset_x INTEGER DEFAULT 0 CHECK (offset_x >= -200 AND offset_x <= 200)")
                logger.info("✅ تم إضافة عمود offset_x للعلامة المائية")
            except Exception:
                pass  # Column already exists
                
            try:
                cursor.execute("ALTER TABLE task_watermark_settings ADD COLUMN offset_y INTEGER DEFAULT 0 CHECK (offset_y >= -200 AND offset_y <= 200)")
                logger.info("✅ تم إضافة عمود offset_y للعلامة المائية")
            except Exception:
                pass  # Column already exists

            # إضافة عمود وضع النشر لجدول إعدادات التوجيه
            try:
                cursor.execute("ALTER TABLE task_forwarding_settings ADD COLUMN publishing_mode TEXT DEFAULT 'auto' CHECK (publishing_mode IN ('auto', 'manual'))")
                logger.info("✅ تم إضافة عمود publishing_mode")
            except Exception:
                pass  # Column already exists

            # Add source_chat_id column to task_admin_filters if it doesn't exist
            try:
                cursor.execute("SELECT source_chat_id FROM task_admin_filters LIMIT 1")
            except sqlite3.OperationalError:
                logger.info("✅ إضافة عمود source_chat_id إلى جدول task_admin_filters")
                cursor.execute("ALTER TABLE task_admin_filters ADD COLUMN source_chat_id TEXT")
            
            # Add admin_signature column for post_author filtering
            try:
                cursor.execute("SELECT admin_signature FROM task_admin_filters LIMIT 1")
            except sqlite3.OperationalError:
                logger.info("✅ إضافة عمود admin_signature إلى جدول task_admin_filters")
                cursor.execute("ALTER TABLE task_admin_filters ADD COLUMN admin_signature TEXT")

            # Task translation settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_translation_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL UNIQUE,
                    enabled BOOLEAN DEFAULT FALSE,
                    source_language TEXT DEFAULT 'auto',
                    target_language TEXT DEFAULT 'ar',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Task watermark settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_watermark_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL UNIQUE,
                    enabled BOOLEAN DEFAULT FALSE,
                    watermark_type TEXT DEFAULT 'text' CHECK (watermark_type IN ('text', 'image')),
                    watermark_text TEXT,
                    watermark_image_path TEXT,
                    position TEXT DEFAULT 'bottom_right' CHECK (position IN ('top_left', 'top_right', 'bottom_left', 'bottom_right', 'center')),
                    size_percentage INTEGER DEFAULT 20 CHECK (size_percentage >= 5 AND size_percentage <= 100),
                    opacity INTEGER DEFAULT 70 CHECK (opacity >= 10 AND opacity <= 100),
                    text_color TEXT DEFAULT '#FFFFFF',
                    use_original_color BOOLEAN DEFAULT FALSE,
                    apply_to_photos BOOLEAN DEFAULT TRUE,
                    apply_to_videos BOOLEAN DEFAULT TRUE,
                    apply_to_documents BOOLEAN DEFAULT FALSE,
                    font_size INTEGER DEFAULT 24,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # ===== Task audio metadata settings table =====
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_audio_metadata_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL UNIQUE,
                    enabled BOOLEAN DEFAULT FALSE,
                    template TEXT DEFAULT 'default',
                    album_art_enabled BOOLEAN DEFAULT FALSE,
                    album_art_path TEXT,
                    apply_art_to_all BOOLEAN DEFAULT FALSE,
                    audio_merge_enabled BOOLEAN DEFAULT FALSE,
                    intro_audio_path TEXT,
                    outro_audio_path TEXT,
                    intro_position TEXT DEFAULT 'start' CHECK (intro_position IN ('start', 'end')),
                    preserve_original BOOLEAN DEFAULT TRUE,
                    convert_to_mp3 BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Task audio tag cleaning settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_audio_tag_cleaning_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL UNIQUE,
                    enabled BOOLEAN DEFAULT FALSE,
                    clean_title BOOLEAN DEFAULT TRUE,
                    clean_artist BOOLEAN DEFAULT TRUE,
                    clean_album_artist BOOLEAN DEFAULT TRUE,
                    clean_album BOOLEAN DEFAULT TRUE,
                    clean_year BOOLEAN DEFAULT TRUE,
                    clean_genre BOOLEAN DEFAULT TRUE,
                    clean_composer BOOLEAN DEFAULT TRUE,
                    clean_comment BOOLEAN DEFAULT TRUE,
                    clean_track BOOLEAN DEFAULT TRUE,
                    clean_length BOOLEAN DEFAULT FALSE,
                    clean_lyrics BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Task character limit settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_character_limit_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    enabled BOOLEAN DEFAULT FALSE,
                    mode TEXT DEFAULT 'allow' CHECK (mode IN ('allow', 'block')),
                    length_mode TEXT DEFAULT 'range' CHECK (length_mode IN ('max', 'min', 'range')),
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

            # Task text formatting settings table
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

            # Create audio template settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_audio_template_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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

            conn.commit()
            logger.info("✅ تم تهيئة جداول SQLite بنجاح مع الفلاتر المتقدمة والميزات الجديدة")
            
        # Create message duplicates table  
        self.create_message_duplicates_table()
        
        # Add missing duplicate filter columns if they don't exist
        self.add_duplicate_filter_columns()
        
        # Add language filter mode support
        self.add_language_filter_mode_support()
        
        # Update character limit table structure
        self.update_character_limit_table()

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

    def update_session_health(self, user_id: int, is_healthy: bool, error_message: str = None):
        """Update session health status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if is_healthy:
                cursor.execute('''
                    UPDATE user_sessions 
                    SET is_healthy = ?, last_activity = CURRENT_TIMESTAMP, connection_errors = 0, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (is_healthy, user_id))
            else:
                cursor.execute('''
                    UPDATE user_sessions 
                    SET is_healthy = ?, connection_errors = connection_errors + 1, 
                        last_error_time = CURRENT_TIMESTAMP, last_error_message = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (is_healthy, error_message, user_id))
            conn.commit()

    def get_user_session_string(self, user_id: int) -> str:
        """Get user session string"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT session_string 
                FROM user_sessions 
                WHERE user_id = ? AND is_authenticated = TRUE
            ''', (user_id,))
            result = cursor.fetchone()
            return result['session_string'] if result else None

    def get_session_health_status(self, user_id: int) -> dict:
        """Get session health status for a user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT is_healthy, last_activity, connection_errors, last_error_time, last_error_message
                FROM user_sessions 
                WHERE user_id = ?
            ''', (user_id,))
            result = cursor.fetchone()
            if result:
                return {
                    'is_healthy': bool(result['is_healthy']),
                    'last_activity': result['last_activity'],
                    'connection_errors': result['connection_errors'] or 0,
                    'last_error_time': result['last_error_time'],
                    'last_error_message': result['last_error_message']
                }
            return None

    def get_all_session_health_status(self) -> dict:
        """Get health status for all users"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, phone_number, is_healthy, last_activity, connection_errors, last_error_time, last_error_message
                FROM user_sessions 
                WHERE is_authenticated = TRUE
            ''')
            results = cursor.fetchall()
            return {
                row['user_id']: {
                    'phone_number': row['phone_number'],
                    'is_healthy': bool(row['is_healthy']),
                    'last_activity': row['last_activity'],
                    'connection_errors': row['connection_errors'] or 0,
                    'last_error_time': row['last_error_time'],
                    'last_error_message': row['last_error_message']
                }
                for row in results
            }

    def cleanup_broken_sessions(self):
        """Clean up sessions with authorization key errors"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Delete sessions that have authorization key errors
                cursor.execute('''
                    DELETE FROM user_sessions 
                    WHERE last_error_message LIKE '%authorization key%' 
                    OR last_error_message LIKE '%different IP%'
                    OR connection_errors >= 5
                ''')
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"🧹 تم حذف {deleted_count} جلسة معطلة من قاعدة البيانات")
                else:
                    logger.info("✅ لا توجد جلسات معطلة للحذف")
                
                return deleted_count
                
        except Exception as e:
            logger.error(f"خطأ في تنظيف الجلسات المعطلة: {e}")
            return 0

    def get_user_session_health(self, user_id: int) -> dict:
        """Get session health status for a specific user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT is_healthy, last_activity, connection_errors, last_error_time, last_error_message
                FROM user_sessions 
                WHERE user_id = ? AND is_authenticated = TRUE
            ''', (user_id,))
            row = cursor.fetchone()
            if row:
                return {
                    'is_healthy': bool(row['is_healthy']),
                    'last_activity': row['last_activity'],
                    'connection_errors': row['connection_errors'] or 0,
                    'last_error_time': row['last_error_time'],
                    'last_error': row['last_error_message']
                }
            return None

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
                    'id': row[0],
                    'task_name': row[1],
                    'source_chat_id': row[2],
                    'source_chat_name': row[3],
                    'target_chat_id': row[4],
                    'target_chat_name': row[5],
                    'forward_mode': row[6] or 'forward',
                    'is_active': bool(row[7]),
                    'created_at': str(row[8])
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
                task_id = row[0]

                # Get all sources for this task
                sources = self.get_task_sources(task_id)
                if not sources:
                    # Fallback to legacy data
                    sources = [{
                        'id': 0,
                        'chat_id': row[2],
                        'chat_name': row[3]
                    }] if row[2] else []

                # Get all targets for this task  
                targets = self.get_task_targets(task_id)
                if not targets:
                    # Fallback to legacy data
                    targets = [{
                        'id': 0,
                        'chat_id': row[4],
                        'chat_name': row[5]
                    }] if row[4] else []

                # Create individual task entries for each source-target combination
                for source in sources:
                    for target in targets:
                        tasks.append({
                            'id': row[0],
                            'task_name': row[1],
                            'source_chat_id': source['chat_id'],
                            'source_chat_name': source['chat_name'],
                            'target_chat_id': target['chat_id'],
                            'target_chat_name': target['chat_name'],
                            'forward_mode': row[6] or 'forward'
                        })
            return tasks
    
    def get_active_user_tasks(self, user_id):
        """Get only active tasks for specific user - alias for get_active_tasks"""
        return self.get_active_tasks(user_id)

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

    def add_word_to_filter(self, task_id: int, filter_type: str, word_or_phrase: str, is_case_sensitive: bool = False, is_whole_word: bool = False):
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
                INSERT INTO word_filter_entries (filter_id, word_or_phrase, is_case_sensitive, is_whole_word)
                VALUES (?, ?, ?, ?)
            ''', (filter_id, word_or_phrase, is_case_sensitive, is_whole_word))
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
                SELECT id, word_or_phrase, is_case_sensitive, COALESCE(is_whole_word, 0) AS is_whole_word FROM word_filter_entries
                WHERE filter_id = ?
                ORDER BY word_or_phrase
            ''', (filter_id,))

            # Return tuples in format (id, filter_id, word_or_phrase, is_case_sensitive)
            # This includes case sensitivity info to avoid separate queries
            words = []
            for row in cursor.fetchall():
                words.append((row['id'], filter_id, row['word_or_phrase'], row['is_case_sensitive'], row['is_whole_word']))
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
                    word = word_data[2]  # word_or_phrase
                    is_case_sensitive = bool(word_data[3])
                    is_whole_word = bool(word_data[4]) if len(word_data) > 4 else False

                    if is_whole_word:
                        import re
                        flags = 0 if is_case_sensitive else re.IGNORECASE
                        pattern = r'\b' + re.escape(word) + r'\b'
                        if re.search(pattern, message_text, flags=flags):
                            found_match = True
                            break
                    else:
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
                word = word_data[2]
                is_case_sensitive = bool(word_data[3])
                is_whole_word = bool(word_data[4]) if len(word_data) > 4 else False

                if is_whole_word:
                    import re
                    flags = 0 if is_case_sensitive else re.IGNORECASE
                    pattern = r'\b' + re.escape(word) + r'\b'
                    if re.search(pattern, message_text, flags=flags):
                        logger.info(f"🚫 الرسالة محظورة: تحتوي على كلمة محظورة '{word}' (تطابق كلمة كاملة)")
                        return False
                else:
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

    # ===== Admin Filter Management =====
    
    def get_admin_filter_setting(self, task_id: int, admin_user_id: int) -> Optional[Dict]:
        """Get admin filter setting for specific admin in a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT admin_user_id, admin_username, admin_first_name, is_allowed, source_chat_id, admin_signature
                FROM task_admin_filters 
                WHERE task_id = ? AND admin_user_id = ?
            ''', (task_id, admin_user_id))
            
            result = cursor.fetchone()
            if result:
                return {
                    'admin_user_id': result['admin_user_id'],
                    'admin_username': result['admin_username'] or '',
                    'admin_first_name': result['admin_first_name'] or '',
                    'is_allowed': bool(result['is_allowed']),
                    'source_chat_id': result['source_chat_id'] or '',
                    'admin_signature': result['admin_signature'] or ''
                }
            return None

    def get_admin_filters(self, task_id: int) -> List[Dict]:
        """Get all admin filters for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT admin_user_id, admin_username, admin_first_name, is_allowed, source_chat_id, admin_signature
                    FROM task_admin_filters 
                    WHERE task_id = ?
                    ORDER BY admin_first_name, admin_username
                ''', (task_id,))
                
                results = cursor.fetchall()
                return [{
                    'admin_user_id': row['admin_user_id'],
                    'admin_username': row['admin_username'] or '',
                    'admin_first_name': row['admin_first_name'] or '',
                    'is_allowed': bool(row['is_allowed']),
                    'source_chat_id': row['source_chat_id'],
                    'admin_signature': row['admin_signature'] or ''
                } for row in results]
                
        except Exception as e:
            logger.error(f"خطأ في الحصول على فلاتر المشرفين: {e}")
            return []

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
                    apply_header_to_texts = True
                    apply_header_to_media = True
                    apply_footer_to_texts = True
                    apply_footer_to_media = True
                else:
                    inline_buttons_enabled = bool(settings_result[0])
                    # Backfill and read scope flags safely
                    try:
                        cursor.execute('SELECT apply_header_to_texts, apply_header_to_media, apply_footer_to_texts, apply_footer_to_media FROM task_message_settings WHERE task_id = ?', (task_id,))
                        scope_row = cursor.fetchone()
                        if scope_row:
                            apply_header_to_texts = bool(scope_row['apply_header_to_texts'])
                            apply_header_to_media = bool(scope_row['apply_header_to_media'])
                            apply_footer_to_texts = bool(scope_row['apply_footer_to_texts'])
                            apply_footer_to_media = bool(scope_row['apply_footer_to_media'])
                        else:
                            apply_header_to_texts = True
                            apply_header_to_media = True
                            apply_footer_to_texts = True
                            apply_footer_to_media = True
                    except Exception:
                        apply_header_to_texts = True
                        apply_header_to_media = True
                        apply_footer_to_texts = True
                        apply_footer_to_media = True

                return {
                    'header_enabled': header_result[0] if header_result else False,
                    'header_text': header_result[1] if header_result else None,
                    'footer_enabled': footer_result[0] if footer_result else False,
                    'footer_text': footer_result[1] if footer_result else None,
                    'apply_header_to_texts': apply_header_to_texts,
                    'apply_header_to_media': apply_header_to_media,
                    'apply_footer_to_texts': apply_footer_to_texts,
                    'apply_footer_to_media': apply_footer_to_media,
                    'inline_buttons_enabled': inline_buttons_enabled
                }
        except Exception as e:
            logger.error(f"خطأ في الحصول على إعدادات الرسالة: {e}")
            return {
                'header_enabled': False,
                'header_text': None,
                'footer_enabled': False,
                'footer_text': None,
                'apply_header_to_texts': True,
                'apply_header_to_media': True,
                'apply_footer_to_texts': True,
                'apply_footer_to_media': True,
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

    def update_message_settings_scope(self, task_id: int, **kwargs):
        """Update scope flags for header/footer application (texts/media)"""
        allowed_keys = {
            'apply_header_to_texts', 'apply_header_to_media',
            'apply_footer_to_texts', 'apply_footer_to_media'
        }
        updates = {k: bool(v) for k, v in kwargs.items() if k in allowed_keys}
        if not updates:
            return False
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Ensure row exists
            cursor.execute('INSERT OR IGNORE INTO task_message_settings (task_id) VALUES (?)', (task_id,))
            set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [task_id]
            cursor.execute(
                f"UPDATE task_message_settings SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE task_id = ?",
                values
            )
            conn.commit()
            return cursor.rowcount > 0

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
                       auto_delete_enabled, auto_delete_time, sync_edit_enabled, sync_delete_enabled,
                       split_album_enabled, publishing_mode,
                       COALESCE(sync_pin_enabled, 0) AS sync_pin_enabled,
                       COALESCE(clear_pin_notification, 0) AS clear_pin_notification,
                       COALESCE(pin_notification_clear_time, 0) AS pin_notification_clear_time,
                       COALESCE(preserve_reply_enabled, 1) AS preserve_reply_enabled
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
                    'sync_delete_enabled': result['sync_delete_enabled'],
                    'split_album_enabled': result['split_album_enabled'] if 'split_album_enabled' in result.keys() else False,
                    'publishing_mode': result['publishing_mode'] if 'publishing_mode' in result.keys() else 'auto',
                    'sync_pin_enabled': bool(result['sync_pin_enabled']) if 'sync_pin_enabled' in result.keys() else False,
                    'clear_pin_notification': bool(result['clear_pin_notification']) if 'clear_pin_notification' in result.keys() else False,
                    'pin_notification_clear_time': int(result['pin_notification_clear_time']) if 'pin_notification_clear_time' in result.keys() else 0,
                    'preserve_reply_enabled': bool(result['preserve_reply_enabled']) if 'preserve_reply_enabled' in result.keys() else True
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
                    'sync_delete_enabled': False,
                    'split_album_enabled': False,
                    'publishing_mode': 'auto',
                    'sync_pin_enabled': False,
                    'clear_pin_notification': False,
                    'pin_notification_clear_time': 0,
                    'preserve_reply_enabled': True
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
                 auto_delete_enabled, auto_delete_time, sync_edit_enabled, sync_delete_enabled, 
                 split_album_enabled, publishing_mode, sync_pin_enabled, clear_pin_notification,
                 pin_notification_clear_time, preserve_reply_enabled, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (task_id, current_settings['link_preview_enabled'], 
                  current_settings['pin_message_enabled'], current_settings['silent_notifications'],
                  current_settings['auto_delete_enabled'], current_settings['auto_delete_time'],
                  current_settings['sync_edit_enabled'], current_settings['sync_delete_enabled'],
                  current_settings['split_album_enabled'], current_settings.get('publishing_mode', 'auto'),
                  current_settings.get('sync_pin_enabled', False), current_settings.get('clear_pin_notification', False),
                  current_settings.get('pin_notification_clear_time', 0), current_settings.get('preserve_reply_enabled', True)))

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

    def toggle_split_album(self, task_id: int) -> bool:
        """Toggle split album setting"""
        current_settings = self.get_forwarding_settings(task_id)
        new_state = not current_settings['split_album_enabled']
        self.update_forwarding_settings(task_id, split_album_enabled=new_state)
        return new_state

    def toggle_sync_pin(self, task_id: int) -> bool:
        """Toggle synchronization of pin/unpin events"""
        current_settings = self.get_forwarding_settings(task_id)
        new_state = not current_settings.get('sync_pin_enabled', False)
        self.update_forwarding_settings(task_id, sync_pin_enabled=new_state)
        return new_state

    def toggle_clear_pin_notification(self, task_id: int) -> bool:
        """Toggle clearing of pin notifications after pinning"""
        current_settings = self.get_forwarding_settings(task_id)
        new_state = not current_settings.get('clear_pin_notification', False)
        self.update_forwarding_settings(task_id, clear_pin_notification=new_state)
        return new_state

    def set_pin_notification_clear_time(self, task_id: int, seconds: int):
        """Set delay for clearing pin notification messages"""
        if seconds < 0:
            seconds = 0
        self.update_forwarding_settings(task_id, pin_notification_clear_time=int(seconds))

    def toggle_preserve_reply(self, task_id: int) -> bool:
        """Toggle preserving reply relationships in forwarded messages"""
        current_settings = self.get_forwarding_settings(task_id)
        new_state = not current_settings.get('preserve_reply_enabled', True)
        self.update_forwarding_settings(task_id, preserve_reply_enabled=new_state)
        return new_state

    def toggle_publishing_mode(self, task_id: int) -> str:
        """Toggle publishing mode between auto and manual"""
        current_settings = self.get_forwarding_settings(task_id)
        new_mode = 'manual' if current_settings['publishing_mode'] == 'auto' else 'auto'
        self.update_forwarding_settings(task_id, publishing_mode=new_mode)
        return new_mode

    def set_publishing_mode(self, task_id: int, mode: str) -> bool:
        """Set publishing mode for a task"""
        if mode not in ['auto', 'manual']:
            return False
        self.update_forwarding_settings(task_id, publishing_mode=mode)
        return True

    # Pending Messages Management
    def add_pending_message(self, task_id: int, user_id: int, source_chat_id: str, 
                           source_message_id: int, message_data: str, message_type: str) -> int:
        """Add a message to pending approval queue"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO pending_messages 
                (task_id, user_id, source_chat_id, source_message_id, message_data, message_type)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (task_id, user_id, source_chat_id, source_message_id, message_data, message_type))
            conn.commit()
            return cursor.lastrowid

    def get_pending_messages(self, user_id: int, status: str = 'pending') -> List[Dict]:
        """Get pending messages for a user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT pm.*, t.task_name 
                FROM pending_messages pm 
                JOIN tasks t ON pm.task_id = t.id
                WHERE pm.user_id = ? AND pm.status = ? AND pm.expires_at > datetime('now')
                ORDER BY pm.created_at DESC
            ''', (user_id, status))
            
            results = cursor.fetchall()
            return [{
                'id': row['id'],
                'task_id': row['task_id'],
                'task_name': row['task_name'],
                'source_chat_id': row['source_chat_id'],
                'source_message_id': row['source_message_id'],
                'message_data': row['message_data'],
                'message_type': row['message_type'],
                'approval_message_id': row['approval_message_id'],
                'status': row['status'],
                'created_at': row['created_at'],
                'expires_at': row['expires_at']
            } for row in results]

    def get_pending_message(self, message_id: int):
        """Get pending message by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, task_id, user_id, source_chat_id, source_message_id,
                       message_data, message_type, approval_message_id, status,
                       created_at, expires_at
                FROM pending_messages 
                WHERE id = ?
            ''', (message_id,))
            result = cursor.fetchone()
            
            if result:
                return {
                    'id': result['id'],
                    'task_id': result['task_id'],
                    'user_id': result['user_id'],
                    'source_chat_id': result['source_chat_id'],
                    'source_message_id': result['source_message_id'],
                    'message_data': result['message_data'],
                    'message_type': result['message_type'],
                    'approval_message_id': result['approval_message_id'],
                    'status': result['status'],
                    'created_at': result['created_at'],
                    'expires_at': result['expires_at']
                }
            return None

    def update_pending_message_status(self, message_id: int, status: str, approval_message_id: int = None) -> bool:
        """Update status of pending message"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if approval_message_id:
                cursor.execute('''
                    UPDATE pending_messages 
                    SET status = ?, approval_message_id = ?
                    WHERE id = ?
                ''', (status, approval_message_id, message_id))
            else:
                cursor.execute('''
                    UPDATE pending_messages 
                    SET status = ?
                    WHERE id = ?
                ''', (status, message_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_task_publishing_mode(self, task_id: int, publishing_mode: str) -> bool:
        """Update publishing mode for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE task_forwarding_settings 
                SET publishing_mode = ?
                WHERE task_id = ?
            ''', (publishing_mode, task_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_pending_message_by_id(self, message_id: int) -> Optional[Dict]:
        """Get pending message by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT pm.*, t.task_name, t.user_id as task_user_id
                FROM pending_messages pm 
                JOIN tasks t ON pm.task_id = t.id
                WHERE pm.id = ?
            ''', (message_id,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'id': result['id'],
                    'task_id': result['task_id'],
                    'task_name': result['task_name'],
                    'user_id': result['user_id'],
                    'task_user_id': result['task_user_id'],
                    'source_chat_id': result['source_chat_id'],
                    'source_message_id': result['source_message_id'],
                    'message_data': result['message_data'],
                    'message_type': result['message_type'],
                    'approval_message_id': result['approval_message_id'],
                    'status': result['status'],
                    'created_at': result['created_at'],
                    'expires_at': result['expires_at']
                }
            return None

    def cleanup_expired_pending_messages(self) -> int:
        """Clean up expired pending messages"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE pending_messages 
                SET status = 'expired'
                WHERE status = 'pending' AND expires_at <= datetime('now')
            ''')
            conn.commit()
            return cursor.rowcount

    def get_pending_messages_count(self, user_id: int) -> int:
        """Get count of pending messages for a user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM pending_messages 
                WHERE user_id = ? AND status = 'pending' AND expires_at > datetime('now')
            ''', (user_id,))
            result = cursor.fetchone()
            return result['count'] if result else 0

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

    def toggle_advanced_filter(self, task_id: int, filter_type: str, enabled: bool = None) -> bool:
        """Toggle a specific advanced filter on/off"""
        # Get current settings
        settings = self.get_advanced_filters_settings(task_id)
        
        # Map filter types to column names
        filter_mapping = {
            'working_hours': 'working_hours_enabled',
            'language': 'language_filter_enabled',
            'day': 'day_filter_enabled',
            'admin': 'admin_filter_enabled',
            'duplicate': 'duplicate_filter_enabled',
            'inline_button': 'inline_button_filter_enabled',
            'forwarded_message': 'forwarded_message_filter_enabled',
            # Support for _enabled suffix patterns from UI
            'day_filter_enabled': 'day_filter_enabled',
            'working_hours_enabled': 'working_hours_enabled',
            'language_filter_enabled': 'language_filter_enabled',
            'admin_filter_enabled': 'admin_filter_enabled',
            'duplicate_filter_enabled': 'duplicate_filter_enabled',
            'inline_button_filter_enabled': 'inline_button_filter_enabled',
            'forwarded_message_filter_enabled': 'forwarded_message_filter_enabled'
        }
        
        if filter_type not in filter_mapping:
            logger.error(f"نوع فلتر غير مدعوم: {filter_type}. الأنواع المدعومة: {list(filter_mapping.keys())}")
            return False
            
        column_name = filter_mapping[filter_type]
        
        # If enabled parameter is provided, use it; otherwise toggle current value
        if enabled is not None:
            new_value = enabled
        else:
            current_value = settings.get(column_name, False)
            new_value = not current_value
        
        # Update the setting
        return self.update_advanced_filter_setting(task_id, filter_type, new_value)

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
            'forwarded_message': 'forwarded_message_filter_enabled',
            # Support for _enabled suffix patterns from UI
            'day_filter_enabled': 'day_filter_enabled',
            'working_hours_enabled': 'working_hours_enabled',
            'language_filter_enabled': 'language_filter_enabled',
            'admin_filter_enabled': 'admin_filter_enabled',
            'duplicate_filter_enabled': 'duplicate_filter_enabled',
            'inline_button_filter_enabled': 'inline_button_filter_enabled',
            'forwarded_message_filter_enabled': 'forwarded_message_filter_enabled'
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
        """Set day filter for a specific day (0=Monday, 6=Sunday)"""
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
            logger.info(f"✅ تم تحديث فلتر اليوم {day_number} للمهمة {task_id}: {is_allowed}")
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
            
            # Get working hours configuration
            cursor.execute('''
                SELECT mode
                FROM task_working_hours WHERE task_id = ?
            ''', (task_id,))
            config = cursor.fetchone()
            
            if not config:
                return {
                    'mode': 'work_hours',
                    'enabled_hours': [],
                    'schedule': {}
                }
            
            # Get enabled hours
            cursor.execute('''
                SELECT hour, is_enabled as enabled
                FROM task_working_hours_schedule 
                WHERE task_id = ? ORDER BY hour
            ''', (task_id,))
            schedule_results = cursor.fetchall()
            
            enabled_hours = [row['hour'] for row in schedule_results if row['enabled']]
            
            return {
                'mode': config['mode'],
                'enabled_hours': enabled_hours,
                'schedule': {row['hour']: row['enabled'] for row in schedule_results}
            }

    def set_working_hours_mode(self, task_id: int, mode: str = 'work_hours'):
        """Set working hours mode for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO task_working_hours 
                (task_id, mode)
                VALUES (?, ?)
            ''', (task_id, mode))
            conn.commit()
            return True

    def set_working_hour_schedule(self, task_id: int, hour: int, is_enabled: bool):
        """Set specific hour schedule for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO task_working_hours_schedule 
                (task_id, hour, is_enabled)
                VALUES (?, ?, ?)
            ''', (task_id, hour, is_enabled))
            conn.commit()
            return True

    def initialize_working_hours_schedule(self, task_id: int):
        """Initialize 24-hour schedule for a task (all disabled by default)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for hour in range(24):
                cursor.execute('''
                    INSERT OR IGNORE INTO task_working_hours_schedule 
                    (task_id, hour, is_enabled)
                    VALUES (?, ?, ?)
                ''', (task_id, hour, False))
            conn.commit()
            return True

    def set_all_working_hours(self, task_id: int, is_enabled: bool):
        """Enable or disable all hours for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for hour in range(24):
                cursor.execute('''
                    INSERT OR REPLACE INTO task_working_hours_schedule 
                    (task_id, hour, is_enabled)
                    VALUES (?, ?, ?)
                ''', (task_id, hour, is_enabled))
            conn.commit()
            return True

    def toggle_working_hour(self, task_id: int, hour: int):
        """Toggle specific hour for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Get current state
            cursor.execute('''
                SELECT is_enabled as enabled FROM task_working_hours_schedule 
                WHERE task_id = ? AND hour = ?
            ''', (task_id, hour))
            result = cursor.fetchone()
            
            if result:
                new_state = not bool(result[0])
            else:
                new_state = True
            
            cursor.execute('''
                INSERT OR REPLACE INTO task_working_hours_schedule 
                (task_id, hour, is_enabled)
                VALUES (?, ?, ?)
            ''', (task_id, hour, new_state))
            conn.commit()
            return new_state

    # Legacy function for compatibility
    def set_working_hours(self, task_id: int, start_hour: int, start_minute: int, 
                         end_hour: int, end_minute: int, timezone_offset: int = 0):
        """Legacy: Set working hours for a task (converts to new system)"""
        # Initialize the new system
        self.set_working_hours_mode(task_id, 'work_hours')
        self.initialize_working_hours_schedule(task_id)
        
        # Enable hours in the range
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for hour in range(24):
                is_in_range = False
                if start_hour <= end_hour:
                    is_in_range = start_hour <= hour <= end_hour
                else:  # spans midnight
                    is_in_range = hour >= start_hour or hour <= end_hour
                
                cursor.execute('''
                    INSERT OR REPLACE INTO task_working_hours_schedule 
                    (task_id, hour, is_enabled)
                    VALUES (?, ?, ?)
                ''', (task_id, hour, is_in_range))
            conn.commit()
            return True

    def update_working_hours(self, task_id: int, start_hour: int = None, start_minute: int = None, 
                           end_hour: int = None, end_minute: int = None, mode: str = None) -> bool:
        """Update working hours settings"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get current settings
                current = self.get_working_hours(task_id)
                if not current:
                    # Create default if doesn't exist
                    self.set_working_hours_mode(task_id, mode or 'work_hours')
                    self.initialize_working_hours_schedule(task_id)
                    return True
                
                # Update mode if provided
                if mode is not None:
                    self.set_working_hours_mode(task_id, mode)
                
                # Update schedule if hours provided
                if start_hour is not None and end_hour is not None:
                    for hour in range(24):
                        is_in_range = False
                        if start_hour <= end_hour:
                            is_in_range = start_hour <= hour <= end_hour
                        else:  # spans midnight
                            is_in_range = hour >= start_hour or hour <= end_hour
                        
                        cursor.execute('''
                            INSERT OR REPLACE INTO task_working_hours_schedule 
                            (task_id, hour, is_enabled)
                            VALUES (?, ?, ?)
                        ''', (task_id, hour, is_in_range))
                    conn.commit()
                
                return True
        except Exception as e:
            logger.error(f"خطأ في تحديث ساعات العمل: {e}")
            return False

    def set_working_hour(self, task_id: int, hour: int, enabled: bool) -> bool:
        """Set a specific working hour"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO task_working_hours_schedule 
                    (task_id, hour, is_enabled)
                    VALUES (?, ?, ?)
                ''', (task_id, hour, enabled))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في تحديد ساعة العمل {hour} للمهمة {task_id}: {e}")
            return False

    # ===== Language Filters Management =====

    def get_language_filters(self, task_id: int) -> Dict:
        """Get language filters and mode for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get filter mode
            cursor.execute('''
                SELECT language_filter_mode 
                FROM task_advanced_filters 
                WHERE task_id = ?
            ''', (task_id,))
            mode_result = cursor.fetchone()
            filter_mode = mode_result['language_filter_mode'] if mode_result else 'allow'
            
            # Get languages
            cursor.execute('''
                SELECT language_code, language_name, is_allowed
                FROM task_language_filters WHERE task_id = ?
                ORDER BY language_name
            ''', (task_id,))

            languages = []
            for row in cursor.fetchall():
                languages.append({
                    'language_code': row['language_code'],
                    'language_name': row['language_name'],
                    'is_allowed': bool(row['is_allowed'])
                })
            
            return {
                'mode': filter_mode,  # 'allow' or 'block'
                'languages': languages
            }

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

    def set_language_filter_mode(self, task_id: int, mode: str):
        """Set language filter mode (allow/block)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # First ensure record exists
                cursor.execute('SELECT id FROM task_advanced_filters WHERE task_id = ?', (task_id,))
                if not cursor.fetchone():
                    cursor.execute('''
                        INSERT INTO task_advanced_filters (task_id, language_filter_mode)
                        VALUES (?, ?)
                    ''', (task_id, mode))
                else:
                    cursor.execute('''
                        UPDATE task_advanced_filters 
                        SET language_filter_mode = ?
                        WHERE task_id = ?
                    ''', (mode, task_id))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في تحديث وضع فلتر اللغة: {e}")
            return False

    def get_language_filter_mode(self, task_id: int) -> str:
        """Get language filter mode"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT language_filter_mode 
                FROM task_advanced_filters 
                WHERE task_id = ?
            ''', (task_id,))
            result = cursor.fetchone()
            return result['language_filter_mode'] if result else 'allow'

    def clear_language_filters(self, task_id: int):
        """Clear all language filters for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM task_language_filters 
                    WHERE task_id = ?
                ''', (task_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في مسح فلاتر اللغات: {e}")
            return False

    # ===== Admin Filters Management =====

    def get_admin_filters(self, task_id: int) -> List[Dict]:
        """Get admin filters for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT admin_user_id, admin_username, admin_first_name, is_allowed, source_chat_id, admin_signature
                FROM task_admin_filters WHERE task_id = ?
                ORDER BY admin_first_name, admin_username
            ''', (task_id,))

            filters = []
            for row in cursor.fetchall():
                filters.append({
                    'admin_user_id': row['admin_user_id'],
                    'admin_username': row['admin_username'],
                    'admin_first_name': row['admin_first_name'],
                    'is_allowed': bool(row['is_allowed']),
                    'source_chat_id': row['source_chat_id'],
                    'admin_signature': row['admin_signature']
                })
            return filters

    def add_admin_filter(self, task_id: int, admin_user_id: int, admin_username: str = None, 
                        admin_first_name: str = None, is_allowed: bool = True, source_chat_id: str = None,
                        admin_signature: str = None):
        """Add admin filter"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO task_admin_filters 
                (task_id, admin_user_id, admin_username, admin_first_name, is_allowed, source_chat_id, admin_signature)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (task_id, admin_user_id, admin_username, admin_first_name, is_allowed, source_chat_id, admin_signature))
            conn.commit()
            return True
            
    def get_admin_filters_by_source(self, task_id: int, source_chat_id: str) -> List[Dict]:
        """Get admin filters for a specific source"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT admin_user_id, admin_username, admin_first_name, is_allowed, source_chat_id, admin_signature
                    FROM task_admin_filters 
                    WHERE task_id = ? AND source_chat_id = ?
                    ORDER BY admin_first_name, admin_username
                ''', (task_id, source_chat_id))
                
                results = cursor.fetchall()
                return [{
                    'admin_user_id': row['admin_user_id'],
                    'admin_username': row['admin_username'] or '',
                    'admin_first_name': row['admin_first_name'] or '',
                    'is_allowed': bool(row['is_allowed']),
                    'source_chat_id': row['source_chat_id'],
                    'admin_signature': row['admin_signature'] or ''
                } for row in results]
                
        except Exception as e:
            logger.error(f"خطأ في الحصول على فلاتر مشرفين المصدر: {e}")
            return []

    def get_admin_filters_by_source_with_stats(self, task_id: int, source_chat_id: str) -> Dict:
        """Get admin filters for a specific source with statistics"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get admins with their status
                cursor.execute('''
                    SELECT admin_user_id, admin_username, admin_first_name, is_allowed, source_chat_id, admin_signature
                    FROM task_admin_filters 
                    WHERE task_id = ? AND source_chat_id = ?
                    ORDER BY admin_first_name, admin_username
                ''', (task_id, source_chat_id))
                
                admins = []
                for row in cursor.fetchall():
                    admins.append({
                        'admin_user_id': row['admin_user_id'],
                        'admin_username': row['admin_username'] or '',
                        'admin_first_name': row['admin_first_name'] or '',
                        'is_allowed': bool(row['is_allowed']),
                        'source_chat_id': row['source_chat_id'],
                        'admin_signature': row['admin_signature'] or ''
                    })
                
                # Get statistics
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_count,
                        SUM(CASE WHEN is_allowed = 1 THEN 1 ELSE 0 END) as allowed_count,
                        SUM(CASE WHEN is_allowed = 0 THEN 1 ELSE 0 END) as blocked_count
                    FROM task_admin_filters 
                    WHERE task_id = ? AND source_chat_id = ?
                ''', (task_id, source_chat_id))
                
                stats = cursor.fetchone()
                
                return {
                    'admins': admins,
                    'stats': {
                        'total': stats['total_count'] if stats else 0,
                        'allowed': stats['allowed_count'] if stats else 0,
                        'blocked': stats['blocked_count'] if stats else 0
                    }
                }
                
        except Exception as e:
            logger.error(f"خطأ في الحصول على فلاتر مشرفين المصدر مع الإحصائيات: {e}")
            return {'admins': [], 'stats': {'total': 0, 'allowed': 0, 'blocked': 0}}

    def update_admin_signature(self, task_id: int, admin_user_id: int, source_chat_id: str, admin_signature: str):
        """Update admin signature for a specific admin in a source"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE task_admin_filters 
                    SET admin_signature = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE task_id = ? AND admin_user_id = ? AND source_chat_id = ?
                ''', (admin_signature, task_id, admin_user_id, source_chat_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"خطأ في تحديث توقيع المشرف: {e}")
            return False

    def bulk_update_admin_permissions(self, task_id: int, source_chat_id: str, admin_permissions: Dict[int, bool]):
        """Bulk update admin permissions for a specific source"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                updated_count = 0
                
                for admin_user_id, is_allowed in admin_permissions.items():
                    cursor.execute('''
                        UPDATE task_admin_filters 
                        SET is_allowed = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE task_id = ? AND admin_user_id = ? AND source_chat_id = ?
                    ''', (is_allowed, task_id, admin_user_id, source_chat_id))
                    updated_count += cursor.rowcount
                
                conn.commit()
                return updated_count
        except Exception as e:
            logger.error(f"خطأ في تحديث صلاحيات المشرفين: {e}")
            return 0

    def get_admin_by_signature(self, task_id: int, source_chat_id: str, admin_signature: str) -> Optional[Dict]:
        """Get admin by signature for a specific source"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT admin_user_id, admin_username, admin_first_name, is_allowed, source_chat_id, admin_signature
                    FROM task_admin_filters 
                    WHERE task_id = ? AND source_chat_id = ? AND admin_signature = ?
                ''', (task_id, source_chat_id, admin_signature))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'admin_user_id': result['admin_user_id'],
                        'admin_username': result['admin_username'] or '',
                        'admin_first_name': result['admin_first_name'] or '',
                        'is_allowed': bool(result['is_allowed']),
                        'source_chat_id': result['source_chat_id'],
                        'admin_signature': result['admin_signature'] or ''
                    }
                return None
                
        except Exception as e:
            logger.error(f"خطأ في البحث عن المشرف بالتوقيع: {e}")
            return None

    def toggle_admin_filter(self, task_id: int, admin_user_id: int, source_chat_id: str = None):
        """Toggle admin filter status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if source_chat_id:
                cursor.execute('''
                    UPDATE task_admin_filters 
                    SET is_allowed = NOT is_allowed, updated_at = CURRENT_TIMESTAMP
                    WHERE task_id = ? AND admin_user_id = ? AND source_chat_id = ?
                ''', (task_id, admin_user_id, source_chat_id))
            else:
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
        # Use the source-specific admin filter function
        return self.get_admin_filters_by_source(task_id, source_chat_id)

    def clear_admin_filters_for_source(self, task_id: int, source_chat_id: str):
        """Clear admin filters for a specific source"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM task_admin_filters 
                WHERE task_id = ? AND source_chat_id = ?
            ''', (task_id, source_chat_id))
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
                                                 previous_permissions: Dict[int, bool] = None, source_chat_id: str = None,
                                                 admin_signature: str = None):
        """Add admin filter while preserving previous permissions if they exist"""
        # Check if this admin had previous permissions
        if previous_permissions and admin_user_id in previous_permissions:
            is_allowed = previous_permissions[admin_user_id]
            logger.info(f"🔄 الحفاظ على إذن سابق للمشرف {admin_user_id}: {is_allowed}")
        else:
            is_allowed = True  # Default for new admins
            logger.info(f"✅ مشرف جديد {admin_user_id}: إذن افتراضي = True")

        return self.add_admin_filter(task_id, admin_user_id, admin_username, admin_first_name, is_allowed, source_chat_id, admin_signature)

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
                       remove_empty_lines, remove_lines_with_keywords, remove_caption
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
                    'remove_lines_with_keywords': bool(result['remove_lines_with_keywords']),
                    'remove_caption': bool(result['remove_caption']) if 'remove_caption' in result.keys() else False
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
                    'remove_lines_with_keywords': False,
                    'remove_caption': False
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
            'remove_lines_with_keywords': 'remove_lines_with_keywords',
            'remove_caption': 'remove_caption'
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
            
            # First get the actual enabled status from advanced filters
            cursor.execute('''
                SELECT duplicate_filter_enabled 
                FROM task_advanced_filters 
                WHERE task_id = ?
            ''', (task_id,))
            
            filter_enabled_result = cursor.fetchone()
            is_filter_enabled = bool(filter_enabled_result['duplicate_filter_enabled']) if filter_enabled_result else False
            
            # Then get the duplicate settings
            cursor.execute('''
                SELECT check_text_similarity, check_media_similarity, 
                       similarity_threshold, time_window_hours
                FROM task_duplicate_settings WHERE task_id = ?
            ''', (task_id,))
            result = cursor.fetchone()

            if result:
                return {
                    'enabled': is_filter_enabled,  # Use actual enabled status from advanced filters
                    'check_text': bool(result['check_text_similarity']),
                    'check_media': bool(result['check_media_similarity']),
                    'similarity_threshold': int(result['similarity_threshold'] * 100),  # Convert to percentage
                    'time_window_hours': int(result['time_window_hours'])
                }
            else:
                # Create default settings
                self.create_default_duplicate_settings(task_id)
                return {
                    'enabled': is_filter_enabled,  # Use actual enabled status from advanced filters
                    'check_text': True,
                    'check_media': True,
                    'similarity_threshold': 80,  # Percentage
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

    def update_duplicate_text_check(self, task_id: int, enabled: bool):
        """Update text similarity check setting"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Ensure default settings exist first
            cursor.execute('INSERT OR IGNORE INTO task_duplicate_settings (task_id) VALUES (?)', (task_id,))
            cursor.execute('''
                UPDATE task_duplicate_settings 
                SET check_text_similarity = ?
                WHERE task_id = ?
            ''', (enabled, task_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_duplicate_media_check(self, task_id: int, enabled: bool):
        """Update media similarity check setting"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Ensure default settings exist first
            cursor.execute('INSERT OR IGNORE INTO task_duplicate_settings (task_id) VALUES (?)', (task_id,))
            cursor.execute('''
                UPDATE task_duplicate_settings 
                SET check_media_similarity = ?
                WHERE task_id = ?
            ''', (enabled, task_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_duplicate_setting(self, task_id: int, setting_type: str, value):
        """Update a specific duplicate setting"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Ensure default settings exist first
            cursor.execute('INSERT OR IGNORE INTO task_duplicate_settings (task_id) VALUES (?)', (task_id,))
            
            if setting_type == 'check_text':
                cursor.execute('''
                    UPDATE task_duplicate_settings 
                    SET check_text_similarity = ?
                    WHERE task_id = ?
                ''', (value, task_id))
            elif setting_type == 'check_media':
                cursor.execute('''
                    UPDATE task_duplicate_settings 
                    SET check_media_similarity = ?
                    WHERE task_id = ?
                ''', (value, task_id))
            elif setting_type == 'similarity_threshold':
                # Convert percentage to decimal
                decimal_value = value / 100.0 if isinstance(value, (int, float)) else 0.8
                cursor.execute('''
                    UPDATE task_duplicate_settings 
                    SET similarity_threshold = ?
                    WHERE task_id = ?
                ''', (decimal_value, task_id))
            elif setting_type == 'time_window_hours':
                cursor.execute('''
                    UPDATE task_duplicate_settings 
                    SET time_window_hours = ?
                    WHERE task_id = ?
                ''', (value, task_id))
            
            conn.commit()
            return cursor.rowcount > 0

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

    def get_button_filter_settings(self, task_id: int) -> dict:
        """Get button filter settings"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT action_mode, block_messages_with_buttons 
                FROM task_inline_button_filters 
                WHERE task_id = ?
            ''', (task_id,))
            result = cursor.fetchone()
            if result:
                return {
                    'action_mode': result['action_mode'] or 'remove_buttons',
                    'block_messages_with_buttons': bool(result['block_messages_with_buttons'])
                }
            return {'action_mode': 'remove_buttons', 'block_messages_with_buttons': False}

    def set_button_filter_mode(self, task_id: int, mode: str):
        """Set button filter mode (remove_buttons or block_message)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Ensure button filter settings exist
            cursor.execute('INSERT OR IGNORE INTO task_inline_button_filters (task_id) VALUES (?)', (task_id,))
            cursor.execute('''
                UPDATE task_inline_button_filters 
                SET action_mode = ?
                WHERE task_id = ?
            ''', (mode, task_id))
            conn.commit()
            return cursor.rowcount > 0

    def set_duplicate_settings(self, task_id: int, **kwargs):
        """Set duplicate filter settings"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Ensure duplicate settings exist
            cursor.execute('INSERT OR IGNORE INTO task_duplicate_settings (task_id) VALUES (?)', (task_id,))
            
            # Update the settings
            if 'repeat_mode_enabled' in kwargs:
                cursor.execute('''
                    UPDATE task_duplicate_settings 
                    SET repeat_mode_enabled = ?
                    WHERE task_id = ?
                ''', (kwargs['repeat_mode_enabled'], task_id))
            
            conn.commit()
            return cursor.rowcount > 0

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

    def get_forwarded_filter_settings(self, task_id: int) -> dict:
        """Get forwarded message filter settings"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT block_forwarded_messages 
                FROM task_forwarded_message_filters 
                WHERE task_id = ?
            ''', (task_id,))
            result = cursor.fetchone()
            if result:
                return {
                    'mode': 'block' if bool(result['block_forwarded_messages']) else 'allow',
                    'block_forwarded_messages': bool(result['block_forwarded_messages'])
                }
            return {'mode': 'allow', 'block_forwarded_messages': False}

    def set_forwarded_filter_mode(self, task_id: int, mode: str):
        """Set forwarded message filter mode (allow or block)"""
        block_forwarded = (mode == 'block')
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO task_forwarded_message_filters 
                (task_id, block_forwarded_messages)
                VALUES (?, ?)
            ''', (task_id, block_forwarded))
            conn.commit()
            return True

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
                
                # Get current settings
                current = self.get_text_formatting_settings(task_id)
                
                # Use current values if new ones not provided
                enabled = text_formatting_enabled if text_formatting_enabled is not None else current['text_formatting_enabled']
                fmt_type = format_type if format_type is not None else current['format_type']
                link_text = hyperlink_text if hyperlink_text is not None else current['hyperlink_text']
                link_url = hyperlink_url if hyperlink_url is not None else current['hyperlink_url']
                
                cursor.execute('''
                    INSERT OR REPLACE INTO task_text_formatting_settings 
                    (task_id, text_formatting_enabled, format_type, hyperlink_text, hyperlink_url, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (task_id, enabled, fmt_type, link_text, link_url))
                
                conn.commit()
                return True

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
                                    min_chars: int = 0, max_chars: int = 4000, use_range: bool = True,
                                    length_mode: str = 'range') -> bool:
        """Save character limit settings for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO task_character_limit_settings 
                    (task_id, enabled, mode, min_chars, max_chars, use_range, length_mode, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (task_id, enabled, mode, min_chars, max_chars, use_range, length_mode))
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
                SELECT enabled, mode, min_chars, max_chars, use_range, length_mode
                FROM task_character_limit_settings 
                WHERE task_id = ?
            ''', (task_id,))
            result = cursor.fetchone()
            if result:
                return {
                    'enabled': bool(result[0]),
                    'mode': result[1],
                    'min_chars': result[2],
                    'max_chars': result[3],
                    'use_range': bool(result[4]),
                    'length_mode': result[5] if result and len(result) >= 6 else 'range'
                }
            return {
                'enabled': False,
                'mode': 'allow',
                'min_chars': 0,
                'max_chars': 4000,
                'use_range': True,
                'length_mode': 'range'
            }

    def update_character_limit_settings(self, task_id: int, **kwargs) -> bool:
        """Update character limit settings for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # First check if record exists
                cursor.execute('SELECT id FROM task_character_limit_settings WHERE task_id = ?', (task_id,))
                if not cursor.fetchone():
                    # Create default settings if not exists
                    cursor.execute('''
                        INSERT INTO task_character_limit_settings 
                        (task_id, enabled, mode, min_chars, max_chars, use_range, length_mode)
                        VALUES (?, FALSE, 'allow', 0, 4000, TRUE, 'range')
                    ''', (task_id,))
                
                updates = []
                params = []
                
                for key, value in kwargs.items():
                    if key in ['enabled', 'mode', 'min_chars', 'max_chars', 'use_range', 'length_mode']:
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
                return True
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
                    'enabled': bool(result[0]),
                    'message_count': result[1],
                    'time_period_seconds': result[2]
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
                
                # First check if record exists
                cursor.execute('SELECT id FROM task_rate_limit_settings WHERE task_id = ?', (task_id,))
                if not cursor.fetchone():
                    # Create default settings if not exists
                    cursor.execute('''
                        INSERT INTO task_rate_limit_settings 
                        (task_id, enabled, message_count, time_period_seconds)
                        VALUES (?, FALSE, 10, 60)
                    ''', (task_id,))
                
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
                return True
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
                    'enabled': bool(result[0]),
                    'delay_seconds': result[1]
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
                
                # First check if record exists
                cursor.execute('SELECT id FROM task_forwarding_delay_settings WHERE task_id = ?', (task_id,))
                if not cursor.fetchone():
                    # Create default settings if not exists
                    cursor.execute('''
                        INSERT INTO task_forwarding_delay_settings 
                        (task_id, enabled, delay_seconds)
                        VALUES (?, FALSE, 0)
                    ''', (task_id,))
                
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
                return True
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
                    'enabled': bool(result[0]),
                    'interval_seconds': result[1]
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
                
                # First check if record exists
                cursor.execute('SELECT id FROM task_sending_interval_settings WHERE task_id = ?', (task_id,))
                if not cursor.fetchone():
                    # Create default settings if not exists
                    cursor.execute('''
                        INSERT INTO task_sending_interval_settings 
                        (task_id, enabled, interval_seconds)
                        VALUES (?, FALSE, 3)
                    ''', (task_id,))
                
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
                return True
        except Exception as e:
            logger.error(f"خطأ في تحديث إعدادات فاصل الإرسال: {e}")
            return False

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
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (task_id, name, enabled, str(source_chat_id), int(source_message_id), int(interval_seconds),
                      bool(delete_previous), bool(preserve_original_buttons), next_run_at))
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"خطأ في إنشاء منشور متكرر: {e}")
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
                        updates.append(f"{key} = ?")
                        params.append(val)
                if not updates:
                    return False
                params.append(recurring_id)
                cursor.execute(f'''
                    UPDATE recurring_posts
                    SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', params)
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"خطأ في تحديث منشور متكرر: {e}")
            return False

    def delete_recurring_post(self, recurring_id: int) -> bool:
        """Delete a recurring post and its deliveries"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM recurring_posts WHERE id = ?', (recurring_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"خطأ في حذف منشور متكرر: {e}")
            return False

    def list_recurring_posts(self, task_id: int) -> List[Dict]:
        """List recurring posts for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, task_id, name, enabled, source_chat_id, source_message_id, interval_seconds,
                       delete_previous, preserve_original_buttons, next_run_at, created_at, updated_at
                FROM recurring_posts WHERE task_id = ? ORDER BY id DESC
            ''', (task_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_recurring_post(self, recurring_id: int) -> Optional[Dict]:
        """Get a single recurring post by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, task_id, name, enabled, source_chat_id, source_message_id, interval_seconds,
                       delete_previous, preserve_original_buttons, next_run_at, created_at, updated_at
                FROM recurring_posts WHERE id = ?
            ''', (recurring_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def upsert_recurring_delivery(self, recurring_post_id: int, target_chat_id: str,
                                  last_message_id: Optional[int]) -> bool:
        """Upsert delivery mapping for a recurring post and target"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO recurring_post_deliveries (recurring_post_id, target_chat_id, last_message_id, last_posted_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(recurring_post_id, target_chat_id)
                    DO UPDATE SET last_message_id = excluded.last_message_id, last_posted_at = CURRENT_TIMESTAMP
                ''', (recurring_post_id, str(target_chat_id), last_message_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في تحديث تسليم منشور متكرر: {e}")
            return False

    def get_recurring_delivery(self, recurring_post_id: int, target_chat_id: str) -> Optional[Dict]:
        """Get last delivery info for a recurring post and target"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, recurring_post_id, target_chat_id, last_message_id, last_posted_at
                FROM recurring_post_deliveries
                WHERE recurring_post_id = ? AND target_chat_id = ?
            ''', (recurring_post_id, str(target_chat_id)))
            row = cursor.fetchone()
            return dict(row) if row else None

    # ===== Translation Settings =====
    
    def get_translation_settings(self, task_id: int) -> Dict:
        """Get translation settings for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT enabled, source_language, target_language
                FROM task_translation_settings 
                WHERE task_id = ?
            ''', (task_id,))
            result = cursor.fetchone()
            if result:
                return {
                    'enabled': bool(result['enabled']),
                    'source_language': result['source_language'],
                    'target_language': result['target_language']
                }
            return {
                'enabled': False,
                'source_language': 'auto',
                'target_language': 'ar'
            }
    
    def update_translation_settings(self, task_id: int, **kwargs) -> bool:
        """Update translation settings for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # First check if record exists
                cursor.execute('SELECT id FROM task_translation_settings WHERE task_id = ?', (task_id,))
                if not cursor.fetchone():
                    # Create default settings if not exists
                    cursor.execute('''
                        INSERT INTO task_translation_settings 
                        (task_id, enabled, source_language, target_language)
                        VALUES (?, FALSE, 'auto', 'ar')
                    ''', (task_id,))
                
                updates = []
                params = []
                
                for key, value in kwargs.items():
                    if key in ['enabled', 'source_language', 'target_language']:
                        updates.append(f"{key} = ?")
                        params.append(value)
                
                if not updates:
                    return False
                
                params.append(task_id)
                cursor.execute(f'''
                    UPDATE task_translation_settings 
                    SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
                    WHERE task_id = ?
                ''', params)
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في تحديث إعدادات الترجمة: {e}")
            return False
    
    # ===== User Settings Management =====
    
    def get_user_settings(self, user_id):
        """Get user settings including timezone and language"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT timezone, language 
                FROM user_settings 
                WHERE user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'timezone': result[0],
                    'language': result[1]
                }
            else:
                # Create default settings for new user
                self.create_user_settings(user_id)
                return {
                    'timezone': 'Asia/Riyadh',
                    'language': 'ar'
                }
    
    def create_user_settings(self, user_id):
        """Create default user settings"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO user_settings (user_id, timezone, language)
                VALUES (?, 'Asia/Riyadh', 'ar')
            ''', (user_id,))
            conn.commit()
            
    def update_user_timezone(self, user_id, timezone):
        """Update user timezone setting"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Ensure user settings exist
            cursor.execute('''
                INSERT OR IGNORE INTO user_settings (user_id, timezone, language)
                VALUES (?, 'Asia/Riyadh', 'ar')
            ''', (user_id,))
            
            # Update timezone
            cursor.execute('''
                UPDATE user_settings 
                SET timezone = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (timezone, user_id))
            conn.commit()
            return cursor.rowcount > 0
            
    def update_user_language(self, user_id, language):
        """Update user language setting"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Ensure user settings exist
            cursor.execute('''
                INSERT OR IGNORE INTO user_settings (user_id, timezone, language)
                VALUES (?, 'Asia/Riyadh', 'ar')
            ''', (user_id,))
            
            # Update language
            cursor.execute('''
                UPDATE user_settings 
                SET language = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (language, user_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def toggle_translation(self, task_id: int) -> bool:
        """Toggle translation on/off for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get current status
                cursor.execute('SELECT enabled FROM task_translation_settings WHERE task_id = ?', (task_id,))
                result = cursor.fetchone()
                
                if result:
                    new_enabled = not result[0]
                    cursor.execute('''
                        UPDATE task_translation_settings 
                        SET enabled = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE task_id = ?
                    ''', (new_enabled, task_id))
                else:
                    # Create default settings if not exists
                    new_enabled = True
                    cursor.execute('''
                        INSERT INTO task_translation_settings 
                        (task_id, enabled, source_language, target_language)
                        VALUES (?, ?, 'auto', 'ar')
                    ''', (task_id, new_enabled))
                
                conn.commit()
                return new_enabled
        except Exception as e:
            logger.error(f"خطأ في تبديل الترجمة: {e}")
            return False

    def cycle_character_limit_mode(self, task_id: int) -> str:
        """Cycle character limit mode between allow and block"""
        try:
            settings = self.get_character_limit_settings(task_id)
            current_mode = settings['mode']
            
            # Cycle through modes
            if current_mode == 'allow':
                new_mode = 'block'
            else:  # block
                new_mode = 'allow'
            
            self.update_character_limit_settings(task_id, mode=new_mode)
            return new_mode
        except Exception as e:
            logger.error(f"خطأ في تدوير وضع حد الأحرف: {e}")
            return 'allow'

    def cycle_length_mode(self, task_id: int) -> str:
        """Cycle length_mode between max -> min -> range"""
        try:
            settings = self.get_character_limit_settings(task_id)
            current = settings.get('length_mode', 'range')
            if current == 'max':
                new_mode = 'min'
            elif current == 'min':
                new_mode = 'range'
            else:
                new_mode = 'max'
            self.update_character_limit_settings(task_id, length_mode=new_mode)
            return new_mode
        except Exception as e:
            logger.error(f"خطأ في تدوير نوع الحد: {e}")
            return 'range'

    def update_character_limit_values(self, task_id: int, min_chars: int = None, max_chars: int = None) -> bool:
        """Update character limit min/max values"""
        try:
            # Update the values
            updates = {}
            if min_chars is not None:
                updates['min_chars'] = min_chars
            if max_chars is not None:
                updates['max_chars'] = max_chars
            
            if updates:
                return self.update_character_limit_settings(task_id, **updates)
            return False
        except Exception as e:
            logger.error(f"خطأ في تحديث قيم حد الأحرف: {e}")
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
                        (task_id, enabled, mode, min_chars, max_chars, use_range, length_mode)
                        VALUES (?, ?, 'allow', 0, 4000, TRUE, 'range')
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
                        (task_id, enabled, mode, min_chars, max_chars, use_range, length_mode)
                        VALUES (?, 1, 'allow', 10, 1000, TRUE, 'range')
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

    def update_duplicate_threshold(self, task_id: int, threshold: float) -> bool:
        """Update duplicate filter similarity threshold"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE task_advanced_filters 
                    SET duplicate_filter_similarity_threshold = ?
                    WHERE task_id = ?
                ''', (threshold, task_id))
                conn.commit()
                logger.info(f"✅ تم تحديث نسبة التشابه لفلتر التكرار: {threshold*100:.0f}% للمهمة {task_id}")
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"خطأ في تحديث نسبة التشابه لفلتر التكرار: {e}")
            return False

    def update_duplicate_time_window(self, task_id: int, time_window_hours: int) -> bool:
        """Update duplicate filter time window"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE task_advanced_filters 
                    SET duplicate_filter_time_window_hours = ?
                    WHERE task_id = ?
                ''', (time_window_hours, task_id))
                conn.commit()
                logger.info(f"✅ تم تحديث النافذة الزمنية لفلتر التكرار: {time_window_hours} ساعة للمهمة {task_id}")
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"خطأ في تحديث النافذة الزمنية لفلتر التكرار: {e}")
            return False

    def get_recent_messages_for_duplicate_check(self, task_id: int, cutoff_timestamp: int) -> list:
        """Get recent messages for duplicate checking"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, message_text, media_hash, media_type, timestamp
                    FROM message_duplicates
                    WHERE task_id = ? AND timestamp > ?
                    ORDER BY timestamp DESC
                ''', (task_id, cutoff_timestamp))
                
                results = cursor.fetchall()
                messages = []
                for row in results:
                    messages.append({
                        'id': row[0],
                        'message_text': row[1],
                        'media_hash': row[2],
                        'media_type': row[3],
                        'timestamp': row[4]
                    })
                
                logger.debug(f"🔍 تم العثور على {len(messages)} رسالة حديثة لفحص التكرار للمهمة {task_id}")
                return messages
                
        except Exception as e:
            logger.error(f"خطأ في الحصول على الرسائل الحديثة لفحص التكرار: {e}")
            return []

    def track_message_for_duplicate_check(self, task_id: int, message_text: str, media_hash: str, media_type: str, timestamp: int):
        """Track message for duplicate checking"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO message_duplicates (task_id, message_text, media_hash, media_type, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (task_id, message_text, media_hash, media_type, timestamp))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"خطأ في تتبع الرسالة لفحص التكرار: {e}")
            return None

    def store_message_for_duplicate_check(self, task_id: int, message_text: str, media_hash: str, media_type: str, timestamp: int):
        """Store message for future duplicate checking"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO message_duplicates (task_id, message_text, media_hash, media_type, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (task_id, message_text, media_hash, media_type, timestamp))
                conn.commit()
                logger.debug(f"💾 تم حفظ الرسالة لفحص التكرار المستقبلي للمهمة {task_id}")
                
        except Exception as e:
            logger.error(f"خطأ في حفظ الرسالة لفحص التكرار: {e}")

    def update_message_timestamp_for_duplicate(self, message_id: int, timestamp: int):
        """Update message timestamp when duplicate is found"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE message_duplicates 
                    SET timestamp = ?
                    WHERE id = ?
                ''', (timestamp, message_id))
                conn.commit()
                logger.debug(f"🔄 تم تحديث طابع الوقت للرسالة المكررة {message_id}")
                
        except Exception as e:
            logger.error(f"خطأ في تحديث طابع الوقت للرسالة المكررة: {e}")

    def create_message_duplicates_table(self):
        """Create message_duplicates table if it doesn't exist"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS message_duplicates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_id INTEGER NOT NULL,
                        message_text TEXT,
                        media_hash TEXT,
                        media_type TEXT,
                        timestamp INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                    )
                ''')
                
                # Create index for faster lookups
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_message_duplicates_task_timestamp 
                    ON message_duplicates (task_id, timestamp)
                ''')
                
                conn.commit()
                logger.info("✅ تم إنشاء جدول message_duplicates والفهارس")
                
        except Exception as e:
            logger.error(f"خطأ في إنشاء جدول message_duplicates: {e}")
        
    def get_pending_message_by_source(self, task_id: int, source_chat_id: str, source_message_id: int) -> Optional[Dict]:
        """Get pending message by source chat and message ID to prevent duplicates"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM pending_messages 
                    WHERE task_id = ? AND source_chat_id = ? AND source_message_id = ?
                    AND status = 'pending'
                ''', (task_id, source_chat_id, source_message_id))
                
                row = cursor.fetchone()
                return dict(row) if row else None
                
        except Exception as e:
            logger.error(f"خطأ في البحث عن رسالة معلقة: {e}")
            return None

    def add_duplicate_filter_columns(self):
        """Add missing duplicate filter columns if they don't exist"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if columns exist and add them if they don't
                columns_to_add = [
                    ('task_duplicate_settings', 'check_media_duplicates', 'BOOLEAN DEFAULT FALSE'),
                    ('task_duplicate_settings', 'check_text_duplicates', 'BOOLEAN DEFAULT FALSE'),
                    ('task_duplicate_settings', 'check_forward_duplicates', 'BOOLEAN DEFAULT FALSE'),
                    ('task_duplicate_settings', 'duplicate_time_window', 'INTEGER DEFAULT 3600'),
                    ('task_duplicate_settings', 'ignore_case', 'BOOLEAN DEFAULT TRUE'),
                    ('task_duplicate_settings', 'ignore_whitespace', 'BOOLEAN DEFAULT TRUE'),
                    ('task_duplicate_settings', 'check_similarity', 'BOOLEAN DEFAULT FALSE'),
                    ('task_duplicate_settings', 'similarity_threshold', 'REAL DEFAULT 0.8')
                ]
                
                for table, column, definition in columns_to_add:
                    try:
                        cursor.execute(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')
                        logger.info(f"✅ تم إضافة العمود {column} إلى الجدول {table}")
                    except Exception as e:
                        if "duplicate column name" in str(e).lower():
                            logger.debug(f"العمود {column} موجود بالفعل في الجدول {table}")
                        else:
                            logger.warning(f"⚠️ خطأ في إضافة العمود {column}: {e}")
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"خطأ في إضافة أعمدة الفلاتر المكررة: {e}")

    def update_character_limit_table(self):
        """Update character limit table structure if needed"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if mode column exists
                cursor.execute("PRAGMA table_info(task_character_limit_settings)")
                columns = [column[1] for column in cursor.fetchall()]
                
                # Add missing columns
                if 'mode' not in columns:
                    cursor.execute('ALTER TABLE task_character_limit_settings ADD COLUMN mode TEXT DEFAULT "allow" CHECK (mode IN ("allow", "block"))')
                    logger.info("✅ تم إضافة عمود mode إلى جدول task_character_limit_settings")
                
                if 'use_range' not in columns:
                    cursor.execute('ALTER TABLE task_character_limit_settings ADD COLUMN use_range BOOLEAN DEFAULT TRUE')
                    logger.info("✅ تم إضافة عمود use_range إلى جدول task_character_limit_settings")

                if 'length_mode' not in columns:
                    cursor.execute('ALTER TABLE task_character_limit_settings ADD COLUMN length_mode TEXT DEFAULT "range" CHECK (length_mode IN ("max", "min", "range"))')
                    logger.info("✅ تم إضافة عمود length_mode إلى جدول task_character_limit_settings")
                
                # Update existing records to use new structure
                cursor.execute('''
                    UPDATE task_character_limit_settings 
                    SET mode = 'allow', use_range = TRUE, length_mode = COALESCE(length_mode, 'range') 
                    WHERE mode IS NULL OR use_range IS NULL OR length_mode IS NULL
                ''')
                
                conn.commit()
                logger.info("✅ تم تحديث بنية جدول حد الأحرف بنجاح")
                
        except Exception as e:
            logger.error(f"خطأ في تحديث بنية جدول حد الأحرف: {e}")

    def add_language_filter_mode_support(self):
        """Add language filter mode support to task_advanced_filters table"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if columns exist first
                cursor.execute("PRAGMA table_info(task_advanced_filters)")
                columns = [row[1] for row in cursor.fetchall()]
                
                # Add language_filter_mode if not exists (allow/block mode)
                if 'language_filter_mode' not in columns:
                    cursor.execute('''
                        ALTER TABLE task_advanced_filters 
                        ADD COLUMN language_filter_mode TEXT DEFAULT 'allow'
                    ''')
                    logger.info("✅ تم إضافة عمود language_filter_mode")
                
                conn.commit()
                logger.info("✅ تم التحقق من وإضافة دعم أوضاع فلتر اللغة")
                
        except Exception as e:
            logger.error(f"خطأ في إضافة دعم أوضاع فلتر اللغة: {e}")

    # Add missing methods for day filters
    def add_day_filter(self, task_id: int, day_number: int, is_allowed: bool = True):
        """Add or update a day filter"""
        return self.set_day_filter(task_id, day_number, is_allowed)
    
    def remove_day_filter(self, task_id: int, day_number: int):
        """Remove a day filter"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM task_day_filters
                    WHERE task_id = ? AND day_number = ?
                ''', (task_id, day_number))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"خطأ في حذف فلتر اليوم: {e}")
            return False
    
    def get_task_day_filters(self, task_id: int):
        """Alias for get_day_filters for backward compatibility"""
        return self.get_day_filters(task_id)
    
    def get_task_languages(self, task_id: int):
        """Get languages for a task - alias for compatibility"""
        filters = self.get_language_filters(task_id)
        return filters.get('languages', [])
    
    def get_task_admin_filters(self, task_id: int):
        """Alias for get_admin_filters for backward compatibility"""
        return self.get_admin_filters(task_id)
    # ===== User Settings Methods =====
    
    def get_user_settings(self, user_id):
        """Get user settings from database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT timezone, language FROM user_settings 
                    WHERE user_id = ?
                """, (user_id,))
                
                result = cursor.fetchone()
                
                if result:
                    return {
                        "timezone": result[0],
                        "language": result[1]
                    }
                else:
                    # Return default values
                    return {
                        "timezone": "Asia/Riyadh",
                        "language": "ar"
                    }
                    
        except Exception as e:
            print(f"خطأ في استرجاع إعدادات المستخدم: {e}")
            return {"timezone": "Asia/Riyadh", "language": "ar"}
    
    def update_user_timezone(self, user_id, timezone):
        """Update user timezone"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Try to update first
                cursor.execute("""
                    UPDATE user_settings SET timezone = ?
                    WHERE user_id = ?
                """, (timezone, user_id))
                
                # If no rows were affected, insert new record
                if cursor.rowcount == 0:
                    cursor.execute("""
                        INSERT INTO user_settings (user_id, timezone, language)
                        VALUES (?, ?, ?)
                    """, (user_id, timezone, "ar"))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"خطأ في تحديث المنطقة الزمنية: {e}")
            return False
    
    def update_user_language(self, user_id, language):
        """Update user language"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Try to update first
                cursor.execute("""
                    UPDATE user_settings SET language = ?
                    WHERE user_id = ?
                """, (language, user_id))
                
                # If no rows were affected, insert new record
                if cursor.rowcount == 0:
                    cursor.execute("""
                        INSERT INTO user_settings (user_id, timezone, language)
                        VALUES (?, ?, ?)
                    """, (user_id, "Asia/Riyadh", language))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"خطأ في تحديث اللغة: {e}")
            return False

    # ===== Watermark Settings Methods =====
    
    def get_watermark_settings(self, task_id: int) -> dict:
        """Get watermark settings for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT enabled, watermark_type, watermark_text, watermark_image_path,
                           position, size_percentage, opacity, text_color, use_original_color,
                           apply_to_photos, apply_to_videos, apply_to_documents, font_size, 
                           default_size, offset_x, offset_y
                    FROM task_watermark_settings WHERE task_id = ?
                ''', (task_id,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'enabled': bool(result[0]),
                        'watermark_type': result[1],
                        'watermark_text': result[2],
                        'watermark_image_path': result[3],
                        'position': result[4],
                        'size_percentage': result[5],
                        'opacity': result[6],
                        'text_color': result[7],
                        'use_original_color': bool(result[8]),
                        'apply_to_photos': bool(result[9]),
                        'apply_to_videos': bool(result[10]),
                        'apply_to_documents': bool(result[11]),
                        'font_size': result[12],
                        'default_size': result[13] if len(result) > 13 and result[13] is not None else 50,
                        'offset_x': result[14] if len(result) > 14 and result[14] is not None else 0,
                        'offset_y': result[15] if len(result) > 15 and result[15] is not None else 0
                    }
                else:
                    return {
                        'enabled': False,
                        'watermark_type': 'text',
                        'watermark_text': '',
                        'watermark_image_path': '',
                        'position': 'bottom_right',
                        'size_percentage': 10,
                        'opacity': 70,
                        'text_color': '#FFFFFF',
                        'use_original_color': False,
                        'apply_to_photos': True,
                        'apply_to_videos': True,
                        'apply_to_documents': False,
                        'font_size': 24,
                        'default_size': 50,
                        'offset_x': 0,
                        'offset_y': 0
                    }
        except Exception as e:
            logger.error(f"خطأ في الحصول على إعدادات العلامة المائية: {e}")
            return {}

    def update_watermark_settings(self, task_id: int, **kwargs) -> bool:
        """Update watermark settings for a task with individual parameters"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get current settings first
                current_settings = self.get_watermark_settings(task_id)
                
                # Update with new values
                for key, value in kwargs.items():
                    current_settings[key] = value
                
                cursor.execute('''
                    INSERT OR REPLACE INTO task_watermark_settings (
                        task_id, enabled, watermark_type, watermark_text, watermark_image_path,
                        position, size_percentage, opacity, text_color, use_original_color,
                        apply_to_photos, apply_to_videos, apply_to_documents, font_size, default_size,
                        offset_x, offset_y, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    task_id,
                    current_settings.get('enabled', False),
                    current_settings.get('watermark_type', 'text'),
                    current_settings.get('watermark_text', ''),
                    current_settings.get('watermark_image_path', ''),
                    current_settings.get('position', 'bottom-right'),
                    current_settings.get('size_percentage', 10),
                    current_settings.get('opacity', 70),
                    current_settings.get('text_color', '#FFFFFF'),
                    current_settings.get('use_original_color', False),
                    current_settings.get('apply_to_photos', True),
                    current_settings.get('apply_to_videos', True),
                    current_settings.get('apply_to_documents', False),
                    current_settings.get('font_size', 24),
                    current_settings.get('default_size', 50),
                    current_settings.get('offset_x', 0),
                    current_settings.get('offset_y', 0)
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في تحديث إعدادات العلامة المائية: {e}")
            return False

    def toggle_watermark_media_type(self, task_id: int, field_name: str) -> bool:
        """Toggle watermark application for specific media type"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get current status
                cursor.execute(f'SELECT {field_name} FROM task_watermark_settings WHERE task_id = ?', (task_id,))
                result = cursor.fetchone()
                
                if result:
                    new_status = not bool(result[0])
                    cursor.execute(f'''
                        UPDATE task_watermark_settings 
                        SET {field_name} = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE task_id = ?
                    ''', (new_status, task_id))
                else:
                    # Create default settings if not exists
                    new_status = True
                    cursor.execute('''
                        INSERT INTO task_watermark_settings 
                        (task_id, enabled, watermark_type, watermark_text, position,
                         apply_to_photos, apply_to_videos, apply_to_documents)
                        VALUES (?, FALSE, 'text', 'العلامة المائية', 'bottom_right', ?, ?, ?)
                    ''', (task_id, field_name == 'apply_to_photos', 
                          field_name == 'apply_to_videos', 
                          field_name == 'apply_to_documents'))
                
                conn.commit()
                return new_status
        except Exception as e:
            logger.error(f"خطأ في تبديل نوع وسائط العلامة المائية: {e}")
            return False

    def toggle_watermark(self, task_id: int) -> bool:
        """Toggle watermark on/off for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get current status
                cursor.execute('SELECT enabled FROM task_watermark_settings WHERE task_id = ?', (task_id,))
                result = cursor.fetchone()
                
                if result:
                    new_enabled = not result[0]
                    cursor.execute('''
                        UPDATE task_watermark_settings 
                        SET enabled = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE task_id = ?
                    ''', (new_enabled, task_id))
                else:
                    # Create default settings if not exists
                    new_enabled = True
                    cursor.execute('''
                        INSERT INTO task_watermark_settings 
                        (task_id, enabled, watermark_type, watermark_text, position)
                        VALUES (?, ?, 'text', 'العلامة المائية', 'bottom_right')
                    ''', (task_id, new_enabled))
                
                conn.commit()
                return new_enabled
        except Exception as e:
            logger.error(f"خطأ في تبديل العلامة المائية: {e}")
            return False

    def update_watermark_text(self, task_id: int, text: str) -> bool:
        """Update watermark text for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE task_watermark_settings 
                    SET watermark_text = ?, watermark_type = 'text', updated_at = CURRENT_TIMESTAMP
                    WHERE task_id = ?
                ''', (text, task_id))
                if cursor.rowcount == 0:
                    # Create if doesn't exist
                    cursor.execute('''
                        INSERT INTO task_watermark_settings 
                        (task_id, watermark_text, watermark_type)
                        VALUES (?, ?, 'text')
                    ''', (task_id, text))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في تحديث نص العلامة المائية: {e}")
            return False

    def update_watermark_image(self, task_id: int, image_path: str) -> bool:
        """Update watermark image for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE task_watermark_settings 
                    SET watermark_image_path = ?, watermark_type = 'image', updated_at = CURRENT_TIMESTAMP
                    WHERE task_id = ?
                ''', (image_path, task_id))
                if cursor.rowcount == 0:
                    # Create if doesn't exist
                    cursor.execute('''
                        INSERT INTO task_watermark_settings 
                        (task_id, watermark_image_path, watermark_type)
                        VALUES (?, ?, 'image')
                    ''', (task_id, image_path))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في تحديث صورة العلامة المائية: {e}")
            return False

    def update_watermark_position(self, task_id: int, position: str) -> bool:
        """Update watermark position for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE task_watermark_settings 
                    SET position = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE task_id = ?
                ''', (position, task_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"خطأ في تحديث موقع العلامة المائية: {e}")
            return False

    def update_watermark_media_settings(self, task_id: int, apply_to_photos: bool, apply_to_videos: bool, apply_to_documents: bool) -> bool:
        """Update watermark media application settings"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE task_watermark_settings 
                    SET apply_to_photos = ?, apply_to_videos = ?, apply_to_documents = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE task_id = ?
                ''', (apply_to_photos, apply_to_videos, apply_to_documents, task_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"خطأ في تحديث إعدادات الوسائط للعلامة المائية: {e}")
            return False

    # ===== Pending Messages Management (Manual Publishing Mode) =====

    def add_pending_message(self, task_id: int, user_id: int, source_chat_id: str, 
                           source_message_id: int, message_data: str, message_type: str = 'text') -> int:
        """Add a pending message for manual approval"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO pending_messages 
                (task_id, user_id, source_chat_id, source_message_id, message_data, message_type)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (task_id, user_id, source_chat_id, source_message_id, message_data, message_type))
            conn.commit()
            pending_id = cursor.lastrowid
            logger.info(f"✅ تم حفظ رسالة للموافقة اليدوية - ID: {pending_id}")
            return pending_id

    def get_pending_message(self, pending_id: int) -> Optional[Dict]:
        """Get a specific pending message"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM pending_messages WHERE id = ?
            ''', (pending_id,))
            result = cursor.fetchone()
            
            if result:
                return dict(result)
            return None

    def get_pending_messages(self, user_id: int, task_id: int = None) -> List[Dict]:
        """Get all pending messages for a user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if task_id:
                cursor.execute('''
                    SELECT * FROM pending_messages 
                    WHERE user_id = ? AND task_id = ? AND status = 'pending'
                    ORDER BY created_at DESC
                ''', (user_id, task_id))
            else:
                cursor.execute('''
                    SELECT * FROM pending_messages 
                    WHERE user_id = ? AND status = 'pending'
                    ORDER BY created_at DESC
                ''', (user_id,))
            
            return [dict(row) for row in cursor.fetchall()]

    def update_pending_message_status(self, pending_id: int, status: str, approval_message_id: int = None):
        """Update the status of a pending message"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if approval_message_id:
                cursor.execute('''
                    UPDATE pending_messages 
                    SET status = ?, approval_message_id = ?
                    WHERE id = ?
                ''', (status, approval_message_id, pending_id))
            else:
                cursor.execute('''
                    UPDATE pending_messages 
                    SET status = ?
                    WHERE id = ?
                ''', (status, pending_id))
            conn.commit()
            return cursor.rowcount > 0

    # ===== Audio Metadata Settings Management =====
    def get_audio_metadata_settings(self, task_id: int) -> dict:
        """Get audio metadata settings for a task (returns defaults if missing)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT enabled, template, album_art_enabled, album_art_path, apply_art_to_all,
                       audio_merge_enabled, intro_audio_path, outro_audio_path, intro_position,
                       preserve_original, convert_to_mp3
                FROM task_audio_metadata_settings
                WHERE task_id = ?
            ''', (task_id,))
            row = cursor.fetchone()
            if row:
                return {
                    'enabled': bool(row['enabled']),
                    'template': row['template'] or 'default',
                    'album_art_enabled': bool(row['album_art_enabled']),
                    'album_art_path': row['album_art_path'] or '',
                    'apply_art_to_all': bool(row['apply_art_to_all']),
                    'audio_merge_enabled': bool(row['audio_merge_enabled']),
                    'intro_audio_path': row['intro_audio_path'] or '',
                    'outro_audio_path': row['outro_audio_path'] or '',
                    'intro_position': row['intro_position'] or 'start',
                    'preserve_original': bool(row['preserve_original']),
                    'convert_to_mp3': bool(row['convert_to_mp3'])
                }
            else:
                return {
                    'enabled': False,
                    'template': 'default',
                    'album_art_enabled': False,
                    'album_art_path': '',
                    'apply_art_to_all': False,
                    'audio_merge_enabled': False,
                    'intro_audio_path': '',
                    'outro_audio_path': '',
                    'intro_position': 'start',
                    'preserve_original': True,
                    'convert_to_mp3': True
                }

    def update_audio_metadata_enabled(self, task_id: int, enabled: bool) -> bool:
        """Enable/disable audio metadata processing for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO task_audio_metadata_settings (
                    task_id, enabled, template, album_art_enabled, album_art_path, apply_art_to_all,
                    audio_merge_enabled, intro_audio_path, outro_audio_path, intro_position,
                    preserve_original, convert_to_mp3, updated_at
                )
                SELECT ?, ?, COALESCE(template, 'default'), COALESCE(album_art_enabled, FALSE), COALESCE(album_art_path, NULL),
                       COALESCE(apply_art_to_all, FALSE), COALESCE(audio_merge_enabled, FALSE), COALESCE(intro_audio_path, NULL),
                       COALESCE(outro_audio_path, NULL), COALESCE(intro_position, 'start'), COALESCE(preserve_original, TRUE),
                       COALESCE(convert_to_mp3, TRUE), CURRENT_TIMESTAMP
                FROM task_audio_metadata_settings WHERE task_id = ?
                UNION SELECT ?, ?, 'default', FALSE, NULL, FALSE, FALSE, NULL, NULL, 'start', TRUE, TRUE, CURRENT_TIMESTAMP
                WHERE NOT EXISTS (SELECT 1 FROM task_audio_metadata_settings WHERE task_id = ?)
            ''', (task_id, enabled, task_id, task_id, enabled, task_id))
            conn.commit()
            return True

    def update_audio_metadata_template(self, task_id: int, template_name: str) -> bool:
        """Set audio metadata template for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO task_audio_metadata_settings (
                    task_id, enabled, template, album_art_enabled, album_art_path, apply_art_to_all,
                    audio_merge_enabled, intro_audio_path, outro_audio_path, intro_position,
                    preserve_original, convert_to_mp3, updated_at
                )
                SELECT ?, COALESCE(enabled, FALSE), ?, COALESCE(album_art_enabled, FALSE), COALESCE(album_art_path, NULL),
                       COALESCE(apply_art_to_all, FALSE), COALESCE(audio_merge_enabled, FALSE), COALESCE(intro_audio_path, NULL),
                       COALESCE(outro_audio_path, NULL), COALESCE(intro_position, 'start'), COALESCE(preserve_original, TRUE),
                       COALESCE(convert_to_mp3, TRUE), CURRENT_TIMESTAMP
                FROM task_audio_metadata_settings WHERE task_id = ?
                UNION SELECT ?, FALSE, ?, FALSE, NULL, FALSE, FALSE, NULL, NULL, 'start', TRUE, TRUE, CURRENT_TIMESTAMP
                WHERE NOT EXISTS (SELECT 1 FROM task_audio_metadata_settings WHERE task_id = ?)
            ''', (task_id, template_name, task_id, task_id, template_name, task_id))
            conn.commit()
            return True

    def set_album_art_settings(self, task_id: int, enabled: Optional[bool] = None, path: Optional[str] = None, apply_to_all: Optional[bool] = None) -> bool:
        """Update album art settings for a task"""
        current = self.get_audio_metadata_settings(task_id)
        new_values = {
            'enabled': current['enabled'],
            'template': current['template'],
            'album_art_enabled': current['album_art_enabled'] if enabled is None else bool(enabled),
            'album_art_path': current['album_art_path'] if path is None else path,
            'apply_art_to_all': current['apply_art_to_all'] if apply_to_all is None else bool(apply_to_all),
            'audio_merge_enabled': current['audio_merge_enabled'],
            'intro_audio_path': current['intro_audio_path'],
            'outro_audio_path': current['outro_audio_path'],
            'intro_position': current['intro_position'],
            'preserve_original': current['preserve_original'],
            'convert_to_mp3': current['convert_to_mp3']
        }
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO task_audio_metadata_settings (
                    task_id, enabled, template, album_art_enabled, album_art_path, apply_art_to_all,
                    audio_merge_enabled, intro_audio_path, outro_audio_path, intro_position,
                    preserve_original, convert_to_mp3, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (task_id, new_values['enabled'], new_values['template'], new_values['album_art_enabled'],
                  new_values['album_art_path'], new_values['apply_art_to_all'], new_values['audio_merge_enabled'],
                  new_values['intro_audio_path'], new_values['outro_audio_path'], new_values['intro_position'],
                  new_values['preserve_original'], new_values['convert_to_mp3']))
            conn.commit()
            return True

    def set_audio_merge_settings(self, task_id: int, enabled: Optional[bool] = None, intro_path: Optional[str] = None, outro_path: Optional[str] = None, intro_position: Optional[str] = None) -> bool:
        """Update audio merge settings for a task"""
        current = self.get_audio_metadata_settings(task_id)
        new_values = {
            'enabled': current['enabled'],
            'template': current['template'],
            'album_art_enabled': current['album_art_enabled'],
            'album_art_path': current['album_art_path'],
            'apply_art_to_all': current['apply_art_to_all'],
            'audio_merge_enabled': current['audio_merge_enabled'] if enabled is None else bool(enabled),
            'intro_audio_path': current['intro_audio_path'] if intro_path is None else intro_path,
            'outro_audio_path': current['outro_audio_path'] if outro_path is None else outro_path,
            'intro_position': current['intro_position'] if intro_position is None else intro_position,
            'preserve_original': current['preserve_original'],
            'convert_to_mp3': current['convert_to_mp3']
        }
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO task_audio_metadata_settings (
                    task_id, enabled, template, album_art_enabled, album_art_path, apply_art_to_all,
                    audio_merge_enabled, intro_audio_path, outro_audio_path, intro_position,
                    preserve_original, convert_to_mp3, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (task_id, new_values['enabled'], new_values['template'], new_values['album_art_enabled'],
                  new_values['album_art_path'], new_values['apply_art_to_all'], new_values['audio_merge_enabled'],
                  new_values['intro_audio_path'], new_values['outro_audio_path'], new_values['intro_position'],
                  new_values['preserve_original'], new_values['convert_to_mp3']))
            conn.commit()
            return True

    def set_audio_quality_settings(self, task_id: int, preserve_original: Optional[bool] = None, convert_to_mp3: Optional[bool] = None) -> bool:
        """Update audio quality/format settings for a task"""
        current = self.get_audio_metadata_settings(task_id)
        new_values = {
            'enabled': current['enabled'],
            'template': current['template'],
            'album_art_enabled': current['album_art_enabled'],
            'album_art_path': current['album_art_path'],
            'apply_art_to_all': current['apply_art_to_all'],
            'audio_merge_enabled': current['audio_merge_enabled'],
            'intro_audio_path': current['intro_audio_path'],
            'outro_audio_path': current['outro_audio_path'],
            'intro_position': current['intro_position'],
            'preserve_original': current['preserve_original'] if preserve_original is None else bool(preserve_original),
            'convert_to_mp3': current['convert_to_mp3'] if convert_to_mp3 is None else bool(convert_to_mp3)
        }
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO task_audio_metadata_settings (
                    task_id, enabled, template, album_art_enabled, album_art_path, apply_art_to_all,
                    audio_merge_enabled, intro_audio_path, outro_audio_path, intro_position,
                    preserve_original, convert_to_mp3, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (task_id, new_values['enabled'], new_values['template'], new_values['album_art_enabled'],
                  new_values['album_art_path'], new_values['apply_art_to_all'], new_values['audio_merge_enabled'],
                  new_values['intro_audio_path'], new_values['outro_audio_path'], new_values['intro_position'],
                  new_values['preserve_original'], new_values['convert_to_mp3']))
            conn.commit()
            return True

    def update_audio_metadata_setting(self, task_id: int, setting_name: str, value) -> bool:
        """Update a specific audio metadata setting for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get current settings
                current = self.get_audio_metadata_settings(task_id)
                
                # Update the specific setting
                current[setting_name] = value
                
                # Insert or replace with updated values
                cursor.execute('''
                    INSERT OR REPLACE INTO task_audio_metadata_settings (
                        task_id, enabled, template, album_art_enabled, album_art_path, apply_art_to_all,
                        audio_merge_enabled, intro_audio_path, outro_audio_path, intro_position,
                        preserve_original, convert_to_mp3, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    task_id, 
                    current.get('enabled', False),
                    current.get('template', 'default'),
                    current.get('album_art_enabled', False),
                    current.get('album_art_path', ''),
                    current.get('apply_art_to_all', False),
                    current.get('audio_merge_enabled', False),
                    current.get('intro_audio_path', ''),
                    current.get('outro_audio_path', ''),
                    current.get('intro_position', 'start'),
                    current.get('preserve_original', True),
                    current.get('convert_to_mp3', False)
                ))
                
                conn.commit()
                logger.info(f"✅ تم تحديث إعداد الوسوم الصوتية '{setting_name}' للمهمة {task_id}: {value}")
                return True
                
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث إعداد الوسوم الصوتية '{setting_name}' للمهمة {task_id}: {e}")
            return False

    # Audio Template Settings Management
    def get_audio_template_settings(self, task_id: int) -> Dict:
        """Get audio template settings for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT title_template, artist_template, album_artist_template, album_template,
                           year_template, genre_template, composer_template, comment_template,
                           track_template, length_template, lyrics_template
                    FROM task_audio_template_settings
                    WHERE task_id = ?
                ''', (task_id,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'title_template': result[0] or '$title',
                        'artist_template': result[1] or '$artist',
                        'album_artist_template': result[2] or '$album_artist',
                        'album_template': result[3] or '$album',
                        'year_template': result[4] or '$year',
                        'genre_template': result[5] or '$genre',
                        'composer_template': result[6] or '$composer',
                        'comment_template': result[7] or '$comment',
                        'track_template': result[8] or '$track',
                        'length_template': result[9] or '$length',
                        'lyrics_template': result[10] or '$lyrics'
                    }
                else:
                    # Return default values if no settings exist
                    return {
                        'title_template': '$title',
                        'artist_template': '$artist',
                        'album_artist_template': '$album_artist',
                        'album_template': '$album',
                        'year_template': '$year',
                        'genre_template': '$genre',
                        'composer_template': '$composer',
                        'comment_template': '$comment',
                        'track_template': '$track',
                        'length_template': '$length',
                        'lyrics_template': '$lyrics'
                    }
                    
        except Exception as e:
            logger.error(f"❌ خطأ في جلب إعدادات قالب الوسوم الصوتية للمهمة {task_id}: {e}")
            return {
                'title_template': '$title',
                'artist_template': '$artist',
                'album_artist_template': '$album_artist',
                'album_template': '$album',
                'year_template': '$year',
                'genre_template': '$genre',
                'composer_template': '$composer',
                'comment_template': '$comment',
                'track_template': '$track',
                'length_template': '$length',
                'lyrics_template': '$lyrics'
            }

    def update_audio_template_setting(self, task_id: int, tag_name: str, template_value: str) -> bool:
        """Update a specific audio template setting for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Whitelist of valid template columns
                valid_columns = {
                    'title': 'title_template',
                    'artist': 'artist_template',
                    'album_artist': 'album_artist_template',
                    'album': 'album_template',
                    'year': 'year_template',
                    'genre': 'genre_template',
                    'composer': 'composer_template',
                    'comment': 'comment_template',
                    'track': 'track_template',
                    'length': 'length_template',
                    'lyrics': 'lyrics_template',
                }

                column_name = valid_columns.get(tag_name)
                if not column_name:
                    logger.error(f"❌ وسم غير مدعوم للتحديث: '{tag_name}'")
                    return False
                
                # Check if record exists
                cursor.execute('SELECT 1 FROM task_audio_template_settings WHERE task_id = ?', (task_id,))
                exists = cursor.fetchone()
                
                if exists:
                    # Update existing record
                    cursor.execute(
                        f"UPDATE task_audio_template_settings SET {column_name} = ?, updated_at = CURRENT_TIMESTAMP WHERE task_id = ?",
                        (template_value, task_id)
                    )
                else:
                    # Create new record with default values
                    cursor.execute('''
                        INSERT INTO task_audio_template_settings (
                            task_id, title_template, artist_template, album_artist_template, album_template,
                            year_template, genre_template, composer_template, comment_template,
                            track_template, length_template, lyrics_template, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ''', (
                        task_id,
                        template_value if column_name == 'title_template' else '$title',
                        template_value if column_name == 'artist_template' else '$artist',
                        template_value if column_name == 'album_artist_template' else '$album_artist',
                        template_value if column_name == 'album_template' else '$album',
                        template_value if column_name == 'year_template' else '$year',
                        template_value if column_name == 'genre_template' else '$genre',
                        template_value if column_name == 'composer_template' else '$composer',
                        template_value if column_name == 'comment_template' else '$comment',
                        template_value if column_name == 'track_template' else '$track',
                        template_value if column_name == 'length_template' else '$length',
                        template_value if column_name == 'lyrics_template' else '$lyrics'
                    ))
                
                conn.commit()
                logger.info(f"✅ تم تحديث قالب الوسم '{tag_name}' للمهمة {task_id}: {template_value}")
                return True
                
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث قالب الوسم '{tag_name}' للمهمة {task_id}: {e}")
            return False

    def reset_audio_template_settings(self, task_id: int) -> bool:
        """Reset audio template settings to default values"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO task_audio_template_settings (
                        task_id, title_template, artist_template, album_artist_template, album_template,
                        year_template, genre_template, composer_template, comment_template,
                        track_template, length_template, lyrics_template, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    task_id, '$title', '$artist', '$album_artist', '$album', '$year', '$genre',
                    '$composer', '$comment', '$track', '$length', '$lyrics'
                ))
                
                conn.commit()
                logger.info(f"✅ تم إعادة تعيين إعدادات قالب الوسوم الصوتية للمهمة {task_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ خطأ في إعادة تعيين إعدادات قالب الوسوم الصوتية للمهمة {task_id}: {e}")
            return False

    def set_audio_quality_settings(self, task_id: int, preserve_original: Optional[bool] = None, convert_to_mp3: Optional[bool] = None) -> bool:
        """Update audio quality/format settings for a task"""
        current = self.get_audio_metadata_settings(task_id)
        new_values = {
            'enabled': current['enabled'],
            'template': current['template'],
            'album_art_enabled': current['album_art_enabled'],
            'album_art_path': current['album_art_path'],
            'apply_art_to_all': current['apply_art_to_all'],
            'audio_merge_enabled': current['audio_merge_enabled'],
            'intro_audio_path': current['intro_audio_path'],
            'outro_audio_path': current['outro_audio_path'],
            'intro_position': current['intro_position'],
            'preserve_original': current['preserve_original'] if preserve_original is None else bool(preserve_original),
            'convert_to_mp3': current['convert_to_mp3'] if convert_to_mp3 is None else bool(convert_to_mp3)
        }
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO task_audio_metadata_settings (
                    task_id, enabled, template, album_art_enabled, album_art_path, apply_art_to_all,
                    audio_merge_enabled, intro_audio_path, outro_audio_path, intro_position,
                    preserve_original, convert_to_mp3, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (task_id, new_values['enabled'], new_values['template'], new_values['album_art_enabled'],
                  new_values['album_art_path'], new_values['apply_art_to_all'], new_values['audio_merge_enabled'],
                  new_values['intro_audio_path'], new_values['outro_audio_path'], new_values['intro_position'],
                  new_values['preserve_original'], new_values['convert_to_mp3']))
            conn.commit()
            return True

    def create_pending_message(self, task_id: int, user_id: int, source_chat_id: str, 
                              source_message_id: int, message_data: str, message_type: str) -> bool:
        """Create a new pending message"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO pending_messages (
                    task_id, user_id, source_chat_id, source_message_id, 
                    message_data, message_type, status, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP, datetime('now', '+24 hours'))
            ''', (task_id, user_id, source_chat_id, source_message_id, message_data, message_type))
            conn.commit()
            return cursor.rowcount > 0

    def get_pending_message(self, pending_id: int) -> Optional[Dict]:
        """Get a specific pending message"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM pending_messages WHERE id = ?
            ''', (pending_id,))
            result = cursor.fetchone()
            
            if result:
                return dict(result)
            return None

    # ===== Audio Tag Cleaning (apply text cleaning to tags) =====
    def get_audio_tag_cleaning_settings(self, task_id: int) -> Dict:
        """Get audio tag cleaning settings for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT enabled, clean_title, clean_artist, clean_album_artist, clean_album,
                       clean_year, clean_genre, clean_composer, clean_comment,
                       clean_track, clean_length, clean_lyrics
                FROM task_audio_tag_cleaning_settings WHERE task_id = ?
            ''', (task_id,))
            row = cursor.fetchone()
            if row:
                return {
                    'enabled': bool(row['enabled']),
                    'clean_title': bool(row['clean_title']),
                    'clean_artist': bool(row['clean_artist']),
                    'clean_album_artist': bool(row['clean_album_artist']),
                    'clean_album': bool(row['clean_album']),
                    'clean_year': bool(row['clean_year']),
                    'clean_genre': bool(row['clean_genre']),
                    'clean_composer': bool(row['clean_composer']),
                    'clean_comment': bool(row['clean_comment']),
                    'clean_track': bool(row['clean_track']),
                    'clean_length': bool(row['clean_length']),
                    'clean_lyrics': bool(row['clean_lyrics'])
                }
            else:
                # Create default record
                self.create_default_audio_tag_cleaning_settings(task_id)
                return {
                    'enabled': False,
                    'clean_title': True,
                    'clean_artist': True,
                    'clean_album_artist': True,
                    'clean_album': True,
                    'clean_year': True,
                    'clean_genre': True,
                    'clean_composer': True,
                    'clean_comment': True,
                    'clean_track': True,
                    'clean_length': False,
                    'clean_lyrics': True
                }

    def create_default_audio_tag_cleaning_settings(self, task_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO task_audio_tag_cleaning_settings (task_id)
                VALUES (?)
            ''', (task_id,))
            conn.commit()

    def update_audio_tag_cleaning_toggle(self, task_id: int, enabled: bool) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO task_audio_tag_cleaning_settings (task_id) VALUES (?)
            ''', (task_id,))
            cursor.execute('''
                UPDATE task_audio_tag_cleaning_settings
                SET enabled = ?, updated_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
            ''', (enabled, task_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_audio_tag_cleaning_field(self, task_id: int, field_name: str, enabled: bool) -> bool:
        valid_fields = {
            'clean_title', 'clean_artist', 'clean_album_artist', 'clean_album',
            'clean_year', 'clean_genre', 'clean_composer', 'clean_comment',
            'clean_track', 'clean_length', 'clean_lyrics'
        }
        if field_name not in valid_fields:
            logger.error(f"Invalid audio tag cleaning field: {field_name}")
            return False
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO task_audio_tag_cleaning_settings (task_id) VALUES (?)
            ''', (task_id,))
            cursor.execute(f'''UPDATE task_audio_tag_cleaning_settings SET {field_name} = ?, updated_at = CURRENT_TIMESTAMP WHERE task_id = ?''', (enabled, task_id))
            conn.commit()
            return cursor.rowcount > 0

    # ===== Audio Tags Advanced Processing Functions =====

    def create_audio_tags_advanced_tables(self):
        """Create audio tags advanced processing tables (text cleaning, word filters, replacements, headers/footers)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Audio tags text cleaning settings
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_audio_tag_text_cleaning_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL UNIQUE,
                    enabled BOOLEAN DEFAULT FALSE,
                    remove_links BOOLEAN DEFAULT FALSE,
                    remove_emojis BOOLEAN DEFAULT FALSE,
                    remove_hashtags BOOLEAN DEFAULT FALSE,
                    remove_phone_numbers BOOLEAN DEFAULT FALSE,
                    remove_empty_lines BOOLEAN DEFAULT FALSE,
                    remove_lines_with_keywords BOOLEAN DEFAULT FALSE,
                    apply_to_title BOOLEAN DEFAULT TRUE,
                    apply_to_artist BOOLEAN DEFAULT TRUE,
                    apply_to_album_artist BOOLEAN DEFAULT TRUE,
                    apply_to_album BOOLEAN DEFAULT TRUE,
                    apply_to_year BOOLEAN DEFAULT TRUE,
                    apply_to_genre BOOLEAN DEFAULT TRUE,
                    apply_to_composer BOOLEAN DEFAULT TRUE,
                    apply_to_comment BOOLEAN DEFAULT TRUE,
                    apply_to_track BOOLEAN DEFAULT TRUE,
                    apply_to_lyrics BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            # Audio tags text cleaning keywords table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_audio_tag_text_cleaning_keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    keyword TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                    UNIQUE(task_id, keyword)
                )
            ''')

            # Audio tags word filters
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_audio_tag_word_filters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    filter_type TEXT NOT NULL CHECK (filter_type IN ('whitelist', 'blacklist')),
                    is_enabled BOOLEAN DEFAULT FALSE,
                    apply_to_title BOOLEAN DEFAULT TRUE,
                    apply_to_artist BOOLEAN DEFAULT TRUE,
                    apply_to_album_artist BOOLEAN DEFAULT TRUE,
                    apply_to_album BOOLEAN DEFAULT TRUE,
                    apply_to_year BOOLEAN DEFAULT TRUE,
                    apply_to_genre BOOLEAN DEFAULT TRUE,
                    apply_to_composer BOOLEAN DEFAULT TRUE,
                    apply_to_comment BOOLEAN DEFAULT TRUE,
                    apply_to_track BOOLEAN DEFAULT TRUE,
                    apply_to_lyrics BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                    UNIQUE(task_id, filter_type)
                )
            ''')

            # Audio tags word filter entries table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audio_tag_word_filter_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filter_id INTEGER NOT NULL,
                    word_or_phrase TEXT NOT NULL,
                    is_case_sensitive BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (filter_id) REFERENCES task_audio_tag_word_filters (id) ON DELETE CASCADE
                )
            ''')

            # Audio tags text replacements
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_audio_tag_text_replacements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    is_enabled BOOLEAN DEFAULT FALSE,
                    apply_to_title BOOLEAN DEFAULT TRUE,
                    apply_to_artist BOOLEAN DEFAULT TRUE,
                    apply_to_album_artist BOOLEAN DEFAULT TRUE,
                    apply_to_album BOOLEAN DEFAULT TRUE,
                    apply_to_year BOOLEAN DEFAULT TRUE,
                    apply_to_genre BOOLEAN DEFAULT TRUE,
                    apply_to_composer BOOLEAN DEFAULT TRUE,
                    apply_to_comment BOOLEAN DEFAULT TRUE,
                    apply_to_track BOOLEAN DEFAULT TRUE,
                    apply_to_lyrics BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                    UNIQUE(task_id)
                )
            ''')

            # Audio tags text replacement entries table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audio_tag_text_replacement_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    replacement_id INTEGER NOT NULL,
                    find_text TEXT NOT NULL,
                    replace_text TEXT NOT NULL,
                    is_case_sensitive BOOLEAN DEFAULT FALSE,
                    is_whole_word BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (replacement_id) REFERENCES task_audio_tag_text_replacements (id) ON DELETE CASCADE
                )
            ''')

            # Audio tags header/footer settings
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_audio_tag_header_footer_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL UNIQUE,
                    header_enabled BOOLEAN DEFAULT FALSE,
                    header_text TEXT DEFAULT '',
                    footer_enabled BOOLEAN DEFAULT FALSE,
                    footer_text TEXT DEFAULT '',
                    apply_to_title BOOLEAN DEFAULT TRUE,
                    apply_to_artist BOOLEAN DEFAULT TRUE,
                    apply_to_album_artist BOOLEAN DEFAULT TRUE,
                    apply_to_album BOOLEAN DEFAULT TRUE,
                    apply_to_year BOOLEAN DEFAULT FALSE,
                    apply_to_genre BOOLEAN DEFAULT TRUE,
                    apply_to_composer BOOLEAN DEFAULT TRUE,
                    apply_to_comment BOOLEAN DEFAULT TRUE,
                    apply_to_track BOOLEAN DEFAULT FALSE,
                    apply_to_lyrics BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            ''')

            conn.commit()
            logger.info("✅ تم إنشاء جداول الوسوم الصوتية المتقدمة بنجاح")
            return True
        except Exception as e:
            logger.error(f"خطأ في إنشاء جداول الوسوم الصوتية المتقدمة: {e}")
            return False

    # === Audio Tags Text Cleaning Functions ===

    def get_audio_tag_text_cleaning_settings(self, task_id: int) -> dict:
        """Get audio tag text cleaning settings for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM task_audio_tag_text_cleaning_settings WHERE task_id = ?
            ''', (task_id,))
            row = cursor.fetchone()
        
        if row:
            return {
                'enabled': bool(row['enabled']),
                'remove_links': bool(row['remove_links']),
                'remove_emojis': bool(row['remove_emojis']),
                'remove_hashtags': bool(row['remove_hashtags']),
                'remove_phone_numbers': bool(row['remove_phone_numbers']),
                'remove_empty_lines': bool(row['remove_empty_lines']),
                'remove_lines_with_keywords': bool(row['remove_lines_with_keywords']),
                'apply_to_title': bool(row['apply_to_title']),
                'apply_to_artist': bool(row['apply_to_artist']),
                'apply_to_album_artist': bool(row['apply_to_album_artist']),
                'apply_to_album': bool(row['apply_to_album']),
                'apply_to_year': bool(row['apply_to_year']),
                'apply_to_genre': bool(row['apply_to_genre']),
                'apply_to_composer': bool(row['apply_to_composer']),
                'apply_to_comment': bool(row['apply_to_comment']),
                'apply_to_track': bool(row['apply_to_track']),
                'apply_to_lyrics': bool(row['apply_to_lyrics'])
            }
        else:
            # Create default settings
            self.create_default_audio_tag_text_cleaning_settings(task_id)
            return self.get_default_audio_tag_text_cleaning_settings()

    def create_default_audio_tag_text_cleaning_settings(self, task_id: int):
        """Create default audio tag text cleaning settings"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO task_audio_tag_text_cleaning_settings (task_id)
                VALUES (?)
            ''', (task_id,))
            conn.commit()

    def get_default_audio_tag_text_cleaning_settings(self) -> dict:
        """Get default audio tag text cleaning settings"""
        return {
            'enabled': False,
            'remove_links': False,
            'remove_emojis': False,
            'remove_hashtags': False,
            'remove_phone_numbers': False,
            'remove_empty_lines': False,
            'remove_lines_with_keywords': False,
            'apply_to_title': True,
            'apply_to_artist': True,
            'apply_to_album_artist': True,
            'apply_to_album': True,
            'apply_to_year': True,
            'apply_to_genre': True,
            'apply_to_composer': True,
            'apply_to_comment': True,
            'apply_to_track': True,
            'apply_to_lyrics': True
        }

    def update_audio_tag_text_cleaning_setting(self, task_id: int, setting_name: str, enabled: bool) -> bool:
        """Update specific audio tag text cleaning setting"""
        valid_settings = {
            'enabled', 'remove_links', 'remove_emojis', 'remove_hashtags',
            'remove_phone_numbers', 'remove_empty_lines', 'remove_lines_with_keywords',
            'apply_to_title', 'apply_to_artist', 'apply_to_album_artist',
            'apply_to_album', 'apply_to_year', 'apply_to_genre',
            'apply_to_composer', 'apply_to_comment', 'apply_to_track', 'apply_to_lyrics'
        }
        
        if setting_name not in valid_settings:
            logger.error(f"Invalid audio tag text cleaning setting: {setting_name}")
            return False

        cursor = self.conn.cursor()
        # Create default record if doesn't exist
        cursor.execute('''
            INSERT OR IGNORE INTO task_audio_tag_text_cleaning_settings (task_id)
            VALUES (?)
        ''', (task_id,))
        
        # Update the specific setting
        cursor.execute(f'''
            UPDATE task_audio_tag_text_cleaning_settings
            SET {setting_name} = ?, updated_at = CURRENT_TIMESTAMP
            WHERE task_id = ?
        ''', (enabled, task_id))
        self.conn.commit()
        return cursor.rowcount > 0

    def add_audio_tag_text_cleaning_keyword(self, task_id: int, keyword: str) -> bool:
        """Add keyword to audio tag text cleaning keywords list"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO task_audio_tag_text_cleaning_keywords (task_id, keyword)
                    VALUES (?, ?)
                ''', (task_id, keyword))
                conn.commit()
                return cursor.rowcount > 0
            except sqlite3.IntegrityError:
                return False  # Keyword already exists

    def remove_audio_tag_text_cleaning_keyword(self, task_id: int, keyword: str) -> bool:
        """Remove keyword from audio tag text cleaning keywords list"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM task_audio_tag_text_cleaning_keywords
                WHERE task_id = ? AND keyword = ?
            ''', (task_id, keyword))
            conn.commit()
            return cursor.rowcount > 0

    def get_audio_tag_text_cleaning_keywords(self, task_id: int) -> list:
        """Get all keywords for audio tag text cleaning"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT keyword FROM task_audio_tag_text_cleaning_keywords
                WHERE task_id = ?
                ORDER BY keyword
            ''', (task_id,))
            return [row['keyword'] for row in cursor.fetchall()]

    # === Audio Tags Word Filter Functions ===

    def get_audio_tag_word_filter_settings(self, task_id: int, filter_type: str) -> dict:
        """Get audio tag word filter settings for a task and filter type"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM task_audio_tag_word_filters WHERE task_id = ? AND filter_type = ?
            ''', (task_id, filter_type))
            row = cursor.fetchone()
        
        if row:
            return {
                'id': row['id'],
                'is_enabled': bool(row['is_enabled']),
                'apply_to_title': bool(row['apply_to_title']),
                'apply_to_artist': bool(row['apply_to_artist']),
                'apply_to_album_artist': bool(row['apply_to_album_artist']),
                'apply_to_album': bool(row['apply_to_album']),
                'apply_to_year': bool(row['apply_to_year']),
                'apply_to_genre': bool(row['apply_to_genre']),
                'apply_to_composer': bool(row['apply_to_composer']),
                'apply_to_comment': bool(row['apply_to_comment']),
                'apply_to_track': bool(row['apply_to_track']),
                'apply_to_lyrics': bool(row['apply_to_lyrics'])
            }
        else:
            # Create default settings
            self.create_default_audio_tag_word_filter_settings(task_id, filter_type)
            return self.get_default_audio_tag_word_filter_settings()

    def create_default_audio_tag_word_filter_settings(self, task_id: int, filter_type: str):
        """Create default audio tag word filter settings"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO task_audio_tag_word_filters (task_id, filter_type)
                VALUES (?, ?)
            ''', (task_id, filter_type))
            conn.commit()

    def get_default_audio_tag_word_filter_settings(self) -> dict:
        """Get default audio tag word filter settings"""
        return {
            'is_enabled': False,
            'apply_to_title': True,
            'apply_to_artist': True,
            'apply_to_album_artist': True,
            'apply_to_album': True,
            'apply_to_year': True,
            'apply_to_genre': True,
            'apply_to_composer': True,
            'apply_to_comment': True,
            'apply_to_track': True,
            'apply_to_lyrics': True
        }

    def update_audio_tag_word_filter_setting(self, task_id: int, filter_type: str, setting_name: str, enabled: bool) -> bool:
        """Update specific audio tag word filter setting"""
        valid_settings = {
            'is_enabled', 'apply_to_title', 'apply_to_artist', 'apply_to_album_artist',
            'apply_to_album', 'apply_to_year', 'apply_to_genre',
            'apply_to_composer', 'apply_to_comment', 'apply_to_track', 'apply_to_lyrics'
        }
        
        if setting_name not in valid_settings or filter_type not in ['whitelist', 'blacklist']:
            logger.error(f"Invalid audio tag word filter setting: {setting_name} or filter_type: {filter_type}")
            return False

        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Create default record if doesn't exist
            cursor.execute('''
                INSERT OR IGNORE INTO task_audio_tag_word_filters (task_id, filter_type)
                VALUES (?, ?)
            ''', (task_id, filter_type))
            
            # Update the specific setting
            cursor.execute(f'''
                UPDATE task_audio_tag_word_filters
                SET {setting_name} = ?, updated_at = CURRENT_TIMESTAMP
                WHERE task_id = ? AND filter_type = ?
            ''', (enabled, task_id, filter_type))
            conn.commit()
        return cursor.rowcount > 0

    def add_audio_tag_word_filter_entry(self, task_id: int, filter_type: str, word_or_phrase: str, is_case_sensitive: bool = False) -> bool:
        """Add word/phrase to audio tag word filter"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get or create filter record
            cursor.execute('''
                INSERT OR IGNORE INTO task_audio_tag_word_filters (task_id, filter_type)
                VALUES (?, ?)
            ''', (task_id, filter_type))
            
            cursor.execute('''
                SELECT id FROM task_audio_tag_word_filters WHERE task_id = ? AND filter_type = ?
            ''', (task_id, filter_type))
            row = cursor.fetchone()
            filter_id = row['id']
            
            cursor.execute('''
                INSERT INTO audio_tag_word_filter_entries (filter_id, word_or_phrase, is_case_sensitive)
                VALUES (?, ?, ?)
            ''', (filter_id, word_or_phrase, is_case_sensitive))
            conn.commit()
        return cursor.rowcount > 0

    def remove_audio_tag_word_filter_entry(self, task_id: int, filter_type: str, word_or_phrase: str) -> bool:
        """Remove word/phrase from audio tag word filter"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM audio_tag_word_filter_entries
                WHERE filter_id IN (
                    SELECT id FROM task_audio_tag_word_filters 
                    WHERE task_id = ? AND filter_type = ?
                ) AND word_or_phrase = ?
            ''', (task_id, filter_type, word_or_phrase))
            conn.commit()
        return cursor.rowcount > 0

    def get_audio_tag_word_filter_entries(self, task_id: int, filter_type: str) -> list:
        """Get all words/phrases for audio tag word filter"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT word_or_phrase, is_case_sensitive FROM audio_tag_word_filter_entries
                WHERE filter_id IN (
                    SELECT id FROM task_audio_tag_word_filters 
                    WHERE task_id = ? AND filter_type = ?
                )
                ORDER BY word_or_phrase
            ''', (task_id, filter_type))
            return [{'word_or_phrase': row['word_or_phrase'], 'is_case_sensitive': bool(row['is_case_sensitive'])} for row in cursor.fetchall()]

    # === Audio Tags Text Replacement Functions ===

    def get_audio_tag_text_replacement_settings(self, task_id: int) -> dict:
        """Get audio tag text replacement settings for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM task_audio_tag_text_replacements WHERE task_id = ?
            ''', (task_id,))
            row = cursor.fetchone()
        
        if row:
            return {
                'id': row['id'],
                'is_enabled': bool(row['is_enabled']),
                'apply_to_title': bool(row['apply_to_title']),
                'apply_to_artist': bool(row['apply_to_artist']),
                'apply_to_album_artist': bool(row['apply_to_album_artist']),
                'apply_to_album': bool(row['apply_to_album']),
                'apply_to_year': bool(row['apply_to_year']),
                'apply_to_genre': bool(row['apply_to_genre']),
                'apply_to_composer': bool(row['apply_to_composer']),
                'apply_to_comment': bool(row['apply_to_comment']),
                'apply_to_track': bool(row['apply_to_track']),
                'apply_to_lyrics': bool(row['apply_to_lyrics'])
            }
        else:
            # Create default settings
            self.create_default_audio_tag_text_replacement_settings(task_id)
            return self.get_default_audio_tag_text_replacement_settings()

    def create_default_audio_tag_text_replacement_settings(self, task_id: int):
        """Create default audio tag text replacement settings"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO task_audio_tag_text_replacements (task_id)
                VALUES (?)
            ''', (task_id,))
            conn.commit()

    def get_default_audio_tag_text_replacement_settings(self) -> dict:
        """Get default audio tag text replacement settings"""
        return {
            'is_enabled': False,
            'apply_to_title': True,
            'apply_to_artist': True,
            'apply_to_album_artist': True,
            'apply_to_album': True,
            'apply_to_year': True,
            'apply_to_genre': True,
            'apply_to_composer': True,
            'apply_to_comment': True,
            'apply_to_track': True,
            'apply_to_lyrics': True
        }

    def update_audio_tag_text_replacement_setting(self, task_id: int, setting_name: str, enabled: bool) -> bool:
        """Update specific audio tag text replacement setting"""
        valid_settings = {
            'is_enabled', 'apply_to_title', 'apply_to_artist', 'apply_to_album_artist',
            'apply_to_album', 'apply_to_year', 'apply_to_genre',
            'apply_to_composer', 'apply_to_comment', 'apply_to_track', 'apply_to_lyrics'
        }
        
        if setting_name not in valid_settings:
            logger.error(f"Invalid audio tag text replacement setting: {setting_name}")
            return False

        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Create default record if doesn't exist
            cursor.execute('''
                INSERT OR IGNORE INTO task_audio_tag_text_replacements (task_id)
                VALUES (?)
            ''', (task_id,))
            
            # Update the specific setting
            cursor.execute(f'''
                UPDATE task_audio_tag_text_replacements
                SET {setting_name} = ?, updated_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
            ''', (enabled, task_id))
            conn.commit()
        return cursor.rowcount > 0

    def add_audio_tag_text_replacement_entry(self, task_id: int, find_text: str, replace_text: str, is_case_sensitive: bool = False, is_whole_word: bool = False) -> bool:
        """Add text replacement entry for audio tags"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get or create replacement record
            cursor.execute('''
                INSERT OR IGNORE INTO task_audio_tag_text_replacements (task_id)
                VALUES (?)
            ''', (task_id,))
            
            cursor.execute('''
                SELECT id FROM task_audio_tag_text_replacements WHERE task_id = ?
            ''', (task_id,))
            row = cursor.fetchone()
            replacement_id = row['id']
            
            cursor.execute('''
                INSERT INTO audio_tag_text_replacement_entries (replacement_id, find_text, replace_text, is_case_sensitive, is_whole_word)
                VALUES (?, ?, ?, ?, ?)
            ''', (replacement_id, find_text, replace_text, is_case_sensitive, is_whole_word))
            conn.commit()
        return cursor.rowcount > 0

    def remove_audio_tag_text_replacement_entry(self, task_id: int, find_text: str) -> bool:
        """Remove text replacement entry from audio tags"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM audio_tag_text_replacement_entries
                WHERE replacement_id IN (
                    SELECT id FROM task_audio_tag_text_replacements 
                    WHERE task_id = ?
                ) AND find_text = ?
            ''', (task_id, find_text))
            conn.commit()
        return cursor.rowcount > 0

    def get_audio_tag_text_replacement_entries(self, task_id: int) -> list:
        """Get all text replacement entries for audio tags"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT find_text, replace_text, is_case_sensitive, is_whole_word 
                FROM audio_tag_text_replacement_entries
                WHERE replacement_id IN (
                    SELECT id FROM task_audio_tag_text_replacements 
                    WHERE task_id = ?
                )
                ORDER BY find_text
            ''', (task_id,))
            return [{
                'find_text': row['find_text'],
                'replace_text': row['replace_text'],
                'is_case_sensitive': bool(row['is_case_sensitive']),
                'is_whole_word': bool(row['is_whole_word'])
            } for row in cursor.fetchall()]

    # === Audio Tags Header/Footer Functions ===

    def get_audio_tag_header_footer_settings(self, task_id: int) -> dict:
        """Get audio tag header/footer settings for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM task_audio_tag_header_footer_settings WHERE task_id = ?
            ''', (task_id,))
            row = cursor.fetchone()
        
        if row:
            return {
                'header_enabled': bool(row['header_enabled']),
                'header_text': row['header_text'] or '',
                'footer_enabled': bool(row['footer_enabled']),
                'footer_text': row['footer_text'] or '',
                'apply_to_title': bool(row['apply_to_title']),
                'apply_to_artist': bool(row['apply_to_artist']),
                'apply_to_album_artist': bool(row['apply_to_album_artist']),
                'apply_to_album': bool(row['apply_to_album']),
                'apply_to_year': bool(row['apply_to_year']),
                'apply_to_genre': bool(row['apply_to_genre']),
                'apply_to_composer': bool(row['apply_to_composer']),
                'apply_to_comment': bool(row['apply_to_comment']),
                'apply_to_track': bool(row['apply_to_track']),
                'apply_to_lyrics': bool(row['apply_to_lyrics'])
            }
        else:
            # Create default settings
            self.create_default_audio_tag_header_footer_settings(task_id)
            return self.get_default_audio_tag_header_footer_settings()

    def create_default_audio_tag_header_footer_settings(self, task_id: int):
        """Create default audio tag header/footer settings"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO task_audio_tag_header_footer_settings (task_id)
                VALUES (?)
            ''', (task_id,))
            conn.commit()

    def get_default_audio_tag_header_footer_settings(self) -> dict:
        """Get default audio tag header/footer settings"""
        return {
            'header_enabled': False,
            'header_text': '',
            'footer_enabled': False,
            'footer_text': '',
            'apply_to_title': True,
            'apply_to_artist': True,
            'apply_to_album_artist': True,
            'apply_to_album': True,
            'apply_to_year': False,
            'apply_to_genre': True,
            'apply_to_composer': True,
            'apply_to_comment': True,
            'apply_to_track': False,
            'apply_to_lyrics': True
        }

    def update_audio_tag_header_footer_setting(self, task_id: int, setting_name: str, value) -> bool:
        """Update specific audio tag header/footer setting"""
        valid_text_settings = {'header_text', 'footer_text'}
        valid_bool_settings = {
            'header_enabled', 'footer_enabled', 'apply_to_title', 'apply_to_artist', 
            'apply_to_album_artist', 'apply_to_album', 'apply_to_year', 'apply_to_genre',
            'apply_to_composer', 'apply_to_comment', 'apply_to_track', 'apply_to_lyrics'
        }
        
        if setting_name not in valid_text_settings and setting_name not in valid_bool_settings:
            logger.error(f"Invalid audio tag header/footer setting: {setting_name}")
            return False

        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Create default record if doesn't exist
            cursor.execute('''
                INSERT OR IGNORE INTO task_audio_tag_header_footer_settings (task_id)
                VALUES (?)
            ''', (task_id,))
            
            # Update the specific setting
            cursor.execute(f'''
                UPDATE task_audio_tag_header_footer_settings
                SET {setting_name} = ?, updated_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
            ''', (value, task_id))
            conn.commit()
        return cursor.rowcount > 0

    # ===== Enhanced Audio Text Processing Methods =====
    
    def get_audio_text_processing_settings(self, task_id: int) -> Dict:
        """Get all audio text processing settings for a task"""
        try:
            cleaning_settings = self.get_audio_tag_text_cleaning_settings(task_id)
            replacements_settings = self.get_audio_text_replacements_settings(task_id)
            word_filters_settings = self.get_audio_word_filters_settings(task_id)
            header_footer_settings = self.get_audio_tag_header_footer_settings(task_id)
            
            return {
                'text_cleaning_enabled': cleaning_settings.get('enabled', False),
                'text_replacements_enabled': replacements_settings.get('enabled', False),
                'word_filters_enabled': word_filters_settings.get('enabled', False),
                'header_footer_enabled': header_footer_settings.get('header_enabled', False) or header_footer_settings.get('footer_enabled', False)
            }
        except Exception as e:
            logger.error(f"خطأ في جلب إعدادات معالجة النصوص للوسوم الصوتية: {e}")
            return {
                'text_cleaning_enabled': False,
                'text_replacements_enabled': False,
                'word_filters_enabled': False,
                'header_footer_enabled': False
            }
    
    def get_audio_text_replacements_settings(self, task_id: int) -> Dict:
        """Get audio text replacements settings for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT is_enabled
                FROM task_audio_tag_text_replacements
                WHERE task_id = ?
            ''', (task_id,))
            
            row = cursor.fetchone()
            return {
                'enabled': bool(row['is_enabled']) if row else False
            }
    
    def get_audio_word_filters_settings(self, task_id: int) -> Dict:
        """Get audio word filters settings for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT enabled
                FROM task_audio_tag_word_filters
                WHERE task_id = ? 
                LIMIT 1
            ''', (task_id,))
            
            row = cursor.fetchone()
            return {
                'enabled': bool(row['enabled']) if row else False
            }
    
    def get_audio_selected_tags(self, task_id: int) -> List[str]:
        """Get selected tags for audio text processing"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT selected_tags
                FROM task_audio_tag_selection_settings
                WHERE task_id = ?
            ''', (task_id,))
            
            row = cursor.fetchone()
            if row and row['selected_tags']:
                try:
                    import json
                    return json.loads(row['selected_tags'])
                except:
                    return []
            return []
    
    def update_audio_text_cleaning_enabled(self, task_id: int, enabled: bool) -> bool:
        """Toggle audio text cleaning enabled status"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get current settings
                current = self.get_audio_tag_text_cleaning_settings(task_id)
                
                # Update enabled status
                cursor.execute('''
                    INSERT OR REPLACE INTO task_audio_tag_text_cleaning_settings 
                    (task_id, enabled, remove_links, remove_emojis, remove_hashtags, 
                     remove_phone_numbers, remove_empty_lines, remove_keywords, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (task_id, enabled, 
                      current.get('remove_links', False),
                      current.get('remove_emojis', False),
                      current.get('remove_hashtags', False),
                      current.get('remove_phone_numbers', False),
                      current.get('remove_empty_lines', False),
                      current.get('remove_keywords', False)))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في تحديث حالة تنظيف الوسوم الصوتية: {e}")
            return False
    
    def update_audio_text_replacements_enabled(self, task_id: int, enabled: bool) -> bool:
        """Toggle audio text replacements enabled status"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO task_audio_tag_text_replacements 
                    (task_id, is_enabled, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (task_id, enabled))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في تحديث حالة استبدالات الوسوم الصوتية: {e}")
            return False
    
    def update_audio_word_filters_enabled(self, task_id: int, enabled: bool) -> bool:
        """Toggle audio word filters enabled status"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO task_audio_tag_word_filters 
                    (task_id, filter_type, enabled, updated_at)
                    VALUES (?, 'whitelist', ?, CURRENT_TIMESTAMP)
                ''', (task_id, enabled))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في تحديث حالة فلاتر الوسوم الصوتية: {e}")
            return False
    
    def update_audio_header_footer_enabled(self, task_id: int, enabled: bool) -> bool:
        """Toggle audio header/footer enabled status"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO task_audio_tag_header_footer_settings 
                    (task_id, header_enabled, footer_enabled, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', (task_id, enabled, enabled))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في تحديث حالة هيدر/فوتر الوسوم الصوتية: {e}")
            return False
    
    def update_audio_selected_tags(self, task_id: int, selected_tags: List[str]) -> bool:
        """Update selected tags for audio text processing"""
        try:
            import json
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if table exists, if not create it
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS task_audio_tag_selection_settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_id INTEGER NOT NULL UNIQUE,
                        selected_tags TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                    )
                ''')
                
                cursor.execute('''
                    INSERT OR REPLACE INTO task_audio_tag_selection_settings 
                    (task_id, selected_tags, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (task_id, json.dumps(selected_tags)))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"خطأ في تحديث الوسوم المحددة للمعالجة: {e}")
            return False
    
    def toggle_audio_tag_selection(self, task_id: int, tag_name: str) -> bool:
        """Toggle a specific tag in the selection"""
        try:
            current_tags = self.get_audio_selected_tags(task_id)
            if tag_name in current_tags:
                current_tags.remove(tag_name)
            else:
                current_tags.append(tag_name)
            
            return self.update_audio_selected_tags(task_id, current_tags)
        except Exception as e:
            logger.error(f"خطأ في تبديل اختيار الوسم {tag_name}: {e}")
            return False