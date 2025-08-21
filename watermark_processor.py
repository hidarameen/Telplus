"""
وحدة معالجة العلامة المائية للصور والفيديوهات - الإصدار المحسن والمُصلح
تدعم إضافة علامة مائية نصية أو صورة مع إعدادات مخصصة

التحسينات والإصلاحات:
1. إصلاح مشكلة عدم تطبيق العلامة المائية على الصور
2. تحسين معالجة الفيديو وحل مشكلة المعاينة
3. تحسين ضغط الفيديو لتقليل الحجم
4. إصلاح مشاكل الذاكرة المؤقتة
5. تحسين معالجة الأخطاء

المتطلبات:
- FFmpeg لتحسين الفيديو
- OpenCV, Pillow, NumPy للمعالجة
"""
import os
import io
import logging
from PIL import Image, ImageDraw, ImageFont, ImageColor
import cv2
import numpy as np
from typing import Optional, Tuple, Union, Dict, Any
import tempfile
import subprocess
import json
import hashlib
import time

logger = logging.getLogger(__name__)

class WatermarkProcessor:
    """معالج العلامة المائية للصور والفيديوهات - محسن ومُصلح"""
    
    def __init__(self):
        """تهيئة معالج العلامة المائية"""
        self.supported_image_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
        self.supported_video_formats = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
        
        # Cache للملفات المعالجة مسبقاً مع تحسين
        self.processed_media_cache = {}
        self.cache_max_size = 100  # زيادة حجم الذاكرة المؤقتة
        self.cache_cleanup_threshold = 80
        
        # التحقق من توفر FFmpeg
        self.ffmpeg_available = self._check_ffmpeg_availability()
        
        if self.ffmpeg_available:
            logger.info("✅ FFmpeg متوفر - سيتم استخدامه لتحسين الفيديو")
        else:
            logger.warning("⚠️ FFmpeg غير متوفر - سيتم استخدام OpenCV كبديل")
        
        # إعدادات افتراضية محسنة
        self.default_video_quality = 'medium'
        self.default_video_crf = 23
        self.default_audio_bitrate = '128k'
        
        logger.info("🚀 تم تهيئة معالج العلامة المائية بنجاح")
        
        # CRITICAL FIX: Enhanced global cache for media processing optimization  
        self.global_media_cache = {}
        self.media_processing_locks = {}
        
        logger.info("🎯 تم تفعيل النظام المحسن لمعالجة الوسائط مرة واحدة لكل الأهداف")
        self.cache_lock = {}  # Per-task locks to prevent concurrent processing

    def process_media_once_for_all_targets(self, media_bytes, filename, watermark_settings, task_id):
        """
        CRITICAL FIX: Process media once and reuse for all targets to prevent repeated uploads
        This is the core optimization that fixes the repeated media upload issue
        """
        import hashlib
        
        # Create unique cache key based on media content and settings
        cache_key = hashlib.md5(
            f"{len(media_bytes)}_{filename}_{task_id}_{str(watermark_settings)}".encode()
        ).hexdigest()
        
        # Check if already processed and cached
        if cache_key in self.global_media_cache:
            logger.info(f"🎯 إعادة استخدام الوسائط المعالجة من التخزين المؤقت: {filename}")
            return self.global_media_cache[cache_key]
        
        # Process media once 
        processed_media = None
        try:
            if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp')):
                processed_media = self.apply_watermark_to_image(media_bytes, watermark_settings)
                logger.info(f"🖼️ تمت معالجة الصورة مرة واحدة: {filename}")
            elif filename.lower().endswith(('.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm')):
                processed_media = self.apply_watermark_to_video(media_bytes, watermark_settings, task_id)
                logger.info(f"🎬 تمت معالجة الفيديو مرة واحدة: {filename}")
            else:
                processed_media = media_bytes
                logger.info(f"📄 ملف غير مدعوم للعلامة المائية: {filename}")
                
        except Exception as e:
            logger.error(f"خطأ في معالجة الوسائط {filename}: {e}")
            processed_media = media_bytes
        
        # Store in cache for reuse across all targets - CRITICAL FOR PERFORMANCE
        if processed_media:
            self.global_media_cache[cache_key] = processed_media
            logger.info(f"💾 تم حفظ الوسائط المعالجة في التخزين المؤقت لإعادة الاستخدام عبر جميع الأهداف: {filename}")
        
        return processed_media if processed_media else media_bytes
    
    def _check_ffmpeg_availability(self) -> bool:
        """التحقق من توفر FFmpeg في النظام"""
        try:
            # التحقق من توفر ffmpeg
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # التحقق من توفر ffprobe
                result_probe = subprocess.run(['ffprobe', '-version'], capture_output=True, text=True, timeout=10)
                return result_probe.returncode == 0
            return False
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def _generate_cache_key(self, media_bytes: bytes, file_name: str, watermark_settings: dict, task_id: int) -> str:
        """إنشاء مفتاح فريد للذاكرة المؤقتة"""
        # إنشاء hash من البيانات والإعدادات
        content_hash = hashlib.md5(media_bytes).hexdigest()
        settings_hash = hashlib.md5(json.dumps(watermark_settings, sort_keys=True).encode()).hexdigest()
        return f"{task_id}_{content_hash}_{settings_hash}_{file_name}"
    
    def _cleanup_cache(self):
        """تنظيف الذاكرة المؤقتة إذا أصبحت كبيرة جداً"""
        if len(self.processed_media_cache) > self.cache_cleanup_threshold:
            # حذف أقدم 20% من العناصر
            items_to_remove = int(len(self.processed_media_cache) * 0.2)
            oldest_keys = list(self.processed_media_cache.keys())[:items_to_remove]
            
            for key in oldest_keys:
                del self.processed_media_cache[key]
            
            logger.info(f"🧹 تم تنظيف الذاكرة المؤقتة: حذف {items_to_remove} عنصر")
    
    def calculate_position(self, base_size: Tuple[int, int], watermark_size: Tuple[int, int], position: str, offset_x: int = 0, offset_y: int = 0) -> Tuple[int, int]:
        """حساب موقع العلامة المائية على الصورة/الفيديو مع الإزاحة اليدوية"""
        base_width, base_height = base_size
        watermark_width, watermark_height = watermark_size
        
        # تحديد الهامش (5% من حجم الصورة)
        margin = min(base_width, base_height) // 20
        
        position_map = {
            'top_left': (margin, margin),
            'top_right': (base_width - watermark_width - margin, margin),
            'top': ((base_width - watermark_width) // 2, margin),
            'bottom_left': (margin, base_height - watermark_height - margin),
            'bottom_right': (base_width - watermark_width - margin, base_height - watermark_height - margin),
            'bottom': ((base_width - watermark_width) // 2, base_height - watermark_height - margin),
            'center': ((base_width - watermark_width) // 2, (base_height - watermark_height) // 2)
        }
        
        base_position = position_map.get(position, position_map['bottom_right'])
        
        # إضافة الإزاحة اليدوية مع التأكد من البقاء داخل حدود الصورة
        final_x = max(0, min(base_position[0] + offset_x, base_width - watermark_width))
        final_y = max(0, min(base_position[1] + offset_y, base_height - watermark_height))
        
        logger.info(f"📍 الموقع الأساسي: {base_position}, الإزاحة: ({offset_x}, {offset_y}), الموقع النهائي: ({final_x}, {final_y})")
        
        return (final_x, final_y)
    
    def create_text_watermark(self, text: str, font_size: int, color: str, opacity: int, 
                            image_size: Tuple[int, int]) -> Image.Image:
        """إنشاء علامة مائية نصية محسنة"""
        try:
            # إنشاء صورة شفافة للنص
            img_width, img_height = image_size
            
            # حساب حجم الخط بناءً على حجم الصورة
            calculated_font_size = max(font_size, img_width // 25)  # زيادة حجم الخط
            
            # محاولة استخدام خط عربي إذا أمكن
            font = None
            try:
                # محاولة استخدام خط عربي
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", calculated_font_size)
            except:
                try:
                    # محاولة استخدام خط عربي آخر
                    font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", calculated_font_size)
                except:
                    try:
                        # استخدام الخط الافتراضي
                        font = ImageFont.load_default()
                        # تكبير الخط الافتراضي
                        font = font.font_variant(size=calculated_font_size)
                    except:
                        # إنشاء خط بسيط
                        font = ImageFont.load_default()
            
            # إنشاء صورة شفافة
            watermark_img = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(watermark_img)
            
            # حساب حجم النص
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # إنشاء صورة بحجم النص فقط
            watermark_img = Image.new('RGBA', (text_width + 20, text_height + 20), (0, 0, 0, 0))
            draw = ImageDraw.Draw(watermark_img)
            
            # إضافة خلفية شفافة للنص
            if opacity < 100:
                # إنشاء خلفية شفافة
                background_opacity = int((100 - opacity) * 255 / 100)
                background = Image.new('RGBA', watermark_img.size, (0, 0, 0, background_opacity))
                watermark_img = Image.alpha_composite(background, watermark_img)
            
            # رسم النص
            try:
                # محاولة استخدام اللون المحدد
                text_color = ImageColor.getrgb(color)
                draw.text((10, 10), text, fill=text_color + (255,), font=font)
            except:
                # استخدام اللون الأبيض كبديل
                draw.text((10, 10), text, fill=(255, 255, 255, 255), font=font)
            
            logger.info(f"✅ تم إنشاء علامة مائية نصية: '{text}', الحجم: {watermark_img.size}")
            return watermark_img
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء العلامة المائية النصية: {e}")
            # إنشاء علامة مائية بسيطة كبديل
            try:
                watermark_img = Image.new('RGBA', (200, 50), (0, 0, 0, 0))
                draw = ImageDraw.Draw(watermark_img)
                draw.text((10, 10), text[:20], fill=(255, 255, 255, 255))
                return watermark_img
            except:
                return None
    
    def calculate_smart_watermark_size(self, base_image_size: Tuple[int, int], watermark_size: Tuple[int, int],
                                     size_percentage: int, position: str) -> Tuple[int, int]:
        """حساب حجم ذكي للعلامة المائية بناءً على موضعها"""
        base_width, base_height = base_image_size
        watermark_width, watermark_height = watermark_size
        
        # حساب النسبة المئوية من حجم الصورة الأساسية
        base_area = base_width * base_height
        target_area = base_area * (size_percentage / 100)
        
        # الحفاظ على نسبة الأبعاد
        aspect_ratio = watermark_width / watermark_height
        
        # حساب الأبعاد الجديدة
        new_height = int((target_area / aspect_ratio) ** 0.5)
        new_width = int(new_height * aspect_ratio)
        
        # تأكد من الحد الأدنى للحجم
        min_size = 20
        new_width = max(min_size, new_width)
        new_height = max(min_size, new_height)
        
        # تأكد من عدم تجاوز أبعاد الصورة الأساسية
        new_width = min(new_width, base_width - 10)  # هامش 10 بكسل
        new_height = min(new_height, base_height - 10)  # هامش 10 بكسل
        
        logger.info(f"📏 حساب حجم العلامة المائية: {size_percentage}% → {(new_width, new_height)} من أصل {base_image_size}")
        
        return (new_width, new_height)

    def load_image_watermark(self, image_path: str, size_percentage: int, opacity: int,
                           base_image_size: Tuple[int, int], position: str = 'bottom_right') -> Optional[Image.Image]:
        """تحميل وتحضير علامة مائية من صورة بحجم ذكي"""
        try:
            if not os.path.exists(image_path):
                logger.error(f"ملف الصورة غير موجود: {image_path}")
                return None
            
            # تحميل الصورة
            watermark_img = Image.open(image_path)
            
            # تحويل إلى RGBA للدعم الشفافية
            if watermark_img.mode != 'RGBA':
                watermark_img = watermark_img.convert('RGBA')
            
            # حساب الحجم الذكي
            original_size = watermark_img.size
            smart_size = self.calculate_smart_watermark_size(base_image_size, original_size, size_percentage, position)
            
            logger.info(f"📏 تحجيم العلامة المائية الذكي: {original_size} → {smart_size}")
            logger.info(f"🎯 إعدادات: نسبة {size_percentage}%, موضع {position}, أبعاد الصورة {base_image_size}")
            
            # تغيير حجم الصورة
            watermark_img = watermark_img.resize(smart_size, Image.Resampling.LANCZOS)
            
            # تطبيق الشفافية
            if opacity < 100:
                alpha = watermark_img.split()[-1]
                alpha = alpha.point(lambda p: int(p * opacity / 100))
                watermark_img.putalpha(alpha)
            
            return watermark_img
            
        except Exception as e:
            logger.error(f"خطأ في تحميل صورة العلامة المائية: {e}")
            return None
    
    def apply_watermark_to_image(self, image_bytes: bytes, watermark_settings: dict) -> Optional[bytes]:
        """تطبيق العلامة المائية على صورة - مُصلح"""
        try:
            # تحميل الصورة
            image = Image.open(io.BytesIO(image_bytes))
            
            # تحويل إلى RGB إذا لزم الأمر
            if image.mode not in ['RGB', 'RGBA']:
                image = image.convert('RGB')
            
            # إنشاء العلامة المائية
            watermark = None
            
            if watermark_settings['watermark_type'] == 'text' and watermark_settings.get('watermark_text'):
                color = watermark_settings.get('text_color', '#FFFFFF')
                if watermark_settings.get('use_original_color', False):
                    color = '#FFFFFF'  # استخدام اللون الأبيض كافتراضي
                
                watermark = self.create_text_watermark(
                    watermark_settings['watermark_text'],
                    watermark_settings.get('font_size', 32),
                    color,
                    watermark_settings.get('opacity', 70),
                    image.size
                )
            
            elif watermark_settings['watermark_type'] == 'image' and watermark_settings.get('watermark_image_path'):
                watermark = self.load_image_watermark(
                    watermark_settings['watermark_image_path'],
                    watermark_settings.get('size_percentage', 20),
                    watermark_settings.get('opacity', 70),
                    image.size,
                    watermark_settings.get('position', 'bottom_right')
                )
            
            if watermark is None:
                logger.warning("فشل في إنشاء العلامة المائية")
                return image_bytes
            
            # حساب موقع العلامة المائية مع الإزاحة اليدوية
            offset_x = watermark_settings.get('offset_x', 0)
            offset_y = watermark_settings.get('offset_y', 0)
            position = self.calculate_position(image.size, watermark.size, watermark_settings.get('position', 'bottom_right'), offset_x, offset_y)
            
            # تطبيق العلامة المائية
            if image.mode == 'RGBA':
                image.paste(watermark, position, watermark)
            else:
                # تحويل إلى RGBA لتطبيق العلامة المائية
                image = image.convert('RGBA')
                image.paste(watermark, position, watermark)
                # تحويل مرة أخرى إلى RGB
                image = image.convert('RGB')
            
            # حفظ الصورة بتنسيقها الأصلي أو PNG للحفاظ على الجودة
            output = io.BytesIO()
            
            # تحديد تنسيق الحفظ بناءً على الصورة الأصلية
            try:
                original_image = Image.open(io.BytesIO(image_bytes))
                original_format = original_image.format or 'PNG'
                
                # استخدام PNG للصور التي تحتوي على شفافية
                if image.mode == 'RGBA' or original_format == 'PNG':
                    image.save(output, format='PNG', optimize=True)
                elif original_format in ['JPEG', 'JPG']:
                    # تحويل RGBA إلى RGB للـ JPEG
                    if image.mode == 'RGBA':
                        background = Image.new('RGB', image.size, (255, 255, 255))
                        background.paste(image, mask=image.split()[-1])
                        image = background
                    image.save(output, format='JPEG', quality=95, optimize=True)
                else:
                    # استخدام PNG كتنسيق افتراضي
                    image.save(output, format='PNG', optimize=True)
            except Exception:
                # في حالة فشل تحديد التنسيق، استخدم PNG
                image.save(output, format='PNG', optimize=True)
                
            logger.info(f"✅ تم تطبيق العلامة المائية على الصورة بنجاح")
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"خطأ في تطبيق العلامة المائية على الصورة: {e}")
            return image_bytes
    
    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """الحصول على معلومات الفيديو باستخدام ffprobe أو OpenCV كبديل"""
        try:
            # محاولة استخدام ffprobe أولاً
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            info = json.loads(result.stdout)
            
            # استخراج المعلومات المهمة
            video_stream = next((s for s in info['streams'] if s['codec_type'] == 'video'), None)
            format_info = info['format']
            
            if video_stream:
                return {
                    'width': int(video_stream.get('width', 0)),
                    'height': int(video_stream.get('height', 0)),
                    'fps': eval(video_stream.get('r_frame_rate', '30/1')),
                    'duration': float(format_info.get('duration', 0)),
                    'bitrate': int(format_info.get('bit_rate', 0)),
                    'size_mb': float(format_info.get('size', 0)) / (1024 * 1024),
                    'codec': video_stream.get('codec_name', 'unknown')
                }
            
            return {}
            
        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"فشل في استخدام ffprobe: {e}")
            
            # استخدام OpenCV كبديل
            try:
                cap = cv2.VideoCapture(video_path)
                if not cap.isOpened():
                    logger.error(f"فشل في فتح الفيديو باستخدام OpenCV: {video_path}")
                    return {}
                
                # الحصول على خصائص الفيديو
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                
                # حساب المدة التقريبية
                duration = total_frames / fps if fps > 0 else 0
                
                # الحصول على حجم الملف
                file_size = os.path.getsize(video_path)
                size_mb = file_size / (1024 * 1024)
                
                cap.release()
                
                logger.info(f"✅ تم الحصول على معلومات الفيديو باستخدام OpenCV: {width}x{height}, {fps:.2f} FPS, {size_mb:.2f} MB")
                
                return {
                    'width': width,
                    'height': height,
                    'fps': fps,
                    'duration': duration,
                    'bitrate': int((file_size * 8) / duration) if duration > 0 else 0,
                    'size_mb': size_mb,
                    'codec': 'unknown'
                }
                
            except Exception as opencv_error:
                logger.error(f"فشل في الحصول على معلومات الفيديو باستخدام OpenCV: {opencv_error}")
                return {}
                
        except Exception as e:
            logger.error(f"خطأ عام في الحصول على معلومات الفيديو: {e}")
            return {}
    
    def optimize_video_compression(self, input_path: str, output_path: str, target_size_mb: float = None) -> bool:
        """تحسين ضغط الفيديو مع الحفاظ على الجودة - محسن"""
        try:
            # الحصول على معلومات الفيديو الأصلي
            video_info = self.get_video_info(input_path)
            if not video_info:
                logger.warning("فشل في الحصول على معلومات الفيديو، استخدام إعدادات افتراضية")
                return False
            
            original_size = video_info.get('size_mb', 0)
            original_bitrate = video_info.get('bitrate', 0)
            
            logger.info(f"📹 معلومات الفيديو الأصلي: {video_info['width']}x{video_info['height']}, "
                       f"{video_info['fps']:.2f} FPS, {original_size:.2f} MB")
            
            # حساب معدل البت الأمثل
            if target_size_mb and original_size > target_size_mb:
                # حساب معدل البت المطلوب للوصول للحجم المطلوب
                target_bitrate = int((target_size_mb * 8 * 1024 * 1024) / video_info['duration'])
                target_bitrate = max(target_bitrate, 500000)  # حد أدنى 500 kbps
            else:
                # استخدام معدل البت الأصلي مع تحسين كبير
                target_bitrate = int(original_bitrate * 0.5)  # تقليل 50% للحصول على حجم أصغر بشكل أقصى
            
            # استخدام FFmpeg إذا كان متوفراً
            if self.ffmpeg_available:
                try:
                    # إعدادات FFmpeg محسنة للضغط الأقصى مع الحفاظ على الجودة
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
                    ]
                    
                    logger.info(f"🎬 بدء تحسين الفيديو باستخدام FFmpeg: معدل البت المستهدف {target_bitrate/1000:.0f} kbps")
                    
                    # تنفيذ الضغط
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                    
                    if result.returncode == 0:
                        # التحقق من النتيجة
                        final_info = self.get_video_info(output_path)
                        if final_info:
                            final_size = final_info.get('size_mb', 0)
                            compression_ratio = (original_size - final_size) / original_size * 100
                            
                            logger.info(f"✅ تم تحسين الفيديو بنجاح باستخدام FFmpeg: "
                                       f"{original_size:.2f} MB → {final_size:.2f} MB "
                                       f"(توفير {compression_ratio:.1f}%)")
                            return True
                        else:
                            logger.warning("تم إنشاء الفيديو ولكن فشل في التحقق من النتيجة")
                            return True
                    else:
                        logger.warning(f"فشل في استخدام FFmpeg: {result.stderr}")
                        # الانتقال إلى الطريقة البديلة
                        raise Exception("FFmpeg فشل في التنفيذ")
                        
                except Exception as ffmpeg_error:
                    logger.warning(f"فشل في استخدام FFmpeg: {ffmpeg_error}")
                    # الانتقال إلى الطريقة البديلة
            
            # استخدام OpenCV كبديل لضغط بسيط
            try:
                logger.info("🔄 استخدام OpenCV كبديل لضغط الفيديو...")
                
                # محاولة استخدام OpenCV لمعالجة الفيديو
                if self.optimize_video_with_opencv(input_path, output_path, target_size_mb):
                    logger.info("✅ تم معالجة الفيديو بنجاح باستخدام OpenCV")
                    return True
                else:
                    # إذا فشل OpenCV، استخدم النسخ البسيط
                    logger.warning("فشل في معالجة الفيديو باستخدام OpenCV، استخدام النسخ البسيط")
                    import shutil
                    shutil.copy2(input_path, output_path)
                    
                    logger.info(f"✅ تم نسخ الفيديو إلى {output_path} (بدون ضغط إضافي)")
                    if not self.ffmpeg_available:
                        logger.info("💡 للحصول على ضغط أفضل، قم بتثبيت FFmpeg")
                    else:
                        logger.info("💡 FFmpeg متوفر ولكن فشل في التنفيذ، تم استخدام النسخ البسيط")
                    
                    return True
                
            except Exception as opencv_error:
                logger.error(f"فشل في استخدام OpenCV كبديل: {opencv_error}")
                return False
                
        except Exception as e:
            logger.error(f"خطأ في تحسين ضغط الفيديو: {e}")
            return False
    
    def optimize_video_with_opencv(self, input_path: str, output_path: str, target_size_mb: float = None) -> bool:
        """تحسين الفيديو باستخدام OpenCV كبديل لـ FFmpeg"""
        try:
            # فتح الفيديو
            cap = cv2.VideoCapture(input_path)
            if not cap.isOpened():
                logger.error(f"فشل في فتح الفيديو: {input_path}")
                return False
            
            # الحصول على خصائص الفيديو
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # حساب معدل البت المستهدف
            original_size = os.path.getsize(input_path) / (1024 * 1024)  # MB
            duration = total_frames / fps if fps > 0 else 0
            
            # تحديد معاملات التحسين بناءً على الحجم المستهدف
            scale_factor = 1.0
            fps_factor = 1.0
            
            if target_size_mb and original_size > target_size_mb:
                # حساب معامل التصغير المطلوب
                target_ratio = target_size_mb / original_size
                
                if target_ratio < 0.5:
                    # تقليل كبير - تقليل الدقة ومعدل الإطارات
                    scale_factor = 0.7
                    fps_factor = 0.75
                elif target_ratio < 0.8:
                    # تقليل متوسط - تقليل الدقة قليلاً
                    scale_factor = 0.85
                    fps_factor = 0.9
                else:
                    # تقليل بسيط - تقليل الدقة قليلاً جداً
                    scale_factor = 0.95
                    fps_factor = 0.95
                
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                new_fps = int(fps * fps_factor)
                
                logger.info(f"🔄 تحسين الفيديو: الدقة {width}x{height} → {new_width}x{new_height}, "
                           f"معدل الإطارات {fps} → {new_fps}")
            else:
                new_width, new_height = width, height
                new_fps = fps
            
            # إعداد كاتب الفيديو
            fourcc = cv2.VideoWriter.fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, new_fps, (new_width, new_height))
            
            if not out.isOpened():
                logger.error("فشل في إنشاء كاتب الفيديو")
                cap.release()
                return False
            
            logger.info(f"🎬 بدء معالجة الفيديو باستخدام OpenCV: {total_frames} إطار")
            
            frame_count = 0
            skip_frames = 1
            
            # حساب عدد الإطارات التي يجب تخطيها للحصول على معدل الإطارات المطلوب
            if new_fps < fps:
                skip_frames = int(fps / new_fps)
                logger.info(f"⏭️ تخطي {skip_frames - 1} إطار من كل {skip_frames} إطار")
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # تخطي الإطارات إذا لزم الأمر
                if frame_count % skip_frames != 0:
                    frame_count += 1
                    continue
                
                # تغيير حجم الإطار إذا لزم الأمر
                if new_width != width or new_height != height:
                    frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
                
                # كتابة الإطار
                out.write(frame)
                
                frame_count += 1
                if frame_count % 100 == 0:
                    progress = (frame_count / total_frames) * 100
                    logger.info(f"معالجة الفيديو: {progress:.1f}% ({frame_count}/{total_frames})")
            
            # إغلاق الموارد
            cap.release()
            out.release()
            
            # التحقق من النتيجة
            if os.path.exists(output_path):
                final_size = os.path.getsize(output_path) / (1024 * 1024)
                compression_ratio = (original_size - final_size) / original_size * 100
                
                logger.info(f"✅ تم معالجة الفيديو بنجاح باستخدام OpenCV: "
                           f"{original_size:.2f} MB → {final_size:.2f} MB "
                           f"(توفير {compression_ratio:.1f}%)")
                return True
            else:
                logger.error("فشل في إنشاء ملف الفيديو")
                return False
                
        except Exception as e:
            logger.error(f"خطأ في معالجة الفيديو باستخدام OpenCV: {e}")
            return False
    
    def apply_watermark_to_video(self, video_path: str, watermark_settings: dict) -> Optional[str]:
        """تطبيق العلامة المائية على فيديو مع الحفاظ على الصوت والدقة"""
        try:
            # فتح الفيديو
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"فشل في فتح الفيديو: {video_path}")
                return None
            
            # الحصول على خصائص الفيديو
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if fps <= 0 or total_frames <= 0:
                logger.error(f"خصائص الفيديو غير صحيحة: FPS={fps}, Frames={total_frames}")
                cap.release()
                return None
            
            logger.info(f"📹 معلومات الفيديو: {width}x{height}, {fps} FPS, {total_frames} إطار")
            
            # إنشاء ملف مؤقت للفيديو الجديد
            temp_dir = tempfile.gettempdir()
            temp_output = os.path.join(temp_dir, f"temp_watermarked_{os.path.basename(video_path)}")
            final_output = os.path.join(temp_dir, f"watermarked_{os.path.basename(video_path)}")
            
            # تغيير امتداد الملف إلى MP4
            if not final_output.endswith('.mp4'):
                final_output = os.path.splitext(final_output)[0] + '.mp4'
            
            # إعداد كاتب الفيديو - استخدام كودك H.264 للحفاظ على الجودة
            fourcc = cv2.VideoWriter.fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_output, fourcc, fps, (width, height))
            
            if not out.isOpened():
                logger.error("فشل في إنشاء كاتب الفيديو")
                cap.release()
                return None
            
            # تحضير العلامة المائية
            watermark_img = None
            
            if watermark_settings['watermark_type'] == 'text' and watermark_settings.get('watermark_text'):
                color = watermark_settings.get('text_color', '#FFFFFF')
                if watermark_settings.get('use_original_color', False):
                    color = '#FFFFFF'  # استخدام اللون الأبيض كافتراضي
                
                watermark_pil = self.create_text_watermark(
                    watermark_settings['watermark_text'],
                    watermark_settings.get('font_size', 32),
                    color,
                    watermark_settings.get('opacity', 70),
                    (width, height)
                )
                
                if watermark_pil:
                    # تحويل PIL إلى OpenCV
                    watermark_cv = cv2.cvtColor(np.array(watermark_pil), cv2.COLOR_RGBA2BGRA)
                    watermark_img = watermark_cv
                    
            elif watermark_settings['watermark_type'] == 'image' and watermark_settings.get('watermark_image_path'):
                watermark_pil = self.load_image_watermark(
                    watermark_settings['watermark_image_path'],
                    watermark_settings.get('size_percentage', 20),
                    watermark_settings.get('opacity', 70),
                    (width, height),
                    watermark_settings.get('position', 'bottom_right')
                )
                
                if watermark_pil:
                    # تحويل PIL إلى OpenCV
                    watermark_cv = cv2.cvtColor(np.array(watermark_pil), cv2.COLOR_RGBA2BGRA)
                    watermark_img = watermark_cv
            
            # حساب موقع العلامة المائية
            watermark_position = None
            if watermark_img is not None:
                watermark_height, watermark_width = watermark_img.shape[:2]
                offset_x = watermark_settings.get('offset_x', 0)
                offset_y = watermark_settings.get('offset_y', 0)
                watermark_position = self.calculate_position(
                    (width, height), 
                    (watermark_width, watermark_height), 
                    watermark_settings.get('position', 'bottom_right'), 
                    offset_x, 
                    offset_y
                )
            
            logger.info(f"🎬 بدء معالجة الفيديو: {total_frames} إطار")
            
            # معالجة كل إطار
            frame_count = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # تطبيق العلامة المائية إذا كانت موجودة
                if watermark_img is not None and watermark_position is not None:
                    try:
                        # إنشاء نسخة من الإطار
                        frame_with_watermark = frame.copy()
                        
                        # تطبيق العلامة المائية
                        x, y = watermark_position
                        
                        # التأكد من أن العلامة المائية تتناسب مع حدود الإطار
                        if x + watermark_width <= width and y + watermark_height <= height:
                            # تطبيق العلامة المائية مع الشفافية
                            if watermark_img.shape[2] == 4:  # RGBA
                                alpha = watermark_img[:, :, 3] / 255.0
                                alpha = np.expand_dims(alpha, axis=2)
                                
                                # دمج العلامة المائية مع الإطار
                                for c in range(3):  # BGR
                                    frame_with_watermark[y:y+watermark_height, x:x+watermark_width, c] = \
                                        frame_with_watermark[y:y+watermark_height, x:x+watermark_width, c] * (1 - alpha[:, :, 0]) + \
                                        watermark_img[:, :, c] * alpha[:, :, 0]
                            
                            frame = frame_with_watermark
                    except Exception as e:
                        logger.warning(f"فشل في تطبيق العلامة المائية على الإطار {frame_count}: {e}")
                
                # كتابة الإطار
                out.write(frame)
                
                frame_count += 1
                if frame_count % 100 == 0:
                    progress = (frame_count / total_frames) * 100
                    logger.info(f"معالجة الفيديو: {progress:.1f}% ({frame_count}/{total_frames})")
            
            # إغلاق الموارد
            cap.release()
            out.release()
            
            logger.info(f"✅ تم معالجة {frame_count} إطار بنجاح")
            
            # الآن نقوم بنسخ الصوت من الفيديو الأصلي إلى الفيديو المعالج
            # باستخدام FFmpeg للحفاظ على الصوت
            if self.ffmpeg_available:
                try:
                    logger.info("🔊 نسخ الصوت من الفيديو الأصلي...")
                    
                    # استخدام FFmpeg لدمج الفيديو المعالج مع الصوت الأصلي
                    cmd = [
                        'ffmpeg', '-y',
                        '-i', temp_output,  # الفيديو المعالج
                        '-i', video_path,   # الفيديو الأصلي (للصوت)
                        '-c:v', 'copy',     # نسخ الفيديو كما هو
                        '-c:a', 'aac',      # تحويل الصوت إلى AAC
                        '-b:a', '128k',     # معدل بت الصوت
                        '-map', '0:v:0',    # استخدام الفيديو من الملف الأول
                        '-map', '1:a:0',    # استخدام الصوت من الملف الثاني
                        final_output
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        logger.info("✅ تم دمج الصوت بنجاح")
                        # حذف الملف المؤقت
                        if os.path.exists(temp_output):
                            os.unlink(temp_output)
                        return final_output
                    else:
                        logger.warning(f"فشل في دمج الصوت: {result.stderr}")
                        # استخدام الملف المؤقت بدون صوت
                        shutil.copy2(temp_output, final_output)
                        if os.path.exists(temp_output):
                            os.unlink(temp_output)
                        return final_output
                        
                except Exception as e:
                    logger.warning(f"فشل في دمج الصوت: {e}")
                    # استخدام الملف المؤقت بدون صوت
                    shutil.copy2(temp_output, final_output)
                    if os.path.exists(temp_output):
                        os.unlink(temp_output)
                    return final_output
            else:
                # بدون FFmpeg، استخدم الملف المؤقت
                logger.warning("FFmpeg غير متوفر، الفيديو سيكون بدون صوت")
                shutil.copy2(temp_output, final_output)
                if os.path.exists(temp_output):
                    os.unlink(temp_output)
                return final_output
                
        except Exception as e:
            logger.error(f"خطأ في تطبيق العلامة المائية على الفيديو: {e}")
            # تنظيف الملفات المؤقتة
            for temp_file in [temp_output, final_output]:
                if os.path.exists(temp_file):
                    try:
                        os.unlink(temp_file)
                    except:
                        pass
            return None
    
    def should_apply_watermark(self, media_type: str, watermark_settings: dict) -> bool:
        """تحديد ما إذا كان يجب تطبيق العلامة المائية على نوع الوسائط - مُصلح"""
        if not watermark_settings.get('enabled', False):
            logger.debug("🏷️ العلامة المائية معطلة")
            return False
        
        if media_type == 'photo' and not watermark_settings.get('apply_to_photos', True):
            logger.debug("🏷️ العلامة المائية لا تطبق على الصور")
            return False
        
        if media_type == 'video' and not watermark_settings.get('apply_to_videos', True):
            logger.debug("🏷️ العلامة المائية لا تطبق على الفيديوهات")
            return False
        
        if media_type == 'document' and not watermark_settings.get('apply_to_documents', False):
            logger.debug("🏷️ العلامة المائية لا تطبق على المستندات")
            return False
        
        logger.debug(f"🏷️ العلامة المائية سيطبق على {media_type}")
        return True
    
    def get_media_type_from_file(self, file_path: str) -> str:
        """تحديد نوع الوسائط من امتداد الملف - مُصلح"""
        ext = os.path.splitext(file_path.lower())[1]
        
        if ext in self.supported_image_formats:
            return 'photo'
        elif ext in self.supported_video_formats:
            return 'video'
        else:
            return 'document'
    
    def process_media_with_watermark(self, media_bytes: bytes, file_name: str, watermark_settings: dict) -> Optional[bytes]:
        """معالجة الوسائط مع العلامة المائية - مُصلح"""
        try:
            # تحديد نوع الوسائط
            media_type = self.get_media_type_from_file(file_name)
            logger.info(f"🎬 معالجة {media_type}: {file_name}")
            
            if media_type == 'photo':
                # معالجة الصور
                logger.info(f"🖼️ معالجة صورة: {file_name}")
                result = self.apply_watermark_to_image(media_bytes, watermark_settings)
                if result:
                    logger.info(f"✅ تم معالجة الصورة بنجاح: {file_name}")
                    return result
                else:
                    logger.warning(f"⚠️ فشل في معالجة الصورة: {file_name}")
                    return media_bytes
                
            elif media_type == 'video':
                # معالجة الفيديوهات
                logger.info(f"🎬 معالجة فيديو: {file_name}")
                
                # إنشاء ملف مؤقت للفيديو
                temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_name)[1])
                temp_input.write(media_bytes)
                temp_input.close()
                
                try:
                    # تطبيق العلامة المائية
                    watermarked_path = self.apply_watermark_to_video(temp_input.name, watermark_settings)
                    
                    if watermarked_path and os.path.exists(watermarked_path):
                        # الآن نقوم بضغط الفيديو مع الحفاظ على الدقة
                        compressed_path = tempfile.mktemp(suffix='.mp4')
                        
                        if self.compress_video_preserve_quality(watermarked_path, compressed_path):
                            logger.info("✅ تم ضغط الفيديو مع الحفاظ على الدقة")
                            final_path = compressed_path
                        else:
                            logger.warning("فشل في ضغط الفيديو، استخدام الفيديو الأصلي")
                            final_path = watermarked_path
                        
                        # قراءة الفيديو المعالج
                        with open(final_path, 'rb') as f:
                            watermarked_bytes = f.read()
                        
                        # تنظيف الملفات المؤقتة
                        os.unlink(temp_input.name)
                        if os.path.exists(watermarked_path):
                            os.unlink(watermarked_path)
                        if final_path != watermarked_path and os.path.exists(final_path):
                            os.unlink(final_path)
                        
                        logger.info(f"✅ تم معالجة الفيديو بنجاح: {file_name}")
                        return watermarked_bytes
                    else:
                        logger.warning("فشل في تطبيق العلامة المائية على الفيديو")
                        os.unlink(temp_input.name)
                        return media_bytes
                        
                except Exception as e:
                    logger.error(f"خطأ في معالجة الفيديو: {e}")
                    os.unlink(temp_input.name)
                    return media_bytes
            else:
                logger.warning(f"نوع وسائط غير مدعوم: {media_type}")
                return media_bytes
                
        except Exception as e:
            logger.error(f"خطأ في معالجة الوسائط: {e}")
            return media_bytes
    
    def process_media_once_for_all_targets(self, media_bytes: bytes, file_name: str, watermark_settings: dict, 
                                         task_id: int) -> Optional[bytes]:
        """معالجة الوسائط مرة واحدة وإعادة استخدامها لكل الأهداف - مُصلح"""
        try:
            # إنشاء مفتاح فريد للملف
            cache_key = self._generate_cache_key(media_bytes, file_name, watermark_settings, task_id)
            
            # التحقق من وجود الملف في الذاكرة المؤقتة
            if cache_key in self.processed_media_cache:
                logger.info(f"🔄 إعادة استخدام الوسائط المعالجة مسبقاً للمهمة {task_id}")
                return self.processed_media_cache[cache_key]
            
            # التحقق من أن العلامة المائية مفعلة
            if not watermark_settings.get('enabled', False):
                logger.info(f"🏷️ العلامة المائية معطلة للمهمة {task_id}")
                self.processed_media_cache[cache_key] = media_bytes
                return media_bytes
            
            # تحديد نوع الوسائط
            media_type = self.get_media_type_from_file(file_name)
            logger.info(f"🎬 نوع الوسائط: {media_type}, اسم الملف: {file_name}")
            
            # التحقق من تطبيق العلامة المائية على نوع الوسائط
            if not self.should_apply_watermark(media_type, watermark_settings):
                logger.info(f"🏷️ العلامة المائية لا تطبق على {media_type} للمهمة {task_id}")
                self.processed_media_cache[cache_key] = media_bytes
                return media_bytes
            
            # معالجة الوسائط
            processed_media = self.process_media_with_watermark(media_bytes, file_name, watermark_settings)
            
            if processed_media and processed_media != media_bytes:
                # حفظ النتيجة في الذاكرة المؤقتة
                self.processed_media_cache[cache_key] = processed_media
                logger.info(f"✅ تم معالجة الوسائط وحفظها في الذاكرة المؤقتة للمهمة {task_id}")
                
                # تنظيف الذاكرة المؤقتة إذا أصبحت كبيرة جداً
                self._cleanup_cache()
                
                return processed_media
            else:
                # إذا لم يتم تطبيق العلامة المائية، احفظ الملف الأصلي
                logger.warning(f"⚠️ فشل في معالجة الوسائط للمهمة {task_id}")
                self.processed_media_cache[cache_key] = media_bytes
                return media_bytes
                
        except Exception as e:
            logger.error(f"خطأ في معالجة الوسائط مرة واحدة: {e}")
            return media_bytes
    
    def clear_cache(self):
        """مسح الذاكرة المؤقتة"""
        cache_size = len(self.processed_media_cache)
        self.processed_media_cache.clear()
        logger.info(f"🧹 تم مسح الذاكرة المؤقتة للعلامة المائية ({cache_size} عنصر)")
    
    def get_cache_stats(self):
        """الحصول على إحصائيات الذاكرة المؤقتة"""
        return {
            'cache_size': len(self.processed_media_cache),
            'cache_keys': list(self.processed_media_cache.keys()),
            'cache_max_size': self.cache_max_size,
            'cleanup_threshold': self.cache_cleanup_threshold
        }

    def compress_video_preserve_quality(self, input_path: str, output_path: str, target_size_mb: float = None) -> bool:
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
                '-c:a', 'aac',               # كودك الصوت
                '-b:a', '96k',               # معدل بت صوت أقل (96k بدلاً من 128k)
                '-ar', '44100',              # معدل عينات قياسي
                # إعدادات إضافية للضغط
                '-movflags', '+faststart',   # تحسين التشغيل
                '-pix_fmt', 'yuv420p',       # تنسيق بكسل متوافق
                '-g', '30',                  # مجموعة صور كل 30 إطار
                '-keyint_min', '15',         # الحد الأدنى لمجموعة الصور
                '-sc_threshold', '0',        # تعطيل تبديل المشهد
                '-tune', 'film',             # تحسين للفيديوهات
                output_path
            ]
            
            logger.info(f"🎬 بدء ضغط الفيديو باستخدام FFmpeg: معدل البت {target_bitrate/1000:.0f} kbps")
            
            # تنفيذ الضغط
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)  # timeout 5 دقائق
            
            if result.returncode == 0:
                # التحقق من النتيجة
                final_info = self.get_video_info(output_path)
                if final_info:
                    final_size = final_info.get('size_mb', 0)
                    compression_ratio = (original_size - final_size) / original_size * 100
                    
                    logger.info(f"✅ تم ضغط الفيديو بنجاح: "
                               f"{original_size:.2f} MB → {final_size:.2f} MB "
                               f"(توفير {compression_ratio:.1f}%)")
                    
                    # التحقق من أن الحجم النهائي مقبول
                    if target_size_mb and final_size > target_size_mb * 1.2:  # سماح بزيادة 20%
                        logger.warning(f"⚠️ الحجم النهائي أكبر من المستهدف: {final_size:.2f} MB > {target_size_mb:.2f} MB")
                        # محاولة ضغط إضافي
                        return self._compress_video_aggressive(input_path, output_path, target_size_mb)
                    
                    return True
                else:
                    logger.warning("تم إنشاء الفيديو ولكن فشل في التحقق من النتيجة")
                    return True
            else:
                logger.error(f"فشل في ضغط الفيديو: {result.stderr}")
                # محاولة استخدام إعدادات أبسط
                return self._compress_video_simple(input_path, output_path, target_size_mb)
                
        except subprocess.TimeoutExpired:
            logger.error("انتهت مهلة ضغط الفيديو (5 دقائق)")
            return False
        except Exception as e:
            logger.error(f"خطأ في ضغط الفيديو: {e}")
            return False
    
    def _compress_video_maximum(self, input_path: str, output_path: str, preserve_resolution: bool = True) -> bool:
        """ضغط الفيديو للحصول على أقصى ضغط ممكن مع الحفاظ على الدقة الأصلية"""
        try:
            logger.info("🔥 تطبيق أقصى ضغط ممكن للفيديو مع الحفاظ على الدقة...")
            
            # الحصول على معلومات الفيديو الأصلي
            video_info = self.get_video_info(input_path)
            if not video_info:
                logger.warning("فشل في الحصول على معلومات الفيديو")
                return False
            
            original_width = video_info.get('width', 0)
            original_height = video_info.get('height', 0)
            duration = video_info.get('duration', 0)
            original_size = video_info.get('size_mb', 0)
            
            # حساب معدل البت منخفض جداً للحصول على أقصى ضغط
            target_bitrate = int((original_size * 8 * 1024 * 1024 * 0.15) / duration) if duration > 0 else 300000  # تقليل 85%
            target_bitrate = max(target_bitrate, 200000)  # حد أدنى 200 kbps
            
            logger.info(f"🎯 أقصى ضغط: {original_width}x{original_height}, معدل البت: {target_bitrate/1000:.0f} kbps")
            
            # إعدادات FFmpeg للحصول على أقصى ضغط ممكن مع الحفاظ على الدقة
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                # إعدادات الفيديو - ضغط أقصى
                '-c:v', 'libx264',               # كودك H.264
                '-preset', 'veryslow',           # أبطء إعداد للحصول على أقصى ضغط
                '-crf', '28',                    # جودة منخفضة للحصول على حجم أصغر
                '-maxrate', f'{target_bitrate}', # معدل بت منخفض جداً
                '-bufsize', f'{target_bitrate}', # حجم buffer مساوي لمعدل البت
                '-profile:v', 'high',            # ملف عالي للضغط الأمثل
                '-level', '4.1',                 # مستوى عالي
                '-tune', 'film',                 # تحسين للفيديوهات
                # إعدادات متقدمة لأقصى ضغط
                '-x264opts', 'ref=5:bframes=16:b-adapt=2:direct=auto:me=umh:merange=24:subme=10:psy-rd=1.0,0.1:deblock=1,1:trellis=2:aq-mode=2:aq-strength=1.0',
                # إعدادات الصوت - ضغط أقصى
                '-c:a', 'aac',                   # كودك الصوت
                '-b:a', '64k',                   # معدل بت صوت منخفض جداً
                '-ar', '22050',                  # معدل عينات منخفض
                '-ac', '1',                      # صوت أحادي لتوفير المساحة
                # إعدادات إضافية للضغط الأقصى
                '-movflags', '+faststart',       # تحسين التشغيل
                '-pix_fmt', 'yuv420p',           # تنسيق بكسل متوافق
                '-g', '15',                      # مجموعة صور صغيرة
                '-keyint_min', '5',              # الحد الأدنى لمجموعة الصور
                '-sc_threshold', '0',            # تعطيل تبديل المشهد
                '-threads', '0',                 # استخدام كل المعالجات
                output_path
            ]
            
            # إضافة إعدادات الحفاظ على الدقة إن طُلب ذلك
            if preserve_resolution:
                # إدراج إعدادات الحجم قبل output_path
                cmd.insert(-1, '-s')
                cmd.insert(-1, f'{original_width}x{original_height}')
                logger.info(f"🔒 الحفاظ على الدقة الأصلية: {original_width}x{original_height}")
            
            logger.info("🚀 بدء تطبيق أقصى ضغط للفيديو...")
            
            # تنفيذ الضغط مع وقت أطول
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)  # timeout 15 دقيقة
            
            if result.returncode == 0:
                # التحقق من النتيجة
                final_info = self.get_video_info(output_path)
                if final_info:
                    final_size = final_info.get('size_mb', 0)
                    compression_ratio = (original_size - final_size) / original_size * 100
                    
                    logger.info(f"✅ تم تطبيق أقصى ضغط للفيديو: "
                               f"{original_size:.2f} MB → {final_size:.2f} MB "
                               f"(توفير {compression_ratio:.1f}%)")
                    
                    # التأكد من الحفاظ على الدقة
                    final_width = final_info.get('width', 0)
                    final_height = final_info.get('height', 0)
                    if preserve_resolution and (final_width != original_width or final_height != original_height):
                        logger.warning(f"⚠️ تغيرت الدقة: {original_width}x{original_height} → {final_width}x{final_height}")
                    else:
                        logger.info(f"✅ تم الحفاظ على الدقة الأصلية: {final_width}x{final_height}")
                    
                    return True
                else:
                    logger.warning("تم إنشاء الفيديو ولكن فشل في التحقق من النتيجة")
                    return True
            else:
                logger.error(f"فشل في تطبيق أقصى ضغط: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("انتهت مهلة ضغط الفيديو (15 دقيقة)")
            return False
        except Exception as e:
            logger.error(f"خطأ في تطبيق أقصى ضغط: {e}")
            return False

    def _compress_video_aggressive(self, input_path: str, output_path: str, target_size_mb: float) -> bool:
        """ضغط فيديو عدواني للحصول على حجم أصغر"""
        try:
            logger.info("🔥 محاولة ضغط عدواني للفيديو...")
            
            # إعدادات FFmpeg عدوانية
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                # إعدادات فيديو عدوانية
                '-c:v', 'libx264',
                '-preset', 'veryslow',       # أبطء للحصول على ضغط أفضل
                '-crf', '28',                # جودة أقل للحصول على حجم أصغر
                '-maxrate', f'{int(target_size_mb * 8 * 1024 * 1024 / 60)}',  # معدل بت منخفض
                '-bufsize', f'{int(target_size_mb * 8 * 1024 * 1024 / 30)}',
                '-profile:v', 'baseline',    # ملف H.264 أساسي (أصغر)
                '-level', '3.1',             # مستوى منخفض
                # إعدادات صوت عدوانية
                '-c:a', 'aac',
                '-b:a', '64k',               # معدل بت صوت منخفض جداً
                '-ar', '22050',              # معدل عينات منخفض
                # إعدادات إضافية
                '-movflags', '+faststart',
                '-pix_fmt', 'yuv420p',
                '-g', '15',                  # مجموعة صور أصغر
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)  # timeout 10 دقائق
            
            if result.returncode == 0:
                final_info = self.get_video_info(output_path)
                if final_info:
                    final_size = final_info.get('size_mb', 0)
                    logger.info(f"✅ تم الضغط العدواني: {final_size:.2f} MB")
                    return final_size <= target_size_mb * 1.1  # سماح بزيادة 10%
            
            return False
            
        except Exception as e:
            logger.error(f"خطأ في الضغط العدواني: {e}")
            return False
    
    def _compress_video_simple(self, input_path: str, output_path: str, target_size_mb: float = None) -> bool:
        """ضغط فيديو بسيط كبديل"""
        try:
            logger.info("🔄 محاولة ضغط بسيط للفيديو...")
            
            # إعدادات FFmpeg بسيطة
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                '-c:v', 'libx264',
                '-preset', 'ultrafast',      # أسرع للحصول على نتيجة سريعة
                '-crf', '30',                # جودة متوسطة
                '-c:a', 'aac',
                '-b:a', '128k',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info("✅ تم الضغط البسيط بنجاح")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"خطأ في الضغط البسيط: {e}")
            return False
    
    def optimize_video_compression(self, input_path: str, output_path: str, target_size_mb: float = None) -> bool:
        """تحسين ضغط الفيديو مع الحفاظ على الجودة - محسن"""
        try:
            # الحصول على معلومات الفيديو الأصلي
            video_info = self.get_video_info(input_path)
            if not video_info:
                logger.warning("فشل في الحصول على معلومات الفيديو، استخدام إعدادات افتراضية")
                return False
            
            original_size = video_info.get('size_mb', 0)
            original_bitrate = video_info.get('bitrate', 0)
            
            logger.info(f"📹 معلومات الفيديو الأصلي: {video_info['width']}x{video_info['height']}, "
                       f"{video_info['fps']:.2f} FPS, {original_size:.2f} MB")
            
            # حساب معدل البت الأمثل
            if target_size_mb and original_size > target_size_mb:
                # حساب معدل البت المطلوب للوصول للحجم المطلوب
                target_bitrate = int((target_size_mb * 8 * 1024 * 1024) / video_info['duration'])
                target_bitrate = max(target_bitrate, 500000)  # حد أدنى 500 kbps
            else:
                # استخدام معدل البت الأصلي مع تحسين كبير
                target_bitrate = int(original_bitrate * 0.5)  # تقليل 50% للحصول على حجم أصغر بشكل أقصى
            
            # استخدام FFmpeg إذا كان متوفراً
            if self.ffmpeg_available:
                try:
                    # إعدادات FFmpeg محسنة للضغط الأقصى مع الحفاظ على الجودة
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
                    ]
                    
                    logger.info(f"🎬 بدء تحسين الفيديو باستخدام FFmpeg: معدل البت المستهدف {target_bitrate/1000:.0f} kbps")
                    
                    # تنفيذ الضغط
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                    
                    if result.returncode == 0:
                        # التحقق من النتيجة
                        final_info = self.get_video_info(output_path)
                        if final_info:
                            final_size = final_info.get('size_mb', 0)
                            compression_ratio = (original_size - final_size) / original_size * 100
                            
                            logger.info(f"✅ تم تحسين الفيديو بنجاح باستخدام FFmpeg: "
                                       f"{original_size:.2f} MB → {final_size:.2f} MB "
                                       f"(توفير {compression_ratio:.1f}%)")
                            return True
                        else:
                            logger.warning("تم إنشاء الفيديو ولكن فشل في التحقق من النتيجة")
                            return True
                    else:
                        logger.warning(f"فشل في استخدام FFmpeg: {result.stderr}")
                        # الانتقال إلى الطريقة البديلة
                        raise Exception("FFmpeg فشل في التنفيذ")
                        
                except Exception as ffmpeg_error:
                    logger.warning(f"فشل في استخدام FFmpeg: {ffmpeg_error}")
                    # الانتقال إلى الطريقة البديلة
            
            # استخدام OpenCV كبديل لضغط بسيط
            try:
                logger.info("🔄 استخدام OpenCV كبديل لضغط الفيديو...")
                
                # محاولة استخدام OpenCV لمعالجة الفيديو
                if self.optimize_video_with_opencv(input_path, output_path, target_size_mb):
                    logger.info("✅ تم معالجة الفيديو بنجاح باستخدام OpenCV")
                    return True
                else:
                    # إذا فشل OpenCV، استخدم النسخ البسيط
                    logger.warning("فشل في معالجة الفيديو باستخدام OpenCV، استخدام النسخ البسيط")
                    import shutil
                    shutil.copy2(input_path, output_path)
                    
                    logger.info(f"✅ تم نسخ الفيديو إلى {output_path} (بدون ضغط إضافي)")
                    if not self.ffmpeg_available:
                        logger.info("💡 للحصول على ضغط أفضل، قم بتثبيت FFmpeg")
                    else:
                        logger.info("💡 FFmpeg متوفر ولكن فشل في التنفيذ، تم استخدام النسخ البسيط")
                    
                    return True
                
            except Exception as opencv_error:
                logger.error(f"فشل في استخدام OpenCV كبديل: {opencv_error}")
                return False
                
        except Exception as e:
            logger.error(f"خطأ في تحسين ضغط الفيديو: {e}")
            return False