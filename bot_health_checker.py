
#!/usr/bin/env python3
"""
Bot Health Checker - فاحص صحة البوت
يقوم بفحص حالة البوت وتقديم تقارير مفصلة
"""
import asyncio
import logging
import sqlite3
from datetime import datetime
import sys
import os

# إعداد الـ logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BotHealthChecker:
    def __init__(self):
        self.db_path = 'telegram_bot.db'
        
    def get_database_connection(self):
        """الحصول على اتصال بقاعدة البيانات"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.error(f"خطأ في الاتصال بقاعدة البيانات: {e}")
            return None
    
    def check_database_health(self):
        """فحص صحة قاعدة البيانات"""
        print("\n" + "="*60)
        print("🗄️ فحص قاعدة البيانات")
        print("="*60)
        
        try:
            conn = self.get_database_connection()
            if not conn:
                print("❌ لا يمكن الاتصال بقاعدة البيانات")
                return False
                
            cursor = conn.cursor()
            
            # فحص جدول الجلسات
            cursor.execute("SELECT COUNT(*) FROM user_sessions WHERE is_authenticated = 1")
            authenticated_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM user_sessions WHERE is_healthy = 1")
            healthy_sessions = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE is_active = 1")
            active_tasks = cursor.fetchone()[0]
            
            print(f"📊 إحصائيات قاعدة البيانات:")
            print(f"   👤 المستخدمين المصادق عليهم: {authenticated_users}")
            print(f"   💚 الجلسات الصحية: {healthy_sessions}")
            print(f"   ⚡ المهام النشطة: {active_tasks}")
            
            # فحص تفاصيل الجلسات
            cursor.execute("""
                SELECT user_id, phone_number, is_healthy, last_error_message, connection_errors
                FROM user_sessions 
                WHERE is_authenticated = 1
            """)
            sessions = cursor.fetchall()
            
            print(f"\n📱 تفاصيل الجلسات:")
            for session in sessions:
                status = "✅ صحية" if session['is_healthy'] else "❌ معطلة"
                print(f"   المستخدم {session['user_id']} ({session['phone_number']}): {status}")
                if session['last_error_message']:
                    print(f"      📋 آخر خطأ: {session['last_error_message']}")
                if session['connection_errors'] > 0:
                    print(f"      ⚠️ عدد الأخطاء: {session['connection_errors']}")
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ خطأ في فحص قاعدة البيانات: {e}")
            return False
    
    def check_environment_variables(self):
        """فحص متغيرات البيئة"""
        print("\n" + "="*60)
        print("🔧 فحص متغيرات البيئة")
        print("="*60)
        
        required_vars = {
            'BOT_TOKEN': 'رمز البوت',
            'API_ID': 'معرف API',
            'API_HASH': 'هاش API'
        }
        
        all_good = True
        for var, description in required_vars.items():
            value = os.getenv(var)
            if not value or value.startswith('your_'):
                print(f"❌ {description} ({var}): غير محدد")
                all_good = False
            else:
                masked_value = value[:8] + "..." if len(value) > 8 else "محدد"
                print(f"✅ {description} ({var}): {masked_value}")
        
        return all_good
    
    def check_files_structure(self):
        """فحص بنية الملفات"""
        print("\n" + "="*60)
        print("📁 فحص بنية الملفات")
        print("="*60)
        
        required_files = {
            'main.py': 'الملف الرئيسي',
            'telegram_bot.db': 'قاعدة البيانات',
            'bot_package/bot_simple.py': 'كود البوت',
            'userbot_service/userbot.py': 'خدمة UserBot',
            'database/database.py': 'إدارة قاعدة البيانات'
        }
        
        all_good = True
        for file_path, description in required_files.items():
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                print(f"✅ {description}: موجود ({size} بايت)")
            else:
                print(f"❌ {description}: مفقود")
                all_good = False
        
        return all_good
    
    def analyze_session_errors(self):
        """تحليل أخطاء الجلسات"""
        print("\n" + "="*60)
        print("🔍 تحليل أخطاء الجلسات")
        print("="*60)
        
        try:
            conn = self.get_database_connection()
            if not conn:
                return False
                
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, phone_number, last_error_message, connection_errors, last_error_time
                FROM user_sessions 
                WHERE is_authenticated = 1 AND (is_healthy = 0 OR connection_errors > 0)
            """)
            
            problem_sessions = cursor.fetchall()
            
            if not problem_sessions:
                print("✅ لا توجد جلسات معطلة")
                conn.close()
                return True
            
            print(f"⚠️ تم العثور على {len(problem_sessions)} جلسة معطلة:")
            
            ip_conflict_count = 0
            auth_key_errors = 0
            other_errors = 0
            
            for session in problem_sessions:
                print(f"\n👤 المستخدم {session['user_id']} ({session['phone_number']}):")
                print(f"   🔄 عدد الأخطاء: {session['connection_errors']}")
                print(f"   ⏰ آخر خطأ: {session['last_error_time']}")
                
                error_msg = session['last_error_message'] or ""
                if "authorization key" in error_msg.lower() and "different IP" in error_msg.lower():
                    print("   🚫 نوع الخطأ: تضارب IP addresses")
                    print("   💡 الحل: إعادة تسجيل الدخول مطلوبة")
                    ip_conflict_count += 1
                elif "authorization key" in error_msg.lower():
                    print("   🚫 نوع الخطأ: مشكلة مفتاح المصادقة")
                    auth_key_errors += 1
                else:
                    print(f"   🚫 نوع الخطأ: {error_msg}")
                    other_errors += 1
            
            print(f"\n📊 ملخص الأخطاء:")
            print(f"   🔄 تضارب IP: {ip_conflict_count}")
            print(f"   🔑 أخطاء مصادقة: {auth_key_errors}")
            print(f"   ❓ أخطاء أخرى: {other_errors}")
            
            conn.close()
            return False
            
        except Exception as e:
            print(f"❌ خطأ في تحليل أخطاء الجلسات: {e}")
            return False
    
    def generate_repair_recommendations(self):
        """توليد توصيات الإصلاح"""
        print("\n" + "="*60)
        print("🔧 توصيات الإصلاح")
        print("="*60)
        
        print("لإصلاح مشاكل البوت، اتبع هذه الخطوات:")
        print("\n1️⃣ حل مشكلة تضارب IP:")
        print("   • أوقف جميع النسخ الأخرى من البوت")
        print("   • أعد تشغيل Replit مرة واحدة")
        print("   • انتظر 5 دقائق قبل إعادة التشغيل")
        
        print("\n2️⃣ إعادة تسجيل الدخول للمستخدمين:")
        print("   • المستخدمون يحتاجون إرسال /start للبوت")
        print("   • اختيار 'تسجيل الدخول برقم الهاتف'")
        print("   • إدخال رقم الهاتف ورمز التحقق")
        
        print("\n3️⃣ فحص صحة النظام:")
        print("   • تأكد من أن البوت يرد على /start")
        print("   • تحقق من عمل إنشاء المهام")
        print("   • اختبر توجيه رسالة بسيطة")
        
        print("\n4️⃣ مراقبة الأداء:")
        print("   • راقب سجلات النظام للأخطاء")
        print("   • تحقق من استقرار الاتصالات")
        print("   • تأكد من عدم انقطاع الخدمة")
    
    def quick_fix_attempt(self):
        """محاولة إصلاح سريعة"""
        print("\n" + "="*60)
        print("⚡ محاولة إصلاح سريعة")
        print("="*60)
        
        try:
            # حذف الجلسات التالفة من قاعدة البيانات
            conn = self.get_database_connection()
            if not conn:
                return False
            
            cursor = conn.cursor()
            
            # تحديث حالة الجلسات المعطلة
            cursor.execute("""
                UPDATE user_sessions 
                SET is_healthy = 0, connection_errors = connection_errors + 1,
                    last_error_time = CURRENT_TIMESTAMP,
                    last_error_message = 'Session reset required due to IP conflict'
                WHERE is_authenticated = 1 AND is_healthy = 1
            """)
            
            affected_rows = cursor.rowcount
            conn.commit()
            conn.close()
            
            print(f"✅ تم تحديث {affected_rows} جلسة")
            print("💡 المستخدمون سيحتاجون إعادة تسجيل الدخول")
            
            return True
            
        except Exception as e:
            print(f"❌ خطأ في الإصلاح السريع: {e}")
            return False
    
    def run_full_health_check(self):
        """تشغيل فحص شامل للبوت"""
        print("🏥 بدء فحص صحة البوت الشامل")
        print("⏰ " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        checks = [
            ("فحص متغيرات البيئة", self.check_environment_variables),
            ("فحص بنية الملفات", self.check_files_structure),
            ("فحص قاعدة البيانات", self.check_database_health),
            ("تحليل أخطاء الجلسات", self.analyze_session_errors),
        ]
        
        passed_checks = 0
        total_checks = len(checks)
        
        for check_name, check_function in checks:
            try:
                result = check_function()
                if result:
                    passed_checks += 1
            except Exception as e:
                logger.error(f"خطأ في {check_name}: {e}")
        
        # عرض النتيجة النهائية
        print("\n" + "="*60)
        print("📊 ملخص الفحص النهائي")
        print("="*60)
        
        health_percentage = (passed_checks / total_checks) * 100
        
        if health_percentage >= 75:
            status = "✅ صحة جيدة"
        elif health_percentage >= 50:
            status = "⚠️ يحتاج صيانة"
        else:
            status = "❌ يحتاج إصلاح فوري"
        
        print(f"🎯 حالة البوت: {status}")
        print(f"📈 نسبة الصحة: {health_percentage:.1f}%")
        print(f"✅ الفحوصات الناجحة: {passed_checks}/{total_checks}")
        
        # عرض التوصيات
        self.generate_repair_recommendations()
        
        return health_percentage >= 50

def main():
    """الدالة الرئيسية"""
    print("🚀 مرحباً بك في فاحص صحة البوت")
    
    checker = BotHealthChecker()
    
    try:
        # تشغيل الفحص الشامل
        is_healthy = checker.run_full_health_check()
        
        # سؤال المستخدم عن الإصلاح السريع
        print("\n" + "="*60)
        if not is_healthy:
            print("❓ هل تريد تطبيق الإصلاح السريع؟ (y/n): ", end="")
            try:
                response = input().strip().lower()
                if response in ['y', 'yes', 'نعم']:
                    print("🔧 تطبيق الإصلاح السريع...")
                    success = checker.quick_fix_attempt()
                    if success:
                        print("✅ تم تطبيق الإصلاح السريع بنجاح")
                        print("💡 أعد تشغيل البوت الآن")
                    else:
                        print("❌ فشل الإصلاح السريع")
            except:
                pass
        
    except KeyboardInterrupt:
        print("\n⏹️ تم إيقاف الفحص بواسطة المستخدم")
    except Exception as e:
        print(f"\n❌ خطأ عام في الفحص: {e}")

if __name__ == "__main__":
    main()
