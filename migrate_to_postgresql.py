#!/usr/bin/env python3
"""
سكريبت نقل البيانات من SQLite إلى PostgreSQL
"""

import os
import sys
import sqlite3
import psycopg2
import psycopg2.extras
from datetime import datetime
import json

class DataMigrator:
    def __init__(self):
        self.sqlite_path = 'telegram_bot.db'
        self.postgres_config = {
            'host': 'localhost',
            'port': '5432',
            'user': 'telegram_bot_user',
            'password': 'your_secure_password',
            'database': 'telegram_bot_db'
        }
        
    def print_header(self):
        """طباعة عنوان السكريبت"""
        print("=" * 60)
        print("🔄 نقل البيانات من SQLite إلى PostgreSQL")
        print("=" * 60)
        
    def check_sqlite_file(self):
        """فحص وجود ملف SQLite"""
        print("\n🔍 فحص ملف SQLite...")
        
        if not os.path.exists(self.sqlite_path):
            print(f"❌ ملف SQLite غير موجود: {self.sqlite_path}")
            return False
            
        print(f"✅ ملف SQLite موجود: {self.sqlite_path}")
        return True
        
    def connect_sqlite(self):
        """الاتصال بـ SQLite"""
        try:
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            print(f"❌ خطأ في الاتصال بـ SQLite: {e}")
            return None
            
    def connect_postgresql(self):
        """الاتصال بـ PostgreSQL"""
        try:
            conn = psycopg2.connect(**self.postgres_config)
            return conn
        except Exception as e:
            print(f"❌ خطأ في الاتصال بـ PostgreSQL: {e}")
            return None
            
    def get_sqlite_tables(self, sqlite_conn):
        """الحصول على قائمة الجداول في SQLite"""
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        return tables
        
    def migrate_table(self, sqlite_conn, postgres_conn, table_name):
        """نقل جدول واحد"""
        print(f"📊 نقل جدول: {table_name}")
        
        try:
            sqlite_cursor = sqlite_conn.cursor()
            postgres_cursor = postgres_conn.cursor()
            
            # الحصول على بيانات الجدول
            sqlite_cursor.execute(f"SELECT * FROM {table_name}")
            rows = sqlite_cursor.fetchall()
            
            if not rows:
                print(f"⚠️ الجدول فارغ: {table_name}")
                return True
                
            # الحصول على أسماء الأعمدة
            columns = [description[0] for description in sqlite_cursor.description]
            
            # إنشاء استعلام الإدراج
            placeholders = ', '.join(['%s'] * len(columns))
            insert_query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
            
            # نقل البيانات
            for row in rows:
                values = [row[col] for col in columns]
                
                # معالجة القيم الخاصة
                for i, value in enumerate(values):
                    if isinstance(value, dict):
                        values[i] = json.dumps(value)
                    elif isinstance(value, list):
                        values[i] = json.dumps(value)
                    elif isinstance(value, bool):
                        values[i] = 1 if value else 0
                        
                try:
                    postgres_cursor.execute(insert_query, values)
                except psycopg2.errors.UniqueViolation:
                    # تجاهل الأخطاء الفريدة (البيانات موجودة بالفعل)
                    pass
                except Exception as e:
                    print(f"⚠️ خطأ في إدراج صف في {table_name}: {e}")
                    continue
                    
            postgres_conn.commit()
            print(f"✅ تم نقل {len(rows)} صف من {table_name}")
            return True
            
        except Exception as e:
            print(f"❌ خطأ في نقل جدول {table_name}: {e}")
            return False
            
    def migrate_user_sessions(self, sqlite_conn, postgres_conn):
        """نقل بيانات جلسات المستخدمين"""
        print("\n👤 نقل بيانات جلسات المستخدمين...")
        return self.migrate_table(sqlite_conn, postgres_conn, 'user_sessions')
        
    def migrate_tasks(self, sqlite_conn, postgres_conn):
        """نقل بيانات المهام"""
        print("\n📋 نقل بيانات المهام...")
        return self.migrate_table(sqlite_conn, postgres_conn, 'tasks')
        
    def migrate_task_sources(self, sqlite_conn, postgres_conn):
        """نقل بيانات مصادر المهام"""
        print("\n📤 نقل بيانات مصادر المهام...")
        return self.migrate_table(sqlite_conn, postgres_conn, 'task_sources')
        
    def migrate_task_targets(self, sqlite_conn, postgres_conn):
        """نقل بيانات أهداف المهام"""
        print("\n📥 نقل بيانات أهداف المهام...")
        return self.migrate_table(sqlite_conn, postgres_conn, 'task_targets')
        
    def migrate_conversation_states(self, sqlite_conn, postgres_conn):
        """نقل بيانات حالات المحادثة"""
        print("\n💬 نقل بيانات حالات المحادثة...")
        return self.migrate_table(sqlite_conn, postgres_conn, 'conversation_states')
        
    def migrate_audio_settings(self, sqlite_conn, postgres_conn):
        """نقل بيانات إعدادات الوسوم الصوتية"""
        print("\n🎵 نقل بيانات إعدادات الوسوم الصوتية...")
        
        # نقل إعدادات الوسوم الصوتية
        success1 = self.migrate_table(sqlite_conn, postgres_conn, 'task_audio_metadata_settings')
        
        # نقل قوالب الوسوم الصوتية
        success2 = self.migrate_table(sqlite_conn, postgres_conn, 'task_audio_template_settings')
        
        return success1 and success2
        
    def migrate_character_limits(self, sqlite_conn, postgres_conn):
        """نقل بيانات حدود الأحرف"""
        print("\n📏 نقل بيانات حدود الأحرف...")
        return self.migrate_table(sqlite_conn, postgres_conn, 'task_character_limit_settings')
        
    def migrate_rate_limits(self, sqlite_conn, postgres_conn):
        """نقل بيانات حدود المعدل"""
        print("\n⏱️ نقل بيانات حدود المعدل...")
        return self.migrate_table(sqlite_conn, postgres_conn, 'task_rate_limit_settings')
        
    def migrate_forwarding_delays(self, sqlite_conn, postgres_conn):
        """نقل بيانات تأخير التوجيه"""
        print("\n⏳ نقل بيانات تأخير التوجيه...")
        return self.migrate_table(sqlite_conn, postgres_conn, 'task_forwarding_delay_settings')
        
    def migrate_sending_intervals(self, sqlite_conn, postgres_conn):
        """نقل بيانات فترات الإرسال"""
        print("\n🔄 نقل بيانات فترات الإرسال...")
        return self.migrate_table(sqlite_conn, postgres_conn, 'task_sending_interval_settings')
        
    def migrate_message_settings(self, sqlite_conn, postgres_conn):
        """نقل بيانات إعدادات الرسائل"""
        print("\n📝 نقل بيانات إعدادات الرسائل...")
        return self.migrate_table(sqlite_conn, postgres_conn, 'task_message_settings')
        
    def migrate_user_channels(self, sqlite_conn, postgres_conn):
        """نقل بيانات قنوات المستخدمين"""
        print("\n📺 نقل بيانات قنوات المستخدمين...")
        return self.migrate_table(sqlite_conn, postgres_conn, 'user_channels')
        
    def migrate_all_tables(self, sqlite_conn, postgres_conn):
        """نقل جميع الجداول"""
        print("\n🔄 نقل جميع الجداول...")
        
        # الحصول على قائمة الجداول
        tables = self.get_sqlite_tables(sqlite_conn)
        
        # ترتيب الجداول حسب الأولوية
        priority_tables = [
            'user_sessions',
            'tasks',
            'task_sources',
            'task_targets',
            'conversation_states',
            'task_audio_metadata_settings',
            'task_audio_template_settings',
            'task_character_limit_settings',
            'task_rate_limit_settings',
            'task_forwarding_delay_settings',
            'task_sending_interval_settings',
            'task_message_settings',
            'user_channels'
        ]
        
        # نقل الجداول ذات الأولوية أولاً
        for table in priority_tables:
            if table in tables:
                self.migrate_table(sqlite_conn, postgres_conn, table)
                
        # نقل باقي الجداول
        remaining_tables = [table for table in tables if table not in priority_tables]
        for table in remaining_tables:
            self.migrate_table(sqlite_conn, postgres_conn, table)
            
    def verify_migration(self, sqlite_conn, postgres_conn):
        """التحقق من صحة النقل"""
        print("\n🔍 التحقق من صحة النقل...")
        
        verification_tables = [
            'user_sessions',
            'tasks',
            'task_audio_metadata_settings',
            'task_audio_template_settings'
        ]
        
        for table in verification_tables:
            try:
                # عد الصفوف في SQLite
                sqlite_cursor = sqlite_conn.cursor()
                sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                sqlite_count = sqlite_cursor.fetchone()[0]
                
                # عد الصفوف في PostgreSQL
                postgres_cursor = postgres_conn.cursor()
                postgres_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                postgres_count = postgres_cursor.fetchone()[0]
                
                if sqlite_count == postgres_count:
                    print(f"✅ {table}: {sqlite_count} صف")
                else:
                    print(f"⚠️ {table}: SQLite={sqlite_count}, PostgreSQL={postgres_count}")
                    
            except Exception as e:
                print(f"❌ خطأ في التحقق من {table}: {e}")
                
    def create_backup(self):
        """إنشاء نسخة احتياطية من SQLite"""
        print("\n💾 إنشاء نسخة احتياطية من SQLite...")
        
        backup_path = f"telegram_bot_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        
        try:
            import shutil
            shutil.copy2(self.sqlite_path, backup_path)
            print(f"✅ تم إنشاء النسخة الاحتياطية: {backup_path}")
            return backup_path
        except Exception as e:
            print(f"❌ خطأ في إنشاء النسخة الاحتياطية: {e}")
            return None
            
    def run(self):
        """تشغيل عملية النقل"""
        self.print_header()
        
        # فحص ملف SQLite
        if not self.check_sqlite_file():
            return False
            
        # إنشاء نسخة احتياطية
        backup_path = self.create_backup()
        
        # الاتصال بقواعد البيانات
        sqlite_conn = self.connect_sqlite()
        if not sqlite_conn:
            return False
            
        postgres_conn = self.connect_postgresql()
        if not postgres_conn:
            sqlite_conn.close()
            return False
            
        try:
            # نقل البيانات
            print("\n🚀 بدء نقل البيانات...")
            
            # نقل الجداول المهمة
            self.migrate_user_sessions(sqlite_conn, postgres_conn)
            self.migrate_tasks(sqlite_conn, postgres_conn)
            self.migrate_task_sources(sqlite_conn, postgres_conn)
            self.migrate_task_targets(sqlite_conn, postgres_conn)
            self.migrate_conversation_states(sqlite_conn, postgres_conn)
            self.migrate_audio_settings(sqlite_conn, postgres_conn)
            self.migrate_character_limits(sqlite_conn, postgres_conn)
            self.migrate_rate_limits(sqlite_conn, postgres_conn)
            self.migrate_forwarding_delays(sqlite_conn, postgres_conn)
            self.migrate_sending_intervals(sqlite_conn, postgres_conn)
            self.migrate_message_settings(sqlite_conn, postgres_conn)
            self.migrate_user_channels(sqlite_conn, postgres_conn)
            
            # نقل باقي الجداول
            self.migrate_all_tables(sqlite_conn, postgres_conn)
            
            # التحقق من صحة النقل
            self.verify_migration(sqlite_conn, postgres_conn)
            
            print("\n🎉 تم نقل البيانات بنجاح!")
            print(f"📁 النسخة الاحتياطية: {backup_path}")
            
            return True
            
        except Exception as e:
            print(f"❌ خطأ في نقل البيانات: {e}")
            return False
            
        finally:
            sqlite_conn.close()
            postgres_conn.close()

def main():
    """الدالة الرئيسية"""
    migrator = DataMigrator()
    
    try:
        success = migrator.run()
        if success:
            print("\n✅ تم إكمال نقل البيانات بنجاح")
            print("📋 الخطوات التالية:")
            print("  1. تأكد من تحديث ملف .env لاستخدام PostgreSQL")
            print("  2. اختبر البوت مع قاعدة البيانات الجديدة")
            print("  3. احتفظ بالنسخة الاحتياطية من SQLite")
            sys.exit(0)
        else:
            print("\n❌ فشل في نقل البيانات")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n❌ تم إلغاء العملية")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ خطأ غير متوقع: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()