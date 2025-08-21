#!/usr/bin/env python3
"""
قاعدة بيانات القنوات
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class ChannelsDatabase:
    """إدارة قاعدة بيانات القنوات"""
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.init_channels_table()
    
    def init_channels_table(self):
        """إنشاء جدول القنوات إذا لم يكن موجوداً"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create channels table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_channels (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        chat_id INTEGER NOT NULL,
                        chat_name TEXT,
                        username TEXT,
                        is_admin BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, chat_id)
                    )
                ''')
                
                # Create index for faster queries
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_user_channels_user_id 
                    ON user_channels(user_id)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_user_channels_chat_id 
                    ON user_channels(chat_id)
                ''')
                
                conn.commit()
                logger.info("✅ تم تهيئة جدول القنوات بنجاح")
                
        except Exception as e:
            logger.error(f"❌ خطأ في تهيئة جدول القنوات: {e}")
    
    def add_channel(self, user_id: int, chat_id: int, chat_name: str, username: Optional[str] = None, is_admin: bool = False) -> bool:
        """إضافة قناة جديدة للمستخدم"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO user_channels 
                    (user_id, chat_id, chat_name, username, is_admin, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (user_id, chat_id, chat_name, username, is_admin))
                
                conn.commit()
                logger.info(f"✅ تم إضافة القناة {chat_name} للمستخدم {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ خطأ في إضافة القناة: {e}")
            return False
    
    def get_user_channels(self, user_id: int) -> List[Dict]:
        """الحصول على قنوات المستخدم"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT chat_id, chat_name, username, is_admin, created_at, updated_at
                    FROM user_channels 
                    WHERE user_id = ?
                    ORDER BY chat_name ASC
                ''', (user_id,))
                
                channels = []
                for row in cursor.fetchall():
                    channels.append({
                        'chat_id': row[0],
                        'chat_name': row[1],
                        'username': row[2],
                        'is_admin': bool(row[3]),
                        'created_at': row[4],
                        'updated_at': row[5]
                    })
                
                return channels
                
        except Exception as e:
            logger.error(f"❌ خطأ في الحصول على قنوات المستخدم: {e}")
            return []
    
    def get_channel_info(self, chat_id: int, user_id: int) -> Optional[Dict]:
        """الحصول على معلومات قناة محددة"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT chat_id, chat_name, username, is_admin, created_at, updated_at
                    FROM user_channels 
                    WHERE chat_id = ? AND user_id = ?
                ''', (chat_id, user_id))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'chat_id': row[0],
                        'chat_name': row[1],
                        'username': row[2],
                        'is_admin': bool(row[3]),
                        'created_at': row[4],
                        'updated_at': row[5]
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"❌ خطأ في الحصول على معلومات القناة: {e}")
            return None
    
    def update_channel_info(self, chat_id: int, user_id: int, updates: Dict) -> bool:
        """تحديث معلومات القناة"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build update query dynamically
                set_clauses = []
                values = []
                
                for key, value in updates.items():
                    if key in ['chat_name', 'username', 'is_admin']:
                        set_clauses.append(f"{key} = ?")
                        values.append(value)
                
                if not set_clauses:
                    return False
                
                set_clauses.append("updated_at = CURRENT_TIMESTAMP")
                values.extend([chat_id, user_id])
                
                query = f'''
                    UPDATE user_channels 
                    SET {', '.join(set_clauses)}
                    WHERE chat_id = ? AND user_id = ?
                '''
                
                cursor.execute(query, values)
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"✅ تم تحديث معلومات القناة {chat_id}")
                    return True
                else:
                    logger.warning(f"⚠️ لم يتم العثور على القناة {chat_id} للمستخدم {user_id}")
                    return False
                
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث معلومات القناة: {e}")
            return False
    
    def delete_channel(self, chat_id: int, user_id: int) -> bool:
        """حذف قناة"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    DELETE FROM user_channels 
                    WHERE chat_id = ? AND user_id = ?
                ''', (chat_id, user_id))
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"✅ تم حذف القناة {chat_id} للمستخدم {user_id}")
                    return True
                else:
                    logger.warning(f"⚠️ لم يتم العثور على القناة {chat_id} للمستخدم {user_id}")
                    return False
                
        except Exception as e:
            logger.error(f"❌ خطأ في حذف القناة: {e}")
            return False
    
    def get_channel_by_name(self, user_id: int, chat_name: str) -> Optional[Dict]:
        """البحث عن قناة بالاسم"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT chat_id, chat_name, username, is_admin, created_at, updated_at
                    FROM user_channels 
                    WHERE user_id = ? AND chat_name LIKE ?
                ''', (user_id, f"%{chat_name}%"))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'chat_id': row[0],
                        'chat_name': row[1],
                        'username': row[2],
                        'is_admin': bool(row[3]),
                        'created_at': row[4],
                        'updated_at': row[5]
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"❌ خطأ في البحث عن القناة بالاسم: {e}")
            return None
    
    def get_admin_channels(self, user_id: int) -> List[Dict]:
        """الحصول على القنوات التي فيها المستخدم مشرف"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT chat_id, chat_name, username, is_admin, created_at, updated_at
                    FROM user_channels 
                    WHERE user_id = ? AND is_admin = TRUE
                    ORDER BY chat_name ASC
                ''', (user_id,))
                
                channels = []
                for row in cursor.fetchall():
                    channels.append({
                        'chat_id': row[0],
                        'chat_name': row[1],
                        'username': row[2],
                        'is_admin': bool(row[3]),
                        'created_at': row[4],
                        'updated_at': row[5]
                    })
                
                return channels
                
        except Exception as e:
            logger.error(f"❌ خطأ في الحصول على قنوات المشرف: {e}")
            return []
    
    def get_member_channels(self, user_id: int) -> List[Dict]:
        """الحصول على القنوات التي فيها المستخدم عضو"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT chat_id, chat_name, username, is_admin, created_at, updated_at
                    FROM user_channels 
                    WHERE user_id = ? AND is_admin = FALSE
                    ORDER BY chat_name ASC
                ''', (user_id,))
                
                channels = []
                for row in cursor.fetchall():
                    channels.append({
                        'chat_id': row[0],
                        'chat_name': row[1],
                        'username': row[2],
                        'is_admin': bool(row[3]),
                        'created_at': row[4],
                        'updated_at': row[5]
                    })
                
                return channels
                
        except Exception as e:
            logger.error(f"❌ خطأ في الحصول على قنوات العضو: {e}")
            return []
    
    def get_channels_count(self, user_id: int) -> Dict[str, int]:
        """الحصول على إحصائيات القنوات"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Total channels
                cursor.execute('SELECT COUNT(*) FROM user_channels WHERE user_id = ?', (user_id,))
                total = cursor.fetchone()[0]
                
                # Admin channels
                cursor.execute('SELECT COUNT(*) FROM user_channels WHERE user_id = ? AND is_admin = TRUE', (user_id,))
                admin_count = cursor.fetchone()[0]
                
                # Member channels
                member_count = total - admin_count
                
                return {
                    'total': total,
                    'admin': admin_count,
                    'member': member_count
                }
                
        except Exception as e:
            logger.error(f"❌ خطأ في الحصول على إحصائيات القنوات: {e}")
            return {'total': 0, 'admin': 0, 'member': 0}
    
    def search_channels(self, user_id: int, search_term: str) -> List[Dict]:
        """البحث في القنوات"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT chat_id, chat_name, username, is_admin, created_at, updated_at
                    FROM user_channels 
                    WHERE user_id = ? AND (chat_name LIKE ? OR username LIKE ?)
                    ORDER BY chat_name ASC
                ''', (user_id, f"%{search_term}%", f"%{search_term}%"))
                
                channels = []
                for row in cursor.fetchall():
                    channels.append({
                        'chat_id': row[0],
                        'chat_name': row[1],
                        'username': row[2],
                        'is_admin': bool(row[3]),
                        'created_at': row[4],
                        'updated_at': row[5]
                    })
                
                return channels
                
        except Exception as e:
            logger.error(f"❌ خطأ في البحث في القنوات: {e}")
            return []
    
    def bulk_add_channels(self, user_id: int, channels_data: List[Dict]) -> Dict[str, int]:
        """إضافة عدة قنوات دفعة واحدة"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                success_count = 0
                error_count = 0
                
                for channel_data in channels_data:
                    try:
                        cursor.execute('''
                            INSERT OR REPLACE INTO user_channels 
                            (user_id, chat_id, chat_name, username, is_admin, updated_at)
                            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        ''', (
                            user_id,
                            channel_data['chat_id'],
                            channel_data['chat_name'],
                            channel_data.get('username'),
                            channel_data.get('is_admin', False)
                        ))
                        success_count += 1
                        
                    except Exception as e:
                        logger.error(f"❌ خطأ في إضافة القناة {channel_data.get('chat_name')}: {e}")
                        error_count += 1
                
                conn.commit()
                logger.info(f"✅ تم إضافة {success_count} قناة بنجاح، {error_count} فشلت")
                
                return {
                    'success': success_count,
                    'error': error_count,
                    'total': len(channels_data)
                }
                
        except Exception as e:
            logger.error(f"❌ خطأ في إضافة القنوات دفعة واحدة: {e}")
            return {'success': 0, 'error': len(channels_data), 'total': len(channels_data)}
    
    def cleanup_old_channels(self, days: int = 30) -> int:
        """تنظيف القنوات القديمة"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    DELETE FROM user_channels 
                    WHERE updated_at < datetime('now', '-{} days')
                '''.format(days))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"✅ تم حذف {deleted_count} قناة قديمة")
                
                return deleted_count
                
        except Exception as e:
            logger.error(f"❌ خطأ في تنظيف القنوات القديمة: {e}")
            return 0