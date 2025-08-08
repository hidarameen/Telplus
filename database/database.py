
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

            conn.commit()
            logger.info("✅ تم تهيئة جداول SQLite بنجاح")

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
