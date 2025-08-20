#!/usr/bin/env python3
"""
اختبار شامل لزر المميزات المتقدمة
"""

import asyncio
import sys
import os

# إضافة المسار للوحدات
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot_package'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'database'))

from database.database import Database
from bot_package.bot_simple import SimpleTelegramBot

class MockEvent:
    def __init__(self, sender_id=6556918772, data=None):
        self.sender_id = sender_id
        self.data = data.encode('utf-8') if data else b''
        self.chat_id = 123456789
        self.is_private = True
        
    async def answer(self, text):
        print(f"📤 إجابة: {text}")
        return MockMessage()
    
    async def respond(self, text, buttons=None):
        print(f"📤 رد: {text}")
        if buttons:
            print(f"🔘 الأزرار: {len(buttons)} صفوف")
        return MockMessage()

class MockMessage:
    def __init__(self):
        self.id = 12345

class MockBot(SimpleTelegramBot):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.user_messages = {}
        
    async def edit_or_send_message(self, event, text, buttons=None):
        print(f"📝 رسالة: {text}")
        if buttons:
            print(f"🔘 الأزرار: {len(buttons)} صفوف")
            for i, row in enumerate(buttons):
                for j, button in enumerate(row):
                    print(f"  [{i}][{j}]: {button.text} -> {button.data.decode()}")
        return MockMessage()

async def test_advanced_features_button():
    """اختبار زر المميزات المتقدمة"""
    print("🔧 اختبار زر المميزات المتقدمة")
    print("=" * 60)
    
    bot = MockBot()
    event = MockEvent()
    task_id = 1
    
    print(f"\n📋 اختبار عرض المميزات المتقدمة للمهمة {task_id}")
    print("-" * 50)
    
    try:
        await bot.show_advanced_features(event, task_id)
        print("✅ تم عرض المميزات المتقدمة بنجاح")
    except Exception as e:
        print(f"❌ خطأ في عرض المميزات المتقدمة: {e}")
        return False
    
    return True

async def test_advanced_features_callbacks():
    """اختبار معالجات الأزرار في المميزات المتقدمة"""
    print(f"\n🔘 اختبار معالجات الأزرار")
    print("-" * 50)
    
    bot = MockBot()
    event = MockEvent()
    task_id = 1
    
    # Test cases for advanced features buttons
    test_cases = [
        f"advanced_features_{task_id}",
        f"toggle_char_limit_{task_id}",
        f"cycle_char_mode_{task_id}",
        f"toggle_rate_limit_{task_id}",
        f"toggle_forwarding_delay_{task_id}",
        f"toggle_sending_interval_{task_id}",
        f"toggle_text_formatting_{task_id}",
        f"toggle_duplicate_filter_{task_id}",
        f"toggle_language_filter_{task_id}",
        f"toggle_admin_filter_{task_id}",
        f"toggle_inline_button_filter_{task_id}",
        f"toggle_forwarded_message_filter_{task_id}",
        f"toggle_text_cleaning_{task_id}",
        f"toggle_translation_{task_id}",
        f"toggle_working_hours_{task_id}"
    ]
    
    success_count = 0
    error_count = 0
    
    for test_data in test_cases:
        print(f"\n🔍 اختبار: {test_data}")
        try:
            event.data = test_data.encode('utf-8')
            await bot.handle_callback(event)
            print(f"✅ نجح: {test_data}")
            success_count += 1
        except Exception as e:
            print(f"❌ فشل: {test_data} - {e}")
            error_count += 1
    
    print(f"\n📊 نتائج اختبار الأزرار:")
    print(f"✅ نجح: {success_count}")
    print(f"❌ فشل: {error_count}")
    print(f"📈 نسبة النجاح: {(success_count/(success_count+error_count)*100):.1f}%")
    
    return success_count > 0

async def test_character_limit_settings():
    """اختبار إعدادات حد الأحرف"""
    print(f"\n🔢 اختبار إعدادات حد الأحرف")
    print("-" * 50)
    
    bot = MockBot()
    event = MockEvent()
    task_id = 1
    
    try:
        await bot.show_character_limit_settings(event, task_id)
        print("✅ تم عرض إعدادات حد الأحرف بنجاح")
        return True
    except Exception as e:
        print(f"❌ خطأ في عرض إعدادات حد الأحرف: {e}")
        return False

