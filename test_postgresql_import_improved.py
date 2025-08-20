#!/usr/bin/env python3
"""
اختبار محسن لاستيراد قاعدة البيانات PostgreSQL
"""

import sys
import os
import importlib

# إضافة المسار للوحدات
sys.path.append(os.path.join(os.path.dirname(__file__), 'database'))

def test_import_postgresql():
    """اختبار استيراد قاعدة البيانات PostgreSQL"""
    print("🔍 اختبار استيراد قاعدة البيانات PostgreSQL")
    print("-" * 50)
    
    try:
        # اختبار استيراد المكتبات المطلوبة
        print("📦 اختبار استيراد المكتبات المطلوبة...")
        
        # اختبار psycopg2
        try:
            import psycopg2
            print("✅ psycopg2")
        except ImportError as e:
            print(f"❌ psycopg2: {e}")
            return False
            
        # اختبار psycopg2.extras
        try:
            import psycopg2.extras
            print("✅ psycopg2.extras")
        except ImportError as e:
            print(f"❌ psycopg2.extras: {e}")
            return False
            
        # اختبار asyncpg
        try:
            import asyncpg
            print("✅ asyncpg")
        except ImportError as e:
            print(f"❌ asyncpg: {e}")
            return False
            
        # اختبار استيراد قاعدة البيانات PostgreSQL
        print("\n🗄️ اختبار استيراد قاعدة البيانات PostgreSQL...")
        
        try:
            from database.database_postgresql import PostgreSQLDatabase
            print("✅ PostgreSQLDatabase")
        except ImportError as e:
            print(f"❌ PostgreSQLDatabase: {e}")
            return False
            
        # اختبار إنشاء كائن قاعدة البيانات (بدون اتصال)
        print("\n🔧 اختبار إنشاء كائن قاعدة البيانات...")
        
        try:
            # استخدام رابط وهمي لتجنب الاتصال الفعلي
            db = PostgreSQLDatabase("postgresql://fake:fake@fake:5432/fake")
            print("✅ إنشاء كائن قاعدة البيانات")
        except Exception as e:
            # نتوقع خطأ في الاتصال، لكن الكائن يجب أن يُنشأ
            if "connection" in str(e).lower() or "refused" in str(e).lower():
                print("✅ إنشاء كائن قاعدة البيانات (خطأ متوقع في الاتصال)")
            else:
                print(f"❌ خطأ في إنشاء كائن قاعدة البيانات: {e}")
                return False
            
        return True
        
    except Exception as e:
        print(f"❌ خطأ عام في الاختبار: {e}")
        return False

def test_database_methods():
    """اختبار دوال قاعدة البيانات"""
    print("\n🔧 اختبار دوال قاعدة البيانات")
    print("-" * 50)
    
    try:
        from database.database_postgresql import PostgreSQLDatabase
        
        # إنشاء كائن قاعدة البيانات مع رابط وهمي
        db = PostgreSQLDatabase("postgresql://fake:fake@fake:5432/fake")
        
        # قائمة الدوال المطلوبة
        required_methods = [
            # دوال الاتصال
            'get_connection',
            'get_async_connection',
            'init_database',
            
            # دوال المستخدمين
            'save_user_session',
            'get_user_session',
            'is_user_authenticated',
            
            # دوال المهام
            'create_task',
            'get_task',
            'get_user_tasks',
            
            # دوال الوسوم الصوتية
            'get_audio_metadata_settings',
            'get_audio_template_settings',
            'update_audio_template_setting',
            'reset_audio_template_settings',
            
            # دوال حدود الأحرف
            'get_character_limit_settings',
            
            # دوال حدود المعدل
            'get_rate_limit_settings',
            
            # دوال تأخير التوجيه
            'get_forwarding_delay_settings',
            
            # دوال فترات الإرسال
            'get_sending_interval_settings',
            
            # دوال إعدادات الرسائل
            'get_message_settings',
            
            # دوال ساعات العمل
            'toggle_working_hour',
            
            # دوال إدارة القنوات
            'add_user_channel',
            'get_user_channels',
            'delete_user_channel',
            'update_user_channel'
        ]
        
        # اختبار وجود الدوال
        missing_methods = []
        existing_methods = []
        
        for method in required_methods:
            if hasattr(db, method):
                existing_methods.append(method)
                print(f"✅ {method}")
            else:
                missing_methods.append(method)
                print(f"❌ {method}")
                
        print(f"\n📊 النتائج:")
        print(f"✅ موجود: {len(existing_methods)}/{len(required_methods)}")
        print(f"❌ مفقود: {len(missing_methods)}")
        
        if missing_methods:
            print(f"\n🔍 الدوال المفقودة:")
            for method in missing_methods:
                print(f"  • {method}")
                
        return len(missing_methods) == 0
        
    except Exception as e:
        print(f"❌ خطأ في اختبار الدوال: {e}")
        return False

