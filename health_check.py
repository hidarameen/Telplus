#!/usr/bin/env python3
"""
فحص صحة البوت المحسن
Enhanced Bot Health Check Script
"""

import os
import sys
import subprocess
import importlib
from pathlib import Path

def check_python_version():
    """فحص إصدار Python"""
    print("🐍 فحص إصدار Python...")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python {version.major}.{version.minor} غير مدعوم")
        print("يرجى تثبيت Python 3.8+")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_ffmpeg():
    """فحص FFmpeg"""
    print("\n🎬 فحص FFmpeg...")
    
    try:
        # فحص ffmpeg
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✅ FFmpeg: {version_line}")
        else:
            print("❌ FFmpeg غير مثبت أو لا يعمل")
            return False
    except FileNotFoundError:
        print("❌ FFmpeg غير مثبت")
        print("لتثبيت: sudo apt install ffmpeg")
        return False
    except subprocess.TimeoutExpired:
        print("⚠️ فشل في فحص FFmpeg (مهلة زمنية)")
        return False
    
    try:
        # فحص ffprobe
        result = subprocess.run(['ffprobe', '-version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✅ ffprobe: {version_line}")
        else:
            print("❌ ffprobe غير مثبت أو لا يعمل")
            return False
    except FileNotFoundError:
        print("❌ ffprobe غير مثبت")
        return False
    except subprocess.TimeoutExpired:
        print("⚠️ فشل في فحص ffprobe (مهلة زمنية)")
        return False
    
    return True

def check_python_packages():
    """فحص مكتبات Python"""
    print("\n📦 فحص مكتبات Python...")
    
    required_packages = [
        'telethon',
        'cv2',  # opencv-python
        'PIL',  # Pillow
        'numpy',
        'flask',
        'psycopg2',
        'requests',
        'cryptography'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'cv2':
                importlib.import_module('cv2')
                print(f"✅ opencv-python")
            elif package == 'PIL':
                importlib.import_module('PIL')
                print(f"✅ Pillow")
            else:
                importlib.import_module(package)
                print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package}")
    
    if missing_packages:
        print(f"\n⚠️ المكتبات المفقودة: {missing_packages}")
        print("لتثبيت: pip install -r requirements.txt")
        return False
    
    return True

def check_files():
    """فحص الملفات المطلوبة"""
    print("\n📁 فحص الملفات...")
    
    required_files = [
        'main.py',
        'requirements.txt',
        'watermark_processor.py',
        'userbot_service/userbot.py',
        'database/database.py'
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            missing_files.append(file_path)
            print(f"❌ {file_path}")
    
    if missing_files:
        print(f"\n⚠️ الملفات المفقودة: {missing_files}")
        return False
    
    return True

def check_directories():
    """فحص المجلدات المطلوبة"""
    print("\n📂 فحص المجلدات...")
    
    required_dirs = [
        'watermark_images',
        'database',
        'userbot_service',
        'bot_package'
    ]
    
    missing_dirs = []
    
    for dir_path in required_dirs:
        if Path(dir_path).exists() and Path(dir_path).is_dir():
            print(f"✅ {dir_path}/")
        else:
            missing_dirs.append(dir_path)
            print(f"❌ {dir_path}/")
    
    if missing_dirs:
        print(f"\n⚠️ المجلدات المفقودة: {missing_dirs}")
        return False
    
    return True

def check_environment():
    """فحص متغيرات البيئة"""
    print("\n🔧 فحص متغيرات البيئة...")
    
    required_env_vars = [
        'API_ID',
        'API_HASH',
        'BOT_TOKEN'
    ]
    
    missing_env_vars = []
    
    for env_var in required_env_vars:
        if os.getenv(env_var):
            # إخفاء القيم الحساسة
            value = os.getenv(env_var)
            if len(value) > 8:
                masked_value = value[:4] + '*' * (len(value) - 8) + value[-4:]
            else:
                masked_value = '*' * len(value)
            print(f"✅ {env_var}: {masked_value}")
        else:
            missing_env_vars.append(env_var)
            print(f"❌ {env_var}")
    
    if missing_env_vars:
        print(f"\n⚠️ متغيرات البيئة المفقودة: {missing_env_vars}")
        print("يرجى إعداد ملف .env")
        return False
    
    return True

def check_database():
    """فحص قاعدة البيانات"""
    print("\n🗄️ فحص قاعدة البيانات...")
    
    db_file = Path('telegram_bot.db')
    if db_file.exists():
        size_mb = db_file.stat().st_size / (1024 * 1024)
        print(f"✅ قاعدة البيانات موجودة ({size_mb:.2f} MB)")
        return True
    else:
        print("⚠️ قاعدة البيانات غير موجودة")
        print("سيتم إنشاؤها عند أول تشغيل")
        return True

def run_health_check():
    """تشغيل فحص الصحة الكامل"""
    print("🏥 فحص صحة البوت المحسن")
    print("=" * 50)
    
    checks = [
        ("إصدار Python", check_python_version),
        ("FFmpeg", check_ffmpeg),
        ("مكتبات Python", check_python_packages),
        ("الملفات", check_files),
        ("المجلدات", check_directories),
        ("متغيرات البيئة", check_environment),
        ("قاعدة البيانات", check_database)
    ]
    
    results = []
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ خطأ في فحص {check_name}: {e}")
            results.append((check_name, False))
    
    print("\n" + "=" * 50)
    print("📊 نتائج فحص الصحة:")
    
    passed = 0
    total = len(results)
    
    for check_name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {check_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 النتيجة: {passed}/{total} فحوصات نجحت")
    
    if passed == total:
        print("🎉 البوت جاهز للتشغيل!")
        return True
    else:
        print("⚠️ يرجى إصلاح المشاكل قبل التشغيل")
        return False

if __name__ == "__main__":
    success = run_health_check()
    sys.exit(0 if success else 1)