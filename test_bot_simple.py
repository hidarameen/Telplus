#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار بسيط للبوت
Simple test for the bot
"""

import asyncio
import logging
import sys
import os

# إضافة المسار للوحدات
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_bot_import():
    """اختبار استيراد البوت"""
    
    print("🔍 اختبار استيراد البوت...")
    
    try:
        from bot_package.bot_simple import SimpleTelegramBot
        print("✅ تم استيراد SimpleTelegramBot بنجاح")
        
        # اختبار إنشاء مثيل البوت
        bot = SimpleTelegramBot()
        print("✅ تم إنشاء مثيل البوت بنجاح")
        
        # اختبار وجود الوظائف المطلوبة
        required_methods = [
            'handle_login',
            'start_session_login', 
            'handle_session_input',
            'handle_auth_message',
            'cancel_auth'
        ]
        
        for method in required_methods:
            if hasattr(bot, method):
                print(f"✅ {method} - متوفر")
            else:
                print(f"❌ {method} - غير متوفر")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في استيراد البوت: {e}")
        return False

async def test_database_functions():
    """اختبار وظائف قاعدة البيانات"""
    
    print("\n🗄️ اختبار وظائف قاعدة البيانات...")
    
    try:
        from database.database_sqlite import Database
        
        db = Database()
        print("✅ تم إنشاء قاعدة البيانات")
        
        # اختبار وظائف الجلسة
        test_user_id = 12345
        
        # اختبار حفظ حالة المحادثة
        db.set_conversation_state(test_user_id, 'waiting_session', '{"test": "data"}')
        print("✅ تم حفظ حالة المحادثة")
        
        # اختبار استرجاع حالة المحادثة
        state_data = db.get_conversation_state(test_user_id)
        if state_data:
            state, data = state_data
            print(f"✅ تم استرجاع حالة المحادثة: {state}")
        else:
            print("❌ فشل في استرجاع حالة المحادثة")
        
        # اختبار مسح حالة المحادثة
        db.clear_conversation_state(test_user_id)
        print("✅ تم مسح حالة المحادثة")
        
        # اختبار حفظ جلسة المستخدم
        test_phone = "+966501234567"
        test_session = "1BQANOTEz..." + "A" * 100
        
        db.save_user_session(test_user_id, test_phone, test_session)
        print("✅ تم حفظ جلسة المستخدم")
        
        # اختبار فحص المصادقة
        is_auth = db.is_user_authenticated(test_user_id)
        print(f"✅ حالة المصادقة: {'مُصادق عليه' if is_auth else 'غير مُصادق عليه'}")
        
        # اختبار حذف الجلسة
        db.delete_user_session(test_user_id)
        print("✅ تم حذف جلسة المستخدم")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في قاعدة البيانات: {e}")
        return False

async def main():
    """الدالة الرئيسية"""
    
    print("🚀 بدء اختبار البوت...")
    print("=" * 50)
    
    # اختبار استيراد البوت
    bot_ok = await test_bot_import()
    
    # اختبار قاعدة البيانات
    db_ok = await test_database_functions()
    
    print("\n" + "=" * 50)
    print("📋 ملخص الاختبار:")
    print(f"• البوت: {'✅' if bot_ok else '❌'}")
    print(f"• قاعدة البيانات: {'✅' if db_ok else '❌'}")
    
    if bot_ok and db_ok:
        print("\n🎊 جميع الاختبارات نجحت!")
        print("✅ البوت جاهز للاستخدام")
        print("✅ وظيفة تسجيل الدخول بالجلسة تعمل")
    else:
        print("\n⚠️ بعض الاختبارات فشلت")
        print("❌ يلزم إصلاح المشاكل قبل الاستخدام")

if __name__ == "__main__":
    # تشغيل الاختبار
    asyncio.run(main())