async def test_rate_limit_settings():
    """اختبار إعدادات حد المعدل"""
    print(f"\n⏰ اختبار إعدادات حد المعدل")
    print("-" * 50)
    
    bot = MockBot()
    event = MockEvent()
    task_id = 1
    
    try:
        await bot.show_rate_limit_settings(event, task_id)
        print("✅ تم عرض إعدادات حد المعدل بنجاح")
        return True
    except Exception as e:
        print(f"❌ خطأ في عرض إعدادات حد المعدل: {e}")
        return False

async def test_forwarding_delay_settings():
    """اختبار إعدادات تأخير التوجيه"""
    print(f"\n⏳ اختبار إعدادات تأخير التوجيه")
    print("-" * 50)
    
    bot = MockBot()
    event = MockEvent()
    task_id = 1
    
    try:
        await bot.show_forwarding_delay_settings(event, task_id)
        print("✅ تم عرض إعدادات تأخير التوجيه بنجاح")
        return True
    except Exception as e:
        print(f"❌ خطأ في عرض إعدادات تأخير التوجيه: {e}")
        return False

async def test_sending_interval_settings():
    """اختبار إعدادات فاصل الإرسال"""
    print(f"\n📤 اختبار إعدادات فاصل الإرسال")
    print("-" * 50)
    
    bot = MockBot()
    event = MockEvent()
    task_id = 1
    
    try:
        await bot.show_sending_interval_settings(event, task_id)
        print("✅ تم عرض إعدادات فاصل الإرسال بنجاح")
        return True
    except Exception as e:
        print(f"❌ خطأ في عرض إعدادات فاصل الإرسال: {e}")
        return False

async def test_database_functions():
    """اختبار دوال قاعدة البيانات للمميزات المتقدمة"""
    print(f"\n🗄️ اختبار دوال قاعدة البيانات")
    print("-" * 50)
    
    db = Database()
    task_id = 1
    
    # Test character limit settings
    try:
        char_settings = db.get_character_limit_settings(task_id)
        print(f"✅ إعدادات حد الأحرف: {char_settings}")
    except Exception as e:
        print(f"❌ خطأ في إعدادات حد الأحرف: {e}")
    
    # Test rate limit settings
    try:
        rate_settings = db.get_rate_limit_settings(task_id)
        print(f"✅ إعدادات حد المعدل: {rate_settings}")
    except Exception as e:
        print(f"❌ خطأ في إعدادات حد المعدل: {e}")
    
    # Test forwarding delay settings
    try:
        delay_settings = db.get_forwarding_delay_settings(task_id)
        print(f"✅ إعدادات تأخير التوجيه: {delay_settings}")
    except Exception as e:
        print(f"❌ خطأ في إعدادات تأخير التوجيه: {e}")
    
    # Test sending interval settings
    try:
        interval_settings = db.get_sending_interval_settings(task_id)
        print(f"✅ إعدادات فاصل الإرسال: {interval_settings}")
    except Exception as e:
        print(f"❌ خطأ في إعدادات فاصل الإرسال: {e}")
    
    # Test message settings
    try:
        message_settings = db.get_message_settings(task_id)
        print(f"✅ إعدادات الرسائل: {message_settings}")
    except Exception as e:
        print(f"❌ خطأ في إعدادات الرسائل: {e}")

if __name__ == "__main__":
    print("🔧 اختبار شامل لزر المميزات المتقدمة")
    print("=" * 80)
    
    # تشغيل الاختبارات
    results = []
    
    # Test main button
    results.append(asyncio.run(test_advanced_features_button()))
    
    # Test callbacks
    results.append(asyncio.run(test_advanced_features_callbacks()))
    
    # Test individual settings
    results.append(asyncio.run(test_character_limit_settings()))
    results.append(asyncio.run(test_rate_limit_settings()))
    results.append(asyncio.run(test_forwarding_delay_settings()))
    results.append(asyncio.run(test_sending_interval_settings()))
    
    # Test database functions
    asyncio.run(test_database_functions())
    
    # Summary
    print(f"\n📊 ملخص النتائج:")
    print(f"✅ نجح: {sum(results)}")
    print(f"❌ فشل: {len(results) - sum(results)}")
    print(f"📈 نسبة النجاح الإجمالية: {(sum(results)/len(results)*100):.1f}%")
    
    if all(results):
        print("\n🎉 جميع اختبارات المميزات المتقدمة نجحت!")
    else:
        print("\n⚠️ بعض الاختبارات فشلت. يرجى مراجعة الأخطاء أعلاه.")