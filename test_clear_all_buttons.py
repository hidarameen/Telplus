#!/usr/bin/env python3
"""
اختبار أزرار احذف الكل في لوحة التحكم
"""

import asyncio
import sys
import os

# إضافة المجلد الحالي إلى مسار Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot_package.bot_simple import SimpleTelegramBot

async def test_clear_all_buttons():
    """اختبار أزرار احذف الكل"""
    try:
        print("🚀 بدء اختبار أزرار احذف الكل...")
        
        # إنشاء مثيل البوت
        bot = SimpleTelegramBot()
        
        # إنشاء كائن وهمي للحدث
        class MockEvent:
            def __init__(self):
                self.sender_id = 6556918772  # نفس user_id الموجود في قاعدة البيانات
                self.chat_id = 123456789
                
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
                
        event = MockEvent()
        event.message = MockMessage()
        
        # اختبار 1: حذف كلمات الفلتر
        print("\n🔍 اختبار 1: حذف كلمات الفلتر")
        print("اختبار confirm_clear_filter...")
        await bot.confirm_clear_filter(event, 7, 'whitelist')
        
        # اختبار 2: حذف الاستبدالات النصية
        print("\n🔍 اختبار 2: حذف الاستبدالات النصية")
        print("اختبار clear_replacements_execute...")
        await bot.clear_replacements_execute(event, 7)
        
        # اختبار 3: حذف الأزرار الإنلاين
        print("\n🔍 اختبار 3: حذف الأزرار الإنلاين")
        print("اختبار clear_inline_buttons_execute...")
        await bot.clear_inline_buttons_execute(event, 7)
        
        print("\n🎉 تم إكمال اختبار أزرار احذف الكل بنجاح!")
        
    except Exception as e:
        print(f"❌ خطأ في اختبار أزرار احذف الكل: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_clear_all_buttons())