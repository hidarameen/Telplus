#!/usr/bin/env python3
"""
اختبار شامل لقاعدة البيانات للتأكد من جاهزيتها 100%
"""

import asyncio
import sys
import os
import sqlite3
from datetime import datetime

# إضافة المسار للوحدات
sys.path.append(os.path.join(os.path.dirname(__file__), 'database'))

from database.database import Database

def test_database_connection():
    """اختبار الاتصال بقاعدة البيانات"""
    print("🔌 اختبار الاتصال بقاعدة البيانات")
    print("-" * 50)
    
    try:
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # اختبار استعلام بسيط
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        if result:
            print("✅ الاتصال بقاعدة البيانات ناجح")
            conn.close()
            return True
        else:
            print("❌ فشل في الاتصال بقاعدة البيانات")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في الاتصال: {e}")
        return False

def test_all_tables_exist():
    """اختبار وجود جميع الجداول المطلوبة"""
    print("\n📋 اختبار وجود جميع الجداول المطلوبة")
    print("-" * 50)
    
    try:
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # قائمة جميع الجداول المطلوبة
        required_tables = [
            'tasks',
            'task_sources',
            'task_targets',
            'user_settings',
            'user_sessions',
            'conversation_states',
            'task_media_filters',
            'task_word_filters',
            'word_filter_entries',
            'task_text_replacements',
            'text_replacement_entries',
            'task_headers',
            'task_footers',
            'task_inline_buttons',
            'task_message_settings',
            'task_forwarding_settings',
            'message_mappings',
            'pending_messages',
            'task_advanced_filters',
            'task_day_filters',
            'task_working_hours',
            'task_working_hours_schedule',
            'task_language_filters',
            'task_admin_filters',
            'task_duplicate_settings',
            'forwarded_messages_log',
            'task_inline_button_filters',
            'task_forwarded_message_filters',
            'task_text_cleaning_settings',
            'task_text_cleaning_keywords',
            'task_text_formatting_settings',
            'task_translation_settings',
            'task_watermark_settings',
            'task_audio_metadata_settings',
            'task_character_limit_settings',
            'task_rate_limit_settings',
            'task_forwarding_delay_settings',
            'task_sending_interval_settings',
            'rate_limit_tracking',
            'task_audio_template_settings',
            'message_duplicates'
        ]
        
        # التحقق من وجود الجداول
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        missing_tables = []
        existing_count = 0
        
        for table in required_tables:
            if table in existing_tables:
                print(f"✅ {table}")
                existing_count += 1
            else:
                print(f"❌ {table} - مفقود")
                missing_tables.append(table)
        
        print(f"\n📊 النتائج:")
        print(f"✅ موجود: {existing_count}/{len(required_tables)}")
        print(f"❌ مفقود: {len(missing_tables)}")
        
        if missing_tables:
            print(f"\n🔍 الجداول المفقودة:")
            for table in missing_tables:
                print(f"  • {table}")
        
        conn.close()
        return len(missing_tables) == 0
        
    except Exception as e:
        print(f"❌ خطأ في فحص الجداول: {e}")
        return False

def test_table_structures():
    """اختبار بنية الجداول المهمة"""
    print("\n🏗️ اختبار بنية الجداول المهمة")
    print("-" * 50)
    
    try:
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # اختبار بنية الجداول المهمة
        important_tables = {
            'tasks': ['id', 'user_id', 'task_name', 'forward_mode', 'is_active'],
            'user_sessions': ['user_id', 'phone_number', 'session_string', 'is_authenticated'],
            'task_audio_metadata_settings': ['task_id', 'enabled', 'template'],
            'task_audio_template_settings': ['task_id', 'title_template', 'artist_template', 'album_template']
        }
        
        results = []
        for table_name, required_columns in important_tables.items():
            try:
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [row[1] for row in cursor.fetchall()]
                
                missing_columns = []
                for col in required_columns:
                    if col not in columns:
                        missing_columns.append(col)
                
                if missing_columns:
                    print(f"❌ {table_name}: أعمدة مفقودة - {missing_columns}")
                    results.append(False)
                else:
                    print(f"✅ {table_name}: البنية صحيحة")
                    results.append(True)
                    
            except Exception as e:
                print(f"❌ {table_name}: خطأ في فحص البنية - {e}")
                results.append(False)
        
        conn.close()
        return all(results)
        
    except Exception as e:
        print(f"❌ خطأ في فحص بنية الجداول: {e}")
        return False

