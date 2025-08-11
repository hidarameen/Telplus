#!/usr/bin/env python3
"""
Test script to debug signature matching specifically
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from userbot_service.userbot import UserbotService
from database.database import Database

async def test_signature_matching():
    print("🧪 اختبار مطابقة التوقيع للمشرف H...")
    
    # Initialize database and userbot service
    db = Database()
    userbot = UserbotService()
    userbot.db = db
    
    task_id = 7
    author_signature = "H"
    
    print(f"📋 اختبار التوقيع: '{author_signature}' للمهمة {task_id}")
    
    # Get admin filters directly from database
    admin_filters = db.get_admin_filters(task_id)
    print(f"📝 عدد فلاتر المشرفين: {len(admin_filters) if admin_filters else 0}")
    
    if admin_filters:
        print("\n👥 قائمة المشرفين:")
        for i, admin in enumerate(admin_filters, 1):
            admin_name = admin.get('admin_first_name', '').strip()
            admin_username = admin.get('admin_username', '').strip()
            is_allowed = admin.get('is_allowed', True)
            print(f"  {i}. اسم='{admin_name}', مستخدم='{admin_username}', مسموح={is_allowed}")
            
            # Test matching logic manually
            name_match = admin_name and (
                author_signature.lower() == admin_name.lower() or
                author_signature.lower() in admin_name.lower() or
                admin_name.lower() in author_signature.lower()
            )
            
            username_match = admin_username and (
                author_signature.lower() == admin_username.lower() or
                author_signature.lower() in admin_username.lower()
            )
            
            print(f"     🔍 تطابق الاسم: {name_match} ('{author_signature}' vs '{admin_name}')")
            print(f"     🔍 تطابق المستخدم: {username_match} ('{author_signature}' vs '{admin_username}')")
            
            if name_match or username_match:
                print(f"     {'🚫' if not is_allowed else '✅'} تطابق! {'محظور' if not is_allowed else 'مسموح'}")
                if admin_name == "H":
                    print(f"     ⭐ هذا هو المشرف H المطلوب!")
    
    print(f"\n🧪 اختبار دالة _check_admin_by_signature...")
    try:
        result = await userbot._check_admin_by_signature(task_id, author_signature)
        print(f"🚨 نتيجة الدالة: {result} (True=محظور, False=مسموح)")
    except Exception as e:
        print(f"❌ خطأ في دالة _check_admin_by_signature: {e}")

if __name__ == "__main__":
    asyncio.run(test_signature_matching())