#!/usr/bin/env python3
"""
اختبار شامل لمصنع قاعدة البيانات
"""

import os
import sys

def test_database_factory():
    """اختبار مصنع قاعدة البيانات"""
    print("🔧 اختبار مصنع قاعدة البيانات")
    print("-" * 50)
    
    try:
        from database import DatabaseFactory
        
        # اختبار إنشاء قاعدة البيانات الافتراضية (SQLite)
        print("\n📦 اختبار إنشاء قاعدة البيانات الافتراضية...")
        
        # تعيين نوع قاعدة البيانات إلى SQLite
        os.environ['DATABASE_TYPE'] = 'sqlite'
        
        try:
            db = DatabaseFactory.create_database()
            print("✅ تم إنشاء قاعدة بيانات SQLite بنجاح")
        except Exception as e:
            print(f"❌ فشل في إنشاء قاعدة بيانات SQLite: {e}")
            return False
        
        # اختبار معلومات قاعدة البيانات
        print("\n📊 اختبار معلومات قاعدة البيانات...")
        
        db_info = DatabaseFactory.get_database_info()
        print(f"✅ نوع قاعدة البيانات: {db_info['name']}")
        print(f"✅ المعرف: {db_info['type']}")
        
        if db_info['type'] != 'sqlite':
            print(f"❌ نوع قاعدة البيانات غير صحيح: {db_info['type']}")
            return False
        
        # اختبار إنشاء قاعدة بيانات PostgreSQL (إذا كانت المكتبات متوفرة)
        print("\n📦 اختبار إنشاء قاعدة بيانات PostgreSQL...")
        
        # تعيين نوع قاعدة البيانات إلى PostgreSQL
        os.environ['DATABASE_TYPE'] = 'postgresql'
        
        try:
            db = DatabaseFactory.create_database()
            print("✅ تم إنشاء قاعدة بيانات PostgreSQL بنجاح")
        except ImportError:
            print("⚠️ مكتبات PostgreSQL غير متوفرة - العودة إلى SQLite")
            # يجب أن يعود إلى SQLite تلقائياً
            db = DatabaseFactory.create_database()
            print("✅ تم العودة إلى SQLite بنجاح")
        except Exception as e:
            print(f"❌ فشل في إنشاء قاعدة بيانات PostgreSQL: {e}")
            return False
        
        # اختبار معلومات قاعدة البيانات مرة أخرى
        db_info = DatabaseFactory.get_database_info()
        print(f"✅ نوع قاعدة البيانات: {db_info['name']}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار مصنع قاعدة البيانات: {e}")
        return False

def test_database_import():
    """اختبار استيراد قاعدة البيانات"""
    print("\n📦 اختبار استيراد قاعدة البيانات")
    print("-" * 50)
    
    try:
        # اختبار استيراد get_database
        from database import get_database
        print("✅ استيراد get_database")
        
        # اختبار استيراد DatabaseFactory
        from database import DatabaseFactory
        print("✅ استيراد DatabaseFactory")
        
        # اختبار إنشاء قاعدة البيانات
        db = get_database()
        print("✅ تم إنشاء قاعدة البيانات بنجاح")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار الاستيراد: {e}")
        return False

