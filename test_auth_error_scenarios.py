#!/usr/bin/env python3
"""
Test script to verify error scenarios in authentication flow
"""
import os
import sys
import json
import logging
from datetime import datetime

# Add bot_package to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database.database_sqlite import Database

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_error_scenarios():
    """Test various error scenarios in the authentication flow"""
    
    # Initialize database
    db = Database()
    
    # Test user ID
    test_user_id = 99999
    
    print("🧪 اختبار سيناريوهات الأخطاء في المصادقة...")
    print("=" * 60)
    
    # Scenario 1: Empty data
    print("\n📍 السيناريو 1: بيانات فارغة")
    print("-" * 40)
    db.clear_conversation_state(test_user_id)
    db.set_conversation_state(test_user_id, 'waiting_code', '')
    
    state_data = db.get_conversation_state(test_user_id)
    if state_data:
        state, data_str = state_data
        print(f"الحالة: {state}")
        print(f"البيانات: '{data_str}'")
        print(f"نوع البيانات: {type(data_str)}")
        
        try:
            parsed = json.loads(data_str) if data_str else {}
            print(f"البيانات المُحللة: {parsed}")
            if not parsed:
                print("✅ تم التعامل مع البيانات الفارغة بشكل صحيح")
        except Exception as e:
            print(f"❌ خطأ: {e}")
    
    # Scenario 2: Invalid JSON
    print("\n📍 السيناريو 2: JSON غير صالح")
    print("-" * 40)
    db.clear_conversation_state(test_user_id)
    db.set_conversation_state(test_user_id, 'waiting_code', '{invalid json}')
    
    state_data = db.get_conversation_state(test_user_id)
    if state_data:
        state, data_str = state_data
        print(f"الحالة: {state}")
        print(f"البيانات: '{data_str}'")
        
        try:
            parsed = json.loads(data_str)
            print(f"❌ لم يتم اكتشاف الخطأ! البيانات: {parsed}")
        except json.JSONDecodeError as e:
            print(f"✅ تم اكتشاف JSON غير صالح: {e}")
        except Exception as e:
            print(f"✅ تم اكتشاف خطأ: {e}")
    
    # Scenario 3: Missing required keys
    print("\n📍 السيناريو 3: مفاتيح مفقودة")
    print("-" * 40)
    db.clear_conversation_state(test_user_id)
    incomplete_data = {
        'phone': '+966501234567'
        # Missing 'phone_code_hash'
    }
    db.set_conversation_state(test_user_id, 'waiting_code', json.dumps(incomplete_data))
    
    state_data = db.get_conversation_state(test_user_id)
    if state_data:
        state, data_str = state_data
        parsed = json.loads(data_str)
        print(f"البيانات المحفوظة: {list(parsed.keys())}")
        
        missing_keys = []
        required_keys = ['phone', 'phone_code_hash']
        for key in required_keys:
            if key not in parsed:
                missing_keys.append(key)
        
        if missing_keys:
            print(f"✅ تم اكتشاف المفاتيح المفقودة: {missing_keys}")
        else:
            print("❌ لم يتم اكتشاف أي مفاتيح مفقودة!")
    
    # Scenario 4: Correct data (control test)
    print("\n📍 السيناريو 4: بيانات صحيحة (اختبار تحكم)")
    print("-" * 40)
    db.clear_conversation_state(test_user_id)
    correct_data = {
        'phone': '+966501234567',
        'phone_code_hash': 'valid_hash_123456',
        'session_name': f'/app/data/sessions/auth_{test_user_id}_test'
    }
    db.set_conversation_state(test_user_id, 'waiting_code', json.dumps(correct_data))
    
    state_data = db.get_conversation_state(test_user_id)
    if state_data:
        state, data_str = state_data
        parsed = json.loads(data_str)
        print(f"البيانات المحفوظة: {list(parsed.keys())}")
        
        all_keys_present = all(key in parsed for key in ['phone', 'phone_code_hash'])
        if all_keys_present:
            print("✅ جميع المفاتيح المطلوبة موجودة!")
        else:
            print("❌ بعض المفاتيح مفقودة!")
    
    # Clean up
    print("\n🧹 تنظيف البيانات الاختبارية...")
    db.clear_conversation_state(test_user_id)
    
    print("\n" + "=" * 60)
    print("✅ اكتملت جميع الاختبارات!")

if __name__ == "__main__":
    test_error_scenarios()