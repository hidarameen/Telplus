#!/usr/bin/env python3
"""
اختبار النظام الجديد لإعدادات قالب الوسوم الصوتية
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

async def test_audio_template_settings():
    """اختبار عرض إعدادات قالب الوسوم الصوتية"""
    print("⚙️ اختبار عرض إعدادات قالب الوسوم الصوتية")
    print("-" * 50)
    
    bot = MockBot()
    event = MockEvent()
    task_id = 1
    
    try:
        await bot.audio_template_settings(event, task_id)
        print("✅ تم عرض إعدادات قالب الوسوم الصوتية بنجاح")
        return True
    except Exception as e:
        print(f"❌ خطأ في عرض إعدادات قالب الوسوم الصوتية: {e}")
        return False

async def test_start_edit_audio_tag():
    """اختبار بدء تحرير وسم صوتي"""
    print("\n✏️ اختبار بدء تحرير وسم صوتي")
    print("-" * 50)
    
    bot = MockBot()
    event = MockEvent()
    task_id = 1
    tag_name = "title"
    
    try:
        await bot.start_edit_audio_tag(event, task_id, tag_name)
        print("✅ تم بدء تحرير وسم العنوان بنجاح")
        return True
    except Exception as e:
        print(f"❌ خطأ في بدء تحرير وسم العنوان: {e}")
        return False

async def test_reset_audio_template():
    """اختبار إعادة تعيين قالب الوسوم"""
    print("\n🔄 اختبار إعادة تعيين قالب الوسوم")
    print("-" * 50)
    
    bot = MockBot()
    event = MockEvent()
    task_id = 1
    
    try:
        await bot.reset_audio_template(event, task_id)
        print("✅ تم إعادة تعيين قالب الوسوم بنجاح")
        return True
    except Exception as e:
        print(f"❌ خطأ في إعادة تعيين قالب الوسوم: {e}")
        return False

async def test_database_functions():
    """اختبار دوال قاعدة البيانات"""
    print("\n🗄️ اختبار دوال قاعدة البيانات")
    print("-" * 50)
    
    db = Database()
    task_id = 1
    
    try:
        # اختبار جلب الإعدادات
        settings = db.get_audio_template_settings(task_id)
        print(f"✅ تم جلب إعدادات القالب: {len(settings)} وسوم")
        
        # اختبار تحديث إعداد
        success = db.update_audio_template_setting(task_id, 'title', '$title - Official')
        print(f"✅ تم تحديث قالب العنوان: {success}")
        
        # اختبار إعادة التعيين
        success = db.reset_audio_template_settings(task_id)
        print(f"✅ تم إعادة تعيين القالب: {success}")
        
        return True
    except Exception as e:
        print(f"❌ خطأ في دوال قاعدة البيانات: {e}")
        return False

async def test_callback_handlers():
    """اختبار معالجات الأزرار"""
    print("\n🔘 اختبار معالجات الأزرار")
    print("-" * 50)
    
    bot = MockBot()
    event = MockEvent()
    
    callbacks_to_test = [
        ("audio_template_settings_1", "إعدادات القالب"),
        ("edit_audio_tag_1_title", "تحرير العنوان"),
        ("edit_audio_tag_1_artist", "تحرير الفنان"),
        ("reset_audio_template_1", "إعادة تعيين القالب")
    ]
    
    results = []
    for callback_data, description in callbacks_to_test:
        try:
            event.data = callback_data
            await bot.handle_callback(event)
            print(f"✅ {description}: تمت المعالجة بنجاح")
            results.append(True)
        except Exception as e:
            print(f"❌ {description}: {e}")
            results.append(False)
    
    return results

async def test_template_validation():
    """اختبار التحقق من صحة القوالب"""
    print("\n✅ اختبار التحقق من صحة القوالب")
    print("-" * 50)
    
    db = Database()
    task_id = 1
    
    test_templates = [
        ("title", "$title - Official"),
        ("artist", "$artist ft. Guest"),
        ("album", "$album (Remastered)"),
        ("comment", "Uploaded by Bot\\n$title"),
        ("lyrics", "$lyrics\\n\\nTranslated by Bot")
    ]
    
    results = []
    for tag_name, template in test_templates:
        try:
            success = db.update_audio_template_setting(task_id, tag_name, template)
            if success:
                print(f"✅ قالب {tag_name}: {template}")
                results.append(True)
            else:
                print(f"❌ فشل في تحديث قالب {tag_name}")
                results.append(False)
        except Exception as e:
            print(f"❌ خطأ في قالب {tag_name}: {e}")
            results.append(False)
    
    return results

if __name__ == "__main__":
    print("🎵 اختبار النظام الجديد لإعدادات قالب الوسوم الصوتية")
    print("=" * 80)
    
    # تشغيل الاختبارات
    all_results = []
    
    # Test audio template settings display
    settings_result = asyncio.run(test_audio_template_settings())
    all_results.append(settings_result)
    
    # Test start edit audio tag
    edit_result = asyncio.run(test_start_edit_audio_tag())
    all_results.append(edit_result)
    
    # Test reset audio template
    reset_result = asyncio.run(test_reset_audio_template())
    all_results.append(reset_result)
    
    # Test database functions
    db_result = asyncio.run(test_database_functions())
    all_results.append(db_result)
    
    # Test callback handlers
    callback_results = asyncio.run(test_callback_handlers())
    all_results.extend(callback_results)
    
    # Test template validation
    template_results = asyncio.run(test_template_validation())
    all_results.extend(template_results)
    
    # Summary
    print(f"\n📊 ملخص النتائج:")
    print(f"✅ نجح: {sum(all_results)}")
    print(f"❌ فشل: {len(all_results) - sum(all_results)}")
    print(f"📈 نسبة النجاح الإجمالية: {(sum(all_results)/len(all_results)*100):.1f}%")
    
    if all(all_results):
        print("\n🎉 النظام الجديد يعمل بشكل مثالي!")
        print("\n✅ الميزات المختبرة:")
        print("• ⚙️ عرض إعدادات قالب الوسوم الصوتية")
        print("• ✏️ تحرير وسوم فردية")
        print("• 🔄 إعادة تعيين للقيم الافتراضية")
        print("• 🗄️ دوال قاعدة البيانات")
        print("• 🔘 معالجات الأزرار")
        print("• ✅ التحقق من صحة القوالب")
        print("\n📋 الميزات الجديدة:")
        print("• 🔹 العنوان (Title)")
        print("• 🔹 الفنان (Artist)")
        print("• 🔹 فنان الألبوم (Album Artist)")
        print("• 🔹 الألبوم (Album)")
        print("• 🔹 السنة (Year)")
        print("• 🔹 النوع (Genre)")
        print("• 🔹 الملحن (Composer)")
        print("• 🔹 تعليق (Comment)")
        print("• 🔹 رقم المسار (Track)")
        print("• 🔹 المدة (Length)")
        print("• 🔹 كلمات الأغنية (Lyrics)")
        print("\n💡 دعم المتغيرات:")
        print("• `$title`, `$artist`, `$album`, `$year`, `$genre`")
        print("• `$track`, `$length`, `$lyrics`")
        print("• دعم النص متعدد الأسطر")
        print("• دعم إضافة نص مخصص")
    else:
        print("\n⚠️ بعض الاختبارات فشلت. يرجى مراجعة النظام.")
    
    print(f"\n📋 تفاصيل الاختبارات:")
    print(f"• عرض الإعدادات: {'✅' if settings_result else '❌'}")
    print(f"• تحرير الوسوم: {'✅' if edit_result else '❌'}")
    print(f"• إعادة التعيين: {'✅' if reset_result else '❌'}")
    print(f"• قاعدة البيانات: {'✅' if db_result else '❌'}")
    print(f"• معالجات الأزرار: {sum(callback_results)}/{len(callback_results)}")
    print(f"• التحقق من القوالب: {sum(template_results)}/{len(template_results)}")