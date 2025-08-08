"""
Database management for Telegram Bot System
"""
import sqlite3
import logging
import os
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_file: str = 'telegram_bot.db'):
        """Initialize database connection"""
        self.db_file = db_file
        self.init_database()

    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_file)

    def init_database(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Tasks table - Updated to support new features
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
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Task Sources table - For supporting multiple sources per task
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

            # Task Targets table - For supporting multiple targets per task
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

            # Add new columns for existing databases
            try:
                cursor.execute('ALTER TABLE tasks ADD COLUMN task_name TEXT DEFAULT "مهمة توجيه"')
            except sqlite3.OperationalError:
                pass
            
            try:
                cursor.execute('ALTER TABLE tasks ADD COLUMN forward_mode TEXT DEFAULT "forward"')
            except sqlite3.OperationalError:
                pass

            # User sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    user_id INTEGER PRIMARY KEY,
                    phone_number TEXT,
                    session_string TEXT,
                    is_authenticated BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Conversation states table for managing user states
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversation_states (
                    user_id INTEGER PRIMARY KEY,
                    state TEXT,
                    data TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.commit()
            logger.info("✅ تم تهيئة قاعدة البيانات بنجاح")

    # User Session Management
    def save_user_session(self, user_id: int, phone_number: str, session_string: str):
        """Save user session"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO user_sessions 
                (user_id, phone_number, session_string, is_authenticated, updated_at)
                VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
            ''', (user_id, phone_number, session_string))
            conn.commit()

    def get_user_session(self, user_id: int) -> Optional[Tuple[str, str]]:
        """Get user session"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT phone_number, session_string 
                FROM user_sessions 
                WHERE user_id = ? AND is_authenticated = 1
            ''', (user_id,))
            result = cursor.fetchone()
            return result if result else None

    def is_user_authenticated(self, user_id: int) -> bool:
        """Check if user is authenticated"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 1 FROM user_sessions 
                WHERE user_id = ? AND is_authenticated = 1
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
                WHERE is_authenticated = 1 AND session_string IS NOT NULL
            ''')
            return cursor.fetchall()

    # Task Management
    def create_task(self, user_id: int, task_name: str, source_chat_ids: list, 
                   source_chat_names: list, target_chat_id: str, target_chat_name: str) -> int:
        """Create new forwarding task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Handle multiple source chats by creating separate tasks for each
            task_ids = []
            
            for i, source_chat_id in enumerate(source_chat_ids):
                source_chat_name = source_chat_names[i] if source_chat_names and i < len(source_chat_names) else source_chat_id
                
                # Ensure source_chat_name is not None
                if source_chat_name is None or source_chat_name == '':
                    source_chat_name = source_chat_id
                
                cursor.execute('''
                    INSERT INTO tasks 
                    (user_id, task_name, source_chat_id, source_chat_name, target_chat_id, target_chat_name)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, task_name, source_chat_id, source_chat_name, target_chat_id, target_chat_name))
                
                task_ids.append(cursor.lastrowid)
            
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
                    'id': row[0],
                    'task_name': row[1],
                    'source_chat_id': row[2],
                    'source_chat_name': row[3],
                    'target_chat_id': row[4],
                    'target_chat_name': row[5],
                    'forward_mode': row[6] or 'forward',
                    'is_active': bool(row[7]),
                    'created_at': row[8]
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
                    'created_at': row[8]
                }
            return None

    def update_task_status(self, task_id: int, user_id: int, is_active: bool):
        """Update task active status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE tasks 
                SET is_active = ?, updated_at = CURRENT_TIMESTAMP
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

    def delete_all_user_tasks(self, user_id: int):
        """Delete all user tasks"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM tasks WHERE user_id = ?', (user_id,))
            conn.commit()

    def get_active_tasks(self, user_id: int) -> List[Dict]:
        """Get active tasks for user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, source_chat_id, source_chat_name, target_chat_id, target_chat_name
                FROM tasks 
                WHERE user_id = ? AND is_active = 1
            ''', (user_id,))

            tasks = []
            for row in cursor.fetchall():
                tasks.append({
                    'id': row[0],
                    'source_chat_id': row[1],
                    'source_chat_name': row[2],
                    'target_chat_id': row[3],
                    'target_chat_name': row[4]
                })
            return tasks

    def get_all_active_tasks(self):
        """Get all active tasks for userbot"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, source_chat_id, source_chat_name, target_chat_id, target_chat_name
                FROM tasks 
                WHERE is_active = 1
            """, )

            tasks = []
            for row in cursor.fetchall():
                tasks.append({
                    'id': row[0],
                    'source_chat_id': row[1],
                    'source_chat_name': row[2],
                    'target_chat_id': row[3],
                    'target_chat_name': row[4]
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
                SELECT state, data FROM conversation_states WHERE user_id = ?
            ''', (user_id,))
            result = cursor.fetchone()
            return result if result else None

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
                    'id': row[0],
                    'chat_id': row[1], 
                    'chat_name': row[2]
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
                    'id': row[0],
                    'chat_id': row[1],
                    'chat_name': row[2]
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
            
        # Get sources and targets from new tables if they exist
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
            return False
            
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if already migrated
            cursor.execute('SELECT COUNT(*) FROM task_sources WHERE task_id = ?', (task_id,))
            if cursor.fetchone()[0] > 0:
                return True  # Already migrated
            
            # Migrate source
            if task.get('source_chat_id'):
                cursor.execute('''
                    INSERT INTO task_sources (task_id, chat_id, chat_name)
                    VALUES (?, ?, ?)
                ''', (task_id, task['source_chat_id'], task['source_chat_name']))
            
            # Migrate target  
            if task.get('target_chat_id'):
                cursor.execute('''
                    INSERT INTO task_targets (task_id, chat_id, chat_name)
                    VALUES (?, ?, ?)
                ''', (task_id, task['target_chat_id'], task['target_chat_name']))
            
            conn.commit()
            return True

    # Cleanup and maintenance
    def cleanup_old_states(self, hours: int = 24):
        """Clean up old conversation states"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM conversation_states 
                WHERE updated_at < datetime('now', '-{} hours')
            '''.format(hours))
            conn.commit()