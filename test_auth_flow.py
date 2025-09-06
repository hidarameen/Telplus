#!/usr/bin/env python3
"""
Test script to verify the authentication flow is working correctly
"""
import os
import sys
import json
import sqlite3
from datetime import datetime

# Add bot_package to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database.database_sqlite import Database

def test_auth_flow():
    """Test the authentication flow by simulating the database operations"""
    
    # Initialize database
    db = Database()
    
    # Test user ID
    test_user_id = 12345
    
    print("🧪 اختبار تدفق المصادقة...")
    print("-" * 50)
    
    # Step 1: Clear any existing state
    print("1️⃣ مسح أي حالة سابقة...")
    db.clear_conversation_state(test_user_id)
    
    # Step 2: Simulate phone number entry
    print("2️⃣ محاكاة إدخال رقم الهاتف...")
    db.set_conversation_state(test_user_id, 'waiting_phone', '')
    
    # Step 3: Simulate storing auth data after phone verification
    print("3️⃣ محاكاة حفظ بيانات المصادقة بعد إرسال رمز التحقق...")
    auth_data = {
        'phone': '+966501234567',
        'phone_code_hash': 'test_hash_123456',
        'session_name': f'/app/data/sessions/auth_{test_user_id}_{int(datetime.now().timestamp())}'
    }
    auth_data_json = json.dumps(auth_data)
    print(f"   البيانات المحفوظة: {list(auth_data.keys())}")
    db.set_conversation_state(test_user_id, 'waiting_code', auth_data_json)
    
    # Step 4: Read back the state
    print("4️⃣ قراءة الحالة المحفوظة...")
    state_data = db.get_conversation_state(test_user_id)
    
    if state_data:
        state, data_str = state_data
        print(f"   الحالة: {state}")
        print(f"   نوع البيانات: {type(data_str)}")
        
        # Try to parse the data
        try:
            if isinstance(data_str, dict):
                parsed_data = data_str
            else:
                parsed_data = json.loads(data_str) if data_str else {}
            
            print(f"   البيانات المُحللة: {list(parsed_data.keys())}")
            
            # Verify required keys
            if 'phone' in parsed_data and 'phone_code_hash' in parsed_data:
                print("   ✅ جميع المفاتيح المطلوبة موجودة!")
                print(f"   - الهاتف: {parsed_data['phone']}")
                print(f"   - hash الكود: {parsed_data['phone_code_hash'][:20]}...")
            else:
                print("   ❌ مفاتيح مفقودة!")
                print(f"   المفاتيح الموجودة: {list(parsed_data.keys())}")
                
        except Exception as e:
            print(f"   ❌ خطأ في تحليل البيانات: {e}")
            print(f"   البيانات الأصلية: {data_str}")
    else:
        print("   ❌ لا توجد حالة محفوظة!")
    
    # Step 5: Clean up
    print("\n5️⃣ تنظيف البيانات الاختبارية...")
    db.clear_conversation_state(test_user_id)
    
    print("-" * 50)
    print("✅ اكتمل الاختبار!")

if __name__ == "__main__":
    test_auth_flow()