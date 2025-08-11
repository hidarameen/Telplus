#!/usr/bin/env python3
"""
Test script to debug admin filter issue with "H"
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from userbot_service.userbot import UserbotService
from database.database import Database

class MockMessage:
    def __init__(self, sender_id, post_author=None):
        self.sender_id = sender_id
        self.post_author = post_author
        self.from_id = None

async def test_admin_filter():
    print("🧪 بدء اختبار فلتر المشرفين...")
    
    # Initialize database and userbot service
    db = Database()
    userbot = UserbotService()
    userbot.db = db
    
    task_id = 7  # Task ID for "حيدر"
    
    print(f"📋 اختبار المهمة {task_id}")
    
    # Check if admin filter is enabled
    admin_filter_enabled = db.is_advanced_filter_enabled(task_id, 'admin')
    print(f"🔍 فلتر المشرفين مُفعل: {admin_filter_enabled}")
    
    # Get admin filters for this task
    admin_filters = db.get_admin_filters(task_id)
    print(f"📝 عدد فلاتر المشرفين: {len(admin_filters) if admin_filters else 0}")
    
    if admin_filters:
        for admin in admin_filters:
            name = admin.get('admin_first_name', '')
            username = admin.get('admin_username', '')
            is_allowed = admin.get('is_allowed', True)
            print(f"  👤 {name} (@{username}) - مسموح: {is_allowed}")
    
    # Test 1: Mock channel message with author signature "H"
    print("\n🧪 اختبار 1: رسالة قناة مع توقيع المؤلف 'H'")
    channel_id = -1002289754739  # Source channel ID
    mock_message_h = MockMessage(sender_id=channel_id, post_author="H")
    
    try:
        is_blocked = await userbot._check_admin_filter(task_id, mock_message_h)
        print(f"🚨 نتيجة فحص التوقيع 'H': محظور={is_blocked}")
        print(f"🎯 توقع: محظور=True (لأن H محظور في قاعدة البيانات)")
        
        if is_blocked:
            print("✅ الاختبار نجح - تم حظر رسالة المشرف H بالتوقيع")
        else:
            print("❌ الاختبار فشل - لم يتم حظر رسالة المشرف H بالتوقيع")
    except Exception as e:
        print(f"❌ خطأ في اختبار التوقيع: {e}")
    
    # Test 2: Mock user message with user ID for "H"
    print("\n🧪 اختبار 2: رسالة مستخدم بمعرف المشرف H")
    h_user_id = 6602517122  # User ID for "H" from database
    mock_message_id = MockMessage(sender_id=h_user_id)
    
    try:
        is_blocked = await userbot._check_admin_filter(task_id, mock_message_id)
        print(f"🚨 نتيجة فحص المعرف {h_user_id}: محظور={is_blocked}")
        print(f"🎯 توقع: محظور=True (لأن H محظور في قاعدة البيانات)")
        
        if is_blocked:
            print("✅ الاختبار نجح - تم حظر رسالة المشرف H بالمعرف")
        else:
            print("❌ الاختبار فشل - لم يتم حظر رسالة المشرف H بالمعرف")
    except Exception as e:
        print(f"❌ خطأ في اختبار المعرف: {e}")
    
    # Test 3: Mock message without signature from channel
    print("\n🧪 اختبار 3: رسالة قناة بدون توقيع مؤلف")
    mock_message_no_sig = MockMessage(sender_id=channel_id, post_author=None)
    
    try:
        is_blocked = await userbot._check_admin_filter(task_id, mock_message_no_sig)
        print(f"🚨 نتيجة فحص بدون توقيع: محظور={is_blocked}")
        print(f"🎯 توقع: محظور=False (لأن لا يوجد توقيع)")
        
        if not is_blocked:
            print("✅ الاختبار نجح - تم السماح لرسالة بدون توقيع")
        else:
            print("❌ الاختبار فشل - تم حظر رسالة بدون توقيع")
    except Exception as e:
        print(f"❌ خطأ في اختبار عدم وجود توقيع: {e}")

if __name__ == "__main__":
    asyncio.run(test_admin_filter())