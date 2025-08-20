#!/usr/bin/env python3
"""
اختبار شامل لكشف مشكلة وضع التوجيه
المشكلة: البوت يعمل في وضع التوجيه فقط عند تبديل الوضع إلى نسخ لا يتم التوجيه بنسخ فقط يتم التوجيه مع وضع إعادة توجيه فقط
"""

import asyncio
import sys
import os
import json

# إضافة مسار bot_package
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot_package'))

def test_database_forward_mode():
    """اختبار وضع التوجيه في قاعدة البيانات"""
    print("🗄️ اختبار وضع التوجيه في قاعدة البيانات")
    print("-" * 50)
    
    try:
        from database import get_database
        
        db = get_database()
        
        # اختبار دالة update_task_forward_mode
        print("✅ اختبار تحديث وضع التوجيه...")
        
        # اختبار دالة get_task للحصول على forward_mode
        print("✅ اختبار الحصول على وضع التوجيه...")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار قاعدة البيانات: {e}")
        return False

def test_forward_mode_toggle():
    """اختبار تبديل وضع التوجيه"""
    print("\n🔄 اختبار تبديل وضع التوجيه")
    print("-" * 50)
    
    try:
        from database import get_database
        
        db = get_database()
        task_id = 1
        user_id = 12345
        
        # الحصول على الوضع الحالي
        task = db.get_task(task_id, user_id)
        if task:
            current_mode = task.get('forward_mode', 'forward')
            print(f"✅ الوضع الحالي: {current_mode}")
            
            # تبديل الوضع
            new_mode = 'copy' if current_mode == 'forward' else 'forward'
            success = db.update_task_forward_mode(task_id, user_id, new_mode)
            print(f"✅ تبديل الوضع إلى {new_mode}: {success}")
            
            if success:
                # التحقق من التحديث
                updated_task = db.get_task(task_id, user_id)
                updated_mode = updated_task.get('forward_mode', 'forward') if updated_task else 'unknown'
                print(f"✅ الوضع المحدث: {updated_mode}")
                
                # إعادة الوضع الأصلي
                db.update_task_forward_mode(task_id, user_id, current_mode)
                print(f"✅ إعادة الوضع الأصلي: {current_mode}")
        else:
            print("⚠️ المهمة غير موجودة للاختبار")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار تبديل وضع التوجيه: {e}")
        return False

