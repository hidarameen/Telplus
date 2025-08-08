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
            
            # Tasks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    source_chat_id TEXT NOT NULL,
                    source_chat_name TEXT,
                    target_chat_id TEXT NOT NULL,
                    target_chat_name TEXT,
                    is_active BOOLEAN DEFAULT 1,
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
    
    # Task Management
    def create_task(self, user_id: int, source_chat_id: str, source_chat_name: str, 
                   target_chat_id: str, target_chat_name: str) -> int:
        """Create new forwarding task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO tasks 
                (user_id, source_chat_id, source_chat_name, target_chat_id, target_chat_name)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, source_chat_id, source_chat_name, target_chat_id, target_chat_name))
            conn.commit()
            return cursor.lastrowid
    
    def get_user_tasks(self, user_id: int) -> List[Dict]:
        """Get all tasks for user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, source_chat_id, source_chat_name, target_chat_id, 
                       target_chat_name, is_active, created_at
                FROM tasks 
                WHERE user_id = ?
                ORDER BY created_at DESC
            ''', (user_id,))
            
            tasks = []
            for row in cursor.fetchall():
                tasks.append({
                    'id': row[0],
                    'source_chat_id': row[1],
                    'source_chat_name': row[2],
                    'target_chat_id': row[3],
                    'target_chat_name': row[4],
                    'is_active': bool(row[5]),
                    'created_at': row[6]
                })
            return tasks
    
    def get_task(self, task_id: int, user_id: int) -> Optional[Dict]:
        """Get specific task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, source_chat_id, source_chat_name, target_chat_id, 
                       target_chat_name, is_active, created_at
                FROM tasks 
                WHERE id = ? AND user_id = ?
            ''', (task_id, user_id))
            
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'source_chat_id': row[1],
                    'source_chat_name': row[2],
                    'target_chat_id': row[3],
                    'target_chat_name': row[4],
                    'is_active': bool(row[5]),
                    'created_at': row[6]
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
    
    def delete_task(self, task_id: int, user_id: int):
        """Delete task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM tasks WHERE id = ? AND user_id = ?', 
                          (task_id, user_id))
            conn.commit()
    
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