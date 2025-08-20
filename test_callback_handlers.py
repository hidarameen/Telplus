#!/usr/bin/env python3
"""
اختبار معالجات الأزرار في handle_callback
"""

import asyncio
import sys
import os

# إضافة المجلد الحالي إلى مسار Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot_package.bot_simple import SimpleTelegramBot

async def test_callback_handlers():
    """اختبار معالجات الأزرار"""
    try:
        print("🚀 بدء اختبار معالجات الأزرار...")
        
        # إنشاء مثيل البوت
        bot = SimpleTelegramBot()
        
        # إنشاء كائن وهمي للحدث
        class MockEvent:
            def __init__(self, data):
                self.sender_id = 6556918772  # نفس user_id الموجود في قاعدة البيانات
                self.chat_id = 123456789
                self.data = data.encode('utf-8')  # encode data as bytes
                
            async def answer(self, text):
                print(f"📤 إجابة: {text}")
                
            async def edit(self, text, buttons=None):
                print(f"✏️ تعديل: {text}")
                if buttons:
                    print(f"🔘 أزرار: {len(buttons)} صفوف")
                    
            async def respond(self, text, buttons=None):
                print(f"📤 رد: {text}")
                if buttons:
                    print(f"🔘 أزرار: {len(buttons)} صفوف")
                return MockMessage()
                    
        class MockMessage:
            def __init__(self):
                self.id = 12345
        
        # اختبار 1: confirm_clear_ (حذف كلمات الفلتر)
        print("\n🔍 اختبار 1: confirm_clear_ (حذف كلمات الفلتر)")
        print("اختبار confirm_clear_7_whitelist...")
        event1 = MockEvent("confirm_clear_7_whitelist")
        event1.message = MockMessage()
        await bot.handle_callback(event1)
        
        # اختبار 2: confirm_clear_replacements_ (حذف الاستبدالات)
        print("\n🔍 اختبار 2: confirm_clear_replacements_ (حذف الاستبدالات)")
        print("اختبار confirm_clear_replacements_7...")
        event2 = MockEvent("confirm_clear_replacements_7")
        event2.message = MockMessage()
        await bot.handle_callback(event2)
        
        # اختبار 3: confirm_clear_inline_buttons_ (حذف الأزرار)
        print("\n🔍 اختبار 3: confirm_clear_inline_buttons_ (حذف الأزرار)")
        print("اختبار confirm_clear_inline_buttons_7...")
        event3 = MockEvent("confirm_clear_inline_buttons_7")
        event3.message = MockMessage()
        await bot.handle_callback(event3)
        
        print("\n🎉 تم إكمال اختبار معالجات الأزرار بنجاح!")
        
    except Exception as e:
        print(f"❌ خطأ في اختبار معالجات الأزرار: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_callback_handlers())