#!/usr/bin/env python3
"""
Test chat ID normalization - adding -100 prefix if needed
"""
import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from userbot_service.userbot import UserBot

def test_chat_id_normalization():
    """Test chat ID normalization function"""
    print("🧪 اختبار تطبيع معرفات القنوات...")
    
    userbot = UserBot()
    
    # Test cases
    test_cases = [
        # Original ID -> Expected normalized ID
        ("2638960177", "-1002638960177", "معرف قناة بدون -100"),
        ("1234567890123", "-1001234567890123", "معرف قناة كبير بدون -100"),
        ("-1002638960177", "-1002638960177", "معرف قناة مع -100 (لا يتغير)"),
        ("-1001234567890", "-1001234567890", "معرف قناة مع -100 (لا يتغير)"),
        ("-123456789", "-123456789", "معرف مجموعة (لا يتغير)"),
        ("@channel_name", "@channel_name", "اسم قناة (لا يتغير)"),
        ("", "", "معرف فارغ"),
        ("abc123", "abc123", "معرف غير صحيح (لا يتغير)"),
    ]
    
    print("\n📋 نتائج الاختبار:")
    print("=" * 80)
    
    for original_id, expected_id, description in test_cases:
        try:
            normalized_id = userbot._normalize_chat_id(original_id)
            status = "✅ صحيح" if normalized_id == expected_id else "❌ خطأ"
            print(f"{status} | {original_id:15} -> {normalized_id:15} | {description}")
        except Exception as e:
            print(f"❌ خطأ | {original_id:15} -> خطأ: {e}")

async def test_with_real_chat_id():
    """Test with the specific chat ID mentioned by user"""
    print("\n🔧 اختبار معرف القناة المحدد: 2638960177")
    
    userbot = UserBot()
    
    # Test normalization
    original_id = "2638960177"
    normalized_id = userbot._normalize_chat_id(original_id)
    
    print(f"المعرف الأصلي: {original_id}")
    print(f"المعرف المطبيع: {normalized_id}")
    
    # Test validation
    is_valid_original = userbot._validate_chat_id(original_id)
    is_valid_normalized = userbot._validate_chat_id(normalized_id)
    
    print(f"صحة المعرف الأصلي: {'✅ صحيح' if is_valid_original else '❌ غير صحيح'}")
    print(f"صحة المعرف المطبيع: {'✅ صحيح' if is_valid_normalized else '❌ غير صحيح'}")
    
    # Test bot permissions with normalized ID
    if is_valid_normalized:
        print(f"\n🔍 اختبار صلاحيات البوت مع المعرف المطبيع: {normalized_id}")
        try:
            has_permissions = await userbot._check_bot_permissions(normalized_id)
            print(f"الصلاحيات: {'✅ متوفرة' if has_permissions else '❌ غير متوفرة'}")
            
            if has_permissions:
                print("🎉 المعرف المطبيع يعمل بشكل صحيح!")
            else:
                print("⚠️ المعرف صحيح لكن البوت ليس لديه صلاحيات كافية")
                
        except Exception as e:
            print(f"❌ خطأ في فحص الصلاحيات: {e}")
    else:
        print("❌ المعرف المطبيع غير صحيح")

def show_normalization_examples():
    """Show examples of chat ID normalization"""
    print("\n📖 أمثلة على تطبيع معرفات القنوات:")
    print("=" * 50)
    
    examples = [
        ("2638960177", "-1002638960177", "معرف قناة بدون -100"),
        ("1234567890123", "-1001234567890123", "معرف قناة كبير بدون -100"),
        ("9876543210987", "-1009876543210987", "معرف قناة آخر بدون -100"),
    ]
    
    for original, normalized, description in examples:
        print(f"  {original:15} -> {normalized:15} | {description}")
    
    print("\n💡 لا يتغير:")
    print("  -1002638960177 -> -1002638960177 | معرف قناة مع -100")
    print("  -123456789     -> -123456789     | معرف مجموعة")
    print("  @channel_name  -> @channel_name  | اسم قناة")

def explain_normalization():
    """Explain why normalization is needed"""
    print("\n🔍 لماذا نحتاج تطبيع معرف القناة؟")
    print("=" * 50)
    
    explanation = [
        "1. معرفات القنوات في Telegram تبدأ بـ -100",
        "2. أحياناً يتم تخزين المعرف بدون -100 في قاعدة البيانات",
        "3. البوت يحتاج المعرف الكامل مع -100 للوصول للقناة",
        "4. دالة التطبيع تضيف -100 تلقائياً إذا كان مفقوداً",
        "5. هذا يحل مشكلة 'Cannot get entity by phone number'",
    ]
    
    for line in explanation:
        print(f"  {line}")

async def main():
    """Main test function"""
    print("🚀 اختبار تطبيع معرفات القنوات")
    print("=" * 80)
    
    # Show examples
    show_normalization_examples()
    
    # Explain normalization
    explain_normalization()
    
    # Test normalization function
    test_chat_id_normalization()
    
    # Test with real chat ID
    await test_with_real_chat_id()
    
    print("\n" + "=" * 80)
    print("✅ انتهى اختبار تطبيع معرفات القنوات")

if __name__ == "__main__":
    asyncio.run(main())