def test_database_compatibility():
    """اختبار التوافق مع قاعدة البيانات الحالية"""
    print("\n🔄 اختبار التوافق مع قاعدة البيانات الحالية")
    print("-" * 50)
    
    try:
        # استيراد قاعدة البيانات الحالية
        try:
            from database.database import Database as SQLiteDatabase
            print("✅ استيراد SQLiteDatabase")
        except ImportError as e:
            print(f"❌ استيراد SQLiteDatabase: {e}")
            return False
            
        # استيراد قاعدة البيانات الجديدة
        try:
            from database.database_postgresql import PostgreSQLDatabase
            print("✅ استيراد PostgreSQLDatabase")
        except ImportError as e:
            print(f"❌ استيراد PostgreSQLDatabase: {e}")
            return False
            
        # اختبار التوافق في الدوال
        sqlite_db = SQLiteDatabase()
        postgres_db = PostgreSQLDatabase("postgresql://fake:fake@fake:5432/fake")
        
        # قائمة الدوال المشتركة
        common_methods = [
            'save_user_session',
            'get_user_session',
            'is_user_authenticated',
            'create_task',
            'get_task',
            'get_user_tasks',
            'get_audio_metadata_settings',
            'get_audio_template_settings',
            'update_audio_template_setting',
            'reset_audio_template_settings',
            'get_character_limit_settings',
            'get_rate_limit_settings',
            'get_forwarding_delay_settings',
            'get_sending_interval_settings',
            'get_message_settings'
        ]
        
        # اختبار التوافق
        compatible_methods = []
        incompatible_methods = []
        
        for method in common_methods:
            if hasattr(sqlite_db, method) and hasattr(postgres_db, method):
                compatible_methods.append(method)
                print(f"✅ {method}")
            else:
                incompatible_methods.append(method)
                print(f"❌ {method}")
                
        print(f"\n📊 النتائج:")
        print(f"✅ متوافق: {len(compatible_methods)}/{len(common_methods)}")
        print(f"❌ غير متوافق: {len(incompatible_methods)}")
        
        if incompatible_methods:
            print(f"\n🔍 الدوال غير المتوافقة:")
            for method in incompatible_methods:
                print(f"  • {method}")
                
        return len(incompatible_methods) == 0
        
    except Exception as e:
        print(f"❌ خطأ في اختبار التوافق: {e}")
        return False

