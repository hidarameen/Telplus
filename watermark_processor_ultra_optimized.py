"""
معالج العلامة المائية المحسن للغاية - الإصدار الأسرع
تحسينات شاملة لسرعة المعالجة والرفع والتحميل
"""

import os
import io
import logging
import asyncio
import threading
import tempfile
import subprocess
import json
import hashlib
import time
import shutil
import gzip
import pickle
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Tuple, Union, Dict, Any, List
from PIL import Image, ImageDraw, ImageFont, ImageColor
import cv2
import numpy as np

logger = logging.getLogger(__name__)

class UltraOptimizedWatermarkProcessor:
    """معالج العلامة المائية المحسن للغاية"""
    
    def __init__(self):
        """تهيئة المعالج المحسن للغاية"""
        self.supported_image_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
        self.supported_video_formats = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
        
        # ذاكرة مؤقتة محسنة للغاية
        self.global_media_cache = {}
        self.cache_lock = threading.RLock()
        self.cache_stats = {'hits': 0, 'misses': 0, 'size': 0}
        
        # إعدادات FFmpeg للسرعة القصوى
        self.ultra_fast_settings = {
            'crf': 40,              # جودة أقل للسرعة القصوى
            'preset': 'ultrafast',   # أسرع preset
            'threads': 16,          # استخدام جميع النوى المتاحة
            'tile-columns': 6,      # تحسين الترميز أكثر
            'frame-parallel': 1,    # معالجة متوازية
            'tune': 'fastdecode',   # تحسين للسرعة
            'profile': 'baseline',  # profile بسيط
            'level': '3.0',         # مستوى بسيط
            'x264opts': 'no-scenecut',  # إيقاف scene cut detection
        }
        
        # إعدادات الذاكرة المؤقتة
        self.max_cache_size = 100 * 1024 * 1024  # 100 MB
        self.max_cache_items = 50
        self.compression_enabled = True
        
        # التحقق من توفر FFmpeg
        self.ffmpeg_available = self._check_ffmpeg_availability()
        
        # ThreadPool للعمليات المتوازية
        self.executor = ThreadPoolExecutor(max_workers=8)
        
        # إحصائيات الأداء
        self.performance_stats = {
            'total_processed': 0,
            'total_time': 0,
            'avg_time': 0,
            'cache_hit_rate': 0
        }
        
        logger.info("🚀 تم تهيئة المعالج المحسن للغاية")
    
    def _check_ffmpeg_availability(self) -> bool:
        """التحقق من توفر FFmpeg"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def _compress_data(self, data: bytes) -> bytes:
        """ضغط البيانات لتوفير الذاكرة"""
        if not self.compression_enabled:
            return data
        try:
            return gzip.compress(data, compresslevel=1)  # ضغط سريع
        except:
            return data
    
    def _decompress_data(self, data: bytes) -> bytes:
        """فك ضغط البيانات"""
        if not self.compression_enabled:
            return data
        try:
            return gzip.decompress(data)
        except:
            return data
    
    def _smart_cache_key(self, media_bytes: bytes, filename: str, watermark_settings: dict, task_id: int) -> str:
        """إنشاء مفتاح ذكي للذاكرة المؤقتة"""
        # استخدام hash سريع للبيانات
        content_hash = hashlib.md5(media_bytes[:1024] + media_bytes[-1024:]).hexdigest()  # أول وآخر 1KB فقط
        settings_hash = hashlib.md5(json.dumps(watermark_settings, sort_keys=True).encode()).hexdigest()
        return f"{task_id}_{content_hash}_{settings_hash}_{os.path.splitext(filename)[1]}"
    
    def _cleanup_cache_smart(self):
        """تنظيف ذكي للذاكرة المؤقتة"""
        with self.cache_lock:
            if len(self.global_media_cache) > self.max_cache_items:
                # حذف أقدم العناصر
                items_to_remove = len(self.global_media_cache) - self.max_cache_items + 10
                oldest_keys = list(self.global_media_cache.keys())[:items_to_remove]
                
                for key in oldest_keys:
                    if key in self.global_media_cache:
                        del self.global_media_cache[key]
                
                logger.info(f"🧹 تم تنظيف الذاكرة المؤقتة: حذف {items_to_remove} عنصر")
    
    async def process_media_ultra_fast(self, media_bytes: bytes, filename: str, watermark_settings: dict, task_id: int) -> bytes:
        """
        معالجة الوسائط بسرعة قصوى مع تحسينات شاملة
        """
        start_time = time.time()
        
        # إنشاء مفتاح ذكي للذاكرة المؤقتة
        cache_key = self._smart_cache_key(media_bytes, filename, watermark_settings, task_id)
        
        # التحقق من الذاكرة المؤقتة
        with self.cache_lock:
            if cache_key in self.global_media_cache:
                self.cache_stats['hits'] += 1
                cached_data = self._decompress_data(self.global_media_cache[cache_key])
                logger.info(f"🎯 إعادة استخدام فورية من الذاكرة المؤقتة: {filename}")
                return cached_data
        
        self.cache_stats['misses'] += 1
        
        # تحديد نوع الملف
        file_ext = os.path.splitext(filename)[1].lower()
        
        # معالجة متوازية حسب النوع
        if file_ext in self.supported_image_formats:
            processed_media = await self._process_image_ultra_fast(media_bytes, watermark_settings)
        elif file_ext in self.supported_video_formats:
            processed_media = await self._process_video_ultra_fast(media_bytes, filename, watermark_settings)
        else:
            processed_media = media_bytes
        
        # حفظ في الذاكرة المؤقتة
        if processed_media and processed_media != media_bytes:
            compressed_data = self._compress_data(processed_media)
            with self.cache_lock:
                self.global_media_cache[cache_key] = compressed_data
                self._cleanup_cache_smart()
        
        # تحديث الإحصائيات
        processing_time = time.time() - start_time
        self.performance_stats['total_processed'] += 1
        self.performance_stats['total_time'] += processing_time
        self.performance_stats['avg_time'] = self.performance_stats['total_time'] / self.performance_stats['total_processed']
        self.performance_stats['cache_hit_rate'] = self.cache_stats['hits'] / (self.cache_stats['hits'] + self.cache_stats['misses']) * 100
        
        logger.info(f"⚡ معالجة فائقة السرعة: {filename} في {processing_time:.2f}s")
        
        return processed_media if processed_media else media_bytes
    
    async def _process_image_ultra_fast(self, image_bytes: bytes, watermark_settings: dict) -> bytes:
        """معالجة الصور بسرعة قصوى"""
        try:
            # تحميل الصورة
            image = Image.open(io.BytesIO(image_bytes))
            
            # تحويل إلى RGB إذا لزم الأمر
            if image.mode not in ['RGB', 'RGBA']:
                image = image.convert('RGB')
            
            # إنشاء العلامة المائية
            if watermark_settings['watermark_type'] == 'text' and watermark_settings.get('watermark_text'):
                watermark = self._create_text_watermark_ultra_fast(
                    watermark_settings['watermark_text'],
                    watermark_settings.get('font_size', 32),
                    watermark_settings.get('text_color', '#FFFFFF'),
                    watermark_settings.get('opacity', 70),
                    image.size
                )
                
                if watermark:
                    # تطبيق العلامة المائية
                    if image.mode == 'RGBA':
                        image.paste(watermark, (0, 0), watermark)
                    else:
                        image = image.convert('RGBA')
                        image.paste(watermark, (0, 0), watermark)
                        image = image.convert('RGB')
            
            # حفظ الصورة محسنة
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=85, optimize=True, progressive=True)
            
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"خطأ في معالجة الصورة: {e}")
            return image_bytes
    
    async def _process_video_ultra_fast(self, video_bytes: bytes, filename: str, watermark_settings: dict) -> bytes:
        """معالجة الفيديو بسرعة قصوى"""
        try:
            if not self.ffmpeg_available:
                logger.warning("FFmpeg غير متوفر - استخدام الطريقة البطيئة")
                return video_bytes
            
            # حفظ الفيديو مؤقتاً
            temp_input = tempfile.NamedTemporaryFile(suffix=os.path.splitext(filename)[1], delete=False)
            temp_input.write(video_bytes)
            temp_input.close()
            
            # إنشاء ملف الإخراج
            temp_output = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
            temp_output.close()
            
            try:
                # الحصول على معلومات الفيديو
                video_info = await self._get_video_info_async(temp_input.name)
                if not video_info:
                    return video_bytes
                
                # إنشاء العلامة المائية
                watermark_path = await self._create_watermark_image_async(watermark_settings, video_info['width'], video_info['height'])
                if not watermark_path:
                    return video_bytes
                
                # معالجة الفيديو بسرعة قصوى
                success = await self._process_video_with_ffmpeg_async(
                    temp_input.name, watermark_path, temp_output.name, watermark_settings
                )
                
                if success and os.path.exists(temp_output.name):
                    # قراءة النتيجة
                    with open(temp_output.name, 'rb') as f:
                        result_bytes = f.read()
                    
                    # تنظيف الملفات المؤقتة
                    os.unlink(temp_input.name)
                    os.unlink(temp_output.name)
                    os.unlink(watermark_path)
                    
                    return result_bytes
                else:
                    return video_bytes
                    
            except Exception as e:
                logger.error(f"خطأ في معالجة الفيديو: {e}")
                # تنظيف الملفات المؤقتة
                for temp_file in [temp_input.name, temp_output.name]:
                    if os.path.exists(temp_file):
                        try:
                            os.unlink(temp_file)
                        except:
                            pass
                return video_bytes
                
        except Exception as e:
            logger.error(f"خطأ في معالجة الفيديو: {e}")
            return video_bytes
    
    def _create_text_watermark_ultra_fast(self, text: str, font_size: int, color: str, opacity: int, 
                                        image_size: Tuple[int, int]) -> Optional[Image.Image]:
        """إنشاء علامة مائية نصية بسرعة قصوى"""
        try:
            img_width, img_height = image_size
            calculated_font_size = max(font_size, img_width // 20)
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", calculated_font_size)
            except:
                font = ImageFont.load_default()
                font = font.font_variant(size=calculated_font_size)
            # احسب حجم النص على لوحة مؤقتة
            tmp_img = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
            tmp_draw = ImageDraw.Draw(tmp_img)
            bbox = tmp_draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            # أنشئ صورة العلامة المائية بحجم النص فقط
            watermark_img = Image.new('RGBA', (text_width, text_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(watermark_img)
            alpha = int(255 * opacity / 100)
            draw.text((0, 0), text, font=font, fill=color + hex(alpha)[2:].zfill(2))
            return watermark_img
         
        except Exception as e:
            logger.error(f"خطأ في إنشاء العلامة المائية النصية: {e}")
            return None
    
    def _calculate_position_ultra_fast(self, base_size: Tuple[int, int], watermark_size: Tuple[int, int], position: str) -> Tuple[int, int]:
        """حساب موقع العلامة المائية بسرعة"""
        base_width, base_height = base_size
        watermark_width, watermark_height = watermark_size
        
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
        
        return position_map.get(position, position_map['bottom_right'])
    
    async def _get_video_info_async(self, video_path: str) -> Optional[Dict]:
        """الحصول على معلومات الفيديو بشكل متوازي"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', video_path
            ]
            
            def run_ffprobe():
                return subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(self.executor, run_ffprobe)
            
            if result.returncode != 0:
                return None
            
            info = json.loads(result.stdout)
            
            # البحث عن stream الفيديو
            video_stream = None
            for stream in info.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                    break
            
            if not video_stream:
                return None
            
            # استخراج المعلومات
            width = int(video_stream.get('width', 0))
            height = int(video_stream.get('height', 0))
            fps_str = video_stream.get('r_frame_rate', '30/1')
            
            # حساب FPS
            if '/' in fps_str:
                num, den = map(int, fps_str.split('/'))
                fps = num / den if den != 0 else 30
            else:
                fps = float(fps_str)
            
            # الحصول على المدة
            duration = float(info.get('format', {}).get('duration', 0))
            
            return {
                'width': width,
                'height': height,
                'fps': fps,
                'duration': duration
            }
            
        except Exception as e:
            logger.error(f"خطأ في الحصول على معلومات الفيديو: {e}")
            return None
    
    async def _create_watermark_image_async(self, watermark_settings: dict, width: int, height: int) -> Optional[str]:
        """إنشاء صورة العلامة المائية بشكل متوازي"""
        try:
            temp_dir = tempfile.gettempdir()
            watermark_path = os.path.join(temp_dir, f"watermark_{hash(str(watermark_settings))}.png")
            
            if watermark_settings['watermark_type'] == 'text':
                watermark_img = self._create_text_watermark_ultra_fast(
                    watermark_settings['watermark_text'],
                    watermark_settings.get('font_size', 32),
                    watermark_settings.get('text_color', '#FFFFFF'),
                    watermark_settings.get('opacity', 70),
                    (width, height)
                )
                
                if watermark_img:
                    watermark_img.save(watermark_path, 'PNG', optimize=True)
                    return watermark_path
            elif watermark_settings['watermark_type'] == 'image' and watermark_settings.get('watermark_image_path'):
                # تحميل صورة العلامة، تحجيمها، وتطبيق الشفافية
                try:
                    wm_img = Image.open(watermark_settings['watermark_image_path'])
                    if wm_img.mode != 'RGBA':
                        wm_img = wm_img.convert('RGBA')
                    size_percentage = int(watermark_settings.get('size_percentage', 20))
                    opacity = int(watermark_settings.get('opacity', 70))
                    # حساب أبعاد مناسبة نسبةً إلى الفيديو
                    wm_w, wm_h = wm_img.size
                    aspect = wm_w / wm_h if wm_h else 1
                    target_area = max(1, int(width * height * (max(1, size_percentage) / 100.0)))
                    new_h = int((target_area / aspect) ** 0.5)
                    new_w = int(new_h * aspect)
                    new_w = max(20, min(new_w, width - 10))
                    new_h = max(20, min(new_h, height - 10))
                    if (new_w, new_h) != wm_img.size:
                        wm_img = wm_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    if 0 <= opacity < 100:
                        alpha = wm_img.split()[-1]
                        alpha = alpha.point(lambda p: int(p * opacity / 100))
                        wm_img.putalpha(alpha)
                    wm_img.save(watermark_path, 'PNG', optimize=True)
                    return watermark_path
                except Exception as _e:
                    logger.error(f"فشل تحميل/تحضير صورة العلامة: {_e}")
             
            return None
             
        except Exception as e:
            logger.error(f"خطأ في إنشاء صورة العلامة المائية: {e}")
            return None
    
    async def _process_video_with_ffmpeg_async(self, input_path: str, watermark_path: str, output_path: str, 
                                            watermark_settings: dict) -> bool:
        """معالجة الفيديو باستخدام FFmpeg بشكل متوازي"""
        try:
            # إعدادات السرعة القصوى (قابلة للتخصيص من الإعدادات)
            crf = int(watermark_settings.get('crf', self.ultra_fast_settings['crf']))
            preset = watermark_settings.get('preset', self.ultra_fast_settings['preset'])
            threads = int(watermark_settings.get('threads', self.ultra_fast_settings['threads']))
            
            # حساب موقع العلامة المائية
            position = watermark_settings.get('position', 'bottom_right')
            offset_x = watermark_settings.get('offset_x', 0)
            offset_y = watermark_settings.get('offset_y', 0)
            
            # بناء أمر FFmpeg للسرعة القصوى مع تصحيح الرايات
            cmd = [
                'ffmpeg', '-y', '-loglevel', 'error',
                '-threads', str(threads),
                '-i', input_path,               # الفيديو المدخل
                '-i', watermark_path,           # صورة العلامة المائية
                '-filter_complex', f'[0:v][1:v]overlay={self._get_overlay_position(position, offset_x, offset_y)}:eval=init',
                '-map', '0:v',
                '-map', '0:a?',                 # اجعل الصوت اختيارياً إن وجد
                '-c:v', 'libx264',              # كودك الفيديو
                '-preset', preset,              # preset سريع
                '-crf', str(crf),               # جودة محسنة للسرعة
                '-pix_fmt', 'yuv420p',          # توافق أعلى
                '-movflags', '+faststart',      # تحسين بدء التشغيل
                '-c:a', 'copy',                 # نسخ الصوت بدون إعادة ترميز
                '-avoid_negative_ts', 'make_zero',
                output_path
            ]
 
            def run_ffmpeg():
                return subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(self.executor, run_ffmpeg)
            
            return result.returncode == 0 and os.path.exists(output_path)
            
        except Exception as e:
            logger.error(f"خطأ في معالجة الفيديو بـ FFmpeg: {e}")
            return False
    
    def _build_ultra_fast_ffmpeg_command(self, input_path: str, watermark_path: str, output_path: str, 
                                       watermark_settings: dict) -> List[str]:
        """بناء أمر FFmpeg للسرعة القصوى"""
        
        # إعدادات السرعة القصوى
        crf = self.ultra_fast_settings['crf']
        preset = self.ultra_fast_settings['preset']
        threads = self.ultra_fast_settings['threads']
        
        # حساب موقع العلامة المائية
        position = watermark_settings.get('position', 'bottom_right')
        offset_x = watermark_settings.get('offset_x', 0)
        offset_y = watermark_settings.get('offset_y', 0)
        
        # بناء أمر FFmpeg للسرعة القصوى مع تصحيح الرايات
        cmd = [
            'ffmpeg', '-y', '-loglevel', 'error',
            '-threads', str(threads),
            '-i', input_path,               # الفيديو المدخل
            '-i', watermark_path,           # صورة العلامة المائية
            '-filter_complex', f'[0:v][1:v]overlay={self._get_overlay_position(position, offset_x, offset_y)}:eval=init[v]',
            '-map', '[v]',
            '-map', '0:a?',                 # اجعل الصوت اختيارياً إن وجد
            '-c:v', 'libx264',              # كودك الفيديو
            '-preset', preset,              # preset سريع
            '-crf', str(crf),               # جودة محسنة للسرعة
            '-pix_fmt', 'yuv420p',          # توافق أعلى
            '-movflags', '+faststart',      # تحسين بدء التشغيل
            '-c:a', 'copy',                 # نسخ الصوت بدون إعادة ترميز
            '-avoid_negative_ts', 'make_zero',
            output_path
        ]
 
        return cmd
    
    def _get_overlay_position(self, position: str, offset_x: int, offset_y: int) -> str:
        """الحصول على موقع overlay للعلامة المائية"""
        position_map = {
            'top_left': f'{offset_x}:{offset_y}',
            'top_right': f'W-w-{abs(offset_x)}:{offset_y}',
            'top': f'(W-w)/2+{offset_x}:{offset_y}',
            'bottom_left': f'{offset_x}:H-h-{abs(offset_y)}',
            'bottom_right': f'W-w-{abs(offset_x)}:H-h-{abs(offset_y)}',
            'bottom': f'(W-w)/2+{offset_x}:H-h-{abs(offset_y)}',
            'center': f'(W-w)/2+{offset_x}:(H-h)/2+{offset_y}'
        }
        
        return position_map.get(position, position_map['bottom_right'])
    
    def get_performance_stats(self) -> Dict:
        """الحصول على إحصائيات الأداء"""
        return {
            'total_processed': self.performance_stats['total_processed'],
            'avg_processing_time': self.performance_stats['avg_time'],
            'cache_hit_rate': self.performance_stats['cache_hit_rate'],
            'cache_size': len(self.global_media_cache),
            'cache_hits': self.cache_stats['hits'],
            'cache_misses': self.cache_stats['misses']
        }
    
    def cleanup(self):
        """تنظيف الموارد"""
        self.executor.shutdown(wait=True)
        self.global_media_cache.clear()

# إنشاء instance عالمي
ultra_optimized_processor = UltraOptimizedWatermarkProcessor()