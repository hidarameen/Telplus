"""
مساعد لإرسال الملفات مع اسم مخصص في Telethon
يحل مشكلة إرسال البيانات الخام (bytes) مع اسم ملف صحيح
ويضيف سمات خاصة للصوت لضمان إرساله كملف موسيقى وليس مستند.
"""
import io
import logging
import tempfile
from typing import Union, Optional, Tuple
from PIL import Image

logger = logging.getLogger(__name__)

def _is_audio_filename(name: str) -> bool:
    try:
        lower = name.lower()
        return lower.endswith((".mp3", ".m4a", ".aac", ".ogg", ".wav", ".flac", ".wma", ".opus"))
    except Exception:
        return False

def _extract_audio_tags_from_bytes(audio_bytes: bytes, filename: str) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    """استخراج العنوان والمؤدي والمدة من بايتات ملف صوتي باستخدام mutagen"""
    title = None
    artist = None
    duration = None
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=("." + filename.split(".")[-1] if "." in filename else ".mp3"))
        temp_file.write(audio_bytes)
        temp_file.close()
        try:
            import mutagen
            audio = mutagen.File(temp_file.name)
            if audio is not None:
                try:
                    if hasattr(audio, 'info') and hasattr(audio.info, 'length'):
                        duration = int(audio.info.length)
                except Exception:
                    duration = None
                try:
                    tags = getattr(audio, 'tags', None)
                    if tags:
                        if hasattr(tags, 'getall'):
                            try:
                                t = tags.getall('TIT2')
                                if t:
                                    title = str(t[0].text[0]) if hasattr(t[0], 'text') and t[0].text else None
                            except Exception:
                                pass
                            try:
                                a = tags.getall('TPE1')
                                if a:
                                    artist = str(a[0].text[0]) if hasattr(a[0], 'text') and a[0].text else None
                            except Exception:
                                pass
                        elif hasattr(tags, 'get'):
                            try:
                                title = (tags.get('title') or [None])[0]
                            except Exception:
                                pass
                            try:
                                artist = (tags.get('artist') or [None])[0]
                            except Exception:
                                pass
                except Exception:
                    pass
        finally:
            try:
                import os
                os.unlink(temp_file.name)
            except Exception:
                pass
    except Exception:
        pass
    return title, artist, duration

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

def _extract_video_info_from_bytes(video_bytes: bytes, filename: str) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """استخراج مدة وأبعاد الفيديو من البايتات"""
    duration = None
    width = None
    height = None
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=("." + filename.split(".")[-1] if "." in filename else ".mp4"))
        temp_file.write(video_bytes)
        temp_file.close()
        
        try:
            # Try using OpenCV first
            import cv2
            cap = cv2.VideoCapture(temp_file.name)
            if cap.isOpened():
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                
                if fps > 0 and frame_count > 0:
                    duration = int(frame_count / fps)
                    if duration > 0:
                        logger.info(f"✅ OpenCV استخرج معلومات الفيديو: مدة={duration}s, أبعاد={width}x{height}")
                
                cap.release()
        except Exception as e:
            # Fallback: try with ffprobe if available
            if duration is None or duration <= 0:
                try:
                    import subprocess
                    import json
                    result = subprocess.run([
                        'ffprobe', '-v', 'quiet', '-print_format', 'json',
                        '-show_format', '-show_streams', temp_file.name
                    ], capture_output=True, text=True, timeout=15)
                    
                    if result.returncode == 0:
                        info = json.loads(result.stdout)
                        # Get format duration first
                        if 'format' in info and 'duration' in info['format']:
                            duration = int(float(info['format']['duration']))
                            logger.info(f"✅ FFprobe استخرج مدة الفيديو من المعلومات العامة: {duration}s")
                        
                        # Get video stream info
                        video_stream = next((s for s in info['streams'] if s['codec_type'] == 'video'), None)
                        if video_stream:
                            if duration is None or duration <= 0:
                                stream_duration = video_stream.get('duration')
                                if stream_duration:
                                    duration = int(float(stream_duration))
                                    logger.info(f"✅ FFprobe استخرج مدة الفيديو من Stream: {duration}s")
                            
                            if width is None or width <= 0:
                                width = int(video_stream.get('width', 0))
                            if height is None or height <= 0:
                                height = int(video_stream.get('height', 0))
                except Exception as e:
                    logger.warning(f"⚠️ فشل في استخدام FFprobe: {e}")
        
        finally:
            try:
                import os
                os.unlink(temp_file.name)
            except Exception:
                pass
    except Exception:
        pass
    
    # Final fallback values if extraction completely failed
    if duration is None or duration <= 0:
        duration = 1  # At least 1 second to avoid 00:00 display
        logger.warning("⚠️ لم يتم استخراج مدة الفيديو - استخدام القيمة الافتراضية 1 ثانية")
    
    if width is None or width <= 0:
        width = 640
    if height is None or height <= 0:
        height = 480
    
    logger.info(f"🎬 معلومات الفيديو النهائية: مدة={duration}s, أبعاد={width}x{height}")
    return duration, width, height

