#!/usr/bin/env python3
"""
اختبار فلتر المشرفين بالتوقيع
"""

import re

def extract_signature_from_message(message_text: str) -> str:
    """Extract sender signature from message text"""
    try:
        # Common signature patterns
        signature_patterns = [
            r'[\n\r]~\s*(.+?)[\n\r]',  # ~Name
            r'[\n\r]-\s*(.+?)[\n\r]',  # -Name
            r'[\n\r]—\s*(.+?)[\n\r]',  # —Name
            r'[\n\r]🔸\s*(.+?)[\n\r]', # 🔸Name
            r'[\n\r]📝\s*(.+?)[\n\r]', # 📝Name
            r'[\n\r]✍️\s*(.+?)[\n\r]', # ✍️Name
        ]
        
        for pattern in signature_patterns:
            matches = re.findall(pattern, message_text)
            if matches:
                signature = matches[-1].strip()  # Get last match (usually at end)
                if len(signature) > 2 and len(signature) < 50:  # Reasonable name length
                    print(f"✅ تم استخراج التوقيع بالنمط: '{signature}'")
                    return signature
        
        # Pattern 2: Last line starting with specific characters
        lines = message_text.strip().split('\n')
        if lines:
            last_line = lines[-1].strip()
            if last_line.startswith(('~', '-', '—', '🔸', '📝', '✍️')):
                signature = last_line[1:].strip()
                if len(signature) > 2 and len(signature) < 50:
                    print(f"✅ تم استخراج التوقيع من السطر الأخير: '{signature}'")
                    return signature
        
        return None
        
    except Exception as e:
        print(f"❌ خطأ في استخراج التوقيع: {e}")
        return None

def test_signature_extraction():
    """Test signature extraction with different message formats"""
    print("🧪 اختبار استخراج التوقيع من الرسائل\n")
    
    test_messages = [
        "هذا نص الرسالة العادي\n~أحمد محمد\n",
        "رسالة مهمة للجميع\n-سارة أحمد",
        "إعلان مهم\n🔸محمد علي\n",
        "خبر جديد\n📝فاطمة حسن",
        "تحديث عاجل\n✍️علي محمود\nنهاية الرسالة",
        "رسالة بدون توقيع",
        "رسالة مع توقيع قصير\n~س",  # Should be rejected (too short)
        "رسالة مع توقيع طويل جداً\n~" + "أ" * 60,  # Should be rejected (too long)
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"📝 اختبار {i}:")
        print(f"النص: {repr(message)}")
        signature = extract_signature_from_message(message)
        if signature:
            print(f"✅ التوقيع المستخرج: '{signature}'")
        else:
            print("❌ لم يتم العثور على توقيع")
        print("-" * 50)

def test_admin_matching():
    """Test admin name matching logic"""
    print("\n🧪 اختبار مطابقة أسماء المشرفين\n")
    
    # Simulated admin list
    admin_filters = [
        {'admin_first_name': 'أحمد محمد', 'admin_username': 'ahmed123', 'is_allowed': False},
        {'admin_first_name': 'سارة أحمد', 'admin_username': 'sara_a', 'is_allowed': True},
        {'admin_first_name': 'محمد علي', 'admin_username': '', 'is_allowed': False},
    ]
    
    test_signatures = ['أحمد محمد', 'أحمد', 'محمد', 'سارة', 'علي محمود', 'ahmed123']
    
    for signature in test_signatures:
        print(f"🔍 اختبار التوقيع: '{signature}'")
        
        matched = False
        for admin in admin_filters:
            admin_name = admin.get('admin_first_name', '').strip()
            admin_username = admin.get('admin_username', '').strip()
            is_allowed = admin.get('is_allowed', True)
            
            # Match by name or username
            if (admin_name and signature.lower() in admin_name.lower()) or \
               (admin_username and signature.lower() in admin_username.lower()):
                
                status = "مسموح" if is_allowed else "محظور"
                print(f"✅ تطابق مع المشرف '{admin_name}' ({admin_username}) - {status}")
                matched = True
                break
        
        if not matched:
            print("❌ لا يوجد تطابق - سيتم السماح")
        print("-" * 40)

if __name__ == "__main__":
    test_signature_extraction()
    test_admin_matching()
    print("\n🎉 اكتمال الاختبارات!")