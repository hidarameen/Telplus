#!/usr/bin/env python3
"""
اختبار سريع لإصلاح معالجات القوالب
"""

import sys
import os

# إضافة المسار للوحدات
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot_package'))

def test_template_parsing():
    """اختبار تحليل بيانات القوالب"""
    print("🔍 اختبار تحليل بيانات القوالب")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        "select_audio_template_7",
        "set_audio_template_7_default",
        "set_audio_template_7_enhanced",
        "set_audio_template_7_minimal",
        "set_audio_template_7_professional",
        "set_audio_template_7_custom"
    ]
    
    for data in test_cases:
        print(f"\n📋 اختبار: {data}")
        
        if data.startswith("select_audio_template_"):
            try:
                task_id = int(data.replace("select_audio_template_", ""))
                print(f"✅ select_audio_template: task_id = {task_id}")
            except ValueError as e:
                print(f"❌ خطأ في select_audio_template: {e}")
        
        elif data.startswith("set_audio_template_"):
            try:
                # Extract task_id and template_name from "set_audio_template_7_default"
                remaining = data.replace("set_audio_template_", "")
                parts = remaining.split("_", 1)
                if len(parts) >= 2:
                    task_id = int(parts[0])
                    template_name = parts[1]
                    print(f"✅ set_audio_template: task_id = {task_id}, template_name = {template_name}")
                else:
                    print(f"❌ خطأ في set_audio_template: لا يمكن تحليل البيانات")
            except ValueError as e:
                print(f"❌ خطأ في set_audio_template: {e}")

def test_old_parsing_method():
    """اختبار الطريقة القديمة (المعطلة)"""
    print("\n🔍 اختبار الطريقة القديمة (المعطلة)")
    print("=" * 50)
    
    data = "select_audio_template_7"
    print(f"📋 اختبار: {data}")
    
    # الطريقة القديمة المعطلة
    parts = data.split("_")
    print(f"🔍 parts = {parts}")
    print(f"🔍 parts[2] = {parts[2]}")
    
    try:
        task_id = int(parts[2])  # هذا سيفشل لأن parts[2] = "template"
        print(f"✅ task_id = {task_id}")
    except ValueError as e:
        print(f"❌ خطأ متوقع: {e}")

if __name__ == "__main__":
    print("🔧 اختبار إصلاح معالجات القوالب")
    print("=" * 60)
    
    test_template_parsing()
    test_old_parsing_method()
    
    print("\n🎉 تم الانتهاء من اختبار إصلاح معالجات القوالب!")