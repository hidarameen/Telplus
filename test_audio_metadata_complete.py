#!/usr/bin/env python3
"""
اختبار شامل لقسم الوسوم الصوتية
"""

import asyncio
import sys
import os

# إضافة المسار للوحدات
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot_package'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'database'))

from database.database import Database
from telethon import Button

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

class MockBot:
    def __init__(self):
        self.db = Database()
        self.user_messages = {}
        
    async def edit_or_send_message(self, event, text, buttons=None):
        print(f"📝 رسالة: {text}")
        if buttons:
            print(f"🔘 الأزرار: {len(buttons)} صفوف")
            for i, row in enumerate(buttons):
                for j, button in enumerate(row):
                    print(f"  [{i}][{j}]: {button.text} -> {button.data.decode()}")
    
    async def album_art_settings(self, event, task_id):
        """Show album art settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        # Get current album art settings
        audio_settings = self.db.get_audio_metadata_settings(task_id)
        art_enabled = audio_settings.get('album_art_enabled', False)
        apply_to_all = audio_settings.get('apply_art_to_all', False)
        art_path = audio_settings.get('album_art_path', '')
        
        art_status = "🟢 مفعل" if art_enabled else "🔴 معطل"
        apply_all_status = "🟢 نعم" if apply_to_all else "🔴 لا"
        art_path_display = art_path if art_path else "غير محدد"
        
        buttons = [
            [Button.inline(f"🔄 تبديل الحالة ({art_status.split()[0]})", f"toggle_album_art_enabled_{task_id}")],
            [Button.inline("🖼️ رفع صورة غلاف", f"upload_album_art_{task_id}")],
            [Button.inline(f"⚙️ تطبيق على الجميع ({apply_all_status.split()[0]})", f"toggle_apply_art_to_all_{task_id}")],
            [Button.inline("🔙 رجوع لإعدادات الوسوم الصوتية", f"audio_metadata_settings_{task_id}")]
        ]
        
        message_text = (
            f"🖼️ إعدادات صورة الغلاف للمهمة: {task_name}\n\n"
            f"📝 الوصف:\n"
            f"• رفع صورة غلاف مخصصة للملفات الصوتية\n"
            f"• خيار تطبيقها على جميع الملفات\n"
            f"• خيار تطبيقها فقط على الملفات بدون صورة\n"
            f"• الحفاظ على الجودة 100%\n"
            f"• دعم الصيغ: JPG, PNG, BMP, TIFF\n\n"
            f"📊 الحالة الحالية:\n"
            f"• الحالة: {art_status}\n"
            f"• تطبيق على الجميع: {apply_all_status}\n"
            f"• المسار الحالي: {art_path_display}\n\n"
            f"اختر الإعداد الذي تريد تعديله أو ارفع صورة جديدة:"
        )
        
        await self.edit_or_send_message(event, message_text, buttons=buttons)
    
    async def audio_merge_settings(self, event, task_id):
        """Show audio merge settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        # Get current audio merge settings
        audio_settings = self.db.get_audio_metadata_settings(task_id)
        merge_enabled = audio_settings.get('audio_merge_enabled', False)
        intro_path = audio_settings.get('intro_path', '')
        outro_path = audio_settings.get('outro_path', '')
        intro_position = audio_settings.get('intro_position', 'start')
        
        merge_status = "🟢 مفعل" if merge_enabled else "🔴 معطل"
        intro_path_display = intro_path if intro_path else "غير محدد"
        outro_path_display = outro_path if outro_path else "غير محدد"
        intro_position_display = "البداية" if intro_position == 'start' else "النهاية"
        
        buttons = [
            [Button.inline(f"🎚️ تبديل حالة الدمج ({merge_status.split()[0]})", f"toggle_audio_merge_{task_id}")],
            [Button.inline("🎵 مقطع مقدمة", f"intro_audio_settings_{task_id}")],
            [Button.inline("🎵 مقطع خاتمة", f"outro_audio_settings_{task_id}")],
            [Button.inline("⚙️ خيارات الدمج", f"merge_options_{task_id}")],
            [Button.inline("🔙 رجوع لإعدادات الوسوم الصوتية", f"audio_metadata_settings_{task_id}")]
        ]
        
        message_text = (
            f"🔗 إعدادات دمج المقاطع الصوتية للمهمة: {task_name}\n\n"
            f"📝 الوصف:\n"
            f"• إضافة مقطع مقدمة في البداية\n"
            f"• إضافة مقطع خاتمة في النهاية\n"
            f"• اختيار موضع المقدمة (بداية أو نهاية)\n"
            f"• دعم جميع الصيغ الصوتية\n"
            f"• جودة عالية 320k MP3\n\n"
            f"📊 الحالة الحالية:\n"
            f"• حالة الدمج: {merge_status}\n"
            f"• مقدمة: {intro_path_display}\n"
            f"• خاتمة: {outro_path_display}\n"
            f"• موضع المقدمة: {intro_position_display}\n\n"
            f"اختر الإعداد الذي تريد تعديله:"
        )
        
        await self.edit_or_send_message(event, message_text, buttons=buttons)
    
    async def advanced_audio_settings(self, event, task_id):
        """Show advanced audio settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        # Get current advanced settings
        audio_settings = self.db.get_audio_metadata_settings(task_id)
        preserve_quality = audio_settings.get('preserve_quality', True)
        convert_to_mp3 = audio_settings.get('convert_to_mp3', False)
        
        preserve_status = "🟢" if preserve_quality else "🔴"
        convert_status = "🟢" if convert_to_mp3 else "🔴"
        
        buttons = [
            [Button.inline(f"{preserve_status} الحفاظ على الجودة", f"toggle_preserve_quality_{task_id}")],
            [Button.inline(f"{convert_status} التحويل إلى MP3", f"toggle_convert_to_mp3_{task_id}")],
            [Button.inline("🔙 رجوع لإعدادات الوسوم الصوتية", f"audio_metadata_settings_{task_id}")]
        ]
        
        message_text = (
            f"⚙️ الإعدادات المتقدمة للوسوم الصوتية للمهمة: {task_name}\n\n"
            f"📝 الوصف:\n"
            f"• الحفاظ على الجودة الأصلية 100%\n"
            f"• تحويل إلى MP3 مع الحفاظ على الدقة\n"
            f"• معالجة مرة واحدة وإعادة الاستخدام\n"
            f"• Cache ذكي للملفات المعالجة\n"
            f"• إعدادات الأداء والسرعة\n\n"
            f"📊 الحالة الحالية:\n"
            f"• الحفاظ على الجودة: {preserve_status} {'مفعل' if preserve_quality else 'معطل'}\n"
            f"• التحويل إلى MP3: {convert_status} {'مفعل' if convert_to_mp3 else 'معطل'}\n\n"
            f"اختر الإعداد الذي تريد تعديله:"
        )
        
        await self.edit_or_send_message(event, message_text, buttons=buttons)

async def test_audio_metadata_sections():
    """اختبار جميع أقسام الوسوم الصوتية"""
    print("🎵 بدء اختبار قسم الوسوم الصوتية")
    print("=" * 50)
    
    bot = MockBot()
    event = MockEvent()
    task_id = 7  # مهمة موجودة في قاعدة البيانات
    
    print(f"🔍 اختبار المهمة: {task_id}")
    print("-" * 30)
    
    # اختبار إعدادات صورة الغلاف
    print("\n🖼️ اختبار إعدادات صورة الغلاف:")
    await bot.album_art_settings(event, task_id)
    
    # اختبار إعدادات دمج المقاطع
    print("\n🔗 اختبار إعدادات دمج المقاطع:")
    await bot.audio_merge_settings(event, task_id)
    
    # اختبار الإعدادات المتقدمة
    print("\n⚙️ اختبار الإعدادات المتقدمة:")
    await bot.advanced_audio_settings(event, task_id)
    
    print("\n✅ تم الانتهاء من اختبار قسم الوسوم الصوتية")

async def test_audio_metadata_database():
    """اختبار قاعدة بيانات الوسوم الصوتية"""
    print("\n🗄️ اختبار قاعدة بيانات الوسوم الصوتية")
    print("=" * 50)
    
    db = Database()
    task_id = 7
    
    # اختبار الحصول على الإعدادات
    print(f"🔍 الحصول على إعدادات الوسوم الصوتية للمهمة {task_id}:")
    settings = db.get_audio_metadata_settings(task_id)
    print(f"✅ الإعدادات: {settings}")
    
    # اختبار تحديث الإعدادات
    print(f"\n🔄 اختبار تحديث إعدادات الوسوم الصوتية:")
    
    # تحديث تفعيل صورة الغلاف
    result = db.update_audio_metadata_setting(task_id, 'album_art_enabled', True)
    print(f"✅ تحديث تفعيل صورة الغلاف: {result}")
    
    # تحديث تطبيق على الجميع
    result = db.update_audio_metadata_setting(task_id, 'apply_art_to_all', True)
    print(f"✅ تحديث تطبيق على الجميع: {result}")
    
    # تحديث تفعيل دمج المقاطع
    result = db.update_audio_metadata_setting(task_id, 'audio_merge_enabled', True)
    print(f"✅ تحديث تفعيل دمج المقاطع: {result}")
    
    # تحديث الحفاظ على الجودة
    result = db.update_audio_metadata_setting(task_id, 'preserve_quality', False)
    print(f"✅ تحديث الحفاظ على الجودة: {result}")
    
    # تحديث التحويل إلى MP3
    result = db.update_audio_metadata_setting(task_id, 'convert_to_mp3', True)
    print(f"✅ تحديث التحويل إلى MP3: {result}")
    
    # التحقق من التحديثات
    print(f"\n🔍 التحقق من التحديثات:")
    updated_settings = db.get_audio_metadata_settings(task_id)
    print(f"✅ الإعدادات المحدثة: {updated_settings}")
    
    print("\n✅ تم الانتهاء من اختبار قاعدة البيانات")

if __name__ == "__main__":
    print("🎵 اختبار شامل لقسم الوسوم الصوتية")
    print("=" * 60)
    
    # تشغيل الاختبارات
    asyncio.run(test_audio_metadata_database())
    asyncio.run(test_audio_metadata_sections())
    
    print("\n🎉 تم الانتهاء من جميع الاختبارات!")