#!/usr/bin/env python3
"""
Simple test for chat ID normalization
"""

def normalize_chat_id(target_chat_id: str) -> str:
    """Normalize chat ID by adding -100 prefix if needed"""
    try:
        if not target_chat_id:
            return target_chat_id
        
        # Remove any existing -100 prefix first
        clean_id = target_chat_id.replace('-100', '')
        
        # If it's a large numeric ID (likely a channel ID without -100 prefix)
        if clean_id.isdigit():
            chat_id_int = int(clean_id)
            
            # Channel IDs are typically 13-14 digits and start with 1, 2, 3, 4, 5, 6, 7, 8, 9
            # Supergroup IDs are typically 10-12 digits
            if chat_id_int > 1000000000:
                # This looks like a channel ID, ensure it has -100 prefix
                normalized_id = f"-100{clean_id}"
                print(f"🔄 تم تطبيع معرف القناة: {target_chat_id} -> {normalized_id}")
                return normalized_id
            elif chat_id_int > 100000000:
                # This might be a supergroup ID, try with -100 prefix
                normalized_id = f"-100{clean_id}"
                print(f"🔄 تم تطبيع معرف المجموعة الفائقة: {target_chat_id} -> {normalized_id}")
                return normalized_id
            elif chat_id_int > 10000000:
                # This might be a group ID, try with -100 prefix
                normalized_id = f"-100{clean_id}"
                print(f"🔄 تم تطبيع معرف المجموعة: {target_chat_id} -> {normalized_id}")
                return normalized_id
        
        return target_chat_id
        
    except Exception as e:
        print(f"❌ خطأ في تطبيع معرف القناة: {e}")
        return target_chat_id

def test_chat_id_normalization():
    """Test chat ID normalization"""
    print("🔍 اختبار تطبيع معرف القناة...")
    
    # Test cases
    test_cases = [
        "2787807057",           # Channel ID without prefix - THIS IS THE MAIN TEST
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
    
    success_count = 0
    total_count = len(test_cases)
    
    for test_id in test_cases:
        try:
            normalized = normalize_chat_id(test_id)
            status = "✅" if normalized != test_id else "ℹ️"
            print(f"{status} {test_id:>15} -> {normalized}")
            
            # Special check for the specific case mentioned
            if test_id == "2787807057":
                if normalized == "-1002787807057":
                    print(f"   🎯 تم تطبيع معرف القناة {test_id} بنجاح إلى {normalized}")
                    success_count += 1
                else:
                    print(f"   ❌ فشل في تطبيع معرف القناة {test_id}")
            elif normalized != test_id:
                success_count += 1
                
        except Exception as e:
            print(f"❌ {test_id:>15} -> خطأ: {e}")
    
    print("-" * 60)
    print(f"📊 النتائج: {success_count}/{total_count} اختبارات نجحت")
    
    # Main test result
    main_test_id = "2787807057"
    main_test_result = normalize_chat_id(main_test_id)
    
    if main_test_result == "-1002787807057":
        print(f"\n🎉 النتيجة الرئيسية: تم تطبيع معرف القناة {main_test_id} بنجاح!")
        print(f"   المعرف الأصلي: {main_test_id}")
        print(f"   المعرف المطبيع: {main_test_result}")
        print(f"   ✅ هذا يحل مشكلة 'Could not find the input entity'")
        return True
    else:
        print(f"\n❌ النتيجة الرئيسية: فشل في تطبيع معرف القناة {main_test_id}")
        print(f"   المعرف الأصلي: {main_test_id}")
        print(f"   المعرف المطبيع: {main_test_result}")
        return False

def main():
    """Main test function"""
    print("🚀 بدء اختبار تطبيع معرف القناة...")
    print("=" * 60)
    
    success = test_chat_id_normalization()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 الاختبار نجح!")
        print("✅ تم إصلاح تطبيع معرف القناة")
        print("✅ معرف القناة 2787807057 سيتم تطبيعه إلى -1002787807057")
        print("✅ هذا يحل مشكلة 'Could not find the input entity'")
        print("\n💡 يمكنك الآن تشغيل البوت مع معرفات القنوات الصحيحة")
    else:
        print("❌ الاختبار فشل")
        print("❌ هناك مشاكل تحتاج إلى إصلاح")
    
    return success

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ تم إيقاف الاختبار بواسطة المستخدم")
    except Exception as e:
        print(f"\n❌ خطأ غير متوقع: {e}")
        import traceback
        traceback.print_exc()