"""
معالج الوسوم الصوتية الشامل - Comprehensive Audio Metadata Processor
يدعم تعديل جميع أنواع الوسوم الصوتية (ID3v2) مع قوالب قابلة للتخصيص

الميزات:
1. معالجة جميع أنواع المقاطع الصوتية
2. تعديل الوسوم (Title, Artist, Album, Year, Genre, etc.)
3. دعم صورة الغلاف مع خيارات متقدمة
4. دعم المتغيرات في الوسوم
5. دمج مقاطع صوتية إضافية
6. الحفاظ على الجودة 100%
7. معالجة مرة واحدة وإعادة الاستخدام
"""
import os
import io
import logging
import tempfile
import shutil
from typing import Optional, Dict, Any, List, Tuple
from PIL import Image
import mutagen
from mutagen.id3 import ID3, TIT2, TPE1, TPE2, TALB, TDRC, TCON, TCOM, COMM, TRCK, TIT3, USLT, APIC
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3
import subprocess
import re

logger = logging.getLogger(__name__)

class AudioProcessor:
    """معالج الوسوم الصوتية الشامل"""
    
    def __init__(self):
        """تهيئة معالج الوسوم الصوتية"""
        self.supported_audio_formats = [
            '.mp3', '.m4a', '.aac', '.ogg', '.wav', '.flac', '.wma', '.opus'
        ]
        
        # Cache للملفات الصوتية المعالجة مسبقاً
        self.processed_audio_cache = {}
        
        # التحقق من توفر FFmpeg
        self.ffmpeg_available = self._check_ffmpeg_availability()
        
        if self.ffmpeg_available:
            logger.info("✅ FFmpeg متوفر - دعم كامل للمقاطع الصوتية")
        else:
            logger.warning("⚠️ FFmpeg غير متوفر - دعم محدود")
    
    def _check_ffmpeg_availability(self) -> bool:
        """التحقق من توفر FFmpeg"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
            return result.returncode == 0
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def get_audio_info(self, audio_path: str) -> Dict[str, Any]:
        """الحصول على معلومات المقطع الصوتي"""
        try:
            audio = mutagen.File(audio_path)
            if audio is None:
                return {}
            
            info = {
                'format': audio.mime[0].split('/')[-1].upper() if hasattr(audio, 'mime') and audio.mime else 'UNKNOWN',
                'length': int(audio.info.length) if hasattr(audio.info, 'length') else 0,
                'bitrate': getattr(audio.info, 'bitrate', 0),
                'sample_rate': getattr(audio.info, 'sample_rate', 0),
                'channels': getattr(audio.info, 'channels', 0),
                'size_mb': os.path.getsize(audio_path) / (1024 * 1024)
            }
            
            # الحصول على الوسوم الموجودة
            if hasattr(audio, 'tags'):
                tags = audio.tags
                if tags:
                    # ID3 tags
                    if hasattr(tags, 'getall'):
                        info['title'] = self._get_tag_value(tags, 'TIT2', 'title')
                        info['artist'] = self._get_tag_value(tags, 'TPE1', 'artist')
                        info['album'] = self._get_tag_value(tags, 'TALB', 'album')
                        info['year'] = self._get_tag_value(tags, 'TDRC', 'date')
                        info['genre'] = self._get_tag_value(tags, 'TCON', 'genre')
                        info['composer'] = self._get_tag_value(tags, 'TCOM', 'composer')
                        info['comment'] = self._get_tag_value(tags, 'COMM', 'comment')
                        info['track'] = self._get_tag_value(tags, 'TRCK', 'tracknumber')
                        info['album_artist'] = self._get_tag_value(tags, 'TPE2', 'albumartist')
                        info['lyrics'] = self._get_tag_value(tags, 'USLT', 'lyrics')
                    
                    # EasyID3 tags
                    elif hasattr(tags, 'get'):
                        info['title'] = tags.get('title', [''])[0] if tags.get('title') else ''
                        info['artist'] = tags.get('artist', [''])[0] if tags.get('artist') else ''
                        info['album'] = tags.get('album', [''])[0] if tags.get('album') else ''
                        info['year'] = tags.get('date', [''])[0] if tags.get('date') else ''
                        info['genre'] = tags.get('genre', [''])[0] if tags.get('genre') else ''
                        info['composer'] = tags.get('composer', [''])[0] if tags.get('composer') else ''
                        info['comment'] = tags.get('comment', [''])[0] if tags.get('comment') else ''
                        info['track'] = tags.get('tracknumber', [''])[0] if tags.get('tracknumber') else ''
                        info['album_artist'] = tags.get('albumartist', [''])[0] if tags.get('albumartist') else ''
                        info['lyrics'] = tags.get('lyrics', [''])[0] if tags.get('lyrics') else ''
            
            # الحصول على صورة الغلاف
            info['has_cover'] = self._has_album_art(audio_path)
            
            logger.info(f"🎵 معلومات المقطع الصوتي: {info['format']}, {info['length']}s, {info['size_mb']:.2f} MB")
            return info
            
        except Exception as e:
            logger.error(f"خطأ في الحصول على معلومات المقطع الصوتي: {e}")
            return {}
    
    def _get_tag_value(self, tags, id3_key: str, easy_key: str) -> str:
        """الحصول على قيمة الوسم من ID3 أو EasyID3"""
        try:
            # محاولة ID3 أولاً
            if hasattr(tags, 'getall'):
                values = tags.getall(id3_key)
                if values:
                    return str(values[0])
            
            # محاولة EasyID3
            if hasattr(tags, 'get'):
                values = tags.get(easy_key, [])
                if values:
                    return str(values[0])
            
            return ''
        except Exception:
            return ''
    
    def _has_album_art(self, audio_path: str) -> bool:
        """التحقق من وجود صورة غلاف"""
        try:
            audio = mutagen.File(audio_path)
            if audio and hasattr(audio, 'tags'):
                tags = audio.tags
                if hasattr(tags, 'getall'):
                    return bool(tags.getall('APIC'))
            return False
        except Exception:
            return False
    
    def process_audio_metadata(self, audio_bytes: bytes, file_name: str, 
                              metadata_template: Dict[str, str], 
                              album_art_path: Optional[str] = None,
                              apply_art_to_all: bool = False,
                              audio_intro_path: Optional[str] = None,
                              audio_outro_path: Optional[str] = None,
                              intro_position: str = 'start') -> Optional[bytes]:
        """معالجة الوسوم الصوتية مع القالب المحدد"""
        try:
            # إنشاء ملف مؤقت
            temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_name)[1])
            temp_input.write(audio_bytes)
            temp_input.close()
            
            try:
                # الحصول على معلومات المقطع الصوتي
                audio_info = self.get_audio_info(temp_input.name)
                if not audio_info:
                    logger.error("فشل في الحصول على معلومات المقطع الصوتي")
                    return audio_bytes
                
                # إنشاء ملف مؤقت للمخرجات
                temp_output = tempfile.mktemp(suffix='.mp3') if hasattr(tempfile, 'mktemp') else tempfile.NamedTemporaryFile(delete=False, suffix='.mp3').name
                
                # معالجة الوسوم
                if self._apply_metadata_template(temp_input.name, temp_output, metadata_template, 
                                               audio_info, album_art_path, apply_art_to_all):
                    logger.info("✅ تم تطبيق الوسوم بنجاح")
                    
                    # دمج مقاطع صوتية إضافية إذا تم تحديدها
                    final_output = temp_output
                    if audio_intro_path or audio_outro_path:
                        final_output = self._merge_audio_segments(
                            temp_output, audio_intro_path, audio_outro_path, intro_position
                        )
                        if final_output != temp_output:
                            os.unlink(temp_output)
                            temp_output = final_output
                    
                    # قراءة الملف المعالج
                    with open(temp_output, 'rb') as f:
                        processed_bytes = f.read()
                    
                    # تنظيف الملفات المؤقتة
                    os.unlink(temp_input.name)
                    if os.path.exists(temp_output):
                        os.unlink(temp_output)
                    
                    return processed_bytes
                else:
                    logger.error("فشل في تطبيق الوسوم")
                    os.unlink(temp_input.name)
                    return audio_bytes
                    
            except Exception as e:
                logger.error(f"خطأ في معالجة الوسوم: {e}")
                os.unlink(temp_input.name)
                return audio_bytes
                
        except Exception as e:
            logger.error(f"خطأ عام في معالجة الوسوم الصوتية: {e}")
            return audio_bytes
    
    def _apply_metadata_template(self, input_path: str, output_path: str, 
                                template: Dict[str, str], audio_info: Dict[str, Any],
                                album_art_path: Optional[str], apply_art_to_all: bool) -> bool:
        """تطبيق قالب الوسوم على المقطع الصوتي"""
        try:
            # نسخ الملف الأصلي
            shutil.copy2(input_path, output_path)
            
            # إنشاء كائن ID3
            audio = mutagen.File(output_path)
            if not audio:
                return False
            
            # إضافة tags إذا لم تكن موجودة
            if not audio.tags:
                if output_path.lower().endswith('.mp3'):
                    audio.add_tags()
                else:
                    return False
            
            # تطبيق الوسوم من القالب (مع خيار تنظيف النصوص من إعدادات المهمة)
            # جلب إعدادات تنظيف الوسوم الصوتية
            try:
                from database import get_database
                db = get_database()
                # ملاحظة: audio_info لا يحتوي task_id هنا، لذا التنظيف يتم خارجياً عادة
                # سيتم توفير دالة عامة لاستخدامها خارجياً عند النداء من userbot مع task_id
                cleaning_settings = None
            except Exception:
                cleaning_settings = None

            for tag_key, tag_value in template.items():
                if tag_value:
                    # الحفاظ على فواصل الأسطر في كلمات الأغنية فقط
                    processed_value = self._process_template_value(
                        tag_value,
                        audio_info,
                        keep_newlines=(tag_key == 'lyrics')
                    )
                    # لا يمكن تطبيق تنظيف النص هنا بدون task_id؛ سيتم تطبيقه في مسار userbot قبل النداء لهذه الدالة إذا تم تفعيله
                    if processed_value:
                        self._set_audio_tag(audio, tag_key, processed_value)
            
            # تطبيق صورة الغلاف
            if album_art_path and (apply_art_to_all or not audio_info.get('has_cover', False)):
                if self._set_album_art(audio, album_art_path):
                    logger.info("✅ تم تطبيق صورة الغلاف")
            
            # حفظ التغييرات
            audio.save()
            return True
            
        except Exception as e:
            logger.error(f"خطأ في تطبيق قالب الوسوم: {e}")
            return False
    
    def _process_template_value(self, template_value: str, audio_info: Dict[str, Any], keep_newlines: bool = False) -> str:
        """معالجة قيمة القالب مع المتغيرات
        keep_newlines: إذا True، ستُحفظ فواصل الأسطر (لـ lyrics)
        """
        try:
            # استبدال المتغيرات
            processed_value = template_value
            
            # متغيرات الوسوم الأصلية
            replacements = {
                '$title': audio_info.get('title', ''),
                '$artist': audio_info.get('artist', ''),
                '$album': audio_info.get('album', ''),
                '$year': audio_info.get('year', ''),
                '$genre': audio_info.get('genre', ''),
                '$composer': audio_info.get('composer', ''),
                '$comment': audio_info.get('comment', ''),
                '$track': audio_info.get('track', ''),
                '$album_artist': audio_info.get('album_artist', ''),
                '$lyrics': audio_info.get('lyrics', ''),
                '$length': str(audio_info.get('length', 0)),
                '$format': audio_info.get('format', ''),
                '$bitrate': str(audio_info.get('bitrate', 0))
            }
            
            for var, value in replacements.items():
                if var in processed_value:
                    processed_value = processed_value.replace(var, str(value))
            
            # معالجة السطور المتعددة
            if keep_newlines:
                processed_value = processed_value.replace('\r\n', '\n').replace('\r', '\n')
            else:
                if '\n' in processed_value or '\r' in processed_value:
                    processed_value = processed_value.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')
            
            return processed_value.strip()
            
        except Exception as e:
            logger.error(f"خطأ في معالجة قيمة القالب: {e}")
            return template_value
    
    def _set_audio_tag(self, audio, tag_key: str, value: str):
        """تعيين وسم صوتي"""
        try:
            if hasattr(audio, 'tags') and audio.tags:
                tags = audio.tags
                
                # ID3 tags
                if hasattr(tags, 'add'):
                    tag_mapping = {
                        'title': TIT2,
                        'artist': TPE1,
                        'album': TALB,
                        'year': TDRC,
                        'genre': TCON,
                        'composer': TCOM,
                        'comment': COMM,
                        'track': TRCK,
                        'album_artist': TPE2,
                        'lyrics': USLT
                    }
                    
                    if tag_key in tag_mapping:
                        tag_class = tag_mapping[tag_key]
                        if tag_key == 'comment':
                            tags.add(COMM(encoding=3, lang='eng', desc='', text=value))
                        elif tag_key == 'lyrics':
                            # ضمان الحفاظ على فواصل الأسطر كـ \n
                            lyrics_text = value.replace('\r\n', '\n').replace('\r', '\n')
                            tags.add(USLT(encoding=3, lang='eng', desc='', text=lyrics_text))
                        else:
                            tags.add(tag_class(encoding=3, text=value))
                
                # EasyID3 tags
                elif hasattr(tags, '__setitem__'):
                    easy_mapping = {
                        'title': 'title',
                        'artist': 'artist',
                        'album': 'album',
                        'year': 'date',
                        'genre': 'genre',
                        'composer': 'composer',
                        'comment': 'comment',
                        'track': 'tracknumber',
                        'album_artist': 'albumartist'
                    }
                    
                    if tag_key in easy_mapping:
                        tags[easy_mapping[tag_key]] = [value]
                        
        except Exception as e:
            logger.error(f"خطأ في تعيين الوسم {tag_key}: {e}")
    
    def _set_album_art(self, audio, art_path: str) -> bool:
        """تعيين صورة الغلاف"""
        try:
            if not os.path.exists(art_path):
                return False
            
            # قراءة صورة الغلاف
            with open(art_path, 'rb') as f:
                art_data = f.read()
            
            # تحسين الصورة
            optimized_art = self._optimize_album_art(art_data)
            
            # إضافة صورة الغلاف
            if hasattr(audio, 'tags') and audio.tags:
                tags = audio.tags
                if hasattr(tags, 'add'):
                    # إزالة الصور الموجودة
                    if hasattr(tags, 'getall'):
                        for pic in tags.getall('APIC'):
                            tags.delall('APIC')
                    
                    # إضافة الصورة الجديدة
                    tags.add(APIC(
                        encoding=3,
                        mime='image/jpeg',
                        type=3,  # 3 = front cover
                        desc='Cover',
                        data=optimized_art
                    ))
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"خطأ في تعيين صورة الغلاف: {e}")
            return False
    
    def _optimize_album_art(self, art_data: bytes) -> bytes:
        """تحسين صورة الغلاف مع الحفاظ على الجودة"""
        try:
            # فتح الصورة
            image = Image.open(io.BytesIO(art_data))
            
            # تحويل إلى RGB إذا لزم الأمر
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # تحسين الحجم (الحد الأقصى 1000x1000)
            max_size = 1000
            if image.width > max_size or image.height > max_size:
                # استخدام LANCZOS إذا كان متوفراً، وإلا استخدام ANTIALIAS
                try:
                    image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                except AttributeError:
                    try:
                        image.thumbnail((max_size, max_size), Image.ANTIALIAS)
                    except AttributeError:
                        image.thumbnail((max_size, max_size))
            
            # حفظ الصورة المحسنة
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=95, optimize=True)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"خطأ في تحسين صورة الغلاف: {e}")
            return art_data
    
    def _merge_audio_segments(self, main_audio_path: str, intro_path: Optional[str], 
                              outro_path: Optional[str], intro_position: str) -> str:
        """دمج مقاطع صوتية إضافية"""
        try:
            if not self.ffmpeg_available:
                logger.warning("FFmpeg غير متوفر، لا يمكن دمج المقاطع الصوتية")
                return main_audio_path
            
            # إنشاء ملف مؤقت للمخرجات
            output_path = tempfile.mktemp(suffix='.mp3') if hasattr(tempfile, 'mktemp') else tempfile.NamedTemporaryFile(delete=False, suffix='.mp3').name
            
            # بناء أمر FFmpeg
            cmd = ['ffmpeg', '-y']
            
            # إضافة الملفات
            if intro_path and intro_position == 'start':
                cmd.extend(['-i', intro_path])
            cmd.extend(['-i', main_audio_path])
            if outro_path:
                cmd.extend(['-i', outro_path])
            if intro_path and intro_position == 'end':
                cmd.extend(['-i', intro_path])
            
            # إعدادات الدمج
            cmd.extend([
                '-filter_complex', self._build_filter_complex(intro_path, outro_path, intro_position),
                '-c:a', 'mp3',
                '-b:a', '320k',
                output_path
            ])
            
            # تنفيذ الدمج
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ تم دمج المقاطع الصوتية بنجاح")
                return output_path
            else:
                logger.error(f"فشل في دمج المقاطع الصوتية: {result.stderr}")
                return main_audio_path
                
        except Exception as e:
            logger.error(f"خطأ في دمج المقاطع الصوتية: {e}")
            return main_audio_path
    
    def _build_filter_complex(self, intro_path: Optional[str], outro_path: Optional[str], 
                             intro_position: str) -> str:
        """بناء معامل التصفية لدمج المقاطع الصوتية"""
        try:
            filters = []
            input_count = 1  # الملف الرئيسي دائماً موجود
            
            if intro_path:
                input_count += 1
            if outro_path:
                input_count += 1
            
            if input_count == 1:
                return "[0:a]copy[out]"
            
            # بناء معامل الدمج
            if intro_path and outro_path:
                if intro_position == 'start':
                    filters.append(f"[0:a][1:a][2:a]concat=n=3:v=0:a=1[out]")
                else:
                    filters.append(f"[0:a][1:a][2:a]concat=n=3:v=0:a=1[out]")
            elif intro_path:
                if intro_position == 'start':
                    filters.append(f"[0:a][1:a]concat=n=2:v=0:a=1[out]")
                else:
                    filters.append(f"[0:a][1:a]concat=n=2:v=0:a=1[out]")
            elif outro_path:
                filters.append(f"[0:a][1:a]concat=n=2:v=0:a=1[out]")
            
            return ";".join(filters)
            
        except Exception as e:
            logger.error(f"خطأ في بناء معامل التصفية: {e}")
            return "[0:a]copy[out]"
    
    def process_audio_once_for_all_targets(self, audio_bytes: bytes, file_name: str, 
                                         metadata_template: Dict[str, str], 
                                         album_art_path: Optional[str] = None,
                                         apply_art_to_all: bool = False,
                                         audio_intro_path: Optional[str] = None,
                                         audio_outro_path: Optional[str] = None,
                                         intro_position: str = 'start',
                                         task_id: int = 0) -> Optional[bytes]:
        """معالجة المقطع الصوتي مرة واحدة لإعادة الاستخدام"""
        try:
            # إنشاء مفتاح cache
            cache_key = f"{task_id}_{hash(audio_bytes)}_{file_name}"
            
            # التحقق من cache
            if cache_key in self.processed_audio_cache:
                logger.info(f"🎵 استخدام المقطع الصوتي المعالج من cache للمهمة {task_id}")
                return self.processed_audio_cache[cache_key]
            
            # معالجة المقطع الصوتي
            processed_audio = self.process_audio_metadata(
                audio_bytes,
                file_name,
                metadata_template,
                album_art_path,
                apply_art_to_all,
                audio_intro_path,
                audio_outro_path,
                intro_position,
            )
            
            if processed_audio and processed_audio != audio_bytes:
                # حفظ في cache
                self.processed_audio_cache[cache_key] = processed_audio
                
                # تنظيف cache إذا تجاوز الحجم
                if len(self.processed_audio_cache) > 50:
                    oldest_keys = list(self.processed_audio_cache.keys())[:10]
                    for key in oldest_keys:
                        del self.processed_audio_cache[key]
                
                logger.info(f"✅ تم معالجة المقطع الصوتي وحفظه في cache للمهمة {task_id}")
            else:
                # حفظ الملف الأصلي في cache
                self.processed_audio_cache[cache_key] = audio_bytes
            
            return processed_audio
            
        except Exception as e:
            logger.error(f"خطأ في معالجة المقطع الصوتي مرة واحدة: {e}")
            return audio_bytes
    
    def clear_cache(self):
        """مسح cache"""
        self.processed_audio_cache.clear()
        logger.info("🧹 تم مسح cache المقاطع الصوتية")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """الحصول على إحصائيات cache"""
        return {
            'cache_size': len(self.processed_audio_cache),
            'cache_keys': list(self.processed_audio_cache.keys())
        }