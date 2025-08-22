#!/usr/bin/env python3
"""
Test script for inline buttons functionality
"""
import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from userbot_service.userbot import UserBot
from database.database import Database
from telethon import Button

async def test_inline_buttons():
    """Test inline buttons functionality"""
    print("🧪 بدء اختبار وظيفة الأزرار الإنلاين...")
    
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
        from userbot_service.userbot import UserBot
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
        
        # Test API method
        print("\n🔧 اختبار إضافة الأزرار عبر API...")
        
        # You need to provide real chat_id and message_id for testing
        test_chat_id = input("أدخل معرف القناة الهدف (مثال: -1001234567890): ").strip()
        test_message_id = input("أدخل معرف الرسالة (رقم): ").strip()
        
        if not test_chat_id or not test_message_id:
            print("❌ يجب إدخال معرف القناة والرسالة")
            return
        
        try:
            test_message_id = int(test_message_id)
        except ValueError:
            print("❌ معرف الرسالة يجب أن يكون رقماً")
            return
        
        # Test the API method
        success = await userbot._add_buttons_via_api(
            test_chat_id, 
            test_message_id, 
            button_matrix, 
            test_task_id
        )
        
        if success:
            print("✅ تم اختبار إضافة الأزرار بنجاح!")
        else:
            print("❌ فشل في اختبار إضافة الأزرار")
        
    except Exception as e:
        print(f"❌ خطأ في الاختبار: {e}")
        import traceback
        traceback.print_exc()

async def test_bot_permissions():
    """Test bot permissions in a channel"""
    print("\n🔧 اختبار صلاحيات البوت...")
    
    try:
        from userbot_service.userbot import UserBot
        userbot = UserBot()
        
        test_chat_id = input("أدخل معرف القناة لاختبار الصلاحيات: ").strip()
        
        if not test_chat_id:
            print("❌ يجب إدخال معرف القناة")
            return
        
        has_permissions = await userbot._check_bot_permissions(test_chat_id)
        
        if has_permissions:
            print("✅ البوت لديه صلاحيات كافية في القناة")
        else:
            print("❌ البوت ليس لديه صلاحيات كافية في القناة")
            
    except Exception as e:
        print(f"❌ خطأ في اختبار الصلاحيات: {e}")

async def main():
    """Main test function"""
    print("🚀 بدء اختبارات الأزرار الإنلاين")
    print("=" * 50)
    
    # Test 1: Inline buttons functionality
    await test_inline_buttons()
    
    # Test 2: Bot permissions
    await test_bot_permissions()
    
    print("\n✅ انتهت الاختبارات")

if __name__ == "__main__":
    asyncio.run(main())