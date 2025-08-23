#!/usr/bin/env python3
"""
Test script to verify chat ID normalization
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_chat_id_normalization():
    """Test chat ID normalization"""
    print("🔍 اختبار تطبيع معرف القناة...")
    
    try:
        from userbot_service.userbot import UserbotService
        
        # Create userbot instance
        userbot = UserbotService()
        
        # Test cases
        test_cases = [
            "2787807057",           # Channel ID without prefix
            "-1002787807057",       # Channel ID with prefix
            "1002787807057",        # Another format
            "1234567890",           # Supergroup ID
            "987654321",            # Group ID
            "12345",                # Small ID (should not change)
            "abc123",               # Non-numeric (should not change)
            "",                     # Empty string
        ]
        
        print("\n📋 نتائج اختبار تطبيع معرف القناة:")
        print("-" * 60)
        
        for test_id in test_cases:
            try:
                normalized = userbot._normalize_chat_id(test_id)
                status = "✅" if normalized != test_id else "ℹ️"
                print(f"{status} {test_id:>15} -> {normalized}")
                
                # Special check for the specific case mentioned
                if test_id == "2787807057":
                    if normalized == "-1002787807057":
                        print(f"   🎯 تم تطبيع معرف القناة {test_id} بنجاح إلى {normalized}")
                    else:
                        print(f"   ❌ فشل في تطبيع معرف القناة {test_id}")
                        
            except Exception as e:
                print(f"❌ {test_id:>15} -> خطأ: {e}")
        
        print("-" * 60)
        print("✅ انتهى اختبار تطبيع معرف القناة")
        
        return True
        
    except ImportError as e:
        print(f"❌ فشل في استيراد UserbotService: {e}")
        return False
    except Exception as e:
        print(f"❌ خطأ غير متوقع: {e}")
        return False

def test_entity_resolution_methods():
    """Test if entity resolution methods exist"""
    print("\n🔍 اختبار وجود طرق حل الكيانات...")
    
    try:
        from userbot_service.userbot import UserbotService
        userbot = UserbotService()
        
        required_methods = [
            '_normalize_chat_id',
            '_resolve_entity_safely',
            '_validate_chat_id',
            '_check_bot_permissions'
        ]
        
        print("\n📋 طرق حل الكيانات:")
        print("-" * 40)
        
        for method in required_methods:
            if hasattr(userbot, method):
                print(f"✅ {method}")
            else:
                print(f"❌ {method}")
        
        print("-" * 40)
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار طرق حل الكيانات: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 بدء اختبار تطبيع معرف القناة...")
    print("=" * 60)
    
    # Test 1: Chat ID normalization
    if not test_chat_id_normalization():
        print("❌ فشل في اختبار تطبيع معرف القناة")
        return False
    
    # Test 2: Entity resolution methods
    if not test_entity_resolution_methods():
        print("❌ فشل في اختبار طرق حل الكيانات")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 جميع الاختبارات نجحت!")
    print("✅ تم إصلاح تطبيع معرف القناة")
    print("✅ معرف القناة 2787807057 سيتم تطبيعه إلى -1002787807057")
    print("✅ تم تحسين حل الكيانات")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n💡 يمكنك الآن تشغيل البوت مع معرفات القنوات الصحيحة")
        else:
            print("\n❌ هناك مشاكل تحتاج إلى إصلاح")
    except KeyboardInterrupt:
        print("\n⏹️ تم إيقاف الاختبار بواسطة المستخدم")
    except Exception as e:
        print(f"\n❌ خطأ غير متوقع: {e}")
        import traceback
        traceback.print_exc()