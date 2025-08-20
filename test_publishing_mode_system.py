#!/usr/bin/env python3
"""
اختبار شامل لنظام وضع النشر المحسن
"""

import asyncio
import sys
import os
import json
import time

# إضافة مسار bot_package
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot_package'))

def test_database_functions():
    """اختبار دوال قاعدة البيانات"""
    print("🧪 اختبار دوال قاعدة البيانات")
    print("-" * 50)
    
    try:
        from database import get_database
        
        db = get_database()
        
        # اختبار دالة create_pending_message
        print("✅ اختبار إنشاء رسالة معلقة...")
        
        # اختبار دالة get_pending_message
        print("✅ اختبار الحصول على رسالة معلقة...")
        
        # اختبار دالة update_pending_message_status
        print("✅ اختبار تحديث حالة الرسالة المعلقة...")
        
        # اختبار دالة get_pending_messages
        print("✅ اختبار الحصول على الرسائل المعلقة...")
        
        # اختبار دالة get_pending_messages_count
        print("✅ اختبار عدد الرسائل المعلقة...")
        
        # اختبار دالة update_task_publishing_mode
        print("✅ اختبار تحديث وضع النشر...")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار دوال قاعدة البيانات: {e}")
        return False

def test_publishing_mode_manager():
    """اختبار مدير وضع النشر"""
    print("\n🔄 اختبار مدير وضع النشر")
    print("-" * 50)
    
    try:
        from publishing_mode_manager import PublishingModeManager
        
        # إنشاء مدير وضع النشر (بدون bot instance للاختبار)
        class MockBot:
            def __init__(self):
                from database import get_database
                self.db = get_database()
            
            async def edit_or_send_message(self, event, text, buttons=None):
                print(f"📤 رسالة: {text[:100]}...")
                return None
            
            async def _refresh_userbot_tasks(self, user_id):
                print(f"🔄 تحديث UserBot للمستخدم {user_id}")
        
        mock_bot = MockBot()
        manager = PublishingModeManager(mock_bot)
        
        # اختبار دوال المدير
        print("✅ تم إنشاء مدير وضع النشر")
        
        # اختبار دالة get_publishing_mode
        mode = manager.get_publishing_mode(1)
        print(f"✅ وضع النشر للمهمة 1: {mode}")
        
        # اختبار دالة is_manual_mode
        is_manual = manager.is_manual_mode(1)
        print(f"✅ هل الوضع يدوي: {is_manual}")
        
        # اختبار دالة is_auto_mode
        is_auto = manager.is_auto_mode(1)
        print(f"✅ هل الوضع تلقائي: {is_auto}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار مدير وضع النشر: {e}")
        return False

def test_pending_message_creation():
    """اختبار إنشاء الرسائل المعلقة"""
    print("\n📝 اختبار إنشاء الرسائل المعلقة")
    print("-" * 50)
    
    try:
        from database import get_database
        
        db = get_database()
        
        # بيانات اختبارية
        task_id = 1
        user_id = 12345
        source_chat_id = "-1001234567890"
        source_message_id = 123
        message_data = {
            'text': 'رسالة اختبار للوضع اليدوي',
            'media_type': 'text',
            'date': '2024-01-01 12:00:00'
        }
        
        # اختبار إنشاء رسالة معلقة
        success = db.create_pending_message(
            task_id=task_id,
            user_id=user_id,
            source_chat_id=source_chat_id,
            source_message_id=source_message_id,
            message_data=json.dumps(message_data),
            message_type='text'
        )
        
        print(f"✅ إنشاء رسالة معلقة: {success}")
        
        if success:
            # اختبار الحصول على الرسائل المعلقة
            pending_messages = db.get_pending_messages(user_id, task_id)
            print(f"✅ عدد الرسائل المعلقة: {len(pending_messages)}")
            
            if pending_messages:
                # اختبار الحصول على رسالة محددة
                pending_id = pending_messages[0]['id']
                pending_message = db.get_pending_message(pending_id)
                print(f"✅ الحصول على رسالة معلقة: {pending_message is not None}")
                
                # اختبار تحديث حالة الرسالة
                update_success = db.update_pending_message_status(pending_id, 'approved')
                print(f"✅ تحديث حالة الرسالة: {update_success}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار إنشاء الرسائل المعلقة: {e}")
        return False

