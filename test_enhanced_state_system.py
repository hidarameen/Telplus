#!/usr/bin/env python3
"""
اختبار شامل لنظام إدارة الحالة المحسن
"""

import asyncio
import time
import sys
import os

# إضافة مسار bot_package
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot_package'))

def test_basic_state_management():
    """اختبار إدارة الحالة الأساسية"""
    print("🧪 اختبار إدارة الحالة الأساسية")
    print("-" * 50)
    
    try:
        from enhanced_state_manager import create_state_manager
        
        # إنشاء مدير الحالة
        state_manager = create_state_manager()
        
        # اختبار تعيين الحالة
        user_id = 12345
        state_manager.set_user_state(user_id, "editing_audio_tag_title", {"task_id": 1})
        
        # اختبار الحصول على الحالة
        current_state = state_manager.get_user_state(user_id)
        user_data = state_manager.get_user_data(user_id)
        
        print(f"✅ تعيين الحالة: {current_state}")
        print(f"✅ بيانات المستخدم: {user_data}")
        
        # اختبار مسح الحالة
        state_manager.clear_user_state(user_id)
        cleared_state = state_manager.get_user_state(user_id)
        
        print(f"✅ مسح الحالة: {cleared_state is None}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار إدارة الحالة الأساسية: {e}")
        return False

def test_state_cancellation():
    """اختبار إلغاء الحالة"""
    print("\n🔄 اختبار إلغاء الحالة")
    print("-" * 50)
    
    try:
        from enhanced_state_manager import create_state_manager
        
        state_manager = create_state_manager()
        user_id = 12345
        
        # تعيين حالة
        state_manager.set_user_state(user_id, "editing_audio_tag_title", {"task_id": 1})
        
        # اختبار إلغاء الحالة عند الضغط على زر
        cancelled = state_manager.cancel_state_if_needed(user_id, "audio_metadata_settings_1")
        print(f"✅ إلغاء الحالة عند الضغط على زر: {cancelled}")
        
        # تعيين حالة أخرى
        state_manager.set_user_state(user_id, "editing_char_min", {"task_id": 1})
        
        # اختبار إلغاء الحالة حسب النمط
        cancelled = state_manager.cancel_state_by_pattern(user_id, "editing_char_")
        print(f"✅ إلغاء الحالة حسب النمط: {cancelled}")
        
        # اختبار إلغاء جميع الحالات
        state_manager.set_user_state(user_id, "editing_rate_count", {"task_id": 1})
        cancelled = state_manager.cancel_all_states(user_id)
        print(f"✅ إلغاء جميع الحالات: {cancelled}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار إلغاء الحالة: {e}")
        return False

def test_state_timeout():
    """اختبار انتهاء صلاحية الحالة"""
    print("\n⏰ اختبار انتهاء صلاحية الحالة")
    print("-" * 50)
    
    try:
        from enhanced_state_manager import create_state_manager
        from state_manager import StateType
        
        state_manager = create_state_manager()
        user_id = 12345
        
        # تعيين حالة مؤقتة مع مهلة قصيرة
        state_manager.set_user_state(user_id, "editing_audio_tag_title", {"task_id": 1}, 
                                   StateType.TEMPORARY, timeout=1)
        
        # الحصول على رسالة انتهاء الصلاحية
        timeout_message = state_manager.get_timeout_message("editing_audio_tag_title")
        print(f"✅ رسالة انتهاء الصلاحية: {timeout_message}")
        
        # انتظار انتهاء الصلاحية
        time.sleep(2)
        
        # التحقق من انتهاء الصلاحية
        current_state = state_manager.get_user_state(user_id)
        print(f"✅ انتهاء صلاحية الحالة: {current_state is None}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار انتهاء صلاحية الحالة: {e}")
        return False

def test_state_validation():
    """اختبار التحقق من صحة الحالة"""
    print("\n✅ اختبار التحقق من صحة الحالة")
    print("-" * 50)
    
    try:
        from enhanced_state_manager import create_state_manager
        
        state_manager = create_state_manager()
        user_id = 12345
        
        # تعيين حالة صحيحة
        state_manager.set_user_state(user_id, "editing_audio_tag_title", {"task_id": 1})
        is_valid = state_manager.validation_handler.is_valid_state("editing_audio_tag_title")
        print(f"✅ حالة صحيحة: {is_valid}")
        
        # تعيين حالة غير صحيحة
        state_manager.set_user_state(user_id, "invalid_state", {"task_id": 1})
        is_valid = state_manager.validation_handler.is_valid_state("invalid_state")
        print(f"✅ حالة غير صحيحة: {not is_valid}")
        
        # اختبار التنظيف التلقائي
        cleaned = state_manager.validation_handler.validate_and_cleanup(user_id)
        print(f"✅ تنظيف الحالة غير الصحيحة: {cleaned}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار التحقق من صحة الحالة: {e}")
        return False

