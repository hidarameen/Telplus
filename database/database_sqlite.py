
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
    def create_task(self, user_id: int, task_name: str, source_chat_ids: list, 
                   source_chat_names: list, target_chat_id: str, target_chat_name: str) -> int:
        """Create new forwarding task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            task_ids = []
            
            for i, source_chat_id in enumerate(source_chat_ids):
                source_chat_name = source_chat_names[i] if source_chat_names and i < len(source_chat_names) else source_chat_id
                
                if source_chat_name is None or source_chat_name == '':
                    source_chat_name = source_chat_id
                
                cursor.execute('''
                    INSERT INTO tasks 
                    (user_id, task_name, source_chat_id, source_chat_name, target_chat_id, target_chat_name)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, task_name, source_chat_id, source_chat_name, target_chat_id, target_chat_name))
                
                task_id = cursor.lastrowid
                task_ids.append(task_id)
            
            conn.commit()
            return task_ids[0] if task_ids else None

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
        """Get active tasks for user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, task_name, source_chat_id, source_chat_name, target_chat_id, target_chat_name, forward_mode
                FROM tasks 
                WHERE user_id = ? AND is_active = TRUE
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
