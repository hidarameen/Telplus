#!/usr/bin/env python3
"""
اختبار سريع لإصلاح حد الأحرف
"""

import sys
import os

# إضافة المسار للوحدات
sys.path.append(os.path.join(os.path.dirname(__file__), 'database'))

from database.database import Database

def test_character_limit_settings():
    """اختبار إعدادات حد الأحرف"""
    print("🔢 اختبار إعدادات حد الأحرف")
    print("=" * 50)
    
    db = Database()
    task_id = 1
    
    # Test getting settings
    print("🔍 اختبار الحصول على الإعدادات:")
    settings = db.get_character_limit_settings(task_id)
    print(f"✅ الإعدادات: {settings}")
    
    # Test updating settings
    print("\n🔍 اختبار تحديث الإعدادات:")
    success = db.update_character_limit_settings(task_id, enabled=True, mode='allow', min_chars=10, max_chars=1000)
    print(f"✅ تحديث الإعدادات: {success}")
    
    # Test getting updated settings
    print("\n🔍 اختبار الحصول على الإعدادات المحدثة:")
    updated_settings = db.get_character_limit_settings(task_id)
    print(f"✅ الإعدادات المحدثة: {updated_settings}")
    
    # Test cycling mode
    print("\n🔍 اختبار تدوير الوضع:")
    new_mode = db.cycle_character_limit_mode(task_id)
    print(f"✅ الوضع الجديد: {new_mode}")
    
    # Test toggle
    print("\n🔍 اختبار تبديل الحالة:")
    new_state = db.toggle_character_limit(task_id)
    print(f"✅ الحالة الجديدة: {new_state}")

def test_character_limit_values():
    """اختبار قيم حد الأحرف"""
    print("\n🔢 اختبار قيم حد الأحرف")
    print("=" * 50)
    
    db = Database()
    task_id = 1
    
    # Test updating values
    print("🔍 اختبار تحديث القيم:")
    success = db.update_character_limit_values(task_id, min_chars=50, max_chars=500)
    print(f"✅ تحديث القيم: {success}")
    
    # Test getting settings after update
    print("\n🔍 اختبار الحصول على الإعدادات بعد التحديث:")
    settings = db.get_character_limit_settings(task_id)
    print(f"✅ الإعدادات: {settings}")

if __name__ == "__main__":
    print("🔧 اختبار إصلاح حد الأحرف")
    print("=" * 60)
    
    test_character_limit_settings()
    test_character_limit_values()
    
    print("\n🎉 تم الانتهاء من اختبار إصلاح حد الأحرف!")