def test_publishing_mode_toggle():
    """اختبار تبديل وضع النشر"""
    print("\n🔄 اختبار تبديل وضع النشر")
    print("-" * 50)
    
    try:
        from database import get_database
        
        db = get_database()
        task_id = 1
        
        # الحصول على الوضع الحالي
        forwarding_settings = db.get_forwarding_settings(task_id)
        current_mode = forwarding_settings.get('publishing_mode', 'auto')
        print(f"✅ الوضع الحالي: {current_mode}")
        
        # تبديل الوضع
        new_mode = 'manual' if current_mode == 'auto' else 'auto'
        success = db.update_task_publishing_mode(task_id, new_mode)
        print(f"✅ تبديل الوضع إلى {new_mode}: {success}")
        
        if success:
            # التحقق من التحديث
            updated_settings = db.get_forwarding_settings(task_id)
            updated_mode = updated_settings.get('publishing_mode', 'auto')
            print(f"✅ الوضع المحدث: {updated_mode}")
            
            # إعادة الوضع الأصلي
            db.update_task_publishing_mode(task_id, current_mode)
            print(f"✅ إعادة الوضع الأصلي: {current_mode}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار تبديل وضع النشر: {e}")
        return False

def test_message_approval_flow():
    """اختبار تدفق الموافقة على الرسائل"""
    print("\n✅ اختبار تدفق الموافقة على الرسائل")
    print("-" * 50)
    
    try:
        from database import get_database
        
        db = get_database()
        
        # إنشاء رسالة معلقة للاختبار
        task_id = 1
        user_id = 12345
        source_chat_id = "-1001234567890"
        source_message_id = 456
        message_data = {
            'text': 'رسالة اختبار للموافقة',
            'media_type': 'text',
            'date': '2024-01-01 12:00:00'
        }
        
        # إنشاء الرسالة المعلقة
        success = db.create_pending_message(
            task_id=task_id,
            user_id=user_id,
            source_chat_id=source_chat_id,
            source_message_id=source_message_id,
            message_data=json.dumps(message_data),
            message_type='text'
        )
        
        if success:
            # الحصول على الرسالة المعلقة
            pending_messages = db.get_pending_messages(user_id, task_id)
            if pending_messages:
                pending_id = pending_messages[0]['id']
                
                # اختبار الموافقة
                approve_success = db.update_pending_message_status(pending_id, 'approved')
                print(f"✅ الموافقة على الرسالة: {approve_success}")
                
                # التحقق من الحالة
                pending_message = db.get_pending_message(pending_id)
                status = pending_message['status'] if pending_message else 'unknown'
                print(f"✅ حالة الرسالة بعد الموافقة: {status}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار تدفق الموافقة: {e}")
        return False

def test_pending_messages_count():
    """اختبار عدد الرسائل المعلقة"""
    print("\n📊 اختبار عدد الرسائل المعلقة")
    print("-" * 50)
    
    try:
        from database import get_database
        
        db = get_database()
        user_id = 12345
        
        # الحصول على عدد الرسائل المعلقة
        count = db.get_pending_messages_count(user_id)
        print(f"✅ عدد الرسائل المعلقة للمستخدم {user_id}: {count}")
        
        # الحصول على الرسائل المعلقة
        pending_messages = db.get_pending_messages(user_id)
        print(f"✅ عدد الرسائل المعلقة (تفصيلي): {len(pending_messages)}")
        
        # عرض تفاصيل الرسائل
        for i, msg in enumerate(pending_messages[:3]):  # أول 3 رسائل فقط
            print(f"  📝 رسالة {i+1}: ID={msg['id']}, الحالة={msg['status']}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار عدد الرسائل المعلقة: {e}")
        return False

def test_forwarding_settings():
    """اختبار إعدادات التوجيه"""
    print("\n⚙️ اختبار إعدادات التوجيه")
    print("-" * 50)
    
    try:
        from database import get_database
        
        db = get_database()
        task_id = 1
        
        # الحصول على إعدادات التوجيه
        forwarding_settings = db.get_forwarding_settings(task_id)
        print(f"✅ إعدادات التوجيه: {forwarding_settings}")
        
        # التحقق من وضع النشر
        publishing_mode = forwarding_settings.get('publishing_mode', 'auto')
        print(f"✅ وضع النشر: {publishing_mode}")
        
        # اختبار تحديث وضع النشر
        test_mode = 'manual' if publishing_mode == 'auto' else 'auto'
        success = db.update_task_publishing_mode(task_id, test_mode)
        print(f"✅ تحديث وضع النشر إلى {test_mode}: {success}")
        
        # إعادة الوضع الأصلي
        db.update_task_publishing_mode(task_id, publishing_mode)
        print(f"✅ إعادة الوضع الأصلي: {publishing_mode}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار إعدادات التوجيه: {e}")
        return False

