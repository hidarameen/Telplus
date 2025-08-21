#!/usr/bin/env python3
"""
إصلاح إرسال الفيديوهات لتظهر بشكل صحيح مع معاينة ومدة زمنية
"""

# إضافة دعم فيديو إلى send_file_helper.py
video_functions = '''
def _is_video_filename(name: str) -> bool:
    """فحص إذا كان اسم الملف يدل على فيديو"""
    try:
        lower = name.lower()
        return lower.endswith((".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v", ".3gp", ".flv", ".wmv"))
    except Exception:
        return False

def _extract_video_info_from_bytes(video_bytes: bytes, filename: str) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[bytes]]:
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
    
    return width, height, int(duration) if duration else None, thumbnail
'''

# إضافة معالج الفيديو إلى دالة الإرسال
video_handler = '''
                # CRITICAL FIX: إضافة سمات الفيديو للتأكد من ظهوره كفيديو مع معاينة ومدة
                elif _is_video_filename(filename):
                    try:
                        from telethon.tl.types import DocumentAttributeVideo, DocumentAttributeFilename
                        width, height, duration, thumbnail = _extract_video_info_from_bytes(file_data, filename)
                        attributes = list(kwargs.pop('attributes', []) or [])
                        
                        # إضافة سمة الفيديو مع الأبعاد والمدة
                        attributes.append(DocumentAttributeVideo(
                            duration=duration or 0,
                            w=width or 320,
                            h=height or 240,
                            round_message=False,
                            supports_streaming=True  # يدعم التشغيل المباشر
                        ))
                        
                        # تأكيد اسم الملف كسِمة ضمن الوثيقة
                        attributes.append(DocumentAttributeFilename(file_name=filename))
                        kwargs['attributes'] = attributes
                        kwargs.setdefault('force_document', False)  # لا نرسله كمستند
                        
                        # إضافة المعاينة إن توفرت
                        if thumbnail and not kwargs.get('thumb'):
                            kwargs['thumb'] = thumbnail
                            logger.info("🖼️ تم تعيين معاينة للفيديو")
                        
                        logger.info(f"🎬 إضافة سمات فيديو: width={width}, height={height}, duration={duration}, streaming=True")
                    except Exception as e_attr:
                        logger.warning(f"⚠️ تعذر إضافة سمات الفيديو: {e_attr}")
'''

if __name__ == "__main__":
    print("تم إنشاء ملف الإصلاح لإرسال الفيديوهات")
    print("يجب إضافة الدوال إلى send_file_helper.py وتطبيق المعالج")