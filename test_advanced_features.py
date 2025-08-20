#!/usr/bin/env python3
"""
اختبار زر المميزات المتقدمة
"""

import asyncio
import sys
import os

# إضافة المجلد الحالي إلى مسار Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot_package.bot_simple import SimpleTelegramBot

async def test_advanced_features():
    """اختبار زر المميزات المتقدمة"""
    try:
        print("🚀 بدء اختبار زر المميزات المتقدمة...")
        
        # إنشاء مثيل البوت
        bot = SimpleTelegramBot()
        
        # اختبار دالة show_advanced_features
        print("📋 اختبار دالة show_advanced_features...")
        
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
                
        # إضافة خاصية message للحدث
        event = MockEvent()
        event.message = MockMessage()
        
        event = MockEvent()
        
        # اختبار مع مهمة موجودة
        print("\n✅ اختبار مع مهمة موجودة (7):")
        await bot.show_advanced_features(event, 7)
        
        # اختبار مع مهمة غير موجودة
        print("\n❌ اختبار مع مهمة غير موجودة (999):")
        await bot.show_advanced_features(event, 999)
        
        print("\n🎉 تم إكمال اختبار زر المميزات المتقدمة بنجاح!")
        
    except Exception as e:
        print(f"❌ خطأ في اختبار زر المميزات المتقدمة: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_advanced_features())