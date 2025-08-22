
#!/usr/bin/env python3
"""
أداة التنصيب التلقائي لبوت التوجيه التلقائي - تليجرام
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

class BotInstaller:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.env_file = self.project_root / ".env"
        self.env_example = self.project_root / ".env.example"
        
    def print_header(self):
        """طباعة رأس التنصيب"""
        print("=" * 60)
        print("🤖 أداة التنصيب التلقائي - بوت التوجيه التلقائي")
        print("=" * 60)
        
    def check_python_version(self):
        """فحص إصدار Python"""
        print("🐍 فحص إصدار Python...")
        version = sys.version_info
        if version.major != 3 or version.minor < 11:
            print("❌ يتطلب Python 3.11 أو أحدث")
            print(f"   الإصدار الحالي: {version.major}.{version.minor}.{version.micro}")
            return False
        print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
        
    def install_dependencies(self):
        """تنصيب المكتبات المطلوبة"""
        print("\n📦 تنصيب المكتبات المطلوبة...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
            ])
            print("✅ تم تنصيب جميع المكتبات بنجاح")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ فشل في تنصيب المكتبات: {e}")
            return False
            
    def setup_environment(self):
        """إعداد ملف متغيرات البيئة"""
        print("\n🔧 إعداد متغيرات البيئة...")
        
        if not self.env_file.exists():
            if self.env_example.exists():
                shutil.copy2(self.env_example, self.env_file)
                print(f"✅ تم إنشاء ملف .env من {self.env_example.name}")
            else:
                self.create_env_file()
                
        print("📝 يرجى تحديث ملف .env بالقيم الصحيحة:")
        print("   1. BOT_TOKEN من @BotFather")
        print("   2. API_ID و API_HASH من my.telegram.org")
        print("   3. SECRET_KEY (اختياري)")
        
        return True
        
    def create_env_file(self):
        """إنشاء ملف .env أساسي"""
        env_content = """# معرف البوت من BotFather
BOT_TOKEN=your_bot_token_here

# معرف التطبيق من my.telegram.org
API_ID=12345

# رمز التطبيق من my.telegram.org
API_HASH=your_api_hash_here

# مفتاح سري للتطبيق
SECRET_KEY=your_secret_key_here

# رابط قاعدة البيانات
DATABASE_URL=sqlite:///telegram_bot.db
"""
        with open(self.env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        print("✅ تم إنشاء ملف .env")
        
    def check_database(self):
        """فحص قاعدة البيانات"""
        print("\n🗄️ فحص قاعدة البيانات...")
        try:
            from database.database import Database
            db = Database()
            print("✅ قاعدة البيانات جاهزة")
            return True
        except Exception as e:
            print(f"❌ خطأ في قاعدة البيانات: {e}")
            return False
            
    def create_directories(self):
        """إنشاء المجلدات المطلوبة"""
        print("\n📁 إنشاء المجلدات المطلوبة...")
        
        directories = [
            "watermark_images",
            "attached_assets",
            "static",
            "templates"
        ]
        
        for directory in directories:
            dir_path = self.project_root / directory
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f"✅ تم إنشاء مجلد: {directory}")
            else:
                print(f"📁 موجود بالفعل: {directory}")
                
        return True
        
    def print_completion_guide(self):
        """طباعة دليل إكمال التنصيب"""
        print("\n" + "=" * 60)
        print("🎉 تم التنصيب بنجاح!")
        print("=" * 60)
        print("📋 الخطوات التالية:")
        print("  1. حدث ملف .env بالقيم الصحيحة")
        print("  2. شغل البوت: python run.py")
        print("  3. ابحث عن البوت في تليجرام وابدأ بـ /start")
        print("\n🔗 روابط مفيدة:")
        print("  • إنشاء بوت: https://t.me/BotFather")
        print("  • الحصول على API: https://my.telegram.org")
        print("=" * 60)
        
    def run(self):
        """تشغيل عملية التنصيب"""
        self.print_header()
        
        # فحص إصدار Python
        if not self.check_python_version():
            return False
            
        # تنصيب المكتبات
        if not self.install_dependencies():
            return False
            
        # إعداد البيئة
        if not self.setup_environment():
            return False
            
        # إنشاء المجلدات
        if not self.create_directories():
            return False
            
        # فحص قاعدة البيانات
        self.check_database()
        
        # طباعة دليل الإكمال
        self.print_completion_guide()
        
        return True

def main():
    """الدالة الرئيسية"""
    installer = BotInstaller()
    
    try:
        success = installer.run()
        if success:
            print("✅ تم إكمال التنصيب بنجاح")
            sys.exit(0)
        else:
            print("❌ فشل في التنصيب")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️ تم إلغاء التنصيب")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ خطأ غير متوقع: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
