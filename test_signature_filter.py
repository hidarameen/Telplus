#!/usr/bin/env python3
"""
اختبار فلتر المشرفين بتوقيع المؤلف (Author Signature)
"""

def test_author_signature_matching():
    """Test author signature matching with admin filters"""
    print("🧪 اختبار مطابقة توقيع المؤلف (Author Signature)\n")
    
    # Simulated admin list from database
    admin_filters = [
        {'admin_first_name': 'أحمد محمد', 'admin_username': 'ahmed123', 'is_allowed': False},
        {'admin_first_name': 'سارة أحمد', 'admin_username': 'sara_a', 'is_allowed': True}, 
        {'admin_first_name': 'محمد علي', 'admin_username': '', 'is_allowed': False},
        {'admin_first_name': 'فاطمة حسن', 'admin_username': 'fatima_h', 'is_allowed': True},
    ]
    
    # Test author signatures from Telegram messages
    test_signatures = [
        'أحمد محمد',     # Exact match - blocked admin
        'أحمد',          # Partial match - blocked admin  
        'سارة أحمد',     # Exact match - allowed admin
        'سارة',          # Partial match - allowed admin
        'علي محمد',      # Should not match exactly
        'محمد',          # Partial match - blocked admin
        'ahmed123',      # Username match - blocked admin
        'fatima_h',      # Username match - allowed admin
        'خالد أحمد',     # No match - should allow
        '',              # Empty signature
    ]
    
    for signature in test_signatures:
        print(f"🔍 اختبار توقيع المؤلف: '{signature}'")
        
        if not signature:
            print("❌ توقيع فارغ - سيتم السماح")
            print("-" * 40)
            continue
            
        matched = False
        for admin in admin_filters:
            admin_name = admin.get('admin_first_name', '').strip()
            admin_username = admin.get('admin_username', '').strip()
            is_allowed = admin.get('is_allowed', True)
            
            # Match by name or username (exact or partial match)
            name_match = admin_name and (
                signature.lower() == admin_name.lower() or
                signature.lower() in admin_name.lower() or
                admin_name.lower() in signature.lower()
            )
            
            username_match = admin_username and (
                signature.lower() == admin_username.lower() or
                signature.lower() in admin_username.lower()
            )
            
            if name_match or username_match:
                status = "مسموح" if is_allowed else "محظور"
                match_type = "اسم" if name_match else "اسم مستخدم"
                print(f"✅ تطابق {match_type} مع المشرف '{admin_name}' ({admin_username}) - {status}")
                matched = True
                break
        
        if not matched:
            print("❌ لا يوجد تطابق - سيتم السماح")
        print("-" * 40)
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

def explain_author_signature_feature():
    """Explain Telegram Author Signature feature"""
    print("📋 شرح ميزة توقيع المؤلف (Author Signature) في تليجرام:\n")
    
    print("🔧 كيفية تفعيل الميزة:")
    print("1. في إعدادات القناة، اذهب إلى 'Edit Channel'")
    print("2. فعّل خيار 'Sign Messages'")
    print("3. الآن ستظهر أسماء المشرفين بجانب رسائلهم")
    print("")
    
    print("💡 كيف يعمل الفلتر:")
    print("- عندما ينشر مشرف في القناة مع تفعيل التوقيع")
    print("- يظهر اسم المشرف في الرسالة كـ 'post_author'")
    print("- البوت يقارن هذا الاسم مع قائمة المشرفين المحظورين")
    print("- إذا وجد تطابق → يحظر الرسالة")
    print("- إذا لم يجد تطابق → يسمح بالرسالة")
    print("")
    
    print("⚠️ متطلبات مهمة:")
    print("- يجب تفعيل 'Sign Messages' في القناة المصدر")
    print("- يعمل فقط مع القنوات، ليس المجموعات")
    print("- للمجموعات يستخدم معرف المرسل كما هو معتاد")



if __name__ == "__main__":
    explain_author_signature_feature()
    print("\n" + "="*60 + "\n")
    test_author_signature_matching()
    print("\n🎉 اكتمال الاختبارات!")