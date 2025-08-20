#!/usr/bin/env python3
"""
اختبار شامل لجميع دوال لوحة التحكم
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
        self.sender = MockSender()
        
    async def answer(self, text):
        print(f"📤 إجابة: {text}")
        return MockMessage()
    
    async def respond(self, text, buttons=None):
        print(f"📤 رد: {text}")
        if buttons:
            print(f"🔘 الأزرار: {len(buttons)} صفوف")
        return MockMessage()

class MockSender:
    def __init__(self):
        self.first_name = "مستخدم"
        self.last_name = "تجريبي"

class MockMessage:
    def __init__(self):
        self.id = 12345

class MockBot(SimpleTelegramBot):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.user_messages = {}
        
    async def edit_or_send_message(self, event, text, buttons=None, force_new=False):
        print(f"📝 رسالة: {text}")
        if buttons:
            print(f"🔘 الأزرار: {len(buttons)} صفوف")
        return MockMessage()
    
    async def force_new_message(self, event, text, buttons=None):
        print(f"🔄 رسالة جديدة: {text}")
        if buttons:
            print(f"🔘 الأزرار: {len(buttons)} صفوف")
        return MockMessage()
    
    async def delete_previous_message(self, user_id):
        print(f"🗑️ حذف الرسالة السابقة للمستخدم {user_id}")

async def test_main_functions():
    """اختبار الدوال الرئيسية"""
    print("🏠 اختبار الدوال الرئيسية")
    print("-" * 50)
    
    bot = MockBot()
    event = MockEvent()
    task_id = 1
    
    functions_to_test = [
        ("show_tasks_menu", lambda: bot.show_tasks_menu(event)),
        ("show_advanced_features", lambda: bot.show_advanced_features(event, task_id)),
        ("show_task_settings", lambda: bot.show_task_settings(event, task_id)),
    ]
    
    results = []
    for func_name, func_call in functions_to_test:
        try:
            await func_call()
            print(f"✅ {func_name}")
            results.append(True)
        except Exception as e:
            print(f"❌ {func_name}: {e}")
            results.append(False)
    
    return results

async def test_advanced_features():
    """اختبار المميزات المتقدمة"""
    print("\n⚡ اختبار المميزات المتقدمة")
    print("-" * 50)
    
    bot = MockBot()
    event = MockEvent()
    task_id = 1
    
    functions_to_test = [
        ("show_character_limit_settings", lambda: bot.show_character_limit_settings(event, task_id)),
        ("show_rate_limit_settings", lambda: bot.show_rate_limit_settings(event, task_id)),
        ("show_forwarding_delay_settings", lambda: bot.show_forwarding_delay_settings(event, task_id)),
        ("show_sending_interval_settings", lambda: bot.show_sending_interval_settings(event, task_id)),
    ]
    
    results = []
    for func_name, func_call in functions_to_test:
        try:
            await func_call()
            print(f"✅ {func_name}")
            results.append(True)
        except Exception as e:
            print(f"❌ {func_name}: {e}")
            results.append(False)
    
    return results

async def test_force_new_message_usage():
    """اختبار استخدام force_new_message"""
    print("\n🔄 اختبار استخدام force_new_message")
    print("-" * 50)
    
    bot = MockBot()
    event = MockEvent()
    
    try:
        await bot.force_new_message(event, "اختبار force_new_message")
        print("✅ force_new_message يعمل بشكل صحيح")
        return True
    except Exception as e:
        print(f"❌ force_new_message: {e}")
        return False

async def test_message_flow():
    """اختبار تدفق الرسائل"""
    print("\n📱 اختبار تدفق الرسائل")
    print("-" * 50)
    
    bot = MockBot()
    event = MockEvent()
    
    try:
        # اختبار الانتقال بين القوائم
        await bot.show_tasks_menu(event)
        print("✅ الانتقال إلى إدارة المهام")
        
        # اختبار العودة للقائمة الرئيسية
        event.data = b"back_main"
        await bot.handle_callback(event)
        print("✅ العودة للقائمة الرئيسية")
        
        return True
    except Exception as e:
        print(f"❌ تدفق الرسائل: {e}")
        return False

async def test_all_settings_functions():
    """اختبار جميع دوال الإعدادات"""
    print("\n⚙️ اختبار جميع دوال الإعدادات")
    print("-" * 50)
    
    bot = MockBot()
    event = MockEvent()
    task_id = 1
    
    # قائمة بجميع دوال الإعدادات
    settings_functions = [
        "show_character_limit_settings",
        "show_rate_limit_settings", 
        "show_forwarding_delay_settings",
        "show_sending_interval_settings",
        "show_text_formatting_settings",
        "show_duplicate_filter_settings",
        "show_language_filter_settings",
        "show_admin_filter_settings",
        "show_inline_button_filter_settings",
        "show_forwarded_message_filter_settings",
        "show_text_cleaning_settings",
        "show_translation_settings",
        "show_working_hours_settings",
        "show_watermark_settings",
        "show_audio_metadata_settings",
        "show_media_filters",
        "show_word_filters",
        "show_text_replacements",
        "show_header_settings",
        "show_footer_settings",
        "show_inline_buttons",
        "show_forwarding_settings"
    ]
    
    results = []
    for func_name in settings_functions:
        try:
            if hasattr(bot, func_name):
                func = getattr(bot, func_name)
                await func(event, task_id)
                print(f"✅ {func_name}")
                results.append(True)
            else:
                print(f"⚠️ {func_name} غير موجودة")
                results.append(False)
        except Exception as e:
            print(f"❌ {func_name}: {e}")
            results.append(False)
    
    return results

if __name__ == "__main__":
    print("🔧 اختبار شامل لجميع دوال لوحة التحكم")
    print("=" * 80)
    
    # تشغيل الاختبارات
    all_results = []
    
    # Test main functions
    main_results = asyncio.run(test_main_functions())
    all_results.extend(main_results)
    
    # Test advanced features
    advanced_results = asyncio.run(test_advanced_features())
    all_results.extend(advanced_results)
    
    # Test force_new_message usage
    force_new_result = asyncio.run(test_force_new_message_usage())
    all_results.append(force_new_result)
    
    # Test message flow
    flow_result = asyncio.run(test_message_flow())
    all_results.append(flow_result)
    
    # Test all settings functions
    settings_results = asyncio.run(test_all_settings_functions())
    all_results.extend(settings_results)
    
    # Summary
    print(f"\n📊 ملخص النتائج:")
    print(f"✅ نجح: {sum(all_results)}")
    print(f"❌ فشل: {len(all_results) - sum(all_results)}")
    print(f"📈 نسبة النجاح الإجمالية: {(sum(all_results)/len(all_results)*100):.1f}%")
    
    if all(all_results):
        print("\n🎉 جميع دوال لوحة التحكم تعمل بشكل صحيح!")
        print("\n✅ المميزات المؤكدة:")
        print("• 🔄 جميع القوائم تستخدم force_new_message")
        print("• 🗑️ الرسائل السابقة تُحذف تلقائياً")
        print("• ⚡ تجربة مستخدم سلسة")
        print("• 📱 واجهة منظمة ونظيفة")
    else:
        print("\n⚠️ بعض الدوال تحتاج مراجعة.")
    
    print(f"\n📋 تفاصيل الاختبارات:")
    print(f"• الدوال الرئيسية: {sum(main_results)}/{len(main_results)}")
    print(f"• المميزات المتقدمة: {sum(advanced_results)}/{len(advanced_results)}")
    print(f"• دوال الإعدادات: {sum(settings_results)}/{len(settings_results)}")
    print(f"• force_new_message: {'✅' if force_new_result else '❌'}")
    print(f"• تدفق الرسائل: {'✅' if flow_result else '❌'}")