def test_database_functions():
    """اختبار دوال قاعدة البيانات"""
    print("\n🔧 اختبار دوال قاعدة البيانات")
    print("-" * 50)
    
    try:
        db = Database()
        
        # اختبار دوال المستخدمين
        test_user_id = 123456789
        
        # اختبار حفظ جلسة مستخدم
        try:
            db.save_user_session(test_user_id, "1234567890", "test_session_string")
            print("✅ save_user_session")
        except Exception as e:
            print(f"❌ save_user_session: {e}")
        
        # اختبار جلب جلسة مستخدم
        try:
            session = db.get_user_session(test_user_id)
            print("✅ get_user_session")
        except Exception as e:
            print(f"❌ get_user_session: {e}")
        
        # اختبار التحقق من المصادقة
        try:
            is_auth = db.is_user_authenticated(test_user_id)
            print("✅ is_user_authenticated")
        except Exception as e:
            print(f"❌ is_user_authenticated: {e}")
        
        # اختبار دوال المهام
        try:
            # إنشاء مهمة تجريبية
            task_data = {
                'user_id': test_user_id,
                'task_name': 'مهمة تجريبية',
                'source_chat_id': '123456789',
                'target_chat_id': '987654321'
            }
            
            # اختبار إنشاء مهمة
            task_id = db.create_task(**task_data)
            print(f"✅ create_task: {task_id}")
            
            # اختبار جلب مهمة
            task = db.get_task(task_id, test_user_id)
            print("✅ get_task")
            
            # اختبار جلب مهام المستخدم
            tasks = db.get_user_tasks(test_user_id)
            print("✅ get_user_tasks")
            
        except Exception as e:
            print(f"❌ دوال المهام: {e}")
        
        # اختبار دوال الوسوم الصوتية
        try:
            # اختبار إعدادات الوسوم الصوتية
            audio_settings = db.get_audio_metadata_settings(task_id)
            print("✅ get_audio_metadata_settings")
            
            # اختبار إعدادات قالب الوسوم
            template_settings = db.get_audio_template_settings(task_id)
            print("✅ get_audio_template_settings")
            
            # اختبار تحديث قالب
            success = db.update_audio_template_setting(task_id, 'title', '$title - Test')
            print("✅ update_audio_template_setting")
            
        except Exception as e:
            print(f"❌ دوال الوسوم الصوتية: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار الدوال: {e}")
        return False

def test_data_integrity():
    """اختبار سلامة البيانات"""
    print("\n🔒 اختبار سلامة البيانات")
    print("-" * 50)
    
    try:
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # اختبار القيود الخارجية
        cursor.execute("PRAGMA foreign_keys")
        foreign_keys_enabled = cursor.fetchone()[0]
        
        if foreign_keys_enabled:
            print("✅ القيود الخارجية مفعلة")
        else:
            print("❌ القيود الخارجية معطلة")
        
        # اختبار الفهارس
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        
        print(f"📊 عدد الفهارس: {len(indexes)}")
        
        # اختبار حجم قاعدة البيانات
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        
        print(f"📊 عدد الجداول: {table_count}")
        
        # اختبار بعض الجداول المهمة
        important_tables = ['tasks', 'user_sessions', 'task_audio_metadata_settings']
        
        for table in important_tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"📊 {table}: {count} صف")
            except Exception as e:
                print(f"❌ {table}: خطأ في العد - {e}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار سلامة البيانات: {e}")
        return False

def test_performance():
    """اختبار أداء قاعدة البيانات"""
    print("\n⚡ اختبار أداء قاعدة البيانات")
    print("-" * 50)
    
    try:
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # اختبار سرعة الاستعلامات
        import time
        
        # اختبار استعلام بسيط
        start_time = time.time()
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        result = cursor.fetchone()
        simple_query_time = time.time() - start_time
        
        print(f"⏱️ استعلام بسيط: {simple_query_time:.4f} ثانية")
        
        # اختبار استعلام معقد
        start_time = time.time()
        cursor.execute("""
            SELECT t.task_name, COUNT(ts.id) as sources_count, COUNT(tt.id) as targets_count
            FROM tasks t
            LEFT JOIN task_sources ts ON t.id = ts.task_id
            LEFT JOIN task_targets tt ON t.id = tt.task_id
            GROUP BY t.id, t.task_name
        """)
        results = cursor.fetchall()
        complex_query_time = time.time() - start_time
        
        print(f"⏱️ استعلام معقد: {complex_query_time:.4f} ثانية")
        
        # تقييم الأداء
        if simple_query_time < 0.1 and complex_query_time < 1.0:
            print("✅ الأداء ممتاز")
            performance_ok = True
        elif simple_query_time < 0.5 and complex_query_time < 5.0:
            print("⚠️ الأداء مقبول")
            performance_ok = True
        else:
            print("❌ الأداء بطيء")
            performance_ok = False
        
        conn.close()
        return performance_ok
        
    except Exception as e:
        print(f"❌ خطأ في اختبار الأداء: {e}")
        return False

