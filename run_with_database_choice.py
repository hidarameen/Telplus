#!/usr/bin/env python3
"""
سكريبت تشغيل البوت مع دعم اختيار قاعدة البيانات
"""

import os
import sys
import argparse
from dotenv import load_dotenv

def load_environment(database_type=None):
    """تحميل الإعدادات البيئية"""
    # تحميل ملف .env
    load_dotenv()
    
    # تحديد نوع قاعدة البيانات
    if database_type:
        os.environ['DATABASE_TYPE'] = database_type
        print(f"🗄️ تم تحديد نوع قاعدة البيانات: {database_type}")
    
    # التحقق من الإعدادات المطلوبة
    required_vars = ['BOT_TOKEN', 'API_ID', 'API_HASH']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ متغيرات بيئية مفقودة: {', '.join(missing_vars)}")
        print("يرجى تحديث ملف .env")
        return False
    
    return True

def test_database_connection():
    """اختبار الاتصال بقاعدة البيانات"""
    print("\n🔍 اختبار الاتصال بقاعدة البيانات...")
    
    try:
        from database import DatabaseFactory
        
        # اختبار الاتصال
        result = DatabaseFactory.test_connection()
        
        if result['success']:
            print(f"✅ {result['message']}")
            return True
        else:
            print(f"❌ {result['message']}")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في اختبار الاتصال: {e}")
        return False

def show_database_info():
    """عرض معلومات قاعدة البيانات"""
    try:
        from database import DatabaseFactory
        
        db_info = DatabaseFactory.get_database_info()
        
        print(f"\n📊 معلومات قاعدة البيانات:")
        print(f"• النوع: {db_info['name']}")
        print(f"• المعرف: {db_info['type']}")
        
        if db_info['connection_string']:
            print(f"• رابط الاتصال: {db_info['connection_string']}")
        if db_info['file_path']:
            print(f"• مسار الملف: {db_info['file_path']}")
            
    except Exception as e:
        print(f"❌ خطأ في عرض معلومات قاعدة البيانات: {e}")

def run_bot():
    """تشغيل البوت"""
    print("\n🚀 تشغيل البوت...")
    
    try:
        from bot_package.bot_simple import SimpleTelegramBot
        from bot_package.config import BOT_TOKEN, API_ID, API_HASH
        
        # إنشاء البوت
        bot = SimpleTelegramBot()
        
        # تشغيل البوت
        import asyncio
        asyncio.run(bot.run())
        
    except Exception as e:
        print(f"❌ خطأ في تشغيل البوت: {e}")
        return False
    
    return True

def main():
    """الدالة الرئيسية"""
    parser = argparse.ArgumentParser(description='تشغيل البوت مع دعم اختيار قاعدة البيانات')
    parser.add_argument('--database', '-d', 
                       choices=['sqlite', 'postgresql'], 
                       help='نوع قاعدة البيانات (sqlite أو postgresql)')
    parser.add_argument('--test', '-t', 
                       action='store_true', 
                       help='اختبار الاتصال بقاعدة البيانات فقط')
    parser.add_argument('--info', '-i', 
                       action='store_true', 
                       help='عرض معلومات قاعدة البيانات')
    
    args = parser.parse_args()
    
    print("🤖 تشغيل البوت مع دعم قاعدة البيانات")
    print("=" * 50)
    
    # تحميل الإعدادات البيئية
    if not load_environment(args.database):
        sys.exit(1)
    
    # عرض معلومات قاعدة البيانات
    show_database_info()
    
    # اختبار الاتصال
    if args.test:
        if test_database_connection():
            print("\n✅ اختبار الاتصال ناجح!")
        else:
            print("\n❌ اختبار الاتصال فشل!")
        return
    
    # عرض المعلومات فقط
    if args.info:
        return
    
    # اختبار الاتصال قبل التشغيل
    if not test_database_connection():
        print("\n❌ فشل في الاتصال بقاعدة البيانات")
        print("يرجى التحقق من الإعدادات")
        sys.exit(1)
    
    # تشغيل البوت
    if not run_bot():
        sys.exit(1)

if __name__ == "__main__":
    main()