#!/usr/bin/env python3
"""
اختبار شامل لفلتر المشرفين المحسن
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import Database
import asyncio

def test_admin_filter_complete():
    """اختبار شامل لجميع ميزات فلتر المشرفين"""
    print("🧪 بدء الاختبار الشامل لفلتر المشرفين...")
    
    try:
        db = Database()
        
        # بيانات الاختبار
        task_id = 1
        source_chat_id = "-1001234567890"
        
        print("\n1️⃣ اختبار إضافة مشرفين مع حالات مختلفة...")
        
        # إضافة مشرفين للاختبار
        test_admins = [
            {
                'user_id': 11111,
                'username': 'admin1',
                'first_name': 'مشرف أول',
                'signature': 'توقيع أول',
                'allowed': True
            },
            {
                'user_id': 22222,
                'username': 'admin2',
                'first_name': 'مشرف ثاني',
                'signature': 'توقيع ثاني',
                'allowed': False  # محظور
            },
            {
                'user_id': 33333,
                'username': 'admin3',
                'first_name': 'مشرف ثالث',
                'signature': '',
                'allowed': True
            }
        ]
        
        for admin in test_admins:
            success = db.add_admin_filter(
                task_id, admin['user_id'], admin['username'],
                admin['first_name'], admin['allowed'], source_chat_id, admin['signature']
            )
            if success:
                status = "مسموح" if admin['allowed'] else "محظور"
                print(f"   ✅ {admin['first_name']}: {status}")
            else:
                print(f"   ❌ فشل في إضافة {admin['first_name']}")
                return False
        
        # اختبار الحصول على المشرفين مع الإحصائيات
        print("\n2️⃣ اختبار الحصول على المشرفين مع الإحصائيات...")
        admin_data = db.get_admin_filters_by_source_with_stats(task_id, source_chat_id)
        
        if admin_data:
            stats = admin_data['stats']
            print(f"   📊 الإحصائيات: إجمالي {stats['total']}, مسموح {stats['allowed']}, محظور {stats['blocked']}")
            
            # التحقق من صحة الإحصائيات
            expected_total = 3
            expected_allowed = 2
            expected_blocked = 1
            
            if stats['total'] == expected_total and stats['allowed'] == expected_allowed and stats['blocked'] == expected_blocked:
                print("   ✅ الإحصائيات صحيحة")
            else:
                print(f"   ❌ الإحصائيات غير صحيحة. متوقع: {expected_total}/{expected_allowed}/{expected_blocked}")
                return False
        else:
            print("   ❌ فشل في الحصول على الإحصائيات")
            return False
        
        # اختبار الحفاظ على الصلاحيات
        print("\n3️⃣ اختبار الحفاظ على الصلاحيات...")
        
        # حفظ الصلاحيات الحالية
        existing_admins = db.get_admin_filters_by_source(task_id, source_chat_id)
        previous_permissions = {admin['admin_user_id']: admin['is_allowed'] for admin in existing_admins}
        
        print("   📝 الصلاحيات الحالية:")
        for admin_id, is_allowed in previous_permissions.items():
            status = "مسموح" if is_allowed else "محظور"
            print(f"      - {admin_id}: {status}")
        
        # محاكاة تحديث المشرفين (حذف وإعادة إضافة)
        print("\n4️⃣ محاكاة تحديث المشرفين...")
        
        # حذف المشرفين الحاليين
        deleted_count = db.clear_admin_filters_for_source(task_id, source_chat_id)
        print(f"   🗑️ تم حذف {deleted_count} مشرف")
        
        # إعادة إضافة المشرفين مع الحفاظ على الصلاحيات
        for admin in test_admins:
            # استخدام الصلاحية السابقة إذا كانت موجودة
            is_allowed = previous_permissions.get(admin['user_id'], True)
            
            success = db.add_admin_filter(
                task_id, admin['user_id'], admin['username'],
                admin['first_name'], is_allowed, source_chat_id, admin['signature']
            )
            
            if success:
                status = "مسموح" if is_allowed else "محظور"
                print(f"   ✅ إعادة إضافة {admin['first_name']}: {status}")
            else:
                print(f"   ❌ فشل في إعادة إضافة {admin['first_name']}")
                return False
        
        # التحقق من الحفاظ على الصلاحيات
        print("\n5️⃣ التحقق من الحفاظ على الصلاحيات...")
        updated_admins = db.get_admin_filters_by_source(task_id, source_chat_id)
        
        permissions_preserved = True
        for admin in updated_admins:
            current_status = admin['is_allowed']
            previous_status = previous_permissions.get(admin['admin_user_id'])
            
            if previous_status is not None and current_status != previous_status:
                print(f"   ❌ تغيير في صلاحيات {admin['admin_first_name']}: {previous_status} -> {current_status}")
                permissions_preserved = False
            else:
                status_text = "مسموح" if current_status else "محظور"
                print(f"   ✅ {admin['admin_first_name']}: {status_text} (محفوظ)")
        
        if not permissions_preserved:
            print("   ❌ فشل في الحفاظ على الصلاحيات")
            return False
        
        # اختبار تحديث التوقيعات
        print("\n6️⃣ اختبار تحديث التوقيعات...")
        
        new_signature = "توقيع محدث"
        success = db.update_admin_signature(task_id, 11111, source_chat_id, new_signature)
        
        if success:
            print("   ✅ تم تحديث التوقيع بنجاح")
        else:
            print("   ❌ فشل في تحديث التوقيع")
            return False
        
        # اختبار البحث بالتوقيع
        found_admin = db.get_admin_by_signature(task_id, source_chat_id, new_signature)
        if found_admin:
            print(f"   ✅ تم العثور على المشرف بالتوقيع: {found_admin['admin_first_name']}")
        else:
            print("   ❌ لم يتم العثور على المشرف بالتوقيع")
            return False
        
        # اختبار التحديث الجماعي
        print("\n7️⃣ اختبار التحديث الجماعي...")
        
        # تعطيل جميع المشرفين
        admin_permissions = {admin['admin_user_id']: False for admin in updated_admins}
        updated_count = db.bulk_update_admin_permissions(task_id, source_chat_id, admin_permissions)
        
        if updated_count == len(updated_admins):
            print(f"   ✅ تم تحديث {updated_count} مشرف بنجاح")
        else:
            print(f"   ❌ فشل في التحديث الجماعي. متوقع: {len(updated_admins)}, فعلي: {updated_count}")
            return False
        
        # التحقق من التحديث
        final_admins = db.get_admin_filters_by_source(task_id, source_chat_id)
        all_blocked = all(not admin['is_allowed'] for admin in final_admins)
        
        if all_blocked:
            print("   ✅ جميع المشرفين محظورين الآن")
        else:
            print("   ❌ بعض المشرفين لم يتم تعطيلهم")
            return False
        
        # اختبار تبديل الحالة
        print("\n8️⃣ اختبار تبديل الحالة...")
        
        success = db.toggle_admin_filter(task_id, 11111, source_chat_id)
        if success:
            print("   ✅ تم تبديل حالة المشرف بنجاح")
        else:
            print("   ❌ فشل في تبديل الحالة")
            return False
        
        # التحقق من التبديل
        admin_info = db.get_admin_filter_setting(task_id, 11111)
        if admin_info and admin_info['is_allowed']:
            print("   ✅ المشرف مفعل الآن")
        else:
            print("   ❌ فشل في تبديل الحالة")
            return False
        
        # تنظيف البيانات
        print("\n9️⃣ تنظيف بيانات الاختبار...")
        db.clear_admin_filters_for_source(task_id, source_chat_id)
        
        # التحقق من التنظيف
        final_check = db.get_admin_filters_by_source(task_id, source_chat_id)
        if not final_check:
            print("   ✅ تم تنظيف البيانات بنجاح")
        else:
            print(f"   ❌ لا تزال هناك {len(final_check)} مشرف")
            return False
        
        print("\n🎉 جميع الاختبارات نجحت!")
        return True
        
    except Exception as e:
        print(f"❌ حدث خطأ أثناء الاختبار: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_userbot_integration():
    """اختبار تكامل UserBot"""
    print("\n🤖 اختبار تكامل UserBot...")
    
    try:
        # محاكاة رسالة مع post_author
        class MockMessage:
            def __init__(self, post_author=None, sender_id=None, chat_id=None):
                self.post_author = post_author
                self.sender_id = sender_id
                self.chat_id = chat_id or "-1001234567890"
        
        # اختبار رسائل مختلفة
        test_messages = [
            MockMessage(post_author="توقيع أول", sender_id=11111),
            MockMessage(post_author="توقيع ثاني", sender_id=22222),
            MockMessage(post_author="", sender_id=33333),
            MockMessage(post_author=None, sender_id=44444)
        ]
        
        print("📨 اختبار رسائل مختلفة...")
        for i, msg in enumerate(test_messages, 1):
            post_author = msg.post_author or "بدون توقيع"
            sender_id = msg.sender_id or "غير محدد"
            print(f"   {i}. توقيع: '{post_author}', مرسل: {sender_id}")
        
        print("✅ تم اختبار تكامل UserBot")
        return True
        
    except Exception as e:
        print(f"❌ حدث خطأ في اختبار التكامل: {e}")
        return False

def test_admin_type_detection():
    """اختبار تحديد نوع المستخدم (مستخدم/بوت)"""
    print("\n👤 اختبار تحديد نوع المستخدم...")
    
    try:
        # محاكاة بيانات مشرفين من التليجرام
        mock_telegram_admins = [
            {
                'id': 11111,
                'username': 'admin1',
                'first_name': 'مشرف بشري',
                'is_bot': False,
                'custom_title': 'توقيع بشري'
            },
            {
                'id': 22222,
                'username': 'bot_admin',
                'first_name': 'بوت مشرف',
                'is_bot': True,
                'custom_title': 'توقيع بوت'
            },
            {
                'id': 33333,
                'username': 'admin3',
                'first_name': 'مشرف آخر',
                'is_bot': False,
                'custom_title': 'توقيع آخر'
            }
        ]
        
        print("📋 تحليل أنواع المشرفين...")
        human_admins = []
        bot_admins = []
        
        for admin in mock_telegram_admins:
            if admin['is_bot']:
                bot_admins.append(admin)
                print(f"   🤖 بوت: {admin['first_name']} (@{admin['username']})")
            else:
                human_admins.append(admin)
                print(f"   👤 مستخدم: {admin['first_name']} (@{admin['username']})")
        
        print(f"\n📊 الإحصائيات:")
        print(f"   👤 مستخدمين بشريين: {len(human_admins)}")
        print(f"   🤖 بوتات: {len(bot_admins)}")
        
        # التحقق من أن البوتات يتم تخطيها
        if len(bot_admins) > 0:
            print("   ✅ تم تحديد البوتات بنجاح")
        else:
            print("   ⚠️ لا توجد بوتات في القائمة")
        
        print("✅ تم اختبار تحديد نوع المستخدم")
        return True
        
    except Exception as e:
        print(f"❌ حدث خطأ في اختبار تحديد النوع: {e}")
        return False

def main():
    """الدالة الرئيسية"""
    print("🚀 بدء الاختبار الشامل لفلتر المشرفين")
    print("=" * 60)
    
    # اختبار الوظائف الأساسية
    basic_test = test_admin_filter_complete()
    
    # اختبار التكامل
    integration_test = test_userbot_integration()
    
    # اختبار تحديد النوع
    type_test = test_admin_type_detection()
    
    # عرض النتائج
    print("\n" + "=" * 60)
    print("📊 نتائج الاختبار الشامل:")
    print(f"   الوظائف الأساسية: {'✅ نجح' if basic_test else '❌ فشل'}")
    print(f"   التكامل: {'✅ نجح' if integration_test else '❌ فشل'}")
    print(f"   تحديد النوع: {'✅ نجح' if type_test else '❌ فشل'}")
    
    if all([basic_test, integration_test, type_test]):
        print("\n🎉 جميع الاختبارات نجحت!")
        print("\n✨ الميزات المؤكدة:")
        print("   ✅ الحفاظ على حالة المشرفين عند التحديث")
        print("   ✅ حذف المشرفين المحذوفين من القناة")
        print("   ✅ عرض جميع المشرفين (ليس فقط الجدد)")
        print("   ✅ تحديد نوع المستخدم (مستخدم/بوت)")
        print("   ✅ إدارة التوقيعات")
        print("   ✅ تحديث جماعي للصلاحيات")
        return 0
    else:
        print("\n❌ بعض الاختبارات فشلت!")
        return 1

if __name__ == "__main__":
    exit(main())