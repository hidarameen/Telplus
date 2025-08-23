#!/usr/bin/env python3
"""
اختبار مكون تثبيت FFmpeg التلقائي
"""

import sys
import os
import asyncio

# إضافة المسار للوحدات
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ffmpeg_installer import ffmpeg_installer

async def test_ffmpeg_installer():
    """اختبار مكون تثبيت FFmpeg"""
    print("🔍 اختبار مكون تثبيت FFmpeg التلقائي")
    print("="*60)
    
    # معلومات النظام
    print(f"🖥️ النظام: {ffmpeg_installer.system}")
    print(f"📦 التوزيعة: {ffmpeg_installer.distribution}")
    
    # التحقق من التثبيت الحالي
    print("\n🔍 التحقق من التثبيت الحالي:")
    is_installed = ffmpeg_installer.check_ffmpeg_installed()
    print(f"   FFmpeg مثبت: {'✅ نعم' if is_installed else '❌ لا'}")
    
    if is_installed:
        print("✅ FFmpeg مثبت بالفعل - لا حاجة للتثبيت")
        return
    
    # عرض تعليمات التثبيت اليدوي
    print("\n📋 تعليمات التثبيت اليدوي:")
    instructions = ffmpeg_installer.get_installation_instructions()
    print(instructions)
    
    # سؤال المستخدم
    print("\n🤔 هل تريد محاولة التثبيت التلقائي؟")
    print("⚠️ تحذير: هذا يتطلب صلاحيات sudo")
    print("1. نعم - محاولة التثبيت التلقائي")
    print("2. لا - التثبيت اليدوي")
    
    try:
        choice = input("اختر (1 أو 2): ").strip()
        
        if choice == "1":
            print("\n🚀 بدء التثبيت التلقائي...")
            success, message = ffmpeg_installer.install_ffmpeg()
            
            if success:
                print(f"✅ {message}")
                
                # التحقق مرة أخرى
                is_installed = ffmpeg_installer.check_ffmpeg_installed()
                if is_installed:
                    print("🎉 تم تثبيت FFmpeg بنجاح!")
                else:
                    print("⚠️ FFmpeg مثبت لكن غير متاح في PATH")
            else:
                print(f"❌ {message}")
                print("\n📋 يرجى اتباع التعليمات اليدوية أعلاه")
        else:
            print("✅ سيتم التثبيت اليدوي")
            
    except KeyboardInterrupt:
        print("\n❌ تم إلغاء العملية")
    except Exception as e:
        print(f"❌ خطأ: {e}")

if __name__ == "__main__":
    asyncio.run(test_ffmpeg_installer())