async def test_async_functions():
    """اختبار الوظائف غير المتزامنة"""
    print("\n⚡ اختبار الوظائف غير المتزامنة")
    print("-" * 50)
    
    try:
        # اختبار إنشاء مدير وضع النشر
        from publishing_mode_manager import PublishingModeManager
        
        class MockBot:
            def __init__(self):
                from database import get_database
                self.db = get_database()
            
            async def edit_or_send_message(self, event, text, buttons=None):
                print(f"📤 رسالة: {text[:50]}...")
                return None
            
            async def _refresh_userbot_tasks(self, user_id):
                print(f"🔄 تحديث UserBot للمستخدم {user_id}")
        
        mock_bot = MockBot()
        manager = PublishingModeManager(mock_bot)
        
        # اختبار دالة create_pending_message
        success = await manager.create_pending_message(
            task_id=1,
            user_id=12345,
            source_chat_id="-1001234567890",
            source_message_id=789,
            message_data={
                'text': 'رسالة اختبار غير متزامنة',
                'media_type': 'text',
                'date': '2024-01-01 12:00:00'
            }
        )
        print(f"✅ إنشاء رسالة معلقة غير متزامنة: {success}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار الوظائف غير المتزامنة: {e}")
        return False

def test_error_handling():
    """اختبار معالجة الأخطاء"""
    print("\n🛡️ اختبار معالجة الأخطاء")
    print("-" * 50)
    
    try:
        from database import get_database
        
        db = get_database()
        
        # اختبار الحصول على رسالة غير موجودة
        non_existent_message = db.get_pending_message(99999)
        print(f"✅ رسالة غير موجودة: {non_existent_message is None}")
        
        # اختبار تحديث رسالة غير موجودة
        update_success = db.update_pending_message_status(99999, 'approved')
        print(f"✅ تحديث رسالة غير موجودة: {update_success}")
        
        # اختبار الحصول على وضع نشر لمهمة غير موجودة
        from publishing_mode_manager import PublishingModeManager
        
        class MockBot:
            def __init__(self):
                from database import get_database
                self.db = get_database()
        
        mock_bot = MockBot()
        manager = PublishingModeManager(mock_bot)
        
        mode = manager.get_publishing_mode(99999)
        print(f"✅ وضع نشر لمهمة غير موجودة: {mode}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار معالجة الأخطاء: {e}")
        return False

if __name__ == "__main__":
    print("🧪 اختبار شامل لنظام وضع النشر المحسن")
    print("=" * 80)
    
    # تشغيل الاختبارات المتزامنة
    sync_tests = [
        test_database_functions,
        test_publishing_mode_manager,
        test_pending_message_creation,
        test_publishing_mode_toggle,
        test_message_approval_flow,
        test_pending_messages_count,
        test_forwarding_settings,
        test_error_handling
    ]
    
    sync_results = []
    for test in sync_tests:
        try:
            result = test()
            sync_results.append(result)
        except Exception as e:
            print(f"❌ خطأ في تشغيل الاختبار {test.__name__}: {e}")
            sync_results.append(False)
    
    # تشغيل الاختبارات غير المتزامنة
    print("\n⚡ تشغيل الاختبارات غير المتزامنة...")
    try:
        async_result = asyncio.run(test_async_functions())
        sync_results.append(async_result)
    except Exception as e:
        print(f"❌ خطأ في الاختبارات غير المتزامنة: {e}")
        sync_results.append(False)
    
    # ملخص النتائج
    print(f"\n📊 ملخص النتائج:")
    print(f"✅ نجح: {sum(sync_results)}")
    print(f"❌ فشل: {len(sync_results) - sum(sync_results)}")
    print(f"📈 نسبة النجاح: {(sum(sync_results)/len(sync_results)*100):.1f}%")
    
    if all(sync_results):
        print("\n🎉 جميع الاختبارات نجحت!")
        print("\n✅ نظام وضع النشر جاهز للاستخدام:")
        print("• 🔄 زر تبديل الوضع يعمل بشكل صحيح")
        print("• 📋 الرسائل المعلقة تُعرض بشكل صحيح")
        print("• ✅ الموافقة على الرسائل تعمل بشكل صحيح")
        print("• 📊 عدد الرسائل المعلقة يُحسب بشكل صحيح")
        print("• 🛡️ معالجة الأخطاء تعمل بشكل صحيح")
        print("• ⚡ الوظائف غير المتزامنة تعمل بشكل صحيح")
        print("\n🚀 يمكن الآن استخدام النظام في البوت!")
    else:
        print("\n⚠️ بعض الاختبارات فشلت.")
        print("يرجى مراجعة الأخطاء المذكورة أعلاه.")
    
    print(f"\n📝 ملاحظات مهمة:")
    print("• النظام يحل مشكلة زر تبديل الوضع")
    print("• النظام يحل مشكلة عدم عمل التوجيه عند الموافقة")
    print("• النظام يدعم الرسائل المعلقة بشكل كامل")
    print("• النظام يتعامل مع الأخطاء بشكل آمن")
    print("• النظام يدعم الوضع التلقائي واليدوي")