def _extract_audio_cover_thumbnail(audio_bytes: bytes) -> Optional[bytes]:
    """استخراج صورة غلاف كصورة مصغّرة (JPEG) من ملف صوتي بايتات إن أمكن"""
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        temp_file.write(audio_bytes)
        temp_file.close()
        cover_data = None
        try:
            import mutagen
            from mutagen.id3 import ID3, APIC
            audio = mutagen.File(temp_file.name)
            if isinstance(audio, ID3) or hasattr(audio, 'tags'):
                tags = audio if isinstance(audio, ID3) else getattr(audio, 'tags', None)
                if tags:
                    # البحث عن APIC (صورة غلاف)
                    pics = []
                    try:
                        pics = tags.getall('APIC') if hasattr(tags, 'getall') else []
                    except Exception:
                        apic = tags.get('APIC:') if hasattr(tags, 'get') else None
                        pics = [apic] if apic else []
                    for pic in pics:
                        if pic and hasattr(pic, 'data') and pic.data:
                            cover_data = pic.data
                            break
            if not cover_data:
                return None
            # تحويل الصورة إلى JPEG مصغّر مناسب كـ thumb
            try:
                img = Image.open(io.BytesIO(cover_data))
                img = img.convert('RGB')
                img.thumbnail((320, 320))
                out = io.BytesIO()
                img.save(out, format='JPEG', quality=85)
                out.seek(0)
                return out.getvalue()
            except Exception:
                return cover_data
        finally:
            try:
                import os
                os.unlink(temp_file.name)
            except Exception:
                pass
    except Exception:
        return None

class TelethonFileSender:
    """مساعد لإرسال الملفات مع أسماء صحيحة"""
    
    @staticmethod
    async def send_file_with_name(client, entity, file_data: Union[bytes, any], filename: str, **kwargs):
        """
        إرسال ملف مع اسم مخصص
        يحل مشكلة Telethon مع البيانات الخام والأسماء المخصصة
        """
        try:
            # إذا كانت البيانات هي bytes، استخدم BytesIO مع name attribute
            if isinstance(file_data, bytes):
                logger.info(f"📤 إرسال ملف bytes مع اسم: {filename}")
                logger.info(f"📊 حجم البيانات: {len(file_data)} bytes")
                
                # إنشاء BytesIO stream مع اسم الملف
                file_stream = io.BytesIO(file_data)
                file_stream.name = filename  # تعيين اسم الملف
                
                logger.info(f"🔧 تم إنشاء BytesIO stream مع الاسم: {file_stream.name}")
                
                # إضافة سمات الصوت والصورة المصغّرة إن لزم لضمان ظهور الملف كصوت مع معاينة
                if _is_audio_filename(filename):
                    try:
                        from telethon.tl.types import DocumentAttributeAudio, DocumentAttributeFilename
                        title, artist, duration = _extract_audio_tags_from_bytes(file_data, filename)
                        attributes = list(kwargs.pop('attributes', []) or [])
                        attributes.append(DocumentAttributeAudio(
                            duration=duration or 0,
                            title=title or None,
                            performer=artist or None,
                        ))
                        # تأكيد اسم الملف كسِمة ضمن الوثيقة
                        attributes.append(DocumentAttributeFilename(file_name=filename))
                        kwargs['attributes'] = attributes
                        kwargs.setdefault('force_document', False)
                        # محاولة استخراج صورة الغلاف لتكون صورة مصغّرة للملف الصوتي
                        if not kwargs.get('thumb'):
                            try:
                                cover_thumb = _extract_audio_cover_thumbnail(file_data)
                                if cover_thumb:
                                    kwargs['thumb'] = cover_thumb
                                    logger.info("🖼️ تم تعيين صورة مصغّرة للملف الصوتي من صورة الغلاف")
                            except Exception as e_thumb:
                                logger.warning(f"⚠️ تعذر استخراج صورة مصغّرة للملف الصوتي: {e_thumb}")
                        logger.info(f"🎵 إضافة سمات صوتية: title='{title}', artist='{artist}', duration={duration}")
                    except Exception as e_attr:
                        logger.warning(f"⚠️ تعذر إضافة سمات الصوت: {e_attr}")


                # CRITICAL FIX: Video handling with proper duration and dimensions
                elif filename and filename.lower().endswith((".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v")):
                    try:
                        from telethon.tl.types import DocumentAttributeVideo, DocumentAttributeFilename
                        attributes = list(kwargs.pop("attributes", []) or [])
                        
                        # Try to get actual video info
                        duration, width, height = _extract_video_info_from_bytes(file_data, filename)
                        
                        attributes.append(DocumentAttributeVideo(
                            duration=duration or 1,  # Use actual duration or at least 1 second to avoid 00:00
                            w=width or 640,
                            h=height or 480,
                            round_message=False,
                            supports_streaming=True
                        ))
                        attributes.append(DocumentAttributeFilename(file_name=filename))
                        kwargs["attributes"] = attributes
                        kwargs.setdefault("force_document", False)
                        logger.info(f"🎬 إضافة سمات فيديو للملف: {filename} (مدة: {duration}s, أبعاد: {width}x{height})")
                    except Exception as e_attr:
                        logger.warning(f"⚠️ تعذر إضافة سمات الفيديو: {e_attr}")
                # إرسال الملف مع stream
                result = await client.send_file(entity, file_stream, **kwargs)
                logger.info(f"✅ تم إرسال الملف {filename} بنجاح باستخدام BytesIO")
                return result
            else:
                # للأنواع الأخرى، استخدم الطريقة العادية
                logger.info(f"📤 إرسال ملف عادي مع اسم: {filename}")
                return await client.send_file(entity, file_data, file_name=filename, **kwargs)
                
        except Exception as e:
            logger.error(f"❌ خطأ في إرسال الملف {filename}: {e}")
            import traceback
            logger.error(f"❌ تفاصيل الخطأ: {traceback.format_exc()}")
            # في حالة الخطأ، جرب upload_file أولاً
            try:
                if isinstance(file_data, bytes):
                    logger.info("🔄 محاولة بديلة باستخدام upload_file")
                    file_handle = await client.upload_file(
                        file=io.BytesIO(file_data),
                        file_name=filename
                    )
                    return await client.send_file(entity, file_handle, **kwargs)
                else:
                    return await client.send_file(entity, file_data, **kwargs)
            except Exception as e2:
                logger.error(f"❌ فشل حتى في الإرسال البديل: {e2}")
                raise e