def test_database_methods():
    """اختبار دوال قاعدة البيانات"""
    print("\n🔧 اختبار دوال قاعدة البيانات")
    print("-" * 50)
    
    try:
        from database import get_database
        
        # إنشاء قاعدة البيانات
        db = get_database()
        
        # قائمة الدوال المطلوبة
        required_methods = [
            'get_connection',
            'init_database',
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

def test_environment_variables():
    """اختبار متغيرات البيئة"""
    print("\n🌍 اختبار متغيرات البيئة")
    print("-" * 50)
    
    try:
        from database import DatabaseFactory
        
        # اختبار SQLite
        print("\n📦 اختبار SQLite...")
        os.environ['DATABASE_TYPE'] = 'sqlite'
        
        db_info = DatabaseFactory.get_database_info()
        if db_info['type'] == 'sqlite':
            print("✅ SQLite تم تحديده بشكل صحيح")
        else:
            print(f"❌ نوع قاعدة البيانات غير صحيح: {db_info['type']}")
            return False
        
        # اختبار PostgreSQL
        print("\n📦 اختبار PostgreSQL...")
        os.environ['DATABASE_TYPE'] = 'postgresql'
        
        db_info = DatabaseFactory.get_database_info()
        if db_info['type'] == 'postgresql':
            print("✅ PostgreSQL تم تحديده بشكل صحيح")
        else:
            print(f"❌ نوع قاعدة البيانات غير صحيح: {db_info['type']}")
            return False
        
        # اختبار قيمة غير معروفة
        print("\n📦 اختبار قيمة غير معروفة...")
        os.environ['DATABASE_TYPE'] = 'unknown'
        
        db_info = DatabaseFactory.get_database_info()
        if db_info['type'] == 'sqlite':
            print("✅ العودة إلى SQLite كافتراضي")
        else:
            print(f"❌ لم يتم العودة إلى SQLite: {db_info['type']}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار متغيرات البيئة: {e}")
        return False

def test_connection_strings():
    """اختبار روابط الاتصال"""
    print("\n🔗 اختبار روابط الاتصال")
    print("-" * 50)
    
    try:
        from database import DatabaseFactory
        
        # اختبار SQLite
        print("\n📦 اختبار SQLite...")
        os.environ['DATABASE_TYPE'] = 'sqlite'
        
        db_info = DatabaseFactory.get_database_info()
        if db_info['file_path'] == 'telegram_bot.db':
            print("✅ مسار ملف SQLite صحيح")
        else:
            print(f"❌ مسار ملف SQLite غير صحيح: {db_info['file_path']}")
            return False
        
        # اختبار PostgreSQL
        print("\n📦 اختبار PostgreSQL...")
        os.environ['DATABASE_TYPE'] = 'postgresql'
        
        # تعيين رابط مخصص
        custom_url = "postgresql://test:test@localhost:5432/test"
        os.environ['DATABASE_URL'] = custom_url
        
        db_info = DatabaseFactory.get_database_info()
        if db_info['connection_string'] == custom_url:
            print("✅ رابط PostgreSQL صحيح")
        else:
            print(f"❌ رابط PostgreSQL غير صحيح: {db_info['connection_string']}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار روابط الاتصال: {e}")
        return False

if __name__ == "__main__":
    print("🧪 اختبار شامل لمصنع قاعدة البيانات")
    print("=" * 80)
    
    # تشغيل الاختبارات
    all_results = []
    
    # Test database factory
    factory_result = test_database_factory()
    all_results.append(factory_result)
    
    # Test database import
    import_result = test_database_import()
    all_results.append(import_result)
    
    # Test database methods
    methods_result = test_database_methods()
    all_results.append(methods_result)
    
    # Test environment variables
    env_result = test_environment_variables()
    all_results.append(env_result)
    
    # Test connection strings
    connection_result = test_connection_strings()
    all_results.append(connection_result)
    
    # Summary
    print(f"\n📊 ملخص النتائج:")
    print(f"✅ نجح: {sum(all_results)}")
    print(f"❌ فشل: {len(all_results) - sum(all_results)}")
    print(f"📈 نسبة النجاح: {(sum(all_results)/len(all_results)*100):.1f}%")
    
    print(f"\n📋 تفاصيل الاختبارات:")
    print(f"• مصنع قاعدة البيانات: {'✅' if factory_result else '❌'}")
    print(f"• استيراد قاعدة البيانات: {'✅' if import_result else '❌'}")
    print(f"• دوال قاعدة البيانات: {'✅' if methods_result else '❌'}")
    print(f"• متغيرات البيئة: {'✅' if env_result else '❌'}")
    print(f"• روابط الاتصال: {'✅' if connection_result else '❌'}")
    
    if all(all_results):
        print("\n🎉 مصنع قاعدة البيانات جاهز 100%!")
        print("\n✅ جميع المكونات تعمل:")
        print("• 🔧 المصنع يعمل بشكل صحيح")
        print("• 📦 الاستيراد ناجح")
        print("• 🔧 جميع الدوال موجودة")
        print("• 🌍 متغيرات البيئة تعمل")
        print("• 🔗 روابط الاتصال صحيحة")
        print("\n🚀 يمكنك الآن استخدام كلا النوعين من قواعد البيانات!")
    else:
        print("\n⚠️ بعض المكونات تحتاج إلى إصلاح.")
        print("يرجى مراجعة الأخطاء المذكورة أعلاه.")
        
        if not factory_result:
            print("\n🔧 إصلاح مشكلة المصنع:")
            print("تحقق من ملف database_factory.py")
            
        if not import_result:
            print("\n🔧 إصلاح مشكلة الاستيراد:")
            print("تحقق من ملف __init__.py")
            
        if not methods_result:
            print("\n🔧 إصلاح مشكلة الدوال:")
            print("تحقق من اكتمال ملفات قاعدة البيانات")
            
        if not env_result:
            print("\n🔧 إصلاح مشكلة متغيرات البيئة:")
            print("تحقق من معالجة متغيرات البيئة")
            
        if not connection_result:
            print("\n🔧 إصلاح مشكلة روابط الاتصال:")
            print("تحقق من معالجة روابط الاتصال")
            
    print(f"\n📝 ملاحظة مهمة:")
    print("• يمكنك تحديد نوع قاعدة البيانات عبر متغير البيئة DATABASE_TYPE")
    print("• القيم المدعومة: sqlite, postgresql")
    print("• إذا لم يتم تحديد النوع، سيتم استخدام SQLite كافتراضي")