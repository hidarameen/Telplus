#!/usr/bin/env python3
"""
اختبار محسن لجميع الجداول والوظائف في PostgreSQL
"""

import os
import sys

def test_all_tables():
    """اختبار جميع الجداول المطلوبة"""
    print("🗄️ اختبار جميع الجداول في PostgreSQL")
    print("-" * 50)
    
    try:
        # قراءة ملف قاعدة البيانات PostgreSQL
        with open('database/database_postgresql.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # قائمة جميع الجداول المطلوبة
        required_tables = [
            # الجداول الأساسية
            'tasks',
            'task_sources', 
            'task_targets',
            'user_settings',
            'user_sessions',
            'conversation_states',
            
            # جداول الفلاتر
            'task_media_filters',
            'task_word_filters',
            'word_filter_entries',
            'task_text_replacements',
            'text_replacement_entries',
            'task_headers',
            'task_footers',
            'task_inline_buttons',
            
            # جداول الإعدادات
            'task_message_settings',
            'task_forwarding_settings',
            'task_advanced_filters',
            'task_day_filters',
            'task_working_hours',
            'task_working_hours_schedule',
            'task_language_filters',
            'task_admin_filters',
            'task_duplicate_settings',
            'task_inline_button_filters',
            'task_forwarded_message_filters',
            
            # جداول معالجة النصوص
            'task_text_cleaning_settings',
            'task_text_cleaning_keywords',
            'task_text_formatting_settings',
            
            # جداول الترجمة والعلامة المائية
            'task_translation_settings',
            'task_watermark_settings',
            
            # جداول الوسوم الصوتية
            'task_audio_metadata_settings',
            'task_audio_template_settings',
            
            # جداول حدود الأحرف والمعدل
            'task_character_limit_settings',
            'task_rate_limit_settings',
            'task_forwarding_delay_settings',
            'task_sending_interval_settings',
            
            # جداول التتبع والتسجيل
            'message_mappings',
            'pending_messages',
            'forwarded_messages_log',
            'rate_limit_tracking',
            'message_duplicates',
            
            # جداول إدارة القنوات
            'user_channels'
        ]
        
        # اختبار وجود الجداول في الكود
        missing_tables = []
        existing_tables = []
        
        for table in required_tables:
            if f'CREATE TABLE IF NOT EXISTS {table}' in content:
                existing_tables.append(table)
                print(f"✅ {table}")
            else:
                missing_tables.append(table)
                print(f"❌ {table}")
                
        print(f"\n📊 النتائج:")
        print(f"✅ موجود: {len(existing_tables)}/{len(required_tables)}")
        print(f"❌ مفقود: {len(missing_tables)}")
        
        if missing_tables:
            print(f"\n🔍 الجداول المفقودة:")
            for table in missing_tables:
                print(f"  • {table}")
                
        return len(missing_tables) == 0
        
    except Exception as e:
        print(f"❌ خطأ في اختبار الجداول: {e}")
        return False

def test_all_functions():
    """اختبار جميع الدوال المطلوبة"""
    print("\n🔧 اختبار جميع الدوال في PostgreSQL")
    print("-" * 50)
    
    try:
        from database.database_postgresql import PostgreSQLDatabase
        
        # إنشاء قاعدة البيانات مع رابط وهمي
        try:
            db = PostgreSQLDatabase("postgresql://fake:fake@fake:5432/fake")
        except Exception as e:
            # إذا فشل الاتصال، نستخدم رابط آخر للاختبار
            if "connection" in str(e).lower() or "refused" in str(e).lower() or "translate" in str(e).lower():
                print("⚠️ خادم PostgreSQL غير متوفر - اختبار الكود فقط")
                # إنشاء كائن بدون اتصال للاختبار
                db = PostgreSQLDatabase.__new__(PostgreSQLDatabase)
                db.__init__ = lambda self, conn_str=None: None
                db.__init__(db, "postgresql://fake:fake@fake:5432/fake")
            else:
                raise e
        
        # قائمة جميع الدوال المطلوبة
        required_functions = [
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
        missing_functions = []
        existing_functions = []
        
        for func in required_functions:
            if hasattr(db, func):
                existing_functions.append(func)
                print(f"✅ {func}")
            else:
                missing_functions.append(func)
                print(f"❌ {func}")
                
        print(f"\n📊 النتائج:")
        print(f"✅ موجود: {len(existing_functions)}/{len(required_functions)}")
        print(f"❌ مفقود: {len(missing_functions)}")
        
        if missing_functions:
            print(f"\n🔍 الدوال المفقودة:")
            for func in missing_functions:
                print(f"  • {func}")
                
        return len(missing_functions) == 0
        
    except Exception as e:
        print(f"❌ خطأ في اختبار الدوال: {e}")
        return False

def test_table_structures():
    """اختبار هياكل الجداول"""
    print("\n🏗️ اختبار هياكل الجداول")
    print("-" * 50)
    
    try:
        # قراءة ملف قاعدة البيانات PostgreSQL
        with open('database/database_postgresql.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # اختبار العناصر المطلوبة في هياكل الجداول
        required_elements = [
            'SERIAL PRIMARY KEY',
            'BIGINT',
            'TEXT',
            'BOOLEAN',
            'TIMESTAMP',
            'JSONB',
            'TEXT[]',
            'FOREIGN KEY',
            'ON DELETE CASCADE',
            'CREATE INDEX'
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
        print(f"❌ خطأ في اختبار هياكل الجداول: {e}")
        return False

def test_functionality_groups():
    """اختبار مجموعات الوظائف"""
    print("\n🎯 اختبار مجموعات الوظائف")
    print("-" * 50)
    
    try:
        from database.database_postgresql import PostgreSQLDatabase
        
        # إنشاء قاعدة البيانات مع رابط وهمي
        try:
            db = PostgreSQLDatabase("postgresql://fake:fake@fake:5432/fake")
        except Exception as e:
            # إذا فشل الاتصال، نستخدم رابط آخر للاختبار
            if "connection" in str(e).lower() or "refused" in str(e).lower() or "translate" in str(e).lower():
                print("⚠️ خادم PostgreSQL غير متوفر - اختبار الكود فقط")
                # إنشاء كائن بدون اتصال للاختبار
                db = PostgreSQLDatabase.__new__(PostgreSQLDatabase)
                db.__init__ = lambda self, conn_str=None: None
                db.__init__(db, "postgresql://fake:fake@fake:5432/fake")
            else:
                raise e
        
        # مجموعات الوظائف
        functionality_groups = {
            'إدارة المستخدمين': [
                'save_user_session',
                'get_user_session', 
                'is_user_authenticated'
            ],
            'إدارة المهام': [
                'create_task',
                'get_task',
                'get_user_tasks'
            ],
            'الوسوم الصوتية': [
                'get_audio_metadata_settings',
                'get_audio_template_settings',
                'update_audio_template_setting',
                'reset_audio_template_settings'
            ],
            'حدود الأحرف': [
                'get_character_limit_settings'
            ],
            'حدود المعدل': [
                'get_rate_limit_settings'
            ],
            'تأخير التوجيه': [
                'get_forwarding_delay_settings'
            ],
            'فترات الإرسال': [
                'get_sending_interval_settings'
            ],
            'إعدادات الرسائل': [
                'get_message_settings'
            ],
            'ساعات العمل': [
                'toggle_working_hour'
            ],
            'إدارة القنوات': [
                'add_user_channel',
                'get_user_channels',
                'delete_user_channel',
                'update_user_channel'
            ]
        }
        
        all_groups_ready = True
        
        for group_name, functions in functionality_groups.items():
            missing_functions = []
            existing_functions = []
            
            for func in functions:
                if hasattr(db, func):
                    existing_functions.append(func)
                else:
                    missing_functions.append(func)
            
            if missing_functions:
                print(f"❌ {group_name}: {len(existing_functions)}/{len(functions)}")
                all_groups_ready = False
            else:
                print(f"✅ {group_name}: {len(existing_functions)}/{len(functions)}")
                
        return all_groups_ready
        
    except Exception as e:
        print(f"❌ خطأ في اختبار مجموعات الوظائف: {e}")
        return False

def test_compatibility_with_sqlite():
    """اختبار التوافق مع SQLite"""
    print("\n🔄 اختبار التوافق مع SQLite")
    print("-" * 50)
    
    try:
        from database.database_postgresql import PostgreSQLDatabase
        from database.database import Database as SQLiteDatabase
        
        # إنشاء كلا النوعين
        try:
            postgres_db = PostgreSQLDatabase("postgresql://fake:fake@fake:5432/fake")
        except Exception as e:
            if "connection" in str(e).lower() or "refused" in str(e).lower() or "translate" in str(e).lower():
                print("⚠️ خادم PostgreSQL غير متوفر - اختبار الكود فقط")
                # إنشاء كائن بدون اتصال للاختبار
                postgres_db = PostgreSQLDatabase.__new__(PostgreSQLDatabase)
                postgres_db.__init__ = lambda self, conn_str=None: None
                postgres_db.__init__(postgres_db, "postgresql://fake:fake@fake:5432/fake")
            else:
                raise e
                
        sqlite_db = SQLiteDatabase()
        
        # قائمة الدوال المشتركة
        common_functions = [
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
        compatible_functions = []
        incompatible_functions = []
        
        for func in common_functions:
            if hasattr(postgres_db, func) and hasattr(sqlite_db, func):
                compatible_functions.append(func)
                print(f"✅ {func}")
            else:
                incompatible_functions.append(func)
                print(f"❌ {func}")
                
        print(f"\n📊 النتائج:")
        print(f"✅ متوافق: {len(compatible_functions)}/{len(common_functions)}")
        print(f"❌ غير متوافق: {len(incompatible_functions)}")
        
        if incompatible_functions:
            print(f"\n🔍 الدوال غير المتوافقة:")
            for func in incompatible_functions:
                print(f"  • {func}")
                
        return len(incompatible_functions) == 0
        
    except Exception as e:
        print(f"❌ خطأ في اختبار التوافق: {e}")
        return False

if __name__ == "__main__":
    print("🧪 اختبار محسن لجميع الجداول والوظائف في PostgreSQL")
    print("=" * 80)
    
    # تشغيل الاختبارات
    all_results = []
    
    # Test all tables
    tables_result = test_all_tables()
    all_results.append(tables_result)
    
    # Test all functions
    functions_result = test_all_functions()
    all_results.append(functions_result)
    
    # Test table structures
    structures_result = test_table_structures()
    all_results.append(structures_result)
    
    # Test functionality groups
    groups_result = test_functionality_groups()
    all_results.append(groups_result)
    
    # Test compatibility
    compatibility_result = test_compatibility_with_sqlite()
    all_results.append(compatibility_result)
    
    # Summary
    print(f"\n📊 ملخص النتائج:")
    print(f"✅ نجح: {sum(all_results)}")
    print(f"❌ فشل: {len(all_results) - sum(all_results)}")
    print(f"📈 نسبة النجاح: {(sum(all_results)/len(all_results)*100):.1f}%")
    
    print(f"\n📋 تفاصيل الاختبارات:")
    print(f"• جميع الجداول: {'✅' if tables_result else '❌'}")
    print(f"• جميع الدوال: {'✅' if functions_result else '❌'}")
    print(f"• هياكل الجداول: {'✅' if structures_result else '❌'}")
    print(f"• مجموعات الوظائف: {'✅' if groups_result else '❌'}")
    print(f"• التوافق مع SQLite: {'✅' if compatibility_result else '❌'}")
    
    if all(all_results):
        print("\n🎉 جميع الجداول والوظائف جاهزة 100%!")
        print("\n✅ جميع المكونات تعمل:")
        print("• 🗄️ جميع الجداول موجودة")
        print("• 🔧 جميع الدوال جاهزة")
        print("• 🏗️ هياكل الجداول صحيحة")
        print("• 🎯 مجموعات الوظائف مكتملة")
        print("• 🔄 التوافق مع SQLite مضمون")
        print("\n🚀 PostgreSQL جاهز لجميع الوظائف!")
    else:
        print("\n⚠️ بعض المكونات تحتاج إلى إصلاح.")
        print("يرجى مراجعة الأخطاء المذكورة أعلاه.")
        
        if not tables_result:
            print("\n🔧 إصلاح مشكلة الجداول:")
            print("تحقق من وجود جميع الجداول في database_postgresql.py")
            
        if not functions_result:
            print("\n🔧 إصلاح مشكلة الدوال:")
            print("تحقق من وجود جميع الدوال في database_postgresql.py")
            
        if not structures_result:
            print("\n🔧 إصلاح مشكلة هياكل الجداول:")
            print("تحقق من استخدام أنواع البيانات الصحيحة")
            
        if not groups_result:
            print("\n🔧 إصلاح مشكلة مجموعات الوظائف:")
            print("تحقق من اكتمال مجموعات الوظائف")
            
        if not compatibility_result:
            print("\n🔧 إصلاح مشكلة التوافق:")
            print("تأكد من تطابق أسماء الدوال مع SQLite")
            
    print(f"\n📝 ملاحظة مهمة:")
    print("• هذا الاختبار يتحقق من وجود الجداول والدوال في الكود")
    print("• للاختبار الفعلي، يجب تشغيل خادم PostgreSQL")
    print("• استخدم: python run_with_database_choice.py --database postgresql --test")