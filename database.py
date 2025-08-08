import sqlite3
from datetime import datetime
import json

class Database:
    def __init__(self, db_path='telegram_bot.db'):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tasks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                source_chats TEXT NOT NULL,
                target_chats TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create user sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT UNIQUE NOT NULL,
                session_string TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_task(self, name, source_chats, target_chats):
        """Create a new forwarding task"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO tasks (name, source_chats, target_chats)
            VALUES (?, ?, ?)
        ''', (name, json.dumps(source_chats), json.dumps(target_chats)))
        
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return task_id
    
    def get_all_tasks(self):
        """Get all forwarding tasks"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, source_chats, target_chats, is_active, created_at
            FROM tasks ORDER BY created_at DESC
        ''')
        
        tasks = []
        for row in cursor.fetchall():
            tasks.append({
                'id': row[0],
                'name': row[1],
                'source_chats': json.loads(row[2]),
                'target_chats': json.loads(row[3]),
                'is_active': bool(row[4]),
                'created_at': row[5]
            })
        
        conn.close()
        return tasks
    
    def get_task(self, task_id):
        """Get a specific task by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, source_chats, target_chats, is_active, created_at
            FROM tasks WHERE id = ?
        ''', (task_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'name': row[1],
                'source_chats': json.loads(row[2]),
                'target_chats': json.loads(row[3]),
                'is_active': bool(row[4]),
                'created_at': row[5]
            }
        return None
    
    def update_task(self, task_id, name, source_chats, target_chats):
        """Update an existing task"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE tasks SET name = ?, source_chats = ?, target_chats = ?, 
            updated_at = CURRENT_TIMESTAMP WHERE id = ?
        ''', (name, json.dumps(source_chats), json.dumps(target_chats), task_id))
        
        conn.commit()
        conn.close()
    
    def toggle_task(self, task_id):
        """Toggle task active status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE tasks SET is_active = NOT is_active, 
            updated_at = CURRENT_TIMESTAMP WHERE id = ?
        ''', (task_id,))
        
        conn.commit()
        conn.close()
    
    def delete_task(self, task_id):
        """Delete a task"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        
        conn.commit()
        conn.close()
    
    def get_active_tasks(self):
        """Get only active tasks for the userbot"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, source_chats, target_chats
            FROM tasks WHERE is_active = 1
        ''')
        
        tasks = []
        for row in cursor.fetchall():
            tasks.append({
                'id': row[0],
                'name': row[1],
                'source_chats': json.loads(row[2]),
                'target_chats': json.loads(row[3])
            })
        
        conn.close()
        return tasks
    
    def save_user_session(self, phone_number, session_string):
        """Save user session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_sessions (phone_number, session_string)
            VALUES (?, ?)
        ''', (phone_number, session_string))
        
        conn.commit()
        conn.close()
    
    def get_user_session(self, phone_number):
        """Get user session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT session_string FROM user_sessions 
            WHERE phone_number = ? AND is_active = 1
        ''', (phone_number,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
