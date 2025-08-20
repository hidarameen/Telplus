#!/usr/bin/env python3
"""
اختبار شامل لقسم الوسوم الصوتية وأزراره الفرعية
"""

import asyncio
import sys
import os

# إضافة المجلد الحالي إلى مسار Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot_package.bot_simple import SimpleTelegramBot

async def test_audio_metadata_menu():
    """اختبار شامل لقسم الوسوم الصوتية"""
    try:
        print("🎵 بدء اختبار قسم الوسوم الصوتية...")
        
        # إنشاء مثيل البوت
        bot = SimpleTelegramBot()
        
        # إنشاء كائن وهمي للحدث
        class MockEvent:
            def __init__(self, data=None):
                self.sender_id = 6556918772  # نفس user_id الموجود في قاعدة البيانات
                self.chat_id = 123456789
                self.data = data.encode('utf-8') if data else b''
                
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
        
        # اختبار 1: القائمة الرئيسية للوسوم الصوتية
        print("\n🔍 اختبار 1: القائمة الرئيسية للوسوم الصوتية")
        event1 = MockEvent()
        event1.message = MockMessage()
        await bot.audio_metadata_settings(event1, 7)
        
        # اختبار 2: تبديل حالة الوسوم الصوتية
        print("\n🔍 اختبار 2: تبديل حالة الوسوم الصوتية")
        event2 = MockEvent("toggle_audio_metadata_7")
        event2.message = MockMessage()
        await bot.handle_callback(event2)
        
        # اختبار 3: اختيار قالب الوسوم الصوتية
        print("\n🔍 اختبار 3: اختيار قالب الوسوم الصوتية")
        event3 = MockEvent("select_audio_template_7")
        event3.message = MockMessage()
        await bot.handle_callback(event3)
        
        # اختبار 4: تعيين قالب محسن
        print("\n🔍 اختبار 4: تعيين قالب محسن")
        event4 = MockEvent("set_audio_template_7_enhanced")
        event4.message = MockMessage()
        await bot.handle_callback(event4)
        
        # اختبار 5: إعدادات صورة الغلاف
        print("\n🔍 اختبار 5: إعدادات صورة الغلاف")
        event5 = MockEvent("album_art_settings_7")
        event5.message = MockMessage()
        await bot.handle_callback(event5)
        
        # اختبار 6: إعدادات دمج المقاطع
        print("\n🔍 اختبار 6: إعدادات دمج المقاطع")
        event6 = MockEvent("audio_merge_settings_7")
        event6.message = MockMessage()
        await bot.handle_callback(event6)
        
        # اختبار 7: تبديل حالة دمج المقاطع
        print("\n🔍 اختبار 7: تبديل حالة دمج المقاطع")
        event7 = MockEvent("toggle_audio_merge_7")
        event7.message = MockMessage()
        await bot.handle_callback(event7)
        
        # اختبار 8: إعدادات المقدمة
        print("\n🔍 اختبار 8: إعدادات المقدمة")
        event8 = MockEvent("intro_audio_settings_7")
        event8.message = MockMessage()
        await bot.handle_callback(event8)
        
        # اختبار 9: إعدادات الخاتمة
        print("\n🔍 اختبار 9: إعدادات الخاتمة")
        event9 = MockEvent("outro_audio_settings_7")
        event9.message = MockMessage()
        await bot.handle_callback(event9)
        
        # اختبار 10: الإعدادات المتقدمة
        print("\n🔍 اختبار 10: الإعدادات المتقدمة")
        event10 = MockEvent("advanced_audio_settings_7")
        event10.message = MockMessage()
        await bot.handle_callback(event10)
        
        print("\n🎉 تم إكمال اختبار قسم الوسوم الصوتية بنجاح!")
        
    except Exception as e:
        print(f"❌ خطأ في اختبار قسم الوسوم الصوتية: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_audio_metadata_menu())