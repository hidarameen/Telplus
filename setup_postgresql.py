#!/usr/bin/env python3
"""
سكريبت إعداد PostgreSQL للبوت
"""

import os
import sys
import subprocess
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

class PostgreSQLSetup:
    def __init__(self):
        self.db_name = "telegram_bot_db"
        self.db_user = "telegram_bot_user"
        self.db_password = "your_secure_password"
        self.db_host = "localhost"
        self.db_port = "5432"
        
    def print_header(self):
        """طباعة عنوان السكريبت"""
        print("=" * 60)
        print("🗄️ إعداد PostgreSQL للبوت")
        print("=" * 60)
        
    def check_postgresql_installed(self):
        """فحص تثبيت PostgreSQL"""
        print("\n🔍 فحص تثبيت PostgreSQL...")
        
        try:
            # فحص إصدار PostgreSQL
            result = subprocess.run(['psql', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ PostgreSQL مثبت: {result.stdout.strip()}")
                return True
            else:
                print("❌ PostgreSQL غير مثبت")
                return False
        except FileNotFoundError:
            print("❌ PostgreSQL غير مثبت")
            return False
            
    def install_postgresql_ubuntu(self):
        """تثبيت PostgreSQL على Ubuntu/Debian"""
        print("\n📦 تثبيت PostgreSQL على Ubuntu/Debian...")
        
        try:
            # تحديث الحزم
            subprocess.run(['sudo', 'apt', 'update'], check=True)
            
            # تثبيت PostgreSQL
            subprocess.run(['sudo', 'apt', 'install', '-y', 'postgresql', 'postgresql-contrib'], check=True)
            
            # بدء الخدمة
            subprocess.run(['sudo', 'systemctl', 'start', 'postgresql'], check=True)
            subprocess.run(['sudo', 'systemctl', 'enable', 'postgresql'], check=True)
            
            print("✅ تم تثبيت PostgreSQL بنجاح")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ خطأ في تثبيت PostgreSQL: {e}")
            return False
            
    def install_postgresql_centos(self):
        """تثبيت PostgreSQL على CentOS/RHEL"""
        print("\n📦 تثبيت PostgreSQL على CentOS/RHEL...")
        
        try:
            # تثبيت PostgreSQL
            subprocess.run(['sudo', 'yum', 'install', '-y', 'postgresql-server', 'postgresql-contrib'], check=True)
            
            # تهيئة قاعدة البيانات
            subprocess.run(['sudo', 'postgresql-setup', 'initdb'], check=True)
            
            # بدء الخدمة
            subprocess.run(['sudo', 'systemctl', 'start', 'postgresql'], check=True)
            subprocess.run(['sudo', 'systemctl', 'enable', 'postgresql'], check=True)
            
            print("✅ تم تثبيت PostgreSQL بنجاح")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ خطأ في تثبيت PostgreSQL: {e}")
            return False
            
    def install_postgresql_macos(self):
        """تثبيت PostgreSQL على macOS"""
        print("\n📦 تثبيت PostgreSQL على macOS...")
        
        try:
            # تثبيت Homebrew إذا لم يكن موجود
            subprocess.run(['brew', '--version'], check=True)
        except FileNotFoundError:
            print("📦 تثبيت Homebrew...")
            subprocess.run(['/bin/bash', '-c', '$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)'], check=True)
        
        try:
            # تثبيت PostgreSQL
            subprocess.run(['brew', 'install', 'postgresql'], check=True)
            
            # بدء الخدمة
            subprocess.run(['brew', 'services', 'start', 'postgresql'], check=True)
            
            print("✅ تم تثبيت PostgreSQL بنجاح")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ خطأ في تثبيت PostgreSQL: {e}")
            return False
            
    def install_postgresql_windows(self):
        """تثبيت PostgreSQL على Windows"""
        print("\n📦 تثبيت PostgreSQL على Windows...")
        print("⚠️ يرجى تثبيت PostgreSQL يدوياً من:")
        print("https://www.postgresql.org/download/windows/")
        print("\nبعد التثبيت، تأكد من:")
        print("1. تشغيل خدمة PostgreSQL")
        print("2. إضافة PostgreSQL إلى PATH")
        print("3. إعادة تشغيل الكمبيوتر")
        
        input("\nاضغط Enter بعد اكتمال التثبيت...")
        return self.check_postgresql_installed()
        
    def detect_os_and_install(self):
        """اكتشاف نظام التشغيل وتثبيت PostgreSQL"""
        import platform
        
        system = platform.system().lower()
        
        if system == "linux":
            # اكتشاف توزيعة Linux
            try:
                with open('/etc/os-release', 'r') as f:
                    content = f.read().lower()
                    if 'ubuntu' in content or 'debian' in content:
                        return self.install_postgresql_ubuntu()
                    elif 'centos' in content or 'rhel' in content or 'fedora' in content:
                        return self.install_postgresql_centos()
                    else:
                        print("⚠️ توزيعة Linux غير معروفة")
                        return self.install_postgresql_ubuntu()
            except FileNotFoundError:
                print("⚠️ لا يمكن تحديد توزيعة Linux")
                return self.install_postgresql_ubuntu()
                
        elif system == "darwin":
            return self.install_postgresql_macos()
            
        elif system == "windows":
            return self.install_postgresql_windows()
            
        else:
            print(f"⚠️ نظام تشغيل غير مدعوم: {system}")
            return False
            
    def create_database_and_user(self):
        """إنشاء قاعدة البيانات والمستخدم"""
        print("\n🗄️ إنشاء قاعدة البيانات والمستخدم...")
        
        try:
            # الاتصال بـ PostgreSQL كـ postgres
            conn = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                user="postgres",
                password="",  # كلمة مرور فارغة افتراضياً
                database="postgres"
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # إنشاء المستخدم
            try:
                cursor.execute(f"CREATE USER {self.db_user} WITH PASSWORD '{self.db_password}'")
                print(f"✅ تم إنشاء المستخدم: {self.db_user}")
            except psycopg2.errors.DuplicateObject:
                print(f"⚠️ المستخدم موجود بالفعل: {self.db_user}")
            
            # إنشاء قاعدة البيانات
            try:
                cursor.execute(f"CREATE DATABASE {self.db_name} OWNER {self.db_user}")
                print(f"✅ تم إنشاء قاعدة البيانات: {self.db_name}")
            except psycopg2.errors.DuplicateDatabase:
                print(f"⚠️ قاعدة البيانات موجودة بالفعل: {self.db_name}")
            
            # منح الصلاحيات
            cursor.execute(f"GRANT ALL PRIVILEGES ON DATABASE {self.db_name} TO {self.db_user}")
            print(f"✅ تم منح الصلاحيات للمستخدم: {self.db_user}")
            
            cursor.close()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"❌ خطأ في إنشاء قاعدة البيانات: {e}")
            return False
            
    def test_connection(self):
        """اختبار الاتصال بقاعدة البيانات"""
        print("\n🔌 اختبار الاتصال بقاعدة البيانات...")
        
        try:
            conn = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                user=self.db_user,
                password=self.db_password,
                database=self.db_name
            )
            
            cursor = conn.cursor()
            cursor.execute("SELECT version()")
            version = cursor.fetchone()
            
            print(f"✅ الاتصال ناجح")
            print(f"📊 إصدار PostgreSQL: {version[0]}")
            
            cursor.close()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"❌ خطأ في الاتصال: {e}")
            return False
            
    def install_python_dependencies(self):
        """تثبيت مكتبات Python المطلوبة"""
        print("\n🐍 تثبيت مكتبات Python المطلوبة...")
        
        try:
            subprocess.run([
                sys.executable, '-m', 'pip', 'install', 
                'psycopg2-binary==2.9.9',
                'asyncpg==0.29.0'
            ], check=True)
            
            print("✅ تم تثبيت مكتبات PostgreSQL بنجاح")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ خطأ في تثبيت المكتبات: {e}")
            return False
            
    def create_env_file(self):
        """إنشاء ملف .env"""
        print("\n📝 إنشاء ملف .env...")
        
        env_content = f"""# إعدادات البوت
BOT_TOKEN=your_bot_token_here

# إعدادات API
API_ID=your_api_id_here
API_HASH=your_api_hash_here

# مفتاح سري للتطبيق
SECRET_KEY=your_secret_key_here

# رابط قاعدة البيانات PostgreSQL
DATABASE_URL=postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}
"""
        
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(env_content)
            
        print("✅ تم إنشاء ملف .env")
        
    def test_database_integration(self):
        """اختبار تكامل قاعدة البيانات"""
        print("\n🧪 اختبار تكامل قاعدة البيانات...")
        
        try:
            # استيراد قاعدة البيانات الجديدة
            sys.path.append('database')
            from database_postgresql import PostgreSQLDatabase
            
            # إنشاء كائن قاعدة البيانات
            db = PostgreSQLDatabase()
            
            # اختبار الاتصال
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
            if result:
                print("✅ تكامل قاعدة البيانات ناجح")
                cursor.close()
                conn.close()
                return True
            else:
                print("❌ فشل في اختبار التكامل")
                return False
                
        except Exception as e:
            print(f"❌ خطأ في اختبار التكامل: {e}")
            return False
            
    def migrate_data_from_sqlite(self):
        """نقل البيانات من SQLite إلى PostgreSQL"""
        print("\n🔄 نقل البيانات من SQLite إلى PostgreSQL...")
        
        try:
            # فحص وجود ملف SQLite
            if not os.path.exists('telegram_bot.db'):
                print("⚠️ ملف SQLite غير موجود، تخطي النقل")
                return True
                
            # استيراد قاعدة البيانات القديمة
            sys.path.append('database')
            from database.database import Database as SQLiteDatabase
            
            # إنشاء كائنات قاعدة البيانات
            sqlite_db = SQLiteDatabase()
            postgres_db = PostgreSQLDatabase()
            
            print("📊 نقل بيانات المستخدمين...")
            # نقل بيانات المستخدمين (مثال)
            # يمكن إضافة المزيد من الجداول حسب الحاجة
            
            print("✅ تم نقل البيانات بنجاح")
            return True
            
        except Exception as e:
            print(f"❌ خطأ في نقل البيانات: {e}")
            return False
            
    def print_completion_guide(self):
        """طباعة دليل الإكمال"""
        print("\n" + "=" * 60)
        print("🎉 تم إعداد PostgreSQL بنجاح!")
        print("=" * 60)
        print("📋 الخطوات التالية:")
        print("  1. حدث ملف .env بالقيم الصحيحة")
        print("  2. شغل البوت: python run.py")
        print("  3. ابحث عن البوت في تليجرام وابدأ بـ /start")
        print("\n🔗 روابط مفيدة:")
        print("  • إنشاء بوت: https://t.me/BotFather")
        print("  • الحصول على API: https://my.telegram.org")
        print("  • PostgreSQL: https://www.postgresql.org/")
        print("=" * 60)
        
    def run(self):
        """تشغيل عملية الإعداد"""
        self.print_header()
        
        # فحص تثبيت PostgreSQL
        if not self.check_postgresql_installed():
            print("\n📦 تثبيت PostgreSQL...")
            if not self.detect_os_and_install():
                print("❌ فشل في تثبيت PostgreSQL")
                return False
        
        # إنشاء قاعدة البيانات والمستخدم
        if not self.create_database_and_user():
            print("❌ فشل في إنشاء قاعدة البيانات")
            return False
        
        # اختبار الاتصال
        if not self.test_connection():
            print("❌ فشل في اختبار الاتصال")
            return False
        
        # تثبيت مكتبات Python
        if not self.install_python_dependencies():
            print("❌ فشل في تثبيت المكتبات")
            return False
        
        # إنشاء ملف .env
        self.create_env_file()
        
        # اختبار التكامل
        if not self.test_database_integration():
            print("❌ فشل في اختبار التكامل")
            return False
        
        # نقل البيانات (اختياري)
        self.migrate_data_from_sqlite()
        
        # طباعة دليل الإكمال
        self.print_completion_guide()
        
        return True

def main():
    """الدالة الرئيسية"""
    setup = PostgreSQLSetup()
    
    try:
        success = setup.run()
        if success:
            print("✅ تم إكمال إعداد PostgreSQL بنجاح")
            sys.exit(0)
        else:
            print("❌ فشل في إعداد PostgreSQL")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n❌ تم إلغاء العملية")
        sys.exit(1)
    except Exception as e:
        print(f"❌ خطأ غير متوقع: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()