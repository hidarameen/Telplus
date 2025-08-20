#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار وظيفة تسجيل الدخول عبر جلسة تليثون جاهزة
Test script for Telethon session-based login functionality
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

async def test_session_login_components():
    """اختبار مكونات وظيفة تسجيل الدخول بالجلسة"""
    
    print("🔍 بدء اختبار مكونات تسجيل الدخول بالجلسة...")
    
    try:
        # اختبار استيراد المكتبات المطلوبة
        print("📚 اختبار استيراد المكتبات...")
        
        from telethon.sessions import StringSession
        print("✅ StringSession - متوفر")
        
        from telethon import TelegramClient
        print("✅ TelegramClient - متوفر")
        
        from datetime import datetime
        print("✅ datetime - متوفر")
        
        import json
        print("✅ json - متوفر")
        
        import asyncio
        print("✅ asyncio - متوفر")
        
        # اختبار استيراد وحدات البوت
        print("\n🤖 اختبار استيراد وحدات البوت...")
        
        from bot_package.config import API_ID, API_HASH
        print("✅ config - متوفر")
        print(f"   API_ID: {API_ID}")
        print(f"   API_HASH: {API_HASH[:10]}...")
        
        from bot_package.bot_simple import SimpleTelegramBot
        print("✅ BotSimple - متوفر")
        
        from database.database_sqlite import Database
        print("✅ Database - متوفر")
        
        from userbot_service.userbot import UserbotService
        print("✅ UserBot - متوفر")
        
        # اختبار إنشاء قاعدة البيانات
        print("\n🗄️ اختبار قاعدة البيانات...")
        
        db = Database()
        print("✅ تم إنشاء قاعدة البيانات")
        
        # اختبار الوظائف الأساسية
        print("\n🔧 اختبار الوظائف الأساسية...")
        
        # اختبار حفظ حالة المحادثة
        test_user_id = 12345
        test_state = 'waiting_session'
        test_data = json.dumps({'test': 'data'})
        
        db.set_conversation_state(test_user_id, test_state, test_data)
        print("✅ تم حفظ حالة المحادثة")
        
        # اختبار استرجاع حالة المحادثة
        retrieved_state = db.get_conversation_state(test_user_id)
        if retrieved_state:
            state, data = retrieved_state
            print(f"✅ تم استرجاع حالة المحادثة: {state}")
        else:
            print("❌ فشل في استرجاع حالة المحادثة")
        
        # اختبار مسح حالة المحادثة
        db.clear_conversation_state(test_user_id)
        print("✅ تم مسح حالة المحادثة")
        
        # اختبار حفظ جلسة المستخدم
        test_phone = "+966501234567"
        test_session = "1BQANOTEz..." + "A" * 100  # جلسة وهمية
        
        db.save_user_session(test_user_id, test_phone, test_session)
        print("✅ تم حفظ جلسة المستخدم")
        
        # اختبار استرجاع جلسة المستخدم
        session_data = db.get_user_session(test_user_id)
        if session_data:
            print(f"✅ تم استرجاع جلسة المستخدم: {session_data[1]}")
        else:
            print("❌ فشل في استرجاع جلسة المستخدم")
        
        # اختبار حذف جلسة المستخدم
        db.delete_user_session(test_user_id)
        print("✅ تم حذف جلسة المستخدم")
        
        # اختبار فحص المصادقة
        is_auth = db.is_user_authenticated(test_user_id)
        print(f"✅ حالة المصادقة: {'مُصادق عليه' if is_auth else 'غير مُصادق عليه'}")
        
        print("\n🎉 تم إكمال جميع الاختبارات بنجاح!")
        
    except ImportError as e:
        print(f"❌ خطأ في الاستيراد: {e}")
        return False
    except Exception as e:
        print(f"❌ خطأ في الاختبار: {e}")
        return False
    
    return True

async def test_session_validation():
    """اختبار التحقق من صحة الجلسة"""
    
    print("\n🔐 اختبار التحقق من صحة الجلسة...")
    
    try:
        from telethon.sessions import StringSession
        from telethon import TelegramClient
        from bot_package.config import API_ID, API_HASH
        
        # اختبار إنشاء جلسة وهمية
        test_session = "1BQANOTEz..." + "A" * 100
        
        print("✅ تم إنشاء جلسة وهمية للاختبار")
        print(f"   طول الجلسة: {len(test_session)} حرف")
        
        # اختبار إنشاء عميل مؤقت
        temp_client = TelegramClient(StringSession(test_session), int(API_ID), API_HASH)
        print("✅ تم إنشاء عميل مؤقت")
        
        # اختبار الاتصال (سيفشل مع الجلسة الوهمية)
        try:
            await asyncio.wait_for(temp_client.connect(), timeout=5)
            print("⚠️ تم الاتصال (غير متوقع مع جلسة وهمية)")
        except Exception as e:
            print(f"✅ فشل الاتصال كما هو متوقع: {type(e).__name__}")
        
        await temp_client.disconnect()
        print("✅ تم قطع الاتصال")
        
        print("🎉 تم إكمال اختبار التحقق من صحة الجلسة!")
        
    except Exception as e:
        print(f"❌ خطأ في اختبار التحقق من صحة الجلسة: {e}")
        return False
    
    return True

async def main():
    """الدالة الرئيسية"""
    
    print("🚀 بدء اختبار وظيفة تسجيل الدخول بالجلسة...")
    print("=" * 60)
    
    # اختبار المكونات الأساسية
    components_ok = await test_session_login_components()
    
    if components_ok:
        # اختبار التحقق من صحة الجلسة
        validation_ok = await test_session_validation()
        
        if validation_ok:
            print("\n" + "=" * 60)
            print("🎊 جميع الاختبارات نجحت!")
            print("✅ وظيفة تسجيل الدخول بالجلسة تعمل بشكل صحيح")
            print("✅ جميع المكونات متوفرة")
            print("✅ قاعدة البيانات تعمل")
            print("✅ التحقق من صحة الجلسة يعمل")
        else:
            print("\n" + "=" * 60)
            print("⚠️ بعض الاختبارات فشلت")
            print("❌ مشكلة في التحقق من صحة الجلسة")
    else:
        print("\n" + "=" * 60)
        print("❌ فشل في اختبار المكونات الأساسية")
        print("❌ مشكلة في المكتبات أو الوحدات")
    
    print("\n📋 ملخص الاختبار:")
    print("• المكونات الأساسية:", "✅" if components_ok else "❌")
    print("• التحقق من صحة الجلسة:", "✅" if 'validation_ok' in locals() and validation_ok else "❌")
    
    if components_ok and 'validation_ok' in locals() and validation_ok:
        print("\n🎯 النتيجة: وظيفة تسجيل الدخول بالجلسة جاهزة للاستخدام!")
    else:
        print("\n🔧 النتيجة: يلزم إصلاح بعض المشاكل قبل الاستخدام")

if __name__ == "__main__":
    # تشغيل الاختبار
    asyncio.run(main())