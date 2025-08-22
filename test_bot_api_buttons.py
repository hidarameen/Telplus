#!/usr/bin/env python3
"""
Test adding inline buttons via Bot API
"""
import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from userbot_service.userbot import UserBot
from database.database import Database
from telethon import Button

async def test_bot_api_buttons():
    """Test adding buttons via Bot API"""
    print("🧪 اختبار إضافة الأزرار عبر Bot API...")
    
    try:
        # Initialize database
        db = Database()
        
        # Test task ID (you can change this to a real task ID)
        test_task_id = 1
        
        # Check if task exists
        task = db.get_task(test_task_id)
        if not task:
            print(f"❌ لم يتم العثور على المهمة {test_task_id}")
            return
        
        print(f"✅ تم العثور على المهمة: {task['name']}")
        
        # Check if inline buttons are enabled
        message_settings = db.get_message_settings(test_task_id)
        if not message_settings.get('inline_buttons_enabled', False):
            print("❌ الأزرار الإنلاين غير مفعلة لهذه المهمة")
            return
        
        print("✅ الأزرار الإنلاين مفعلة")
        
        # Get inline buttons
        buttons_data = db.get_inline_buttons(test_task_id)
        if not buttons_data:
            print("❌ لا توجد أزرار إنلاين محددة لهذه المهمة")
            return
        
        print(f"✅ تم العثور على {len(buttons_data)} زر إنلاين")
        
        # Build inline buttons
        userbot = UserBot()
        
        # Group buttons by row
        rows = {}
        for button in buttons_data:
            row = button['row_position']
            if row not in rows:
                rows[row] = []
            rows[row].append(button)
        
        # Build button matrix
        button_matrix = []
        for row_num in sorted(rows.keys()):
            row_buttons = sorted(rows[row_num], key=lambda x: x['col_position'])
            button_row = []
            for button in row_buttons:
                button_row.append(Button.url(button['button_text'], button['button_url']))
            button_matrix.append(button_row)
        
        print(f"✅ تم بناء {len(button_matrix)} صف من الأزرار")
        
        # Test Bot API method
        print("\n🔧 اختبار إضافة الأزرار عبر Bot API...")
        
        # You need to provide real chat_id and message_id for testing
        test_chat_id = input("أدخل معرف القناة الهدف (مثال: 2638960177 أو -1002638960177): ").strip()
        test_message_id = input("أدخل معرف الرسالة (رقم): ").strip()
        
        if not test_chat_id or not test_message_id:
            print("❌ يجب إدخال معرف القناة والرسالة")
            return
        
        try:
            test_message_id = int(test_message_id)
        except ValueError:
            print("❌ معرف الرسالة يجب أن يكون رقماً")
            return
        
        # Test the Bot API method
        success = await userbot._add_buttons_via_api(
            test_chat_id, 
            test_message_id, 
            button_matrix, 
            test_task_id
        )
        
        if success:
            print("✅ تم اختبار إضافة الأزرار عبر Bot API بنجاح!")
        else:
            print("❌ فشل في اختبار إضافة الأزرار عبر Bot API")
        
    except Exception as e:
        print(f"❌ خطأ في الاختبار: {e}")
        import traceback
        traceback.print_exc()

async def test_chat_id_normalization():
    """Test chat ID normalization"""
    print("\n🔄 اختبار تطبيع معرف القناة...")
    
    userbot = UserBot()
    
    # Test cases
    test_cases = [
        ("2638960177", "-1002638960177"),
        ("1234567890123", "-1001234567890123"),
        ("-1002638960177", "-1002638960177"),
        ("@channel_name", "@channel_name"),
    ]
    
    for original_id, expected_id in test_cases:
        normalized_id = userbot._normalize_chat_id(original_id)
        status = "✅ صحيح" if normalized_id == expected_id else "❌ خطأ"
        print(f"{status} | {original_id:15} -> {normalized_id:15}")

async def test_bot_permissions():
    """Test bot permissions"""
    print("\n🔍 اختبار صلاحيات البوت...")
    
    userbot = UserBot()
    
    test_chat_id = input("أدخل معرف القناة لاختبار الصلاحيات: ").strip()
    
    if not test_chat_id:
        print("❌ يجب إدخال معرف القناة")
        return
    
    # Normalize chat ID
    normalized_chat_id = userbot._normalize_chat_id(test_chat_id)
    print(f"المعرف المطبيع: {normalized_chat_id}")
    
    # Test permissions
    try:
        has_permissions = await userbot._check_bot_permissions(normalized_chat_id)
        print(f"الصلاحيات: {'✅ متوفرة' if has_permissions else '❌ غير متوفرة'}")
    except Exception as e:
        print(f"❌ خطأ في فحص الصلاحيات: {e}")

def show_bot_api_methods():
    """Show available Bot API methods"""
    print("\n📖 طرق إضافة الأزرار عبر Bot API:")
    print("=" * 50)
    
    methods = [
        ("editMessageReplyMarkup", "إضافة أزرار بدون تغيير النص"),
        ("editMessageText", "تعديل النص وإضافة أزرار"),
        ("sendMessage", "إرسال رسالة جديدة مع أزرار"),
    ]
    
    for method, description in methods:
        print(f"  {method:20} | {description}")

async def main():
    """Main test function"""
    print("🚀 اختبار إضافة الأزرار عبر Bot API")
    print("=" * 60)
    
    # Show available methods
    show_bot_api_methods()
    
    # Test chat ID normalization
    await test_chat_id_normalization()
    
    # Test bot permissions
    await test_bot_permissions()
    
    # Test Bot API buttons
    await test_bot_api_buttons()
    
    print("\n" + "=" * 60)
    print("✅ انتهى اختبار إضافة الأزرار عبر Bot API")

if __name__ == "__main__":
    asyncio.run(main())