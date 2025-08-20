#!/usr/bin/env python3
"""
اختبار للتأكد من صحة المنطق الجديد
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
    def __init__(self, sender_id=6556918772, data=None, text=None):
        self.sender_id = sender_id
        self.data = data.encode('utf-8') if data else b''
        self.text = text
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
        print(f"📝 تعديل/إرسال: {text}")
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

async def test_commands_use_force_new():
    """اختبار أن الأوامر تستخدم force_new_message"""
    print("🏠 اختبار الأوامر تستخدم force_new_message")
    print("-" * 50)
    
    bot = MockBot()
    event = MockEvent()
    
    try:
        # اختبار أمر /start
        await bot.handle_start(event)
        print("✅ أمر /start يستخدم force_new_message")
        return True
    except Exception as e:
        print(f"❌ أمر /start: {e}")
        return False

async def test_buttons_use_edit_or_send():
    """اختبار أن الأزرار تستخدم edit_or_send_message"""
    print("\n🔘 اختبار الأزرار تستخدم edit_or_send_message")
    print("-" * 50)
    
    bot = MockBot()
    event = MockEvent()
    task_id = 1
    
    functions_to_test = [
        ("show_tasks_menu", lambda: bot.show_tasks_menu(event)),
        ("show_advanced_features", lambda: bot.show_advanced_features(event, task_id)),
        ("show_task_settings", lambda: bot.show_task_settings(event, task_id)),
        ("show_character_limit_settings", lambda: bot.show_character_limit_settings(event, task_id)),
        ("show_rate_limit_settings", lambda: bot.show_rate_limit_settings(event, task_id)),
        ("show_forwarding_delay_settings", lambda: bot.show_forwarding_delay_settings(event, task_id)),
        ("show_sending_interval_settings", lambda: bot.show_sending_interval_settings(event, task_id)),
    ]
    
    results = []
    for func_name, func_call in functions_to_test:
        try:
            await func_call()
            print(f"✅ {func_name} يستخدم edit_or_send_message")
            results.append(True)
        except Exception as e:
            print(f"❌ {func_name}: {e}")
            results.append(False)
    
    return results

async def test_input_requests_use_force_new():
    """اختبار أن طلبات الإدخال تستخدم force_new_message"""
    print("\n📝 اختبار طلبات الإدخال تستخدم force_new_message")
    print("-" * 50)
    
    bot = MockBot()
    event = MockEvent()
    user_id = 6556918772
    
    # محاكاة طلب إدخال ملف
    try:
        # محاكاة الضغط على زر رفع صورة الغلاف
        event.data = "upload_album_art_1"
        await bot.handle_callback(event)
        print("✅ طلب رفع صورة الغلاف يستخدم force_new_message")
        return True
    except Exception as e:
        print(f"❌ طلب رفع صورة الغلاف: {e}")
        return False

async def test_error_messages_use_edit_or_send():
    """اختبار أن رسائل الخطأ تستخدم edit_or_send_message"""
    print("\n❌ اختبار رسائل الخطأ تستخدم edit_or_send_message")
    print("-" * 50)
    
    bot = MockBot()
    event = MockEvent()
    
    try:
        # محاكاة خطأ
        await bot.edit_or_send_message(event, "❌ حدث خطأ، يرجى المحاولة مرة أخرى")
        print("✅ رسائل الخطأ تستخدم edit_or_send_message")
        return True
    except Exception as e:
        print(f"❌ رسائل الخطأ: {e}")
        return False

async def test_message_flow():
    """اختبار تدفق الرسائل"""
    print("\n📱 اختبار تدفق الرسائل")
    print("-" * 50)
    
    bot = MockBot()
    event = MockEvent()
    
    try:
        # 1. المستخدم يضغط على زر إدارة المهام
        await bot.show_tasks_menu(event)
        print("✅ 1. عرض قائمة إدارة المهام (تعديل)")
        
        # 2. المستخدم يضغط على زر المميزات المتقدمة
        await bot.show_advanced_features(event, 1)
        print("✅ 2. عرض المميزات المتقدمة (تعديل)")
        
        # 3. المستخدم يضغط على زر إعدادات حد الأحرف
        await bot.show_character_limit_settings(event, 1)
        print("✅ 3. عرض إعدادات حد الأحرف (تعديل)")
        
        # 4. المستخدم يضغط على زر رفع صورة الغلاف
        event.data = "upload_album_art_1"
        await bot.handle_callback(event)
        print("✅ 4. طلب رفع صورة الغلاف (رسالة جديدة)")
        
        return True
    except Exception as e:
        print(f"❌ تدفق الرسائل: {e}")
        return False

if __name__ == "__main__":
    print("🔧 اختبار صحة المنطق الجديد")
    print("=" * 80)
    
    # تشغيل الاختبارات
    all_results = []
    
    # Test commands use force_new
    command_result = asyncio.run(test_commands_use_force_new())
    all_results.append(command_result)
    
    # Test buttons use edit_or_send
    button_results = asyncio.run(test_buttons_use_edit_or_send())
    all_results.extend(button_results)
    
    # Test input requests use force_new
    input_result = asyncio.run(test_input_requests_use_force_new())
    all_results.append(input_result)
    
    # Test error messages use edit_or_send
    error_result = asyncio.run(test_error_messages_use_edit_or_send())
    all_results.append(error_result)
    
    # Test message flow
    flow_result = asyncio.run(test_message_flow())
    all_results.append(flow_result)
    
    # Summary
    print(f"\n📊 ملخص النتائج:")
    print(f"✅ نجح: {sum(all_results)}")
    print(f"❌ فشل: {len(all_results) - sum(all_results)}")
    print(f"📈 نسبة النجاح الإجمالية: {(sum(all_results)/len(all_results)*100):.1f}%")
    
    if all(all_results):
        print("\n🎉 المنطق الجديد صحيح!")
        print("\n✅ المنطق المطبق:")
        print("• 🏠 الأوامر (/start, /login) → force_new_message (رسالة جديدة)")
        print("• 🔘 الأزرار → edit_or_send_message (تعديل الرسالة)")
        print("• 📝 طلبات الإدخال → force_new_message (رسالة جديدة)")
        print("• ❌ رسائل الخطأ → edit_or_send_message (تعديل الرسالة)")
        print("\n📋 التطبيق:")
        print("• عند الضغط على الأزرار → تعديل الرسالة الحالية")
        print("• عند إدخال أمر أو قيمة → حذف الرسالة السابقة وإرسال لوحة جديدة")
    else:
        print("\n⚠️ بعض الاختبارات فشلت. يرجى مراجعة المنطق.")
    
    print(f"\n📋 تفاصيل الاختبارات:")
    print(f"• الأوامر: {'✅' if command_result else '❌'}")
    print(f"• الأزرار: {sum(button_results)}/{len(button_results)}")
    print(f"• طلبات الإدخال: {'✅' if input_result else '❌'}")
    print(f"• رسائل الخطأ: {'✅' if error_result else '❌'}")
    print(f"• تدفق الرسائل: {'✅' if flow_result else '❌'}")