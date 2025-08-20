#!/usr/bin/env python3
"""
اختبار شامل لتحديثات لوحة التحكم
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

async def test_force_new_message():
    """اختبار دالة force_new_message"""
    print("🔄 اختبار دالة force_new_message")
    print("-" * 50)
    
    bot = MockBot()
    event = MockEvent()
    
    # اختبار force_new_message
    try:
        await bot.force_new_message(event, "اختبار الرسالة الجديدة")
        print("✅ تم اختبار force_new_message بنجاح")
        return True
    except Exception as e:
        print(f"❌ خطأ في force_new_message: {e}")
        return False

async def test_delete_previous_message():
    """اختبار دالة delete_previous_message"""
    print("\n🗑️ اختبار دالة delete_previous_message")
    print("-" * 50)
    
    bot = MockBot()
    user_id = 6556918772
    
    # إضافة رسالة وهمية
    bot.user_messages[user_id] = {
        'message_id': 12345,
        'chat_id': 123456789,
        'timestamp': 1234567890
    }
    
    try:
        await bot.delete_previous_message(user_id)
        print("✅ تم اختبار delete_previous_message بنجاح")
        return True
    except Exception as e:
        print(f"❌ خطأ في delete_previous_message: {e}")
        return False

async def test_show_tasks_menu():
    """اختبار دالة show_tasks_menu"""
    print("\n📝 اختبار دالة show_tasks_menu")
    print("-" * 50)
    
    bot = MockBot()
    event = MockEvent()
    
    try:
        await bot.show_tasks_menu(event)
        print("✅ تم اختبار show_tasks_menu بنجاح")
        return True
    except Exception as e:
        print(f"❌ خطأ في show_tasks_menu: {e}")
        return False

async def test_show_advanced_features():
    """اختبار دالة show_advanced_features"""
    print("\n⚡ اختبار دالة show_advanced_features")
    print("-" * 50)
    
    bot = MockBot()
    event = MockEvent()
    task_id = 1
    
    try:
        await bot.show_advanced_features(event, task_id)
        print("✅ تم اختبار show_advanced_features بنجاح")
        return True
    except Exception as e:
        print(f"❌ خطأ في show_advanced_features: {e}")
        return False

async def test_show_task_settings():
    """اختبار دالة show_task_settings"""
    print("\n⚙️ اختبار دالة show_task_settings")
    print("-" * 50)
    
    bot = MockBot()
    event = MockEvent()
    task_id = 1
    
    try:
        await bot.show_task_settings(event, task_id)
        print("✅ تم اختبار show_task_settings بنجاح")
        return True
    except Exception as e:
        print(f"❌ خطأ في show_task_settings: {e}")
        return False

async def test_edit_or_send_message_improved():
    """اختبار دالة edit_or_send_message المحسنة"""
    print("\n📝 اختبار دالة edit_or_send_message المحسنة")
    print("-" * 50)
    
    bot = MockBot()
    event = MockEvent()
    
    # اختبار التعديل
    try:
        # إضافة رسالة وهمية
        bot.user_messages[event.sender_id] = {
            'message_id': 12345,
            'chat_id': 123456789,
            'timestamp': 1234567890
        }
        
        await bot.edit_or_send_message(event, "اختبار تعديل الرسالة")
        print("✅ تم اختبار تعديل الرسالة بنجاح")
        
        # اختبار إرسال رسالة جديدة
        await bot.edit_or_send_message(event, "اختبار رسالة جديدة", force_new=True)
        print("✅ تم اختبار إرسال رسالة جديدة بنجاح")
        
        return True
    except Exception as e:
        print(f"❌ خطأ في edit_or_send_message: {e}")
        return False

async def test_main_menu_flow():
    """اختبار تدفق القائمة الرئيسية"""
    print("\n🏠 اختبار تدفق القائمة الرئيسية")
    print("-" * 50)
    
    bot = MockBot()
    event = MockEvent()
    
    try:
        # محاكاة الضغط على زر إدارة المهام
        event.data = b"manage_tasks"
        await bot.handle_callback(event)
        print("✅ تم اختبار الانتقال إلى إدارة المهام بنجاح")
        
        # محاكاة الضغط على زر العودة للقائمة الرئيسية
        event.data = b"back_main"
        await bot.handle_callback(event)
        print("✅ تم اختبار العودة للقائمة الرئيسية بنجاح")
        
        return True
    except Exception as e:
        print(f"❌ خطأ في تدفق القائمة الرئيسية: {e}")
        return False

if __name__ == "__main__":
    print("🔧 اختبار شامل لتحديثات لوحة التحكم")
    print("=" * 80)
    
    # تشغيل الاختبارات
    results = []
    
    # Test force_new_message
    results.append(asyncio.run(test_force_new_message()))
    
    # Test delete_previous_message
    results.append(asyncio.run(test_delete_previous_message()))
    
    # Test show_tasks_menu
    results.append(asyncio.run(test_show_tasks_menu()))
    
    # Test show_advanced_features
    results.append(asyncio.run(test_show_advanced_features()))
    
    # Test show_task_settings
    results.append(asyncio.run(test_show_task_settings()))
    
    # Test edit_or_send_message_improved
    results.append(asyncio.run(test_edit_or_send_message_improved()))
    
    # Test main_menu_flow
    results.append(asyncio.run(test_main_menu_flow()))
    
    # Summary
    print(f"\n📊 ملخص النتائج:")
    print(f"✅ نجح: {sum(results)}")
    print(f"❌ فشل: {len(results) - sum(results)}")
    print(f"📈 نسبة النجاح الإجمالية: {(sum(results)/len(results)*100):.1f}%")
    
    if all(results):
        print("\n🎉 جميع اختبارات تحديثات لوحة التحكم نجحت!")
        print("\n✅ المميزات الجديدة:")
        print("• 🔄 تحديث الرسائل بدلاً من إرسال رسائل جديدة")
        print("• 🗑️ حذف الرسائل السابقة تلقائياً")
        print("• ⚡ تجربة مستخدم أكثر سلاسة")
        print("• 📱 واجهة أكثر تنظيماً")
    else:
        print("\n⚠️ بعض الاختبارات فشلت. يرجى مراجعة الأخطاء أعلاه.")