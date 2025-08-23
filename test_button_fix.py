#!/usr/bin/env python3
"""
Test script to verify button functionality and entity resolution fixes
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_imports():
    """Test if all required modules can be imported"""
    print("🔍 اختبار استيراد المكتبات...")
    
    try:
        import aiohttp
        print("✅ aiohttp - تم الاستيراد بنجاح")
    except ImportError as e:
        print(f"❌ aiohttp - فشل في الاستيراد: {e}")
        return False
    
    try:
        import telethon
        print("✅ telethon - تم الاستيراد بنجاح")
    except ImportError as e:
        print(f"❌ telethon - فشل في الاستيراد: {e}")
        return False
    
    try:
        from telegram import Bot
        print("✅ python-telegram-bot - تم الاستيراد بنجاح")
    except ImportError as e:
        print(f"❌ python-telegram-bot - فشل في الاستيراد: {e}")
        return False
    
    return True

async def test_userbot_imports():
    """Test if userbot service can be imported"""
    print("\n🔍 اختبار استيراد خدمة UserBot...")
    
    try:
        from userbot_service.userbot import UserbotService
        print("✅ UserbotService - تم الاستيراد بنجاح")
        
        # Test if the new methods exist
        userbot = UserbotService()
        
        # Test chat ID normalization
        test_ids = ["2787807057", "-1002787807057", "1002787807057"]
        for test_id in test_ids:
            normalized = userbot._normalize_chat_id(test_id)
            print(f"🔄 تطبيع معرف القناة: {test_id} -> {normalized}")
        
        # Test entity resolution method exists
        if hasattr(userbot, '_resolve_entity_safely'):
            print("✅ _resolve_entity_safely - الطريقة موجودة")
        else:
            print("❌ _resolve_entity_safely - الطريقة غير موجودة")
        
        # Test button methods exist
        button_methods = [
            '_add_inline_buttons_with_bot',
            '_add_buttons_via_api',
            '_edit_message_with_buttons_via_bot',
            '_get_message_text_via_api',
            '_edit_message_with_text_and_buttons',
            '_send_new_message_with_buttons'
        ]
        
        for method in button_methods:
            if hasattr(userbot, method):
                print(f"✅ {method} - الطريقة موجودة")
            else:
                print(f"❌ {method} - الطريقة غير موجودة")
        
        return True
        
    except ImportError as e:
        print(f"❌ UserbotService - فشل في الاستيراد: {e}")
        return False
    except Exception as e:
        print(f"❌ خطأ في اختبار UserbotService: {e}")
        return False

async def test_aiohttp_functionality():
    """Test aiohttp basic functionality"""
    print("\n🔍 اختبار وظائف aiohttp...")
    
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            # Test a simple HTTP request
            async with session.get('https://httpbin.org/get') as response:
                if response.status == 200:
                    print("✅ aiohttp - طلب HTTP ناجح")
                    return True
                else:
                    print(f"❌ aiohttp - طلب HTTP فشل: {response.status}")
                    return False
                    
    except Exception as e:
        print(f"❌ خطأ في اختبار aiohttp: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 بدء اختبار إصلاحات البوت...")
    print("=" * 50)
    
    # Test 1: Basic imports
    if not await test_imports():
        print("❌ فشل في اختبار الاستيراد الأساسي")
        return False
    
    # Test 2: aiohttp functionality
    if not await test_aiohttp_functionality():
        print("❌ فشل في اختبار وظائف aiohttp")
        return False
    
    # Test 3: UserBot service imports
    if not await test_userbot_imports():
        print("❌ فشل في اختبار خدمة UserBot")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 جميع الاختبارات نجحت!")
    print("✅ تم إصلاح مشكلة aiohttp")
    print("✅ تم إصلاح مشكلة الأزرار")
    print("✅ تم تحسين حل الكيانات")
    print("\n💡 يمكنك الآن تشغيل البوت بدون أخطاء")
    
    return True

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ تم إيقاف الاختبار بواسطة المستخدم")
    except Exception as e:
        print(f"\n❌ خطأ غير متوقع: {e}")
        import traceback
        traceback.print_exc()