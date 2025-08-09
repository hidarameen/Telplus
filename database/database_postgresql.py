"""
PostgreSQL Database management for Telegram Bot System
"""
import psycopg2
import psycopg2.extras
import logging
import os
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        """Initialize PostgreSQL database connection"""
        self.database_url = os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")

        # Test connection
        self.test_connection()
        self.init_database()

    def get_connection(self):
        """Get PostgreSQL database connection"""
        return psycopg2.connect(
            self.database_url,
            cursor_factory=psycopg2.extras.RealDictCursor
        )

    def test_connection(self):
        """Test database connection"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    logger.info("✅ تم الاتصال بقاعدة بيانات PostgreSQL بنجاح")
        except Exception as e:
            logger.error(f"❌ فشل الاتصال بقاعدة البيانات: {e}")
            raise

    def init_database(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Tasks table with PostgreSQL syntax
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

                # User sessions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        user_id BIGINT PRIMARY KEY,
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
                        user_id BIGINT PRIMARY KEY,
                        state TEXT,
                        data TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Task text formatting settings table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS task_text_formatting_settings (
                        id SERIAL PRIMARY KEY,
                        task_id INTEGER NOT NULL UNIQUE,
                        format_type TEXT DEFAULT 'markdown',
                        text_formatting_enabled BOOLEAN DEFAULT TRUE,
                        hyperlink_text TEXT,
                        hyperlink_url TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                    )
                ''')

                conn.commit()
                logger.info("✅ تم تهيئة جداول PostgreSQL بنجاح")

    # User Session Management
    def save_user_session(self, user_id: int, phone_number: str, session_string: str):
        """Save user session"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO user_sessions 
                    (user_id, phone_number, session_string, is_authenticated, updated_at)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id) DO UPDATE SET
                        phone_number = EXCLUDED.phone_number,
                        session_string = EXCLUDED.session_string,
                        is_authenticated = EXCLUDED.is_authenticated,
                        updated_at = CURRENT_TIMESTAMP
                ''', (user_id, phone_number, session_string, True))
                conn.commit()

    def get_user_session(self, user_id: int) -> Optional[Tuple[str, str, str]]:
        """Get user session"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT phone_number, session_string 
                    FROM user_sessions 
                    WHERE user_id = %s AND is_authenticated = TRUE
                ''', (user_id,))
                result = cursor.fetchone()
                if result:
                    return (result['phone_number'], result['session_string'], result['session_string'])
                return None

    def is_user_authenticated(self, user_id: int) -> bool:
        """Check if user is authenticated"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT 1 FROM user_sessions 
                    WHERE user_id = %s AND is_authenticated = TRUE
                ''', (user_id,))
                return cursor.fetchone() is not None

    def delete_user_session(self, user_id: int):
        """Delete user session"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('DELETE FROM user_sessions WHERE user_id = %s', (user_id,))
                conn.commit()

    def get_all_authenticated_users(self):
        """Get all authenticated users with their sessions"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT user_id, phone_number, session_string 
                    FROM user_sessions 
                    WHERE is_authenticated = TRUE AND session_string IS NOT NULL
                ''')
                return cursor.fetchall()

    # Task Management
    def create_task(self, user_id: int, task_name: str, source_chat_ids: list, 
                   source_chat_names: list, target_chat_id: str, target_chat_name: str) -> int:
        """Create new forwarding task"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Handle multiple source chats by creating separate tasks for each
                task_ids = []

                for i, source_chat_id in enumerate(source_chat_ids):
                    source_chat_name = source_chat_names[i] if source_chat_names and i < len(source_chat_names) else source_chat_id

                    if source_chat_name is None or source_chat_name == '':
                        source_chat_name = source_chat_id

                    cursor.execute('''
                        INSERT INTO tasks 
                        (user_id, task_name, source_chat_id, source_chat_name, target_chat_id, target_chat_name)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id
                    ''', (user_id, task_name, source_chat_id, source_chat_name, target_chat_id, target_chat_name))

                    task_id = cursor.fetchone()['id']
                    task_ids.append(task_id)

                conn.commit()
                return task_ids[0] if task_ids else None

    def get_user_tasks(self, user_id: int):
        """Get all tasks for a user"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, task_name, source_chat_id, source_chat_name, target_chat_id, 
                           target_chat_name, forward_mode, is_active, created_at
                    FROM tasks 
                    WHERE user_id = %s
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
            with conn.cursor() as cursor:
                if user_id:
                    cursor.execute("""
                        SELECT id, task_name, source_chat_id, source_chat_name, target_chat_id, 
                               target_chat_name, forward_mode, is_active, created_at
                        FROM tasks 
                        WHERE id = %s AND user_id = %s
                    """, (task_id, user_id))
                else:
                    cursor.execute("""
                        SELECT id, task_name, source_chat_id, source_chat_name, target_chat_id, 
                               target_chat_name, forward_mode, is_active, created_at
                        FROM tasks 
                        WHERE id = %s
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
            with conn.cursor() as cursor:
                cursor.execute('''
                    UPDATE tasks SET is_active = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND user_id = %s
                ''', (is_active, task_id, user_id))
                conn.commit()
                return cursor.rowcount > 0

    def delete_task(self, task_id: int, user_id: int):
        """Delete task"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('DELETE FROM tasks WHERE id = %s AND user_id = %s', 
                             (task_id, user_id))
                conn.commit()
                return cursor.rowcount > 0

    def get_active_tasks(self, user_id: int) -> List[Dict]:
        """Get active tasks for user"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT id, task_name, source_chat_id, source_chat_name, target_chat_id, target_chat_name, forward_mode
                    FROM tasks 
                    WHERE user_id = %s AND is_active = TRUE
                ''', (user_id,))

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

    def get_all_active_tasks(self):
        """Get all active tasks for userbot"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
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
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO conversation_states 
                    (user_id, state, data, updated_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id) DO UPDATE SET
                        state = EXCLUDED.state,
                        data = EXCLUDED.data,
                        updated_at = CURRENT_TIMESTAMP
                ''', (user_id, state, data))
                conn.commit()

    def get_conversation_state(self, user_id: int) -> Optional[Tuple[str, str]]:
        """Get conversation state for user"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT state, data FROM conversation_states 
                    WHERE user_id = %s
                ''', (user_id,))
                result = cursor.fetchone()
                if result:
                    return (result['state'], result['data'])
                return None

    def clear_conversation_state(self, user_id: int):
        """Clear conversation state for user"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('DELETE FROM conversation_states WHERE user_id = %s', (user_id,))
                conn.commit()

    # Advanced Task Management Functions
    def update_task_forward_mode(self, task_id: int, user_id: int, forward_mode: str):
        """Update task forward mode (copy/forward)"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    UPDATE tasks SET forward_mode = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND user_id = %s
                ''', (forward_mode, task_id, user_id))
                conn.commit()
                return cursor.rowcount > 0

    def add_task_source(self, task_id: int, chat_id: str, chat_name: str = None):
        """Add source to task"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO task_sources (task_id, chat_id, chat_name)
                    VALUES (%s, %s, %s)
                    RETURNING id
                ''', (task_id, chat_id, chat_name))
                result = cursor.fetchone()
                conn.commit()
                return result['id'] if result else None

    def add_task_target(self, task_id: int, chat_id: str, chat_name: str = None):
        """Add target to task"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO task_targets (task_id, chat_id, chat_name)
                    VALUES (%s, %s, %s)
                    RETURNING id
                ''', (task_id, chat_id, chat_name))
                result = cursor.fetchone()
                conn.commit()
                return result['id'] if result else None

    def get_task_sources(self, task_id: int):
        """Get all sources for a task"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT id, chat_id, chat_name FROM task_sources
                    WHERE task_id = %s
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
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT id, chat_id, chat_name FROM task_targets
                    WHERE task_id = %s
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
            with conn.cursor() as cursor:
                # First check if the source exists
                cursor.execute('SELECT COUNT(*) as count FROM task_sources WHERE id = %s AND task_id = %s', 
                             (source_id, task_id))
                exists = cursor.fetchone()['count'] > 0

                if not exists:
                    logger.warning(f"⚠️ محاولة حذف مصدر غير موجود: source_id={source_id}, task_id={task_id}")
                    return False

                cursor.execute('''
                    DELETE FROM task_sources 
                    WHERE id = %s AND task_id = %s
                ''', (source_id, task_id))
                conn.commit()

                deleted_count = cursor.rowcount
                logger.info(f"🗑️ حذف مصدر: source_id={source_id}, task_id={task_id}, deleted={deleted_count}")
                return deleted_count > 0

    def remove_task_target(self, target_id: int, task_id: int):
        """Remove target from task"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # First check if the target exists
                cursor.execute('SELECT COUNT(*) as count FROM task_targets WHERE id = %s AND task_id = %s', 
                             (target_id, task_id))
                exists = cursor.fetchone()['count'] > 0

                if not exists:
                    logger.warning(f"⚠️ محاولة حذف هدف غير موجود: target_id={target_id}, task_id={task_id}")
                    return False

                cursor.execute('''
                    DELETE FROM task_targets 
                    WHERE id = %s AND task_id = %s
                ''', (target_id, task_id))
                conn.commit()

                deleted_count = cursor.rowcount
                logger.info(f"🗑️ حذف هدف: target_id={target_id}, task_id={task_id}, deleted={deleted_count}")
                return deleted_count > 0

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
            with conn.cursor() as cursor:

                # Check if already migrated
                cursor.execute('SELECT COUNT(*) as count FROM task_sources WHERE task_id = %s', (task_id,))
                sources_count = cursor.fetchone()['count']
                cursor.execute('SELECT COUNT(*) as count FROM task_targets WHERE task_id = %s', (task_id,))
                targets_count = cursor.fetchone()['count']

                if sources_count > 0 and targets_count > 0:
                    logger.info(f"✅ المهمة {task_id} مهاجرة بالفعل ({sources_count} مصادر, {targets_count} أهداف)")
                    return True  # Already migrated

                logger.info(f"🔄 بدء تهجير المهمة {task_id} إلى البنية الجديدة")

                # Migrate source if not exists
                if sources_count == 0 and task.get('source_chat_id'):
                    cursor.execute('''
                        INSERT INTO task_sources (task_id, chat_id, chat_name)
                        VALUES (%s, %s, %s)
                    ''', (task_id, task['source_chat_id'], task['source_chat_name']))
                    logger.info(f"➕ أضيف مصدر: {task['source_chat_id']}")

                # Migrate target if not exists
                if targets_count == 0 and task.get('target_chat_id'):
                    cursor.execute('''
                        INSERT INTO task_targets (task_id, chat_id, chat_name)
                        VALUES (%s, %s, %s)
                    ''', (task_id, task['target_chat_id'], task['target_chat_name']))
                    logger.info(f"➕ أضيف هدف: {task['target_chat_id']}")

                conn.commit()
                logger.info(f"✅ تم تهجير المهمة {task_id} بنجاح")
                return True

    def copy_session_from_sqlite(self, sqlite_db_path: str = 'telegram_bot.db'):
        """Copy user session from SQLite to PostgreSQL"""
        if not os.path.exists(sqlite_db_path):
            logger.info("📄 لا توجد قاعدة بيانات SQLite قديمة للنسخ منها")
            return

        try:
            import sqlite3

            # Connect to SQLite
            sqlite_conn = sqlite3.connect(sqlite_db_path)
            sqlite_cursor = sqlite_conn.cursor()

            # Get authenticated users
            sqlite_cursor.execute('''
                SELECT user_id, phone_number, session_string 
                FROM user_sessions 
                WHERE is_authenticated = TRUE AND session_string IS NOT NULL
            ''')

            sessions = sqlite_cursor.fetchall()

            if sessions:
                logger.info(f"📋 تم العثور على {len(sessions)} جلسة في SQLite")

                # Copy to PostgreSQL
                with self.get_connection() as conn:
                    with conn.cursor() as cursor:
                        for user_id, phone_number, session_string in sessions:
                            cursor.execute('''
                                INSERT INTO user_sessions 
                                (user_id, phone_number, session_string, is_authenticated)
                                VALUES (%s, %s, %s, %s)
                                ON CONFLICT (user_id) DO UPDATE SET
                                    phone_number = EXCLUDED.phone_number,
                                    session_string = EXCLUDED.session_string,
                                    is_authenticated = EXCLUDED.is_authenticated,
                                    updated_at = CURRENT_TIMESTAMP
                            ''', (user_id, phone_number, session_string, True))
                            logger.info(f"✅ تم نسخ جلسة المستخدم {user_id} ({phone_number})")

                        conn.commit()

                logger.info(f"🎉 تم نسخ {len(sessions)} جلسة إلى PostgreSQL بنجاح")
            else:
                logger.info("📄 لا توجد جلسات محفوظة في SQLite")

            sqlite_conn.close()

        except Exception as e:
            logger.error(f"❌ خطأ في نسخ الجلسات من SQLite: {e}")

    def update_text_formatting_settings(self, task_id: int, format_type: str = None, text_formatting_enabled: bool = None, hyperlink_text: str = None, hyperlink_url: str = None) -> bool:
        """Update text formatting settings for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Build update query dynamically
                updates = []
                params = []
                param_counter = 1

                if format_type is not None:
                    updates.append(f"format_type = ${param_counter}")
                    params.append(format_type)
                    param_counter += 1

                if text_formatting_enabled is not None:
                    updates.append(f"text_formatting_enabled = ${param_counter}")
                    params.append(text_formatting_enabled)
                    param_counter += 1

                if hyperlink_text is not None:
                    updates.append(f"hyperlink_text = ${param_counter}")
                    params.append(hyperlink_text)
                    param_counter += 1

                if hyperlink_url is not None:
                    updates.append(f"hyperlink_url = ${param_counter}")
                    params.append(hyperlink_url)
                    param_counter += 1

                if not updates:
                    return False

                params.append(task_id)

                cursor.execute(f'''
                    UPDATE task_text_formatting_settings 
                    SET {', '.join(updates)}
                    WHERE task_id = ${param_counter}
                ''', params)

                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"خطأ في تحديث إعدادات تنسيق النص: {e}")
            return False

    def get_text_formatting_settings(self, task_id: int) -> dict:
        """Get text formatting settings for a task"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT text_formatting_enabled, format_type, hyperlink_text, hyperlink_url
                    FROM task_text_formatting_settings 
                    WHERE task_id = %s
                ''', (task_id,))
                result = cursor.fetchone()

                if result:
                    return {
                        'text_formatting_enabled': bool(result['text_formatting_enabled']),
                        'format_type': result['format_type'] or 'regular',
                        'hyperlink_text': result['hyperlink_text'],
                        'hyperlink_url': result['hyperlink_url']
                    }
                else:
                    # Create default settings
                    cursor.execute('''
                        INSERT INTO task_text_formatting_settings (task_id, format_type, text_formatting_enabled)
                        VALUES (%s, 'regular', FALSE)
                    ''', (task_id,))
                    conn.commit()
                    return {
                        'text_formatting_enabled': False,
                        'format_type': 'regular',
                        'hyperlink_text': None,
                        'hyperlink_url': None
                    }
        except Exception as e:
            logger.error(f"خطأ في الحصول على إعدادات تنسيق النص: {e}")
            return {
                'text_formatting_enabled': False,
                'format_type': 'regular',
                'hyperlink_text': None,
                'hyperlink_url': None
            }