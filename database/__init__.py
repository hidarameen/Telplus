"""
Database Package - يدعم SQLite و PostgreSQL
"""

from .database_factory import DatabaseFactory

# إنشاء قاعدة البيانات الافتراضية
def get_database():
    """الحصول على قاعدة البيانات المناسبة"""
    return DatabaseFactory.create_database()

# تصدير المصنع للاستخدام المباشر
__all__ = ['DatabaseFactory', 'get_database']
