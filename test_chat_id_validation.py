#!/usr/bin/env python3
"""
Test chat ID validation and format detection
"""
import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from userbot_service.userbot import UserBot

def test_chat_id_validation():
    """Test chat ID validation function"""
    print("🧪 اختبار التحقق من معرفات القنوات...")
    
    userbot = UserBot()
    
    # Test cases
    test_cases = [
        # Valid chat IDs
        ("-1001234567890", "معرف قناة صحيح"),
        ("-123456789", "معرف مجموعة صحيح"),
        ("1234567890123", "معرف رقمي كبير (محتمل قناة)"),
        ("@channel_name", "اسم مستخدم قناة"),
        
        # Invalid chat IDs (phone numbers)
        ("2638960177", "رقم هاتف (غير صحيح)"),
        ("1234567890", "رقم هاتف (غير صحيح)"),
        ("987654321", "رقم هاتف (غير صحيح)"),
        
        # Edge cases
        ("", "معرف فارغ"),
        ("abc123", "معرف غير صحيح"),
        ("123", "رقم صغير"),
    ]
    
    print("\n📋 نتائج الاختبار:")
    print("=" * 60)
    
    for chat_id, description in test_cases:
        try:
            is_valid = userbot._validate_chat_id(chat_id)
            status = "✅ صحيح" if is_valid else "❌ غير صحيح"
            print(f"{status} | {chat_id:15} | {description}")
        except Exception as e:
            print(f"❌ خطأ | {chat_id:15} | {description} - {e}")

async def test_bot_permissions():
    """Test bot permissions with different chat IDs"""
    print("\n🔧 اختبار صلاحيات البوت...")
    
    userbot = UserBot()
    
    # Test with the problematic chat ID
    problematic_chat_id = "2638960177"
    
    print(f"\nاختبار معرف القناة: {problematic_chat_id}")
    
    # Test validation
    is_valid = userbot._validate_chat_id(problematic_chat_id)
    print(f"التحقق من الصحة: {'✅ صحيح' if is_valid else '❌ غير صحيح'}")
    
    if is_valid:
        # Test permissions
        try:
            has_permissions = await userbot._check_bot_permissions(problematic_chat_id)
            print(f"الصلاحيات: {'✅ متوفرة' if has_permissions else '❌ غير متوفرة'}")
        except Exception as e:
            print(f"❌ خطأ في فحص الصلاحيات: {e}")
    else:
        print("💡 لا يمكن فحص الصلاحيات - معرف القناة غير صحيح")

def show_chat_id_formats():
    """Show examples of correct chat ID formats"""
    print("\n📖 أمثلة على معرفات القنوات الصحيحة:")
    print("=" * 50)
    
    examples = [
        ("-1001234567890", "معرف قناة (يبدأ بـ -100)"),
        ("-123456789", "معرف مجموعة (يبدأ بـ -)"),
        ("1234567890123", "معرف رقمي كبير (> 1 مليار)"),
        ("@channel_name", "اسم مستخدم القناة"),
        ("@group_name", "اسم مستخدم المجموعة"),
    ]
    
    for chat_id, description in examples:
        print(f"  {chat_id:15} | {description}")
    
    print("\n❌ أمثلة على معرفات غير صحيحة:")
    print("=" * 50)
    
    invalid_examples = [
        ("2638960177", "رقم هاتف"),
        ("1234567890", "رقم هاتف"),
        ("987654321", "رقم هاتف"),
        ("123", "رقم صغير"),
        ("", "فارغ"),
    ]
    
    for chat_id, description in invalid_examples:
        print(f"  {chat_id:15} | {description}")

def get_correct_chat_id():
    """Help user get correct chat ID"""
    print("\n🔍 كيفية الحصول على معرف القناة الصحيح:")
    print("=" * 50)
    
    steps = [
        "1. افتح القناة في Telegram",
        "2. انسخ رابط القناة (مثال: https://t.me/channel_name)",
        "3. استخدم اسم القناة بعد @ (مثال: @channel_name)",
        "4. أو استخدم معرف القناة الرقمي (يبدأ بـ -100)",
        "5. تأكد من أن البوت عضو في القناة",
    ]
    
    for step in steps:
        print(f"  {step}")
    
    print("\n💡 نصائح:")
    print("  - لا تستخدم أرقام الهواتف كمعرفات قنوات")
    print("  - تأكد من أن البوت لديه صلاحيات في القناة")
    print("  - استخدم معرف القناة وليس معرف المستخدم")

async def main():
    """Main test function"""
    print("🚀 اختبار التحقق من معرفات القنوات")
    print("=" * 60)
    
    # Test chat ID validation
    test_chat_id_validation()
    
    # Show correct formats
    show_chat_id_formats()
    
    # Help user get correct chat ID
    get_correct_chat_id()
    
    # Test bot permissions
    await test_bot_permissions()
    
    print("\n" + "=" * 60)
    print("✅ انتهى اختبار التحقق من معرفات القنوات")

if __name__ == "__main__":
    asyncio.run(main())