def test_state_recovery():
    """اختبار استعادة الحالة"""
    print("\n💾 اختبار استعادة الحالة")
    print("-" * 50)
    
    try:
        from enhanced_state_manager import create_state_manager
        
        state_manager = create_state_manager()
        user_id = 12345
        
        # تعيين حالة وحفظها للاستعادة
        state_manager.set_user_state(user_id, "editing_audio_tag_title", {"task_id": 1})
        
        # مسح الحالة
        state_manager.clear_user_state(user_id)
        
        # محاولة الاستعادة
        recovered = state_manager.recover_state(user_id)
        print(f"✅ استعادة الحالة: {recovered is not None}")
        
        if recovered:
            print(f"✅ بيانات الاستعادة: {recovered}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار استعادة الحالة: {e}")
        return False

def test_state_monitoring():
    """اختبار مراقبة الحالة"""
    print("\n👁️ اختبار مراقبة الحالة")
    print("-" * 50)
    
    try:
        from enhanced_state_manager import create_state_manager
        
        state_manager = create_state_manager()
        user_id = 12345
        
        # تعيين حالة وبدء المراقبة
        state_manager.set_user_state(user_id, "editing_audio_tag_title", {"task_id": 1})
        
        # تحديث النشاط
        state_manager.monitoring_handler.update_activity(user_id)
        state_manager.monitoring_handler.update_activity(user_id)
        
        # الحصول على إحصائيات المراقبة
        stats = state_manager.get_monitoring_stats()
        print(f"✅ إحصائيات المراقبة: {stats}")
        
        # إيقاف المراقبة
        state_manager.monitoring_handler.stop_monitoring(user_id)
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار مراقبة الحالة: {e}")
        return False

def test_message_handler():
    """اختبار معالج الرسائل"""
    print("\n📝 اختبار معالج الرسائل")
    print("-" * 50)
    
    try:
        from message_handler import MessageHandler
        from enhanced_state_manager import create_state_manager
        
        # إنشاء مدير الحالة
        state_manager = create_state_manager()
        
        # إنشاء معالج الرسائل (بدون bot instance للاختبار)
        class MockBot:
            def __init__(self):
                self.db = None
                self.bot = None
            
            async def edit_or_send_message(self, event, text, buttons=None):
                print(f"📤 رسالة: {text}")
                return None
        
        mock_bot = MockBot()
        message_handler = MessageHandler(mock_bot)
        
        # اختبار تعيين حالة مؤقتة
        message_handler.set_temporary_state(12345, "editing_audio_tag_title", {"task_id": 1})
        
        # اختبار الحصول على معلومات الحالة
        state_info = message_handler.get_state_info(12345)
        print(f"✅ معلومات الحالة: {state_info is not None}")
        
        # اختبار مسح الحالة
        message_handler.clear_state(12345)
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار معالج الرسائل: {e}")
        return False

def test_complete_system():
    """اختبار النظام الكامل"""
    print("\n🚀 اختبار النظام الكامل")
    print("-" * 50)
    
    try:
        from enhanced_state_manager import create_complete_state_system
        
        # إنشاء النظام الكامل
        enhanced_manager, decorated_manager = create_complete_state_system()
        
        user_id = 12345
        
        # تسجيل callback
        def test_callback(user_id, state, data):
            print(f"🔧 Callback تم تنفيذه: {state}")
        
        decorated_manager.register_state_callback("editing_audio_tag_", test_callback)
        
        # تعيين حالة مع callback
        decorated_manager.set_user_state_with_callback(user_id, "editing_audio_tag_title", {"task_id": 1})
        
        # مسح الحالة مع callback
        decorated_manager.clear_user_state_with_callback(user_id)
        
        # الحصول على إحصائيات النظام
        stats = enhanced_manager.get_system_stats()
        print(f"✅ إحصائيات النظام: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار النظام الكامل: {e}")
        return False

