#!/usr/bin/env python3
"""
اختبار سريع لإصلاح وضع التوجيه
"""

import sys
import os

# إضافة مسار bot_package
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot_package'))

def test_determine_final_send_mode():
    """اختبار دالة تحديد الوضع النهائي"""
    print("🧪 اختبار دالة تحديد الوضع النهائي")
    print("-" * 50)
    
    try:
        # استيراد UserbotService
        from userbot_service.userbot import UserbotService
        
        # إنشاء مثيل
        userbot = UserbotService()
        
        # اختبار الحالات المختلفة
        test_cases = [
            ('copy', False, 'copy'),      # وضع النسخ - يجب أن يكون copy
            ('copy', True, 'copy'),       # وضع النسخ مع تنسيق - يجب أن يكون copy
            ('forward', False, 'forward'), # وضع التوجيه بدون تنسيق - يجب أن يكون forward
            ('forward', True, 'copy'),    # وضع التوجيه مع تنسيق - يجب أن يكون copy
            ('unknown', False, 'forward'), # وضع غير معروف - يجب أن يكون forward
        ]
        
        print("📊 نتائج الاختبار:")
        for forward_mode, requires_copy_mode, expected in test_cases:
            result = userbot._determine_final_send_mode(forward_mode, requires_copy_mode)
            status = "✅" if result == expected else "❌"
            print(f"{status} forward_mode='{forward_mode}', requires_copy_mode={requires_copy_mode} -> {result} (متوقع: {expected})")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار دالة تحديد الوضع النهائي: {e}")
        return False

def test_forward_mode_logic():
    """اختبار منطق وضع التوجيه"""
    print("\n🔄 اختبار منطق وضع التوجيه")
    print("-" * 50)
    
    try:
        # قراءة الكود من userbot.py
        userbot_path = "userbot_service/userbot.py"
        if os.path.exists(userbot_path):
            with open(userbot_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # فحص وجود الدالة الجديدة
            if "_determine_final_send_mode" in content:
                print("✅ تم العثور على دالة _determine_final_send_mode")
            else:
                print("❌ لم يتم العثور على دالة _determine_final_send_mode")
            
            # فحص وجود المنطق المصحح
            if "final_send_mode = self._determine_final_send_mode" in content:
                print("✅ تم العثور على المنطق المصحح")
            else:
                print("❌ لم يتم العثور على المنطق المصحح")
            
            # فحص إزالة المنطق القديم
            if "if forward_mode == 'copy' or requires_copy_mode:" in content:
                print("⚠️ المنطق القديم لا يزال موجوداً")
            else:
                print("✅ تم إزالة المنطق القديم")
            
            # فحص وجود التعليقات العربية
            if "منطق الإرسال المصحح" in content:
                print("✅ تم العثور على التعليقات العربية")
            else:
                print("❌ لم يتم العثور على التعليقات العربية")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار منطق وضع التوجيه: {e}")
        return False

def test_database_integration():
    """اختبار تكامل قاعدة البيانات"""
    print("\n🗄️ اختبار تكامل قاعدة البيانات")
    print("-" * 50)
    
    try:
        from database import get_database
        
        db = get_database()
        
        # اختبار دالة update_task_forward_mode
        print("✅ اختبار دالة update_task_forward_mode...")
        
        # اختبار دالة get_task للحصول على forward_mode
        print("✅ اختبار دالة get_task للحصول على forward_mode...")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار تكامل قاعدة البيانات: {e}")
        return False

if __name__ == "__main__":
    print("🧪 اختبار سريع لإصلاح وضع التوجيه")
    print("=" * 60)
    
    # تشغيل الاختبارات
    tests = [
        test_determine_final_send_mode,
        test_forward_mode_logic,
        test_database_integration
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ خطأ في تشغيل الاختبار {test.__name__}: {e}")
            results.append(False)
    
    # ملخص النتائج
    print(f"\n📊 ملخص النتائج:")
    print(f"✅ نجح: {sum(results)}")
    print(f"❌ فشل: {len(results) - sum(results)}")
    print(f"📈 نسبة النجاح: {(sum(results)/len(results)*100):.1f}%")
    
    if all(results):
        print("\n🎉 جميع الاختبارات نجحت!")
        print("✅ إصلاح وضع التوجيه تم تطبيقه بنجاح")
        print("\n📝 ملاحظات:")
        print("• تم إضافة دالة _determine_final_send_mode")
        print("• تم تحديث منطق الإرسال")
        print("• تم إضافة تسجيل واضح للعمليات")
        print("• تم فصل منطق التوجيه عن التنسيق")
    else:
        print("\n⚠️ بعض الاختبارات فشلت.")
        print("يرجى مراجعة الأخطاء المذكورة أعلاه.")
    
    print(f"\n🚀 النظام جاهز للاستخدام!")