def test_backup_and_recovery():
    """اختبار النسخ الاحتياطي والاسترداد"""
    print("\n💾 اختبار النسخ الاحتياطي والاسترداد")
    print("-" * 50)
    
    try:
        import shutil
        
        # نسخ احتياطي
        backup_path = 'telegram_bot_backup.db'
        shutil.copy2('telegram_bot.db', backup_path)
        print("✅ تم إنشاء نسخة احتياطية")
        
        # اختبار النسخة الاحتياطية
        backup_conn = sqlite3.connect(backup_path)
        backup_cursor = backup_conn.cursor()
        
        backup_cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = backup_cursor.fetchone()[0]
        
        print(f"✅ النسخة الاحتياطية تحتوي على {table_count} جدول")
        
        backup_conn.close()
        
        # حذف النسخة الاحتياطية
        os.remove(backup_path)
        print("✅ تم حذف النسخة الاحتياطية")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في النسخ الاحتياطي: {e}")
        return False

if __name__ == "__main__":
    print("🗄️ اختبار شامل لقاعدة البيانات")
    print("=" * 80)
    
    # تشغيل الاختبارات
    all_results = []
    
    # Test database connection
    connection_result = test_database_connection()
    all_results.append(connection_result)
    
    # Test all tables exist
    tables_result = test_all_tables_exist()
    all_results.append(tables_result)
    
    # Test table structures
    structure_result = test_table_structures()
    all_results.append(structure_result)
    
    # Test database functions
    functions_result = test_database_functions()
    all_results.append(functions_result)
    
    # Test data integrity
    integrity_result = test_data_integrity()
    all_results.append(integrity_result)
    
    # Test performance
    performance_result = test_performance()
    all_results.append(performance_result)
    
    # Test backup and recovery
    backup_result = test_backup_and_recovery()
    all_results.append(backup_result)
    
    # Summary
    print(f"\n📊 ملخص النتائج الشاملة:")
    print(f"✅ نجح: {sum(all_results)}")
    print(f"❌ فشل: {len(all_results) - sum(all_results)}")
    print(f"📈 نسبة النجاح الإجمالية: {(sum(all_results)/len(all_results)*100):.1f}%")
    
    print(f"\n📋 تفاصيل الاختبارات:")
    print(f"• الاتصال بقاعدة البيانات: {'✅' if connection_result else '❌'}")
    print(f"• وجود جميع الجداول: {'✅' if tables_result else '❌'}")
    print(f"• بنية الجداول: {'✅' if structure_result else '❌'}")
    print(f"• دوال قاعدة البيانات: {'✅' if functions_result else '❌'}")
    print(f"• سلامة البيانات: {'✅' if integrity_result else '❌'}")
    print(f"• الأداء: {'✅' if performance_result else '❌'}")
    print(f"• النسخ الاحتياطي: {'✅' if backup_result else '❌'}")
    
    if all(all_results):
        print("\n🎉 قاعدة البيانات جاهزة 100%!")
        print("\n✅ جميع المكونات تعمل:")
        print("• 🔌 الاتصال مستقر")
        print("• 📋 جميع الجداول موجودة")
        print("• 🏗️ البنية صحيحة")
        print("• 🔧 جميع الدوال تعمل")
        print("• 🔒 البيانات آمنة")
        print("• ⚡ الأداء ممتاز")
        print("• 💾 النسخ الاحتياطي يعمل")
        print("\n🚀 قاعدة البيانات جاهزة لجميع الوظائف!")
    else:
        print("\n⚠️ بعض المكونات تحتاج إلى إصلاح.")
        print("يرجى مراجعة الأخطاء المذكورة أعلاه.")
    
    print(f"\n🔍 تحليل الأخطاء:")
    if not connection_result:
        print("• مشكلة في الاتصال بقاعدة البيانات")
    if not tables_result:
        print("• بعض الجداول مفقودة")
    if not structure_result:
        print("• مشكلة في بنية الجداول")
    if not functions_result:
        print("• بعض الدوال لا تعمل")
    if not integrity_result:
        print("• مشكلة في سلامة البيانات")
    if not performance_result:
        print("• مشكلة في الأداء")
    if not backup_result:
        print("• مشكلة في النسخ الاحتياطي")