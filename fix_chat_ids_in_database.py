#!/usr/bin/env python3
"""
Fix chat IDs in database - detect and fix phone numbers stored as chat IDs
"""
import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import Database
from userbot_service.userbot import UserBot

def validate_chat_id(chat_id: str) -> bool:
    """Validate if chat_id is a valid chat ID and not a phone number"""
    try:
        if not chat_id:
            return False
        
        # Check if it's a phone number (usually 7-15 digits)
        if chat_id.isdigit():
            chat_id_int = int(chat_id)
            if chat_id_int < 1000000000:  # Likely a phone number
                return False
        
        # Check for valid channel/group ID formats
        if chat_id.startswith('-100'):
            # Channel ID format
            return True
        elif chat_id.startswith('-'):
            # Group ID format
            return True
        elif chat_id.startswith('@'):
            # Username format
            return True
        elif chat_id.isdigit() and int(chat_id) > 1000000000:
            # Large numeric ID (likely a chat ID)
            return True
        else:
            # Allow other formats to try anyway
            return True
            
    except Exception as e:
        print(f"❌ خطأ في التحقق من معرف القناة {chat_id}: {e}")
        return False

def scan_database_for_invalid_chat_ids():
    """Scan database for invalid chat IDs (phone numbers)"""
    print("🔍 فحص قاعدة البيانات للبحث عن معرفات قنوات غير صحيحة...")
    
    try:
        db = Database()
        
        # Get all tasks
        tasks = db.get_all_tasks()
        
        invalid_chat_ids = []
        
        for task in tasks:
            task_id = task['id']
            task_name = task['name']
            
            # Check target_chat_id
            target_chat_id = task.get('target_chat_id')
            if target_chat_id and not validate_chat_id(target_chat_id):
                invalid_chat_ids.append({
                    'type': 'task_target',
                    'task_id': task_id,
                    'task_name': task_name,
                    'chat_id': target_chat_id,
                    'field': 'target_chat_id'
                })
            
            # Check task_targets
            targets = db.get_task_targets(task_id)
            for target in targets:
                target_chat_id = target.get('chat_id')
                if target_chat_id and not validate_chat_id(target_chat_id):
                    invalid_chat_ids.append({
                        'type': 'task_targets',
                        'task_id': task_id,
                        'task_name': task_name,
                        'chat_id': target_chat_id,
                        'field': 'chat_id',
                        'target_id': target.get('id')
                    })
        
        return invalid_chat_ids
        
    except Exception as e:
        print(f"❌ خطأ في فحص قاعدة البيانات: {e}")
        return []

def show_invalid_chat_ids(invalid_chat_ids):
    """Show invalid chat IDs found in database"""
    if not invalid_chat_ids:
        print("✅ لم يتم العثور على معرفات قنوات غير صحيحة في قاعدة البيانات")
        return
    
    print(f"\n❌ تم العثور على {len(invalid_chat_ids)} معرف قناة غير صحيح:")
    print("=" * 80)
    
    for item in invalid_chat_ids:
        print(f"المهمة: {item['task_name']} (ID: {item['task_id']})")
        print(f"النوع: {item['type']}")
        print(f"الحقل: {item['field']}")
        print(f"معرف القناة: {item['chat_id']}")
        if 'target_id' in item:
            print(f"معرف الهدف: {item['target_id']}")
        print("-" * 40)

def fix_chat_id_in_database():
    """Interactive fix for chat IDs in database"""
    print("\n🔧 إصلاح معرفات القنوات في قاعدة البيانات...")
    
    try:
        db = Database()
        
        # Get all tasks
        tasks = db.get_all_tasks()
        
        fixed_count = 0
        
        for task in tasks:
            task_id = task['id']
            task_name = task['name']
            target_chat_id = task.get('target_chat_id')
            
            if target_chat_id and not validate_chat_id(target_chat_id):
                print(f"\n❌ معرف قناة غير صحيح في المهمة: {task_name}")
                print(f"   المعرف الحالي: {target_chat_id}")
                
                # Ask user for correct chat ID
                new_chat_id = input("أدخل معرف القناة الصحيح (أو اضغط Enter لتخطي): ").strip()
                
                if new_chat_id:
                    try:
                        # Update task target_chat_id
                        cursor = db.conn.cursor()
                        cursor.execute('UPDATE tasks SET target_chat_id = ? WHERE id = ?', (new_chat_id, task_id))
                        db.conn.commit()
                        
                        # Update task_targets if exists
                        cursor.execute('UPDATE task_targets SET chat_id = ? WHERE task_id = ?', (new_chat_id, task_id))
                        db.conn.commit()
                        
                        print(f"✅ تم تحديث معرف القناة إلى: {new_chat_id}")
                        fixed_count += 1
                        
                    except Exception as e:
                        print(f"❌ خطأ في تحديث معرف القناة: {e}")
                else:
                    print("⏭️ تم تخطي هذه المهمة")
        
        print(f"\n✅ تم إصلاح {fixed_count} معرف قناة")
        
    except Exception as e:
        print(f"❌ خطأ في إصلاح قاعدة البيانات: {e}")

def show_correct_chat_id_formats():
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

def get_chat_id_from_user():
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

async def test_chat_id_with_bot(chat_id: str):
    """Test if chat ID works with bot"""
    print(f"\n🧪 اختبار معرف القناة: {chat_id}")
    
    try:
        userbot = UserBot()
        
        # Test validation
        is_valid = userbot._validate_chat_id(chat_id)
        print(f"التحقق من الصحة: {'✅ صحيح' if is_valid else '❌ غير صحيح'}")
        
        if is_valid:
            # Test permissions
            try:
                has_permissions = await userbot._check_bot_permissions(chat_id)
                print(f"الصلاحيات: {'✅ متوفرة' if has_permissions else '❌ غير متوفرة'}")
                return has_permissions
            except Exception as e:
                print(f"❌ خطأ في فحص الصلاحيات: {e}")
                return False
        else:
            print("💡 لا يمكن فحص الصلاحيات - معرف القناة غير صحيح")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في اختبار معرف القناة: {e}")
        return False

async def main():
    """Main function"""
    print("🚀 فحص وإصلاح معرفات القنوات في قاعدة البيانات")
    print("=" * 80)
    
    # Show correct formats
    show_correct_chat_id_formats()
    
    # Help user get correct chat ID
    get_chat_id_from_user()
    
    # Scan database
    invalid_chat_ids = scan_database_for_invalid_chat_ids()
    
    # Show results
    show_invalid_chat_ids(invalid_chat_ids)
    
    if invalid_chat_ids:
        print("\n🔧 هل تريد إصلاح معرفات القنوات غير الصحيحة؟")
        choice = input("أدخل 'y' للموافقة أو أي مفتاح آخر للإلغاء: ").strip().lower()
        
        if choice == 'y':
            fix_chat_id_in_database()
        else:
            print("⏭️ تم إلغاء عملية الإصلاح")
    
    # Test specific chat ID
    print("\n🧪 اختبار معرف قناة محدد...")
    test_chat_id = input("أدخل معرف القناة لاختباره: ").strip()
    
    if test_chat_id:
        await test_chat_id_with_bot(test_chat_id)
    
    print("\n" + "=" * 80)
    print("✅ انتهى فحص وإصلاح معرفات القنوات")

if __name__ == "__main__":
    asyncio.run(main())