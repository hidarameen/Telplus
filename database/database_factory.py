"""
Database Factory - يدعم SQLite و PostgreSQL
"""

import os
import logging
from typing import Union

logger = logging.getLogger(__name__)

class DatabaseFactory:
    """مصنع قاعدة البيانات - يختار النوع المناسب حسب الإعدادات"""
    
    @staticmethod
    def create_database() -> Union['SQLiteDatabase', 'PostgreSQLDatabase']:
        """إنشاء قاعدة البيانات المناسبة حسب الإعدادات"""
        
        # الحصول على نوع قاعدة البيانات من متغير البيئة
        database_type = os.getenv('DATABASE_TYPE', 'sqlite').lower()
        
        if database_type == 'postgresql' or database_type == 'postgres':
            logger.info("🚀 إنشاء قاعدة بيانات PostgreSQL")
            try:
                from .database_postgresql import PostgreSQLDatabase
                return PostgreSQLDatabase()
            except ImportError as e:
                logger.error(f"❌ فشل في استيراد PostgreSQL: {e}")
                logger.info("🔄 العودة إلى SQLite")
                from .database import Database as SQLiteDatabase
                return SQLiteDatabase()
            except Exception as e:
                logger.error(f"❌ فشل في الاتصال بـ PostgreSQL: {e}")
                logger.info("🔄 العودة إلى SQLite")
                from .database import Database as SQLiteDatabase
                return SQLiteDatabase()
                
        elif database_type == 'sqlite':
            logger.info("🚀 إنشاء قاعدة بيانات SQLite")
            from .database import Database as SQLiteDatabase
            return SQLiteDatabase()
            
        else:
            logger.warning(f"⚠️ نوع قاعدة البيانات غير معروف: {database_type}")
            logger.info("🔄 استخدام SQLite كافتراضي")
            from .database import Database as SQLiteDatabase
            return SQLiteDatabase()
    
    @staticmethod
    def get_database_info() -> dict:
        """الحصول على معلومات قاعدة البيانات الحالية"""
        
        database_type = os.getenv('DATABASE_TYPE', 'sqlite').lower()
        
        if database_type == 'postgresql' or database_type == 'postgres':
            return {
                'type': 'postgresql',
                'name': 'PostgreSQL',
                'connection_string': os.getenv('DATABASE_URL', 'postgresql://telegram_bot_user:your_secure_password@localhost:5432/telegram_bot_db'),
                'file_path': None
            }
        else:
            return {
                'type': 'sqlite',
                'name': 'SQLite',
                'connection_string': None,
                'file_path': 'telegram_bot.db'
            }
    
    @staticmethod
    def test_connection() -> dict:
        """اختبار الاتصال بقاعدة البيانات"""
        
        try:
            db = DatabaseFactory.create_database()
            db_info = DatabaseFactory.get_database_info()
            
            # اختبار الاتصال
            if db_info['type'] == 'postgresql':
                try:
                    conn = db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    conn.close()
                    
                    if result:
                        return {
                            'success': True,
                            'type': 'postgresql',
                            'message': '✅ الاتصال بـ PostgreSQL ناجح'
                        }
                    else:
                        return {
                            'success': False,
                            'type': 'postgresql',
                            'message': '❌ فشل في اختبار PostgreSQL'
                        }
                except Exception as e:
                    return {
                        'success': False,
                        'type': 'postgresql',
                        'message': f'❌ خطأ في الاتصال بـ PostgreSQL: {e}'
                    }
            else:
                try:
                    conn = db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    conn.close()
                    
                    if result:
                        return {
                            'success': True,
                            'type': 'sqlite',
                            'message': '✅ الاتصال بـ SQLite ناجح'
                        }
                    else:
                        return {
                            'success': False,
                            'type': 'sqlite',
                            'message': '❌ فشل في اختبار SQLite'
                        }
                except Exception as e:
                    return {
                        'success': False,
                        'type': 'sqlite',
                        'message': f'❌ خطأ في الاتصال بـ SQLite: {e}'
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'type': 'unknown',
                'message': f'❌ خطأ عام في اختبار الاتصال: {e}'
            }