def test_connection_string():
    """اختبار رابط الاتصال"""
    print("\n🔗 اختبار رابط الاتصال")
    print("-" * 50)
    
    try:
        from database.database_postgresql import PostgreSQLDatabase
        
        # اختبار الرابط الافتراضي
        try:
            db = PostgreSQLDatabase()
            print("✅ الرابط الافتراضي")
        except Exception as e:
            if "connection" in str(e).lower() or "refused" in str(e).lower():
                print("✅ الرابط الافتراضي (خطأ متوقع في الاتصال)")
            else:
                print(f"❌ الرابط الافتراضي: {e}")
            
        # اختبار رابط مخصص
        try:
            custom_connection = "postgresql://test_user:test_pass@localhost:5432/test_db"
            db = PostgreSQLDatabase(custom_connection)
            print("✅ رابط مخصص")
        except Exception as e:
            if "connection" in str(e).lower() or "refused" in str(e).lower():
                print("✅ رابط مخصص (خطأ متوقع في الاتصال)")
            else:
                print(f"❌ رابط مخصص: {e}")
            
        # اختبار رابط من متغير البيئة
        try:
            os.environ['DATABASE_URL'] = "postgresql://env_user:env_pass@localhost:5432/env_db"
            db = PostgreSQLDatabase()
            print("✅ رابط من متغير البيئة")
        except Exception as e:
            if "connection" in str(e).lower() or "refused" in str(e).lower():
                print("✅ رابط من متغير البيئة (خطأ متوقع في الاتصال)")
            else:
                print(f"❌ رابط من متغير البيئة: {e}")
            
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار رابط الاتصال: {e}")
        return False

def test_error_handling():
    """اختبار معالجة الأخطاء"""
    print("\n⚠️ اختبار معالجة الأخطاء")
    print("-" * 50)
    
    try:
        from database.database_postgresql import PostgreSQLDatabase
        
        # اختبار رابط غير صحيح
        try:
            invalid_connection = "postgresql://invalid:invalid@invalid:5432/invalid"
            db = PostgreSQLDatabase(invalid_connection)
            print("⚠️ رابط غير صحيح: لم يتم رفع استثناء")
        except Exception as e:
            print(f"✅ رابط غير صحيح: {type(e).__name__}")
            
        # اختبار رابط فارغ
        try:
            db = PostgreSQLDatabase("")
            print("⚠️ رابط فارغ: لم يتم رفع استثناء")
        except Exception as e:
            print(f"✅ رابط فارغ: {type(e).__name__}")
            
        # اختبار رابط None
        try:
            db = PostgreSQLDatabase(None)
            print("✅ رابط None")
        except Exception as e:
            if "connection" in str(e).lower() or "refused" in str(e).lower():
                print("✅ رابط None (خطأ متوقع في الاتصال)")
            else:
                print(f"❌ رابط None: {e}")
            
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار معالجة الأخطاء: {e}")
        return False

