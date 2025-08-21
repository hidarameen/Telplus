#!/usr/bin/env python3
"""
CRITICAL FIX: Video Maximum Compression and Send as Video (not file)
إصلاح شامل لضغط الفيديو الأقصى وإرساله كفيديو وليس كملف
"""

import sys
import os

def fix_video_compression():
    """إصلاح إعدادات ضغط الفيديو للحصول على ضغط أقصى"""
    
    # قراءة ملف watermark_processor.py
    with open('watermark_processor.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # إصلاح 1: تحسين ضغط الفيديو الأقصى
    old_compression = """                    # إعدادات FFmpeg محسنة
                    cmd = [
                        'ffmpeg', '-i', input_path,
                        '-c:v', 'libx264',  # كودك H.264
                        '-preset', 'medium',  # توازن بين السرعة والجودة
                        '-crf', '25',  # جودة ثابتة محسنة (25 بدلاً من 23)
                        '-maxrate', f'{target_bitrate}',
                        '-bufsize', f'{target_bitrate * 2}',
                        '-c:a', 'aac',  # كودك الصوت
                        '-b:a', '96k',  # معدل بت صوت أقل
                        '-movflags', '+faststart',  # تحسين التشغيل
                        '-pix_fmt', 'yuv420p',  # تنسيق بكسل متوافق
                        '-y',  # استبدال الملف الموجود
                        output_path
                    ]"""
    
    new_compression = """                    # إعدادات FFmpeg محسنة للضغط الأقصى مع الحفاظ على الجودة
                    cmd = [
                        'ffmpeg', '-i', input_path,
                        '-c:v', 'libx264',  # كودك H.264
                        '-preset', 'slower',  # ضغط أقصى (slower بدلاً من medium)
                        '-crf', '28',  # ضغط أقصى مع جودة مقبولة (28 بدلاً من 25)
                        '-maxrate', f'{int(target_bitrate * 0.6)}',  # تقليل معدل البت بنسبة 40%
                        '-bufsize', f'{target_bitrate}',
                        '-c:a', 'aac',  # كودك الصوت
                        '-b:a', '64k',  # معدل بت صوت أقل (64k بدلاً من 96k)
                        '-movflags', '+faststart',  # تحسين التشغيل
                        '-pix_fmt', 'yuv420p',  # تنسيق بكسل متوافق
                        '-profile:v', 'main',  # ملف H.264 متوسط (أصغر من high)
                        '-tune', 'film',  # تحسين للفيديوهات
                        '-g', '30',  # مجموعة صور كل 30 إطار
                        '-y',  # استبدال الملف الموجود
                        output_path
                    ]"""
    
    if old_compression in content:
        content = content.replace(old_compression, new_compression)
        print("✅ تم إصلاح إعدادات ضغط الفيديو الأقصى")
    
    # إصلاح 2: تقليل معدل البت أكثر
    old_bitrate = """                # استخدام معدل البت الأصلي مع تحسين كبير
                target_bitrate = int(original_bitrate * 0.7)  # تقليل 30% للحصول على حجم أصغر"""
    
    new_bitrate = """                # استخدام معدل البت الأصلي مع تحسين كبير
                target_bitrate = int(original_bitrate * 0.5)  # تقليل 50% للحصول على حجم أصغر بشكل أقصى"""
    
    if old_bitrate in content:
        content = content.replace(old_bitrate, new_bitrate)
        print("✅ تم تحسين معدل البت للضغط الأقصى")
    
    # كتابة الملف المحدث
    with open('watermark_processor.py', 'w', encoding='utf-8') as f:
        f.write(content)

def fix_video_send_as_video():
    """إصلاح إرسال الفيديو كفيديو وليس كملف"""
    
    # قراءة ملف send_file_helper.py
    with open('send_file_helper.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # إصلاح 1: تحسين خصائص الفيديو
    old_video_attrs = """                        attributes.append(DocumentAttributeVideo(
                            duration=duration or 1,  # Use actual duration or at least 1 second to avoid 00:00
                            w=width or 640,
                            h=height or 480,
                            round_message=False,
                            supports_streaming=True
                        ))
                        attributes.append(DocumentAttributeFilename(file_name=filename))
                        kwargs["attributes"] = attributes
                        kwargs.setdefault("force_document", False)"""
    
    new_video_attrs = """                        attributes.append(DocumentAttributeVideo(
                            duration=duration or 1,  # Use actual duration or at least 1 second to avoid 00:00
                            w=width or 640,
                            h=height or 480,
                            round_message=False,
                            supports_streaming=True
                        ))
                        attributes.append(DocumentAttributeFilename(file_name=filename))
                        kwargs["attributes"] = attributes
                        kwargs["force_document"] = False  # CRITICAL: إجبار الإرسال كفيديو وليس ملف
                        kwargs.setdefault("parse_mode", None)  # إزالة parse_mode للفيديوهات"""
    
    if old_video_attrs in content:
        content = content.replace(old_video_attrs, new_video_attrs)
        print("✅ تم إصلاح إرسال الفيديو كفيديو وليس كملف")
    
    # كتابة الملف المحدث
    with open('send_file_helper.py', 'w', encoding='utf-8') as f:
        f.write(content)

def fix_optimized_send_method():
    """إصلاح الدالة المُحسنة لإرسال الفيديوهات كفيديو"""
    
    # قراءة ملف userbot_service/userbot.py
    with open('userbot_service/userbot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # إضافة تحقق خاص للفيديوهات في الدالة المُحسنة
    old_method = """                # Use TelethonFileSender to upload with proper attributes but cache result
                result = await TelethonFileSender.send_file_with_name(
                    client, target_entity, media_bytes, filename, **kwargs
                )"""
    
    new_method = """                # Use TelethonFileSender to upload with proper attributes but cache result
                # CRITICAL FIX: Force video files to be sent as video, not document
                if filename and filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm', '.m4v')):
                    kwargs["force_document"] = False  # إجبار الإرسال كفيديو
                    # إزالة parse_mode للفيديوهات لتجنب مشاكل التنسيق
                    if 'parse_mode' in kwargs:
                        del kwargs['parse_mode']
                
                result = await TelethonFileSender.send_file_with_name(
                    client, target_entity, media_bytes, filename, **kwargs
                )"""
    
    if old_method in content:
        content = content.replace(old_method, new_method)
        print("✅ تم إصلاح الدالة المُحسنة لإرسال الفيديوهات كفيديو")
    
    # كتابة الملف المحدث
    with open('userbot_service/userbot.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    print("🔧 بدء إصلاح ضغط الفيديو الأقصى وإرساله كفيديو...")
    
    try:
        fix_video_compression()
        fix_video_send_as_video()
        fix_optimized_send_method()
        
        print("\n✅ تم إنجاز جميع الإصلاحات بنجاح!")
        print("📝 التحسينات المطبقة:")
        print("   🎬 ضغط فيديو أقصى (CRF 28, preset slower, bitrate 50% تقليل)")
        print("   📤 إرسال الفيديو كفيديو وليس كملف (force_document=False)")
        print("   🎯 إصلاح الدالة المُحسنة للرفع")
        
    except Exception as e:
        print(f"❌ خطأ في تطبيق الإصلاحات: {e}")
        sys.exit(1)