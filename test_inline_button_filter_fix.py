#!/usr/bin/env python3
"""
Test script to verify inline button filter fix
Tests the scenario where inline_button_filter_enabled=0 but block_messages_with_buttons=1
Should result in buttons NOT being removed/blocked since filter is disabled
"""

import sqlite3
import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from userbot_service.userbot import UserbotService
from database.database import Database

class MockMessage:
    """Mock message object for testing"""
    def __init__(self, has_buttons=False, text="Test message"):
        self.text = text
        self.sender_id = 12345
        self.from_id = None
        self.post_author = None
        self.forward = None
        self.media = None
        
        if has_buttons:
            # Create a mock reply markup with inline buttons
            self.reply_markup = MockReplyMarkup()
        else:
            self.reply_markup = None

class MockReplyMarkup:
    """Mock reply markup with inline buttons"""
    def __init__(self):
        # Mock rows with inline buttons
        self.rows = [MockInlineButtonRow()]

class MockInlineButtonRow:
    """Mock inline button row"""
    def __init__(self):
        self.buttons = [MockInlineButton()]

class MockInlineButton:
    """Mock inline button"""
    def __init__(self):
        self.text = "Test Button"
        self.data = b"test_data"

async def test_inline_button_filter_fix():
    """Test the inline button filter fix"""
    
    print("🧪 اختبار إصلاح فلتر الأزرار الشفافة")
    print("=" * 60)
    
    # Initialize database and userbot
    db = Database()
    userbot = UserbotService()
    
    task_id = 7  # Use existing task
    
    # Check current settings
    print("\n📊 إعدادات المهمة الحالية:")
    
    # Get advanced filter settings
    advanced_settings = db.get_advanced_filters_settings(task_id)
    inline_button_filter_enabled = advanced_settings.get('inline_button_filter_enabled', False)
    
    # Get inline button specific setting
    inline_button_setting = db.get_inline_button_filter_setting(task_id)
    
    print(f"   🔧 فلتر الأزرار مفعل: {inline_button_filter_enabled}")
    print(f"   🚫 إعداد حظر الأزرار: {inline_button_setting}")
    print(f"   📋 الحالة المتوقعة: الأزرار يجب أن تمرر دون تغيير (الفلتر معطل)")
    
    # Test scenarios
    print("\n🧪 اختبار السيناريوهات:")
    print("-" * 40)
    
    # Scenario 1: Message with inline buttons
    print("\n1️⃣ رسالة تحتوي على أزرار شفافة:")
    message_with_buttons = MockMessage(has_buttons=True, text="رسالة مع أزرار")
    
    should_block, should_remove_buttons, should_remove_forward = await userbot._check_message_advanced_filters(
        task_id, message_with_buttons
    )
    
    print(f"   📝 النتيجة:")
    print(f"     - حظر الرسالة: {should_block}")
    print(f"     - حذف الأزرار: {should_remove_buttons}")
    print(f"     - حذف علامة التوجيه: {should_remove_forward}")
    
    # Expected result: should_block=False, should_remove_buttons=False
    expected_block = False
    expected_remove_buttons = False
    
    success_1 = (should_block == expected_block and should_remove_buttons == expected_remove_buttons)
    status_1 = "✅ نجح" if success_1 else "❌ فشل"
    print(f"   🎯 التوقع: حظر={expected_block}, حذف أزرار={expected_remove_buttons}")
    print(f"   📊 النتيجة: {status_1}")
    
    # Scenario 2: Message without inline buttons
    print("\n2️⃣ رسالة بدون أزرار شفافة:")
    message_without_buttons = MockMessage(has_buttons=False, text="رسالة بدون أزرار")
    
    should_block_2, should_remove_buttons_2, should_remove_forward_2 = await userbot._check_message_advanced_filters(
        task_id, message_without_buttons
    )
    
    print(f"   📝 النتيجة:")
    print(f"     - حظر الرسالة: {should_block_2}")
    print(f"     - حذف الأزرار: {should_remove_buttons_2}")
    print(f"     - حذف علامة التوجيه: {should_remove_forward_2}")
    
    success_2 = (should_block_2 == False and should_remove_buttons_2 == False)
    status_2 = "✅ نجح" if success_2 else "❌ فشل"
    print(f"   🎯 التوقع: حظر=False, حذف أزرار=False")
    print(f"   📊 النتيجة: {status_2}")
    
    # Overall result
    print("\n" + "=" * 60)
    overall_success = success_1 and success_2
    overall_status = "✅ جميع الاختبارات نجحت" if overall_success else "❌ بعض الاختبارات فشلت"
    print(f"🏁 النتيجة الإجمالية: {overall_status}")
    
    if overall_success:
        print("\n🎉 إصلاح فلتر الأزرار الشفافة يعمل بشكل صحيح!")
        print("   الآن الرسائل التي تحتوي على أزرار شفافة ستمرر دون تغيير")
        print("   عندما يكون الفلتر معطلاً حتى لو كان إعداد الحظر مفعلاً")
    else:
        print("\n⚠️ لا يزال هناك مشكلة في منطق فلتر الأزرار الشفافة")
    
    return overall_success

if __name__ == "__main__":
    result = asyncio.run(test_inline_button_filter_fix())
    sys.exit(0 if result else 1)