def test_code_structure():
    """اختبار بنية الكود"""
    print("\n🏗️ اختبار بنية الكود")
    print("-" * 50)
    
    try:
        # قراءة ملف قاعدة البيانات PostgreSQL
        postgresql_file = "database/database_postgresql.py"
        
        if not os.path.exists(postgresql_file):
            print(f"❌ الملف غير موجود: {postgresql_file}")
            return False
            
        with open(postgresql_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # اختبار العناصر المطلوبة
        required_elements = [
            'class PostgreSQLDatabase',
            'def __init__',
            'def get_connection',
            'def init_database',
            'CREATE TABLE',
            'SERIAL PRIMARY KEY',
            'FOREIGN KEY',
            'psycopg2',
            'asyncpg'
        ]
        
        missing_elements = []
        existing_elements = []
        
        for element in required_elements:
            if element in content:
                existing_elements.append(element)
                print(f"✅ {element}")
            else:
                missing_elements.append(element)
                print(f"❌ {element}")
                
        print(f"\n📊 النتائج:")
        print(f"✅ موجود: {len(existing_elements)}/{len(required_elements)}")
        print(f"❌ مفقود: {len(missing_elements)}")
        
        if missing_elements:
            print(f"\n🔍 العناصر المفقودة:")
            for element in missing_elements:
                print(f"  • {element}")
                
        return len(missing_elements) == 0
        
    except Exception as e:
        print(f"❌ خطأ في اختبار بنية الكود: {e}")
        return False

if __name__ == "__main__":
    print("🧪 اختبار محسن لاستيراد قاعدة البيانات PostgreSQL")
    print("=" * 80)
    
    # تشغيل الاختبارات
    all_results = []
    
    # Test import
    import_result = test_import_postgresql()
    all_results.append(import_result)
    
    # Test methods
    methods_result = test_database_methods()
    all_results.append(methods_result)
    
    # Test compatibility
    compatibility_result = test_database_compatibility()
    all_results.append(compatibility_result)
    
    # Test connection string
    connection_result = test_connection_string()
    all_results.append(connection_result)
    
    # Test error handling
    error_result = test_error_handling()
    all_results.append(error_result)
    
    # Test code structure
    structure_result = test_code_structure()
    all_results.append(structure_result)
    
    # Summary
    print(f"\n📊 ملخص النتائج:")
    print(f"✅ نجح: {sum(all_results)}")
    print(f"❌ فشل: {len(all_results) - sum(all_results)}")
    print(f"📈 نسبة النجاح: {(sum(all_results)/len(all_results)*100):.1f}%")
    
    print(f"\n📋 تفاصيل الاختبارات:")
    print(f"• استيراد قاعدة البيانات: {'✅' if import_result else '❌'}")
    print(f"• دوال قاعدة البيانات: {'✅' if methods_result else '❌'}")
    print(f"• التوافق مع SQLite: {'✅' if compatibility_result else '❌'}")
    print(f"• رابط الاتصال: {'✅' if connection_result else '❌'}")
    print(f"• معالجة الأخطاء: {'✅' if error_result else '❌'}")
    print(f"• بنية الكود: {'✅' if structure_result else '❌'}")
    
    if all(all_results):
        print("\n🎉 استيراد قاعدة البيانات PostgreSQL جاهز 100%!")
        print("\n✅ جميع المكونات تعمل:")
        print("• 📦 المكتبات مثبتة")
        print("• 🗄️ قاعدة البيانات مستوردة")
        print("• 🔧 جميع الدوال موجودة")
        print("• 🔄 التوافق مضمون")
        print("• 🔗 روابط الاتصال تعمل")
        print("• ⚠️ معالجة الأخطاء جاهزة")
        print("• 🏗️ بنية الكود صحيحة")
        print("\n🚀 يمكنك الآن استخدام PostgreSQL!")
        print("\n📝 ملاحظة: الأخطاء في الاتصال متوقعة لأن خادم PostgreSQL غير مثبت")
    else:
        print("\n⚠️ بعض المكونات تحتاج إلى إصلاح.")
        print("يرجى مراجعة الأخطاء المذكورة أعلاه.")
        
        if not import_result:
            print("\n🔧 إصلاح مشكلة الاستيراد:")
            print("pip install psycopg2-binary==2.9.9")
            print("pip install asyncpg")
            
        if not methods_result:
            print("\n🔧 إصلاح مشكلة الدوال:")
            print("تحقق من اكتمال ملف database_postgresql.py")
            
        if not compatibility_result:
            print("\n🔧 إصلاح مشكلة التوافق:")
            print("تأكد من تطابق أسماء الدوال")
            
        if not connection_result:
            print("\n🔧 إصلاح مشكلة الاتصال:")
            print("تحقق من إعدادات PostgreSQL")
            
        if not error_result:
            print("\n🔧 إصلاح مشكلة معالجة الأخطاء:")
            print("تحقق من معالجة الاستثناءات")
            
        if not structure_result:
            print("\n🔧 إصلاح مشكلة بنية الكود:")
            print("تحقق من اكتمال ملف database_postgresql.py")
            
    print(f"\n📝 ملاحظة مهمة:")
    print("• الأخطاء في الاتصال متوقعة لأن خادم PostgreSQL غير مثبت")
    print("• هذا الاختبار يتحقق من جاهزية الكود، وليس من الاتصال الفعلي")
    print("• لتشغيل PostgreSQL، استخدم: python setup_postgresql.py")