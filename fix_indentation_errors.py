#!/usr/bin/env python3
"""
فحص وإصلاح أخطاء المسافات البادئة في ملفات Python
"""

import os
import re
import logging

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_file_indentation(file_path):
    """فحص المسافات البادئة في ملف Python"""
    logger.info(f"🔍 فحص المسافات البادئة في: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        issues = []
        line_number = 0
        
        for line in lines:
            line_number += 1
            
            # فحص السطور الفارغة المتتالية
            if line.strip() == '':
                # فحص السطر التالي
                if line_number < len(lines):
                    next_line = lines[line_number]
                    if next_line.strip() != '' and not next_line.startswith('#'):
                        # فحص إذا كان السطر التالي له مسافات بادئة صحيحة
                        if next_line.startswith(' ') or next_line.startswith('\t'):
                            # هذا قد يكون مشكلة
                            issues.append(f"سطر {line_number}: سطر فارغ متبوع بسطر له مسافات بادئة")
            
            # فحص المسافات البادئة المختلطة
            if '\t' in line and '    ' in line:
                issues.append(f"سطر {line_number}: مسافات بادئة مختلطة (tabs و spaces)")
            
            # فحص المسافات البادئة غير الصحيحة
            if line.strip() != '' and not line.startswith('#'):
                # حساب المسافات البادئة
                indent_count = len(line) - len(line.lstrip())
                if indent_count % 4 != 0:
                    issues.append(f"سطر {line_number}: مسافات بادئة غير صحيحة ({indent_count} spaces)")
        
        if issues:
            logger.warning(f"⚠️ تم العثور على {len(issues)} مشكلة في المسافات البادئة:")
            for issue in issues:
                logger.warning(f"   {issue}")
            return False
        else:
            logger.info("✅ لا توجد مشاكل في المسافات البادئة")
            return True
            
    except Exception as e:
        logger.error(f"❌ خطأ في فحص الملف {file_path}: {e}")
        return False

def fix_indentation_issues(file_path):
    """إصلاح مشاكل المسافات البادئة"""
    logger.info(f"🔧 إصلاح مشاكل المسافات البادئة في: {file_path}")
    
    try:
        # إنشاء نسخة احتياطية
        backup_path = f"{file_path}.backup"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"💾 تم إنشاء نسخة احتياطية: {backup_path}")
        
        # قراءة الملف كسطور
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        fixed_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # حذف السطور الفارغة المتتالية
            if line.strip() == '':
                # فحص السطر التالي
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if next_line.strip() == '':
                        # سطرين فارغين متتاليين، احذف أحدهما
                        logger.info(f"🔄 حذف سطر فارغ إضافي في السطر {i + 1}")
                        i += 1
                        continue
            
            # إصلاح المسافات البادئة المختلطة
            if '\t' in line:
                # استبدال tabs بـ 4 spaces
                line = line.replace('\t', '    ')
                logger.info(f"🔄 استبدال tabs بـ spaces في السطر {i + 1}")
            
            fixed_lines.append(line)
            i += 1
        
        # كتابة الملف المُصلح
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(fixed_lines)
        
        logger.info("✅ تم إصلاح مشاكل المسافات البادئة")
        return True
        
    except Exception as e:
        logger.error(f"❌ خطأ في إصلاح الملف {file_path}: {e}")
        return False

def validate_python_file(file_path):
    """التحقق من صحة ملف Python"""
    logger.info(f"🧪 التحقق من صحة ملف Python: {file_path}")
    
    try:
        import py_compile
        py_compile.compile(file_path, doraise=True)
        logger.info("✅ الملف صحيح من ناحية التركيب")
        return True
    except py_compile.PyCompileError as e:
        logger.error(f"❌ خطأ في التركيب: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ خطأ في التحقق: {e}")
        return False

def main():
    """الدالة الرئيسية"""
    logger.info("🚀 بدء فحص وإصلاح أخطاء المسافات البادئة...")
    
    # قائمة الملفات المهمة
    important_files = [
        'userbot_service/userbot.py',
        'main.py',
        'bot_package/bot_simple.py',
        'database/database.py',
        'database/database_sqlite.py'
    ]
    
    all_fixed = True
    
    for file_path in important_files:
        if os.path.exists(file_path):
            logger.info(f"\n{'='*50}")
            logger.info(f"📁 فحص الملف: {file_path}")
            logger.info(f"{'='*50}")
            
            # فحص المسافات البادئة
            if not check_file_indentation(file_path):
                logger.warning("⚠️ تم العثور على مشاكل، محاولة الإصلاح...")
                
                # إصلاح المشاكل
                if fix_indentation_issues(file_path):
                    # التحقق من صحة الملف بعد الإصلاح
                    if validate_python_file(file_path):
                        logger.info("✅ تم إصلاح الملف بنجاح")
                    else:
                        logger.error("❌ فشل في إصلاح الملف")
                        all_fixed = False
                else:
                    logger.error("❌ فشل في إصلاح الملف")
                    all_fixed = False
            else:
                # التحقق من صحة الملف
                if not validate_python_file(file_path):
                    logger.error("❌ الملف يحتوي على أخطاء تركيبية")
                    all_fixed = False
        else:
            logger.warning(f"⚠️ الملف غير موجود: {file_path}")
    
    # ملخص النتائج
    logger.info(f"\n{'='*50}")
    logger.info("📋 ملخص النتائج:")
    logger.info(f"{'='*50}")
    
    if all_fixed:
        logger.info("🎉 جميع الملفات صحيحة ومُصلحة!")
    else:
        logger.error("⚠️ بعض الملفات تحتاج إلى إصلاح يدوي")
    
    return all_fixed

if __name__ == "__main__":
    main()