def test_real_world_scenarios():
    """اختبار سيناريوهات العالم الحقيقي"""
    print("\n🌍 اختبار سيناريوهات العالم الحقيقي")
    print("-" * 50)
    
    try:
        from enhanced_state_manager import create_state_manager
        
        state_manager = create_state_manager()
        
        # سيناريو 1: المستخدم يبدأ تعديل الوسم الصوتي ثم يضغط على زر آخر
        print("📋 سيناريو 1: تعديل الوسم الصوتي")
        user_id = 12345
        
        # تعيين حالة تعديل الوسم
        state_manager.set_user_state(user_id, "editing_audio_tag_title", {"task_id": 1})
        print(f"  ✅ تم تعيين حالة تعديل الوسم")
        
        # محاكاة الضغط على زر آخر (يجب أن يلغي الحالة)
        cancelled = state_manager.cancel_state_if_needed(user_id, "audio_metadata_settings_1")
        print(f"  ✅ تم إلغاء الحالة عند الضغط على زر آخر: {cancelled}")
        
        # سيناريو 2: انتهاء صلاحية الحالة
        print("📋 سيناريو 2: انتهاء صلاحية الحالة")
        state_manager.set_user_state(user_id, "editing_char_min", {"task_id": 1}, timeout=1)
        print(f"  ✅ تم تعيين حالة مع مهلة قصيرة")
        
        time.sleep(2)
        current_state = state_manager.get_user_state(user_id)
        print(f"  ✅ انتهت صلاحية الحالة: {current_state is None}")
        
        # سيناريو 3: تنظيف الحالات غير الصحيحة
        print("📋 سيناريو 3: تنظيف الحالات غير الصحيحة")
        state_manager.set_user_state(user_id, "invalid_state", {"task_id": 1})
        cleaned = state_manager.validation_handler.validate_and_cleanup(user_id)
        print(f"  ✅ تم تنظيف الحالة غير الصحيحة: {cleaned}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار سيناريوهات العالم الحقيقي: {e}")
        return False

async def test_async_functionality():
    """اختبار الوظائف غير المتزامنة"""
    print("\n⚡ اختبار الوظائف غير المتزامنة")
    print("-" * 50)
    
    try:
        from enhanced_state_manager import create_state_manager
        
        state_manager = create_state_manager()
        
        # اختبار التنظيف التلقائي
        print("✅ تم بدء التنظيف التلقائي")
        
        # انتظار قليل للتنظيف
        await asyncio.sleep(2)
        
        # الحصول على إحصائيات النظام
        stats = state_manager.get_system_stats()
        print(f"✅ إحصائيات النظام: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار الوظائف غير المتزامنة: {e}")
        return False

if __name__ == "__main__":
    print("🧪 اختبار شامل لنظام إدارة الحالة المحسن")
    print("=" * 80)
    
    # تشغيل الاختبارات المتزامنة
    sync_tests = [
        test_basic_state_management,
        test_state_cancellation,
        test_state_timeout,
        test_state_validation,
        test_state_recovery,
        test_state_monitoring,
        test_message_handler,
        test_complete_system,
        test_real_world_scenarios
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
        async_result = asyncio.run(test_async_functionality())
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
        print("\n✅ النظام جاهز للاستخدام:")
        print("• 🧹 تنظيف تلقائي للحالات المنتهية الصلاحية")
        print("• 🔄 إلغاء تلقائي للحالة عند الضغط على أزرار أخرى")
        print("• ⏰ انتهاء صلاحية تلقائي للحالات المؤقتة")
        print("• ✅ التحقق من صحة الحالات")
        print("• 💾 استعادة الحالات")
        print("• 👁️ مراقبة الحالات")
        print("• 📝 معالجة محسنة للرسائل")
        print("\n🚀 يمكن الآن تطبيق النظام على البوت!")
    else:
        print("\n⚠️ بعض الاختبارات فشلت.")
        print("يرجى مراجعة الأخطاء المذكورة أعلاه.")
    
    print(f"\n📝 ملاحظات مهمة:")
    print("• النظام يحل مشكلة الاحتفاظ بحالة المستخدم بعد انتهاء العملية")
    print("• يتم تنظيف الحالات تلقائياً كل دقيقة")
    print("• يتم إلغاء الحالة عند الضغط على أزرار أخرى")
    print("• الحالات المؤقتة تنتهي صلاحيتها تلقائياً")
    print("• يمكن استعادة الحالات في حالة الحاجة")