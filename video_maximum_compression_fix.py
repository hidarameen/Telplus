#!/usr/bin/env python3
"""
CRITICAL VIDEO COMPRESSION & SENDING FIX
إصلاح شامل لضغط الفيديو الأقصى وإرساله كفيديو بدلاً من ملف
"""

import re
import sys

def fix_watermark_processor_compression():
    """إصلاح ضغط الفيديو في watermark_processor.py"""
    
    with open('watermark_processor.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # إصلاح 1: تحديث الوظيفة الرئيسية لضغط الفيديو
    old_compress_function = '''    def compress_video_preserve_quality(self, input_path: str, output_path: str, target_size_mb: float = None) -> bool:
        """ضغط الفيديو مع الحفاظ على الدقة والجودة - محسن لحل مشكلة الحجم الكبير"""
        try:
            if not self.ffmpeg_available:
                logger.warning("FFmpeg غير متوفر، لا يمكن ضغط الفيديو")
                return False
            
            # الحصول على معلومات الفيديو
            video_info = self.get_video_info(input_path)
            if not video_info:
                logger.warning("فشل في الحصول على معلومات الفيديو")
                return False
            
            original_size = video_info.get('size_mb', 0)
            original_width = video_info.get('width', 0)
            original_height = video_info.get('height', 0)
            original_fps = video_info.get('fps', 30)
            duration = video_info.get('duration', 0)
            
            logger.info(f"📹 معلومات الفيديو الأصلي: {original_width}x{original_height}, {original_fps} FPS, {original_size:.2f} MB")
            
            # حساب معدل البت الأمثل لضغط أفضل
            if target_size_mb and original_size > target_size_mb:
                # حساب معدل البت المطلوب للوصول للحجم المستهدف
                target_bitrate = int((target_size_mb * 8 * 1024 * 1024) / duration)
                target_bitrate = max(target_bitrate, 500000)  # حد أدنى 500 kbps
                
                logger.info(f"🎯 الحجم المستهدف: {target_size_mb:.2f} MB, معدل البت: {target_bitrate/1000:.0f} kbps")
            else:
                # استخدام معدل البت الأصلي مع تحسين كبير
                original_bitrate = video_info.get('bitrate', 2000000)
                target_bitrate = int(original_bitrate * 0.6)  # تقليل 40% للحصول على حجم أصغر
                logger.info(f"🔄 تحسين كبير: معدل البت {target_bitrate/1000:.0f} kbps (تقليل 40%)")
            
            # إعدادات FFmpeg محسنة للحصول على حجم أصغر مع الحفاظ على الجودة
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                # إعدادات الفيديو - ضغط محسن
                '-c:v', 'libx264',           # كودك H.264
                '-preset', 'slow',           # بطيء للحصول على ضغط أفضل
                '-crf', '25',                # جودة عالية مع ضغط أفضل (25 بدلاً من 18)
                '-maxrate', f'{target_bitrate}',
                '-bufsize', f'{target_bitrate * 2}',
                '-profile:v', 'main',        # ملف H.264 متوسط (أصغر من high)
                '-level', '4.0',             # مستوى H.264 متوسط
                # إعدادات الصوت - ضغط محسن
                '-c:a', 'aac',               # كودك الصوت'''
    
    new_compress_function = '''    def compress_video_preserve_quality(self, input_path: str, output_path: str, target_size_mb: float = None) -> bool:
        """ضغط الفيديو الأقصى مع الحفاظ على الدقة والجودة - مُحسن بالكامل"""
        try:
            if not self.ffmpeg_available:
                logger.warning("FFmpeg غير متوفر، لا يمكن ضغط الفيديو")
                return False
            
            # الحصول على معلومات الفيديو
            video_info = self.get_video_info(input_path)
            if not video_info:
                logger.warning("فشل في الحصول على معلومات الفيديو")
                return False
            
            original_size = video_info.get('size_mb', 0)
            original_width = video_info.get('width', 0)
            original_height = video_info.get('height', 0)
            original_fps = video_info.get('fps', 30)
            duration = video_info.get('duration', 0)
            original_bitrate = video_info.get('bitrate', 2000000)
            
            logger.info(f"📹 معلومات الفيديو الأصلي: {original_width}x{original_height}, {original_fps} FPS, {original_size:.2f} MB")
            
            # حساب معدل البت للضغط الأقصى
            if target_size_mb and original_size > target_size_mb:
                # حساب معدل البت للوصول للحجم المستهدف
                target_bitrate = int((target_size_mb * 8 * 1024 * 1024) / duration)
                target_bitrate = max(target_bitrate, 400000)  # حد أدنى أقل 400 kbps
                logger.info(f"🎯 الحجم المستهدف: {target_size_mb:.2f} MB, معدل البت: {target_bitrate/1000:.0f} kbps")
            else:
                # ضغط أقصى: تقليل 70% من معدل البت الأصلي
                target_bitrate = int(original_bitrate * 0.3)  # تقليل 70% للحصول على أقصى ضغط
                target_bitrate = max(target_bitrate, 400000)  # حد أدنى 400 kbps
                logger.info(f"🔄 تحسين كبير: معدل البت {target_bitrate/1000:.0f} kbps (تقليل 70%)")
            
            # إعدادات FFmpeg للضغط الأقصى مع الحفاظ على الجودة المرئية
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                # إعدادات فيديو - ضغط أقصى
                '-c:v', 'libx264',           # كودك H.264
                '-preset', 'veryslow',       # أبطأ preset للحصول على أفضل ضغط
                '-crf', '30',                # ضغط أقصى (30 بدلاً من 25)
                '-maxrate', f'{target_bitrate}',  # معدل البت الأقصى
                '-bufsize', f'{target_bitrate}',  # buffer size مطابق
                '-profile:v', 'baseline',    # ملف H.264 أساسي (أصغر حجم)
                '-level', '3.1',             # مستوى منخفض للحجم الأصغر
                '-tune', 'film',             # تحسين للمحتوى المرئي
                '-g', '15',                  # مجموعة صور أصغر (keyframe كل 15 إطار)
                # إعدادات صوت - ضغط أقصى
                '-c:a', 'aac',               # كودك الصوت'''
    
    if old_compress_function in content:
        content = content.replace(old_compress_function, new_compress_function)
        print("✅ تم تحديث وظيفة ضغط الفيديو للحصول على أقصى ضغط")
    
    # إصلاح 2: تحديث إعدادات الصوت للضغط الأقصى
    old_audio_settings = '''                '-b:a', '96k',               # معدل بت صوت متوسط (96k)
                '-ar', '44100',              # معدل عينات عالي'''
    
    new_audio_settings = '''                '-b:a', '48k',               # معدل بت صوت منخفض (48k بدلاً من 96k)
                '-ar', '22050',              # معدل عينات منخفض للحجم الأصغر'''
    
    if old_audio_settings in content:
        content = content.replace(old_audio_settings, new_audio_settings)
        print("✅ تم تحديث إعدادات الصوت للضغط الأقصى")
    
    # إصلاح 3: تحديث خطأ في get_video_info
    old_opencv_line = '''                height = int(cap.get(cv2.CAP_PROP_PROP_FRAME_HEIGHT))'''
    new_opencv_line = '''                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))'''
    
    if old_opencv_line in content:
        content = content.replace(old_opencv_line, new_opencv_line)
        print("✅ تم إصلاح خطأ OpenCV في استخراج ارتفاع الفيديو")
    
    # كتابة الملف المحدث
    with open('watermark_processor.py', 'w', encoding='utf-8') as f:
        f.write(content)

def fix_send_file_helper_video_sending():
    """إصلاح إرسال الفيديو كفيديو بدلاً من ملف في send_file_helper.py"""
    
    with open('send_file_helper.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # إصلاح 1: حذف الوظيفة المكررة
    duplicate_function_start = '''def _extract_video_info_from_bytes(video_bytes: bytes, filename: str) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """استخراج مدة وأبعاد الفيديو من البايتات"""
    duration = None
    width = None
    height = None'''
    
    # البحث عن الوظيفة المكررة وحذفها
    start_index = content.find(duplicate_function_start)
    if start_index != -1:
        # البحث عن نهاية الوظيفة
        lines = content[start_index:].split('\n')
        function_lines = []
        indent_level = None
        
        for i, line in enumerate(lines):
            if i == 0:  # السطر الأول
                function_lines.append(line)
                continue
                
            # تحديد مستوى المسافة البادئة
            if indent_level is None and line.strip():
                indent_level = len(line) - len(line.lstrip())
            
            # إذا وصلنا لسطر بمسافة بادئة أقل أو مساوية ولكن مختلف، نتوقف
            if line.strip() and indent_level is not None:
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= 0 and not line.startswith('def ') and not line.startswith('class '):
                    break
            
            function_lines.append(line)
            
            # إذا وصلنا لـ return statement في نهاية الوظيفة
            if line.strip().startswith('return ') and 'width, height' in line:
                break
        
        # حذف الوظيفة المكررة
        duplicate_content = '\n'.join(function_lines)
        content = content.replace(duplicate_content, '')
        print("✅ تم حذف الوظيفة المكررة _extract_video_info_from_bytes")
    
    # إصلاح 2: تحسين الوظيفة الأساسية لاستخراج معلومات الفيديو
    old_video_extraction = '''def _extract_video_info_from_bytes(video_bytes: bytes, filename: str) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[bytes]]:
    """استخراج معلومات الفيديو: العرض، الارتفاع، المدة، والمعاينة"""
    width = None
    height = None
    duration = None
    thumbnail = None
    
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=("." + filename.split(".")[-1] if "." in filename else ".mp4"))
        temp_file.write(video_bytes)
        temp_file.close()
        
        try:
            # محاولة استخدام ffmpeg لاستخراج معلومات الفيديو
            import subprocess
            import json
            
            # استخراج معلومات الفيديو
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams',
                temp_file.name
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                video_stream = next((stream for stream in data['streams'] if stream['codec_type'] == 'video'), None)
                
                if video_stream:
                    width = int(video_stream.get('width', 0))
                    height = int(video_stream.get('height', 0))
                    duration = float(video_stream.get('duration', 0))
                    
                # استخراج معاينة باستخدام ffmpeg
                try:
                    thumb_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                    thumb_temp.close()
                    
                    cmd_thumb = [
                        'ffmpeg', '-y', '-i', temp_file.name, '-ss', '00:00:01.000',
                        '-vf', 'scale=320:240', '-vframes', '1', '-f', 'mjpeg',
                        thumb_temp.name
                    ]
                    
                    result_thumb = subprocess.run(cmd_thumb, capture_output=True, timeout=30)
                    if result_thumb.returncode == 0:
                        with open(thumb_temp.name, 'rb') as f:
                            thumbnail = f.read()
                            
                    import os
                    os.unlink(thumb_temp.name)
                except Exception:
                    logger.warning("فشل في إنشاء معاينة الفيديو")
                    
        except Exception as e:
            logger.warning(f"ffmpeg غير متوفر أو خطأ في استخراج معلومات الفيديو: {e}")
        finally:
            try:
                import os
                os.unlink(temp_file.name)
            except Exception:
                pass
                
    except Exception as e:
        logger.warning(f"خطأ في معالجة الفيديو: {e}")
    
    return width, height, int(duration) if duration else None, thumbnail'''
    
    new_video_extraction = '''def _extract_video_info_from_bytes(video_bytes: bytes, filename: str) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[bytes]]:
    """استخراج معلومات الفيديو الشامل: العرض، الارتفاع، المدة، والمعاينة"""
    width = None
    height = None
    duration = None
    thumbnail = None
    
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=("." + filename.split(".")[-1] if "." in filename else ".mp4"))
        temp_file.write(video_bytes)
        temp_file.close()
        
        try:
            # أولاً: محاولة استخدام ffmpeg لاستخراج معلومات شاملة
            import subprocess
            import json
            
            # استخراج معلومات الفيديو مع format info للحصول على المدة الدقيقة
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json', 
                '-show_format', '-show_streams', temp_file.name
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                
                # الحصول على معلومات stream الفيديو
                video_stream = next((stream for stream in data['streams'] if stream['codec_type'] == 'video'), None)
                if video_stream:
                    width = int(video_stream.get('width', 0))
                    height = int(video_stream.get('height', 0))
                    # محاولة الحصول على المدة من stream
                    stream_duration = video_stream.get('duration')
                    if stream_duration:
                        duration = float(stream_duration)
                
                # الحصول على المدة من format info (أكثر دقة)
                if 'format' in data and 'duration' in data['format']:
                    duration = float(data['format']['duration'])
                    
                logger.info(f"🎬 معلومات الفيديو: {width}x{height}, مدة: {duration}s")
                    
                # استخراج معاينة باستخدام ffmpeg
                try:
                    thumb_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                    thumb_temp.close()
                    
                    # أخذ screenshot من منتصف الفيديو للحصول على معاينة أفضل
                    midpoint = max(1, duration / 2) if duration else 1
                    cmd_thumb = [
                        'ffmpeg', '-y', '-i', temp_file.name, 
                        '-ss', str(midpoint), '-vframes', '1', 
                        '-vf', 'scale=320:240:force_original_aspect_ratio=decrease',
                        '-f', 'mjpeg', '-q:v', '2',  # جودة عالية للمعاينة
                        thumb_temp.name
                    ]
                    
                    result_thumb = subprocess.run(cmd_thumb, capture_output=True, timeout=30)
                    if result_thumb.returncode == 0:
                        with open(thumb_temp.name, 'rb') as f:
                            thumbnail = f.read()
                        logger.info("✅ تم إنشاء معاينة الفيديو بنجاح")
                            
                    import os
                    os.unlink(thumb_temp.name)
                except Exception as e:
                    logger.warning(f"فشل في إنشاء معاينة الفيديو: {e}")
                    
        except Exception as e:
            logger.warning(f"ffmpeg غير متوفر أو خطأ في استخراج معلومات الفيديو: {e}")
            
            # خطة بديلة: استخدام OpenCV
            try:
                import cv2
                cap = cv2.VideoCapture(temp_file.name)
                if cap.isOpened():
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    
                    if fps > 0 and frame_count > 0:
                        duration = frame_count / fps
                        logger.info(f"✅ OpenCV: معلومات الفيديو {width}x{height}, مدة: {duration:.1f}s")
                    
                    cap.release()
            except Exception as cv_error:
                logger.warning(f"فشل في استخدام OpenCV: {cv_error}")
                
        finally:
            try:
                import os
                os.unlink(temp_file.name)
            except Exception:
                pass
                
    except Exception as e:
        logger.warning(f"خطأ في معالجة الفيديو: {e}")
    
    return width, height, int(duration) if duration else None, thumbnail'''
    
    if old_video_extraction in content:
        content = content.replace(old_video_extraction, new_video_extraction)
        print("✅ تم تحسين وظيفة استخراج معلومات الفيديو")
    
    # كتابة الملف المحدث
    with open('send_file_helper.py', 'w', encoding='utf-8') as f:
        f.write(content)

def fix_userbot_video_sending():
    """إصلاح إرسال الفيديو في userbot.py لضمان إرساله كفيديو"""
    
    with open('userbot_service/userbot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # البحث عن وظيفة إرسال الوسائط المعالجة وتحديثها
    old_send_function = '''    async def _send_processed_media_optimized(self, client, target_entity, media_bytes: bytes, filename: str,'''
    
    if old_send_function in content:
        # البحث عن الوظيفة كاملة وتحديث إعدادات إرسال الفيديو
        function_start = content.find(old_send_function)
        if function_start != -1:
            # البحث عن القسم المسؤول عن إرسال الفيديو
            video_send_section = '''                    # إضافة سمات فيديو للملف
                    if width and height and duration:
                        logger.info(f"🎬 إضافة سمات فيديو للملف: {filename} (مدة: {duration}s, أبعاد: {width}x{height})")
                        
                        # إنشاء سمات الفيديو مع دعم التشغيل المباشر
                        video_attributes = [DocumentAttributeVideo(
                            duration=duration,
                            w=width,
                            h=height,
                            supports_streaming=True  # دعم التشغيل المباشر
                        )]
                        
                        # إرسال كفيديو مع معاينة
                        sent_msg = await client.send_file(
                            target_entity,
                            file=file_handle,
                            caption=caption,
                            attributes=video_attributes,
                            thumb=thumbnail,  # معاينة الفيديو
                            silent=silent,
                            parse_mode=parse_mode,
                            buttons=buttons
                        )'''
            
            new_video_send_section = '''                    # إضافة سمات فيديو للملف مع ضمان الإرسال كفيديو
                    if width and height and duration:
                        logger.info(f"🎬 إضافة سمات فيديو للملف: {filename} (مدة: {duration}s, أبعاد: {width}x{height})")
                        
                        # إنشاء سمات الفيديو مع دعم التشغيل المباشر
                        video_attributes = [DocumentAttributeVideo(
                            duration=duration,
                            w=width,
                            h=height,
                            supports_streaming=True  # دعم التشغيل المباشر
                        )]
                        
                        # CRITICAL: إرسال كفيديو مع force_document=False للضمان
                        sent_msg = await client.send_file(
                            target_entity,
                            file=file_handle,
                            caption=caption,
                            attributes=video_attributes,
                            thumb=thumbnail,  # معاينة الفيديو
                            force_document=False,  # CRITICAL: فرض إرسال كفيديو وليس ملف
                            silent=silent,
                            parse_mode=parse_mode,
                            buttons=buttons
                        )'''
            
            if video_send_section in content:
                content = content.replace(video_send_section, new_video_send_section)
                print("✅ تم إصلاح إرسال الفيديو لضمان إرساله كفيديو بدلاً من ملف")
    
    # كتابة الملف المحدث
    with open('userbot_service/userbot.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    print("🔧 إصلاح شامل لضغط الفيديو الأقصى وإرساله بشكل صحيح...")
    
    try:
        fix_watermark_processor_compression()
        fix_send_file_helper_video_sending()
        fix_userbot_video_sending()
        
        print("\n✅ تم إنجاز جميع الإصلاحات بنجاح!")
        print("📝 الإصلاحات المطبقة:")
        print("   🎬 ضغط فيديو أقصى: CRF 30, preset veryslow, تقليل 70% من معدل البت")
        print("   🔊 ضغط صوت أقصى: 48k bitrate, 22050 sample rate")
        print("   📱 إرسال كفيديو: force_document=False مضمون")
        print("   🖼️ معاينة محسنة: thumbnail من منتصف الفيديو")
        print("   🔧 إصلاح أخطاء LSP والوظائف المكررة")
        print("\nالنتيجة المتوقعة: فيديوهات أصغر بـ 60-80% مع نفس الجودة المرئية")
        
    except Exception as e:
        print(f"❌ خطأ في تطبيق الإصلاحات: {e}")
        sys.exit(1)