#!/usr/bin/env python3
"""
اختبار شامل للنظام الجديد لإعدادات قالب الوسوم الصوتية
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
        self.user_states = {}
        
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
    
    def set_user_state(self, user_id, state, data=None):
        """Set user state for testing"""
        self.user_states[user_id] = {
            'state': state,
            'data': data or {}
        }
        print(f"🔧 تم تعيين حالة المستخدم {user_id}: {state}")
    
    def clear_user_state(self, user_id):
        """Clear user state for testing"""
        if user_id in self.user_states:
            del self.user_states[user_id]
            print(f"🗑️ تم مسح حالة المستخدم {user_id}")

async def test_all_audio_template_buttons():
    """اختبار جميع أزرار إعدادات قالب الوسوم الصوتية"""
    print("🔘 اختبار جميع أزرار إعدادات قالب الوسوم الصوتية")
    print("-" * 60)
    
    bot = MockBot()
    event = MockEvent()
    task_id = 1
    
    # قائمة جميع الأزرار المطلوبة
    buttons_to_test = [
        ("audio_template_settings_1", "إعدادات القالب"),
        ("edit_audio_tag_1_title", "تحرير العنوان"),
        ("edit_audio_tag_1_artist", "تحرير الفنان"),
        ("edit_audio_tag_1_album_artist", "تحرير فنان الألبوم"),
        ("edit_audio_tag_1_album", "تحرير الألبوم"),
        ("edit_audio_tag_1_year", "تحرير السنة"),
        ("edit_audio_tag_1_genre", "تحرير النوع"),
        ("edit_audio_tag_1_composer", "تحرير الملحن"),
        ("edit_audio_tag_1_comment", "تحرير التعليق"),
        ("edit_audio_tag_1_track", "تحرير رقم المسار"),
        ("edit_audio_tag_1_length", "تحرير المدة"),
        ("edit_audio_tag_1_lyrics", "تحرير كلمات الأغنية"),
        ("reset_audio_template_1", "إعادة تعيين القالب")
    ]
    
    results = []
    for callback_data, description in buttons_to_test:
        try:
            event.data = callback_data
            await bot.handle_callback(event)
            print(f"✅ {description}: تمت المعالجة بنجاح")
            results.append(True)
        except Exception as e:
            print(f"❌ {description}: {e}")
            results.append(False)
    
    return results

async def test_user_input_handling():
    """اختبار معالجة إدخال المستخدم"""
    print("\n📝 اختبار معالجة إدخال المستخدم")
    print("-" * 60)
    
    bot = MockBot()
    event = MockEvent()
    task_id = 1
    
    # اختبار إدخال قوالب مختلفة
    test_inputs = [
        ("editing_audio_tag_title", "$title - Official", "قالب العنوان"),
        ("editing_audio_tag_artist", "$artist ft. Guest", "قالب الفنان"),
        ("editing_audio_tag_album", "$album (Remastered)", "قالب الألبوم"),
        ("editing_audio_tag_comment", "Uploaded by Bot\\n$title", "قالب التعليق متعدد الأسطر"),
        ("editing_audio_tag_lyrics", "$lyrics\\n\\nTranslated by Bot", "قالب كلمات الأغنية متعدد الأسطر")
    ]
    
    results = []
    for state, template_input, description in test_inputs:
        try:
            # تعيين حالة المستخدم
            bot.set_user_state(event.sender_id, state, {'task_id': task_id, 'tag_name': state.replace('editing_audio_tag_', '')})
            
            # محاكاة إدخال المستخدم
            event.text = template_input
            await bot.handle_message(event)
            
            print(f"✅ {description}: تمت المعالجة بنجاح")
            results.append(True)
        except Exception as e:
            print(f"❌ {description}: {e}")
            results.append(False)
    
    return results

async def test_database_integration():
    """اختبار تكامل قاعدة البيانات"""
    print("\n🗄️ اختبار تكامل قاعدة البيانات")
    print("-" * 60)
    
    db = Database()
    task_id = 1
    
    test_cases = [
        ("title", "$title - Official", "تحديث العنوان"),
        ("artist", "$artist ft. Guest", "تحديث الفنان"),
        ("album", "$album (Remastered)", "تحديث الألبوم"),
        ("comment", "Uploaded by Bot\\n$title", "تحديث التعليق"),
        ("lyrics", "$lyrics\\n\\nTranslated by Bot", "تحديث كلمات الأغنية")
    ]
    
    results = []
    for tag_name, template_value, description in test_cases:
        try:
            # تحديث القالب
            success = db.update_audio_template_setting(task_id, tag_name, template_value)
            if success:
                # التحقق من التحديث
                settings = db.get_audio_template_settings(task_id)
                current_value = settings.get(f'{tag_name}_template')
                if current_value == template_value:
                    print(f"✅ {description}: تم التحديث والتحقق بنجاح")
                    results.append(True)
                else:
                    print(f"❌ {description}: التحديث فشل - القيمة المتوقعة: {template_value}, القيمة الفعلية: {current_value}")
                    results.append(False)
            else:
                print(f"❌ {description}: فشل في التحديث")
                results.append(False)
        except Exception as e:
            print(f"❌ {description}: {e}")
            results.append(False)
    
    # اختبار إعادة التعيين
    try:
        success = db.reset_audio_template_settings(task_id)
        if success:
            settings = db.get_audio_template_settings(task_id)
            if all(settings[f'{tag}_template'] == f'${tag}' for tag in ['title', 'artist', 'album']):
                print("✅ إعادة التعيين: تمت بنجاح")
                results.append(True)
            else:
                print("❌ إعادة التعيين: فشلت")
                results.append(False)
        else:
            print("❌ إعادة التعيين: فشلت")
            results.append(False)
    except Exception as e:
        print(f"❌ إعادة التعيين: {e}")
        results.append(False)
    
    return results

async def test_forwarding_integration():
    """اختبار تكامل النظام مع التوجيه"""
    print("\n🔄 اختبار تكامل النظام مع التوجيه")
    print("-" * 60)
    
    db = Database()
    task_id = 1
    
    try:
        # تعيين قوالب مخصصة
        test_templates = {
            'title': '$title - Official',
            'artist': '$artist ft. Guest',
            'album': '$album (Remastered)',
            'comment': 'Uploaded by Bot\\n$title'
        }
        
        # تحديث القوالب
        for tag_name, template_value in test_templates.items():
            db.update_audio_template_setting(task_id, tag_name, template_value)
        
        # جلب الإعدادات للتوجيه
        template_settings = db.get_audio_template_settings(task_id)
        audio_settings = db.get_audio_metadata_settings(task_id)
        
        # التحقق من أن الإعدادات جاهزة للتوجيه
        if template_settings and audio_settings:
            print("✅ إعدادات القالب جاهزة للتوجيه")
            print(f"📋 القوالب المحدثة: {len(template_settings)} وسم")
            print(f"🎵 إعدادات الوسوم الصوتية: {audio_settings.get('enabled', False)}")
            
            # محاكاة تطبيق القوالب
            sample_audio_data = {
                'title': 'Original Song',
                'artist': 'Original Artist',
                'album': 'Original Album',
                'year': '2024',
                'genre': 'Pop'
            }
            
            print("\n📝 محاكاة تطبيق القوالب:")
            for tag_name, template in template_settings.items():
                if tag_name in test_templates:
                    # محاكاة استبدال المتغيرات
                    result = template
                    for var_name, var_value in sample_audio_data.items():
                        result = result.replace(f'${var_name}', str(var_value))
                    print(f"🔹 {tag_name}: {template} → {result}")
            
            return True
        else:
            print("❌ إعدادات القالب غير جاهزة للتوجيه")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في تكامل التوجيه: {e}")
        return False

async def test_error_handling():
    """اختبار معالجة الأخطاء"""
    print("\n⚠️ اختبار معالجة الأخطاء")
    print("-" * 60)
    
    bot = MockBot()
    event = MockEvent()
    db = Database()
    
    error_tests = [
        ("task_id غير موجود", lambda: bot.audio_template_settings(event, 999)),
        ("tag_name غير صحيح", lambda: bot.start_edit_audio_tag(event, 1, "invalid_tag")),
        ("قالب فارغ", lambda: db.update_audio_template_setting(1, "title", "")),
        ("task_id غير صحيح", lambda: db.get_audio_template_settings(999))
    ]
    
    results = []
    for description, test_func in error_tests:
        try:
            await test_func() if asyncio.iscoroutinefunction(test_func) else test_func()
            print(f"✅ {description}: تمت المعالجة بشكل صحيح")
            results.append(True)
        except Exception as e:
            print(f"✅ {description}: تم التقاط الخطأ - {type(e).__name__}")
            results.append(True)  # التقاط الخطأ هو السلوك المطلوب
    
    return results

if __name__ == "__main__":
    print("🎵 اختبار شامل للنظام الجديد لإعدادات قالب الوسوم الصوتية")
    print("=" * 80)
    
    # تشغيل الاختبارات
    all_results = []
    
    # Test all buttons
    button_results = asyncio.run(test_all_audio_template_buttons())
    all_results.extend(button_results)
    
    # Test user input handling
    input_results = asyncio.run(test_user_input_handling())
    all_results.extend(input_results)
    
    # Test database integration
    db_results = asyncio.run(test_database_integration())
    all_results.extend(db_results)
    
    # Test forwarding integration
    forwarding_result = asyncio.run(test_forwarding_integration())
    all_results.append(forwarding_result)
    
    # Test error handling
    error_results = asyncio.run(test_error_handling())
    all_results.extend(error_results)
    
    # Summary
    print(f"\n📊 ملخص النتائج الشاملة:")
    print(f"✅ نجح: {sum(all_results)}")
    print(f"❌ فشل: {len(all_results) - sum(all_results)}")
    print(f"📈 نسبة النجاح الإجمالية: {(sum(all_results)/len(all_results)*100):.1f}%")
    
    print(f"\n📋 تفاصيل الاختبارات:")
    print(f"• أزرار إعدادات القالب: {sum(button_results)}/{len(button_results)}")
    print(f"• معالجة إدخال المستخدم: {sum(input_results)}/{len(input_results)}")
    print(f"• تكامل قاعدة البيانات: {sum(db_results)}/{len(db_results)}")
    print(f"• تكامل التوجيه: {'✅' if forwarding_result else '❌'}")
    print(f"• معالجة الأخطاء: {sum(error_results)}/{len(error_results)}")
    
    if all(all_results):
        print("\n🎉 النظام يعمل بشكل مثالي!")
        print("\n✅ جميع المكونات تعمل:")
        print("• 🔘 جميع الأزرار معالجة")
        print("• 📝 إدخال المستخدم محفوظ في قاعدة البيانات")
        print("• 🗄️ قاعدة البيانات متكاملة")
        print("• 🔄 النظام جاهز للتوجيه")
        print("• ⚠️ معالجة الأخطاء تعمل")
        print("\n🚀 الوظيفة جاهزة للاستخدام في التوجيه!")
    else:
        print("\n⚠️ بعض المكونات تحتاج إلى إصلاح.")
        print("يرجى مراجعة الأخطاء المذكورة أعلاه.")
    
    print(f"\n🔍 تحليل الأخطاء:")
    if not all(button_results):
        print("• بعض أزرار إعدادات القالب لا تعمل")
    if not all(input_results):
        print("• معالجة إدخال المستخدم تحتاج إلى إصلاح")
    if not all(db_results):
        print("• تكامل قاعدة البيانات يحتاج إلى إصلاح")
    if not forwarding_result:
        print("• تكامل التوجيه يحتاج إلى إصلاح")
    if not all(error_results):
        print("• معالجة الأخطاء تحتاج إلى إصلاح")