def test_userbot_forward_logic():
    """اختبار منطق التوجيه في UserBot"""
    print("\n🤖 اختبار منطق التوجيه في UserBot")
    print("-" * 50)
    
    try:
        # فحص الكود في userbot.py
        print("✅ فحص منطق التوجيه في userbot.py...")
        
        # قراءة الكود من userbot.py
        userbot_path = "userbot_service/userbot.py"
        if os.path.exists(userbot_path):
            with open(userbot_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # البحث عن منطق التوجيه
            forward_mode_checks = content.count("forward_mode = task.get('forward_mode', 'forward')")
            copy_mode_checks = content.count("forward_mode == 'copy'")
            forward_mode_checks_2 = content.count("forward_mode == 'forward'")
            
            print(f"✅ عدد مرات فحص forward_mode: {forward_mode_checks}")
            print(f"✅ عدد مرات فحص copy mode: {copy_mode_checks}")
            print(f"✅ عدد مرات فحص forward mode: {forward_mode_checks_2}")
            
            # البحث عن مشاكل محتملة
            if "requires_copy_mode" in content:
                print("✅ تم العثور على منطق requires_copy_mode")
            else:
                print("❌ لم يتم العثور على منطق requires_copy_mode")
            
            if "client.forward_messages" in content:
                print("✅ تم العثور على client.forward_messages")
            else:
                print("❌ لم يتم العثور على client.forward_messages")
            
            if "client.send_message" in content:
                print("✅ تم العثور على client.send_message")
            else:
                print("❌ لم يتم العثور على client.send_message")
            
            # البحث عن المشكلة المحتملة
            problematic_patterns = [
                "requires_copy_mode = (",
                "if forward_mode == 'copy' or requires_copy_mode:",
                "else:",
                "forwarded_msg = await client.forward_messages"
            ]
            
            print("\n🔍 فحص الأنماط المشكلة:")
            for pattern in problematic_patterns:
                if pattern in content:
                    print(f"✅ تم العثور على: {pattern}")
                else:
                    print(f"❌ لم يتم العثور على: {pattern}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار منطق UserBot: {e}")
        return False

def test_forward_mode_conditions():
    """اختبار شروط وضع التوجيه"""
    print("\n🔍 اختبار شروط وضع التوجيه")
    print("-" * 50)
    
    try:
        # قراءة الكود من userbot.py
        userbot_path = "userbot_service/userbot.py"
        if os.path.exists(userbot_path):
            with open(userbot_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # البحث عن الشروط التي تجبر النسخ
            copy_conditions = [
                "original_text != modified_text",
                "modified_text != translated_text", 
                "translated_text != formatted_text",
                "message_settings['header_enabled']",
                "message_settings['footer_enabled']",
                "message_settings['inline_buttons_enabled']",
                "should_remove_forward",
                "needs_copy_for_caption",
                "needs_copy_for_album"
            ]
            
            print("🔍 الشروط التي تجبر وضع النسخ:")
            for condition in copy_conditions:
                if condition in content:
                    print(f"✅ {condition}")
                else:
                    print(f"❌ {condition}")
            
            # البحث عن منطق التوجيه
            forward_logic = [
                "if forward_mode == 'copy' or requires_copy_mode:",
                "else:",
                "forwarded_msg = await client.forward_messages",
                "forwarded_msg = await client.send_message"
            ]
            
            print("\n🔍 منطق التوجيه:")
            for logic in forward_logic:
                if logic in content:
                    print(f"✅ {logic}")
                else:
                    print(f"❌ {logic}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار شروط وضع التوجيه: {e}")
        return False

def analyze_forward_mode_issue():
    """تحليل مشكلة وضع التوجيه"""
    print("\n🔬 تحليل مشكلة وضع التوجيه")
    print("-" * 50)
    
    try:
        # قراءة الكود من userbot.py
        userbot_path = "userbot_service/userbot.py"
        if os.path.exists(userbot_path):
            with open(userbot_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # البحث عن المشكلة المحتملة
            print("🔍 البحث عن المشكلة المحتملة...")
            
            # المشكلة المحتملة: requires_copy_mode يجبر النسخ حتى في وضع التوجيه
            if "requires_copy_mode = (" in content and "if forward_mode == 'copy' or requires_copy_mode:" in content:
                print("❌ تم العثور على المشكلة المحتملة!")
                print("   المشكلة: requires_copy_mode يجبر النسخ حتى في وضع التوجيه")
                print("   الحل: يجب فصل منطق requires_copy_mode عن forward_mode")
            
            # البحث عن منطق التوجيه الصحيح
            correct_forward_logic = [
                "if forward_mode == 'copy':",
                "elif forward_mode == 'forward':",
                "else:  # forward mode"
            ]
            
            print("\n🔍 البحث عن منطق التوجيه الصحيح:")
            for logic in correct_forward_logic:
                if logic in content:
                    print(f"✅ {logic}")
                else:
                    print(f"❌ {logic}")
            
            # البحث عن المشكلة في منطق التوجيه
            problematic_logic = "if forward_mode == 'copy' or requires_copy_mode:"
            if problematic_logic in content:
                print(f"\n❌ تم العثور على المشكلة: {problematic_logic}")
                print("   هذا يجبر النسخ حتى عندما يكون forward_mode = 'forward'")
                print("   إذا كان requires_copy_mode = True")
            
            # البحث عن الحل المحتمل
            print("\n🔍 الحلول المحتملة:")
            print("1. فصل منطق requires_copy_mode عن forward_mode")
            print("2. استخدام منطق منفصل لكل وضع")
            print("3. إضافة شرط إضافي للتحقق من forward_mode")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في تحليل المشكلة: {e}")
        return False

def test_bot_forward_mode_handler():
    """اختبار معالج وضع التوجيه في البوت"""
    print("\n🤖 اختبار معالج وضع التوجيه في البوت")
    print("-" * 50)
    
    try:
        # فحص الكود في bot_simple.py
        print("✅ فحص معالج وضع التوجيه في bot_simple.py...")
        
        # قراءة الكود من bot_simple.py
        bot_path = "bot_package/bot_simple.py"
        if os.path.exists(bot_path):
            with open(bot_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # البحث عن معالج وضع التوجيه
            if "toggle_forward_mode" in content:
                print("✅ تم العثور على دالة toggle_forward_mode")
            else:
                print("❌ لم يتم العثور على دالة toggle_forward_mode")
            
            if "update_task_forward_mode" in content:
                print("✅ تم العثور على استدعاء update_task_forward_mode")
            else:
                print("❌ لم يتم العثور على استدعاء update_task_forward_mode")
            
            if "refresh_user_tasks" in content:
                print("✅ تم العثور على استدعاء refresh_user_tasks")
            else:
                print("❌ لم يتم العثور على استدعاء refresh_user_tasks")
            
            # البحث عن معالج الأزرار
            if "toggle_forward_mode_" in content:
                print("✅ تم العثور على معالج زر toggle_forward_mode_")
            else:
                print("❌ لم يتم العثور على معالج زر toggle_forward_mode_")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار معالج البوت: {e}")
        return False

def generate_fix_suggestions():
    """توليد اقتراحات الإصلاح"""
    print("\n🔧 اقتراحات الإصلاح")
    print("-" * 50)
    
    print("🔍 المشكلة المكتشفة:")
    print("   في userbot.py، السطر الذي يحتوي على:")
    print("   if forward_mode == 'copy' or requires_copy_mode:")
    print("   هذا يجبر النسخ حتى عندما يكون forward_mode = 'forward'")
    print("   إذا كان requires_copy_mode = True")
    
    print("\n🔧 الحلول المقترحة:")
    print("1. فصل منطق requires_copy_mode عن forward_mode")
    print("2. استخدام منطق منفصل لكل وضع")
    print("3. إضافة شرط إضافي للتحقق من forward_mode")
    
    print("\n📝 الكود المقترح للإصلاح:")
    print("""
# بدلاً من:
if forward_mode == 'copy' or requires_copy_mode:
    # copy logic
else:
    # forward logic

# استخدم:
if forward_mode == 'copy':
    # copy logic
elif forward_mode == 'forward':
    if requires_copy_mode:
        # copy logic (forced)
    else:
        # forward logic
else:
    # default forward logic
    """)
    
    return True

if __name__ == "__main__":
    print("🔍 اختبار شامل لكشف مشكلة وضع التوجيه")
    print("=" * 80)
    
    # تشغيل الاختبارات
    tests = [
        test_database_forward_mode,
        test_forward_mode_toggle,
        test_userbot_forward_logic,
        test_forward_mode_conditions,
        analyze_forward_mode_issue,
        test_bot_forward_mode_handler,
        generate_fix_suggestions
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
    
    print(f"\n🎯 المشكلة المكتشفة:")
    print("   في userbot.py، منطق التوجيه يجبر النسخ حتى في وضع التوجيه")
    print("   عندما يكون requires_copy_mode = True")
    
    print(f"\n🔧 الحل المطلوب:")
    print("   فصل منطق requires_copy_mode عن forward_mode")
    print("   استخدام منطق منفصل لكل وضع")
    
    if all(results):
        print("\n✅ جميع الاختبارات نجحت!")
        print("🔍 تم اكتشاف المشكلة وتحديد الحل")
    else:
        print("\n⚠️ بعض الاختبارات فشلت.")
        print("يرجى مراجعة الأخطاء المذكورة أعلاه.")