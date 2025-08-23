#!/usr/bin/env python3
"""
Comprehensive test script to verify all fixes are working
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test all critical imports"""
    print("🔍 اختبار الاستيرادات الحرجة...")
    
    try:
        # Test aiohttp
        import aiohttp
        print("✅ aiohttp - تم الاستيراد بنجاح")
    except ImportError as e:
        print(f"❌ aiohttp - فشل في الاستيراد: {e}")
        return False
    
    try:
        # Test telethon
        import telethon
        print("✅ telethon - تم الاستيراد بنجاح")
    except ImportError as e:
        print(f"❌ telethon - فشل في الاستيراد: {e}")
        return False
    
    try:
        # Test python-telegram-bot
        from telegram import Bot
        print("✅ python-telegram-bot - تم الاستيراد بنجاح")
    except ImportError as e:
        print(f"❌ python-telegram-bot - فشل في الاستيراد: {e}")
        return False
    
    return True

def test_userbot_service():
    """Test userbot service imports"""
    print("\n🔍 اختبار خدمة UserBot...")
    
    try:
        from userbot_service.userbot import UserbotService, userbot_instance
        print("✅ UserbotService - تم الاستيراد بنجاح")
        print("✅ userbot_instance - تم الاستيراد بنجاح")
        
        # Test if userbot_instance is properly initialized
        if userbot_instance:
            print("✅ userbot_instance تم تهيئته بنجاح")
        else:
            print("❌ userbot_instance لم يتم تهيئته")
            return False
        
        return True
        
    except ImportError as e:
        print(f"❌ فشل في استيراد UserbotService: {e}")
        return False
    except Exception as e:
        print(f"❌ خطأ غير متوقع: {e}")
        return False

def test_chat_id_normalization():
    """Test chat ID normalization"""
    print("\n🔍 اختبار تطبيع معرف القناة...")
    
    try:
        from userbot_service.userbot import UserbotService
        
        # Create userbot instance
        userbot = UserbotService()
        
        # Test cases
        test_cases = [
            ("2787807057", "-1002787807057", "معرف قناة بدون -100"),
            ("-1002787807057", "-1002787807057", "معرف قناة مع -100"),
            ("1234567890", "-1001234567890", "معرف مجموعة فائقة"),
            ("987654321", "-100987654321", "معرف مجموعة"),
            ("12345", "12345", "معرف صغير"),
        ]
        
        print("\n📋 نتائج اختبار تطبيع معرف القناة:")
        print("-" * 70)
        
        success_count = 0
        for original, expected, description in test_cases:
            try:
                normalized = userbot._normalize_chat_id(original)
                if normalized == expected:
                    print(f"✅ {original:>15} -> {normalized:>15} | {description}")
                    success_count += 1
                else:
                    print(f"❌ {original:>15} -> {normalized:>15} | {description} (متوقع: {expected})")
                    
            except Exception as e:
                print(f"❌ {original:>15} -> خطأ: {e}")
        
        print("-" * 70)
        print(f"📊 النتائج: {success_count}/{len(test_cases)} اختبارات نجحت")
        
        # Main test result
        main_test_id = "2787807057"
        main_test_result = userbot._normalize_chat_id(main_test_id)
        
        if main_test_result == "-1002787807057":
            print(f"\n🎯 النتيجة الرئيسية: تم تطبيع معرف القناة {main_test_id} بنجاح!")
            print(f"   المعرف الأصلي: {main_test_id}")
            print(f"   المعرف المطبيع: {main_test_result}")
            return True
        else:
            print(f"\n❌ النتيجة الرئيسية: فشل في تطبيع معرف القناة {main_test_id}")
            return False
        
    except Exception as e:
        print(f"❌ خطأ في اختبار تطبيع معرف القناة: {e}")
        return False

def test_button_methods():
    """Test if button methods exist"""
    print("\n🔍 اختبار وجود طرق إضافة الأزرار...")
    
    try:
        from userbot_service.userbot import UserbotService
        userbot = UserbotService()
        
        required_methods = [
            '_add_inline_buttons_with_bot',
            '_add_buttons_via_api',
            '_edit_message_with_buttons_via_bot',
            '_get_message_text_via_api',
            '_edit_message_with_text_and_buttons',
            '_send_new_message_with_buttons'
        ]
        
        print("\n📋 طرق إضافة الأزرار:")
        print("-" * 50)
        
        success_count = 0
        for method in required_methods:
            if hasattr(userbot, method):
                print(f"✅ {method}")
                success_count += 1
            else:
                print(f"❌ {method}")
        
        print("-" * 50)
        print(f"📊 النتائج: {success_count}/{len(required_methods)} طرق موجودة")
        
        return success_count == len(required_methods)
        
    except Exception as e:
        print(f"❌ خطأ في اختبار طرق إضافة الأزرار: {e}")
        return False

def test_main_import():
    """Test main.py import"""
    print("\n🔍 اختبار استيراد main.py...")
    
    try:
        import main
        print("✅ main.py - تم الاستيراد بنجاح")
        return True
        
    except ImportError as e:
        print(f"❌ فشل في استيراد main.py: {e}")
        return False
    except Exception as e:
        print(f"❌ خطأ غير متوقع في main.py: {e}")
        return False

def test_bot_simple_import():
    """Test bot_simple.py import"""
    print("\n🔍 اختبار استيراد bot_simple.py...")
    
    try:
        from bot_package.bot_simple import SimpleTelegramBot
        print("✅ bot_simple.py - تم الاستيراد بنجاح")
        return True
        
    except ImportError as e:
        print(f"❌ فشل في استيراد bot_simple.py: {e}")
        return False
    except Exception as e:
        print(f"❌ خطأ غير متوقع في bot_simple.py: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 بدء الاختبار الشامل لإصلاحات البوت...")
    print("=" * 80)
    
    tests = [
        ("الاستيرادات الحرجة", test_imports),
        ("خدمة UserBot", test_userbot_service),
        ("تطبيع معرف القناة", test_chat_id_normalization),
        ("طرق إضافة الأزرار", test_button_methods),
        ("استيراد main.py", test_main_import),
        ("استيراد bot_simple.py", test_bot_simple_import),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 اختبار: {test_name}")
        print("-" * 40)
        
        try:
            success = test_func()
            results.append((test_name, success))
            
            if success:
                print(f"✅ {test_name} - نجح")
            else:
                print(f"❌ {test_name} - فشل")
                
        except Exception as e:
            print(f"❌ {test_name} - خطأ: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 ملخص النتائج:")
    print("-" * 40)
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {test_name}")
    
    print("-" * 40)
    print(f"📊 النتائج: {success_count}/{total_count} اختبارات نجحت")
    
    if success_count == total_count:
        print("\n🎉 جميع الاختبارات نجحت!")
        print("✅ تم إصلاح جميع المشاكل بنجاح")
        print("✅ البوت جاهز للتشغيل")
        print("\n💡 يمكنك الآن تشغيل البوت باستخدام:")
        print("   source venv/bin/activate")
        print("   python3 main.py")
    else:
        print(f"\n⚠️ {total_count - success_count} اختبارات فشلت")
        print("❌ هناك مشاكل تحتاج إلى إصلاح")
    
    return success_count == total_count

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️ تم إيقاف الاختبار بواسطة المستخدم")
    except Exception as e:
        print(f"\n❌ خطأ غير متوقع: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)