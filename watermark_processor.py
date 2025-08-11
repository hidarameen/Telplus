
"""
وحدة معالجة العلامة المائية للصور والفيديوهات
تدعم إضافة علامة مائية نصية أو صورة مع إعدادات مخصصة
"""
import os
import io
import logging
from PIL import Image, ImageDraw, ImageFont, ImageColor
import cv2
import numpy as np
from typing import Optional, Tuple, Union
import tempfile
import subprocess
import time

logger = logging.getLogger(__name__)

class WatermarkProcessor:
    """معالج العلامة المائية للصور والفيديوهات"""
    
    def __init__(self):
        """تهيئة معالج العلامة المائية"""
        self.supported_image_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
        self.supported_video_formats = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
        
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
        """إنشاء علامة مائية نصية"""
        try:
            # إنشاء صورة شفافة للنص
            img_width, img_height = image_size
            
            # حساب حجم الخط بناءً على حجم الصورة
            calculated_font_size = max(font_size, img_width // 25)  # زيادة حجم الخط
            
            # محاولة استخدام خط عربي إذا أمكن
            font = None
            try:
                # البحث عن خط عربي في النظام
                font_paths = [
                    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "/System/Library/Fonts/Arial.ttf",
                    "arial.ttf"
                ]
                
                for font_path in font_paths:
                    if os.path.exists(font_path):
                        font = ImageFont.truetype(font_path, calculated_font_size)
                        break
            except Exception:
                pass
            
            if font is None:
                font = ImageFont.load_default()
            
            # حساب حجم النص
            dummy_img = Image.new('RGBA', (1, 1))
            dummy_draw = ImageDraw.Draw(dummy_img)
            text_bbox = dummy_draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            # إنشاء صورة للنص مع خلفية شفافة
            text_img = Image.new('RGBA', (int(text_width + 20), int(text_height + 10)), (0, 0, 0, 0))
            text_draw = ImageDraw.Draw(text_img)
            
            # تحويل اللون إلى RGBA مع الشفافية
            try:
                if color.startswith('#'):
                    rgb_color = ImageColor.getcolor(color, "RGB")
                    rgba_color = rgb_color + (int(255 * opacity / 100),)
                else:
                    rgba_color = (255, 255, 255, int(255 * opacity / 100))
            except Exception:
                rgba_color = (255, 255, 255, int(255 * opacity / 100))
            
            # رسم النص
            text_draw.text((10, 5), text, font=font, fill=rgba_color)
            
            return text_img
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء العلامة المائية النصية: {e}")
            return None
    
    def calculate_smart_watermark_size(self, base_image_size: Tuple[int, int], watermark_size: Tuple[int, int], 
                                     size_percentage: int, position: str = 'bottom_right') -> Tuple[int, int]:
        """حساب حجم العلامة المائية الذكي حسب أبعاد الصورة والموضع"""
        base_width, base_height = base_image_size
        watermark_width, watermark_height = watermark_size
        
        # الحفاظ على النسبة الأصلية للعلامة المائية
        aspect_ratio = watermark_width / watermark_height
        
        # حساب الحجم بناءً على النسبة المئوية المطلوبة
        scale_factor = size_percentage / 100.0
        
        if size_percentage == 100:
            # للحجم 100%، استخدم كامل أبعاد الصورة الأساسية مع هامش صغير فقط
            new_width = int(base_width * 0.98)  # 98% لترك هامش صغير جداً
            new_height = int(base_height * 0.98)  # 98% لترك هامش صغير جداً
            
            # الحفاظ على النسبة إذا أمكن، وإلا استخدم الحجم الكامل
            calculated_height_from_width = int(new_width / aspect_ratio)
            calculated_width_from_height = int(new_height * aspect_ratio)
            
            # اختر الحجم الذي يحقق أقصى استفادة من المساحة
            if calculated_height_from_width <= new_height:
                # يمكن استخدام العرض الكامل
                new_height = calculated_height_from_width
            else:
                # استخدم الارتفاع الكامل وحساب العرض
                new_width = calculated_width_from_height
                
            logger.info(f"🎯 حجم 100%: أبعاد الصورة {base_image_size} → أبعاد العلامة {(new_width, new_height)}")
        else:
            # للنسب المئوية الأخرى، حساب عادي
            if position in ['top', 'bottom', 'center']:
                # للمواضع الأفقية، استخدم النسبة المئوية كاملة من العرض
                new_width = int(base_width * scale_factor)
            else:
                # للمواضع الركنية، استخدم نسبة معدلة
                new_width = int(base_width * scale_factor * 0.8)
            
            new_height = int(new_width / aspect_ratio)
            
            # تطبيق حدود معقولة للأحجام الأخرى
            max_allowed_width = base_width * 0.9  
            max_allowed_height = base_height * 0.7
            
            if new_width > max_allowed_width:
                new_width = int(max_allowed_width)
                new_height = int(new_width / aspect_ratio)
                
            if new_height > max_allowed_height:
                new_height = int(max_allowed_height)
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
        """تطبيق العلامة المائية على صورة"""
        try:
            # تحميل الصورة
            image = Image.open(io.BytesIO(image_bytes))
            
            # تحويل إلى RGB إذا لزم الأمر
            if image.mode not in ['RGB', 'RGBA']:
                image = image.convert('RGB')
            
            # إنشاء العلامة المائية
            watermark = None
            
            if watermark_settings['watermark_type'] == 'text' and watermark_settings['watermark_text']:
                color = watermark_settings['text_color'] if not watermark_settings['use_original_color'] else '#FFFFFF'
                watermark = self.create_text_watermark(
                    watermark_settings['watermark_text'],
                    watermark_settings['font_size'],
                    color,
                    watermark_settings['opacity'],
                    image.size
                )
            
            elif watermark_settings['watermark_type'] == 'image' and watermark_settings['watermark_image_path']:
                watermark = self.load_image_watermark(
                    watermark_settings['watermark_image_path'],
                    watermark_settings['size_percentage'],
                    watermark_settings['opacity'],
                    image.size,
                    watermark_settings.get('position', 'bottom_right')
                )
            
            if watermark is None:
                logger.warning("فشل في إنشاء العلامة المائية")
                return image_bytes
            
            # حساب موقع العلامة المائية مع الإزاحة اليدوية
            offset_x = watermark_settings.get('offset_x', 0)
            offset_y = watermark_settings.get('offset_y', 0)
            position = self.calculate_position(image.size, watermark.size, watermark_settings['position'], offset_x, offset_y)
            
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
                
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"خطأ في تطبيق العلامة المائية على الصورة: {e}")
            return image_bytes

    def apply_watermark_to_video_ffmpeg(self, video_path: str, watermark_settings: dict) -> Optional[str]:
        """تطبيق العلامة المائية على فيديو باستخدام FFmpeg - الطريقة الأسرع والأكثر فعالية"""
        try:
            logger.info(f"🎬 بدء معالجة الفيديو بـ FFmpeg: {video_path}")
            
            # إنشاء ملف مؤقت للفيديو الجديد
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, f"watermarked_ffmpeg_{int(time.time())}_{os.path.basename(video_path)}")
            
            # تحضير العلامة المائية
            watermark_file = None
            
            if watermark_settings['watermark_type'] == 'text' and watermark_settings['watermark_text']:
                # إنشاء علامة مائية نصية مؤقتة
                watermark_file = self._create_text_watermark_for_ffmpeg(watermark_settings, video_path)
            elif watermark_settings['watermark_type'] == 'image' and watermark_settings['watermark_image_path']:
                # استخدام صورة العلامة المائية مباشرة
                if os.path.exists(watermark_settings['watermark_image_path']):
                    watermark_file = watermark_settings['watermark_image_path']
            
            if not watermark_file or not os.path.exists(watermark_file):
                logger.warning("فشل في تحضير ملف العلامة المائية لـ FFmpeg")
                return None
            
            # حساب موقع العلامة المائية
            position_map = {
                'top_left': '10:10',
                'top_right': 'W-w-10:10',
                'top': '(W-w)/2:10',
                'bottom_left': '10:H-h-10',
                'bottom_right': 'W-w-10:H-h-10',
                'bottom': '(W-w)/2:H-h-10',
                'center': '(W-w)/2:(H-h)/2'
            }
            
            position = watermark_settings.get('position', 'bottom_right')
            overlay_position = position_map.get(position, 'W-w-10:H-h-10')
            
            # إضافة الإزاحة اليدوية
            offset_x = watermark_settings.get('offset_x', 0)
            offset_y = watermark_settings.get('offset_y', 0)
            
            if offset_x != 0 or offset_y != 0:
                # تعديل موقع العلامة المائية حسب الإزاحة
                if position == 'bottom_right':
                    overlay_position = f'W-w-10+{offset_x}:H-h-10+{offset_y}'
                elif position == 'bottom_left':
                    overlay_position = f'10+{offset_x}:H-h-10+{offset_y}'
                elif position == 'top_right':
                    overlay_position = f'W-w-10+{offset_x}:10+{offset_y}'
                elif position == 'top_left':
                    overlay_position = f'10+{offset_x}:10+{offset_y}'
                else:
                    overlay_position = f'(W-w)/2+{offset_x}:(H-h)/2+{offset_y}'
            
            # بناء أمر FFmpeg
            ffmpeg_cmd = [
                'ffmpeg', '-y',  # overwrite output files
                '-i', video_path,  # input video
                '-i', watermark_file,  # watermark image
                '-filter_complex', 
                f'[0:v][1:v] overlay={overlay_position}:enable=\'between(t,0,999999)\'',  # overlay filter
                '-c:a', 'copy',  # copy audio stream
                '-c:v', 'libx264',  # video codec
                '-preset', 'fast',  # encoding speed
                '-crf', '23',  # quality
                output_path
            ]
            
            logger.info(f"🔧 تشغيل أمر FFmpeg...")
            logger.debug(f"📝 الأمر: {' '.join(ffmpeg_cmd)}")
            
            # تشغيل FFmpeg
            process = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if process.returncode == 0:
                logger.info(f"✅ تم تطبيق العلامة المائية بـ FFmpeg: {output_path}")
                
                # حذف ملف العلامة المائية المؤقت إذا كان نصياً
                if watermark_settings['watermark_type'] == 'text' and watermark_file != watermark_settings.get('watermark_image_path'):
                    try:
                        os.unlink(watermark_file)
                    except:
                        pass
                
                return output_path
            else:
                logger.error(f"❌ فشل FFmpeg: {process.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("⏰ انتهت مهلة انتظار FFmpeg")
            return None
        except FileNotFoundError:
            logger.warning("⚠️ FFmpeg غير مثبت، سيتم استخدام OpenCV")
            return None
        except Exception as e:
            logger.error(f"خطأ في FFmpeg: {e}")
            return None

    def _create_text_watermark_for_ffmpeg(self, watermark_settings: dict, video_path: str) -> Optional[str]:
        """إنشاء ملف صورة للعلامة المائية النصية لاستخدامها مع FFmpeg"""
        try:
            # الحصول على أبعاد الفيديو
            cap = cv2.VideoCapture(video_path)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            
            # إنشاء العلامة المائية النصية
            color = watermark_settings['text_color'] if not watermark_settings['use_original_color'] else '#FFFFFF'
            watermark_img = self.create_text_watermark(
                watermark_settings['watermark_text'],
                watermark_settings['font_size'],
                color,
                watermark_settings['opacity'],
                (width, height)
            )
            
            if watermark_img is None:
                return None
            
            # حفظ العلامة المائية كملف مؤقت
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            watermark_img.save(temp_file.name, 'PNG')
            temp_file.close()
            
            return temp_file.name
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء علامة مائية نصية لـ FFmpeg: {e}")
            return None
    
    def apply_watermark_to_video_opencv(self, video_path: str, watermark_settings: dict) -> Optional[str]:
        """تطبيق العلامة المائية على فيديو باستخدام OpenCV - الطريقة البديلة"""
        try:
            logger.info(f"🎬 بدء معالجة الفيديو بـ OpenCV: {video_path}")
            
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
            
            logger.info(f"📊 خصائص الفيديو: {width}x{height}, {fps} FPS, {total_frames} إطار")
            
            # إنشاء ملف مؤقت للفيديو الجديد
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, f"watermarked_opencv_{int(time.time())}_{os.path.basename(video_path)}")
            
            # إعداد كاتب الفيديو مع تحسينات
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            if not out.isOpened():
                logger.error("فشل في إنشاء كاتب الفيديو")
                cap.release()
                return None
            
            # تحضير العلامة المائية
            watermark_opencv = None
            
            if watermark_settings['watermark_type'] == 'text' and watermark_settings['watermark_text']:
                color = watermark_settings['text_color'] if not watermark_settings['use_original_color'] else '#FFFFFF'
                watermark_pil = self.create_text_watermark(
                    watermark_settings['watermark_text'],
                    watermark_settings['font_size'],
                    color,
                    watermark_settings['opacity'],
                    (width, height)
                )
                if watermark_pil:
                    watermark_opencv = cv2.cvtColor(np.array(watermark_pil), cv2.COLOR_RGBA2BGRA)
            
            elif watermark_settings['watermark_type'] == 'image' and watermark_settings['watermark_image_path']:
                watermark_pil = self.load_image_watermark(
                    watermark_settings['watermark_image_path'],
                    watermark_settings['size_percentage'],
                    watermark_settings['opacity'],
                    (width, height),
                    watermark_settings.get('position', 'bottom_right')
                )
                if watermark_pil:
                    watermark_opencv = cv2.cvtColor(np.array(watermark_pil), cv2.COLOR_RGBA2BGRA)
            
            if watermark_opencv is None:
                logger.warning("فشل في تحضير العلامة المائية لـ OpenCV")
                cap.release()
                out.release()
                return video_path
            
            # حساب موقع العلامة المائية مع الإزاحة اليدوية
            watermark_height, watermark_width = watermark_opencv.shape[:2]
            offset_x = watermark_settings.get('offset_x', 0)
            offset_y = watermark_settings.get('offset_y', 0)
            position = self.calculate_position((width, height), (watermark_width, watermark_height), 
                                            watermark_settings['position'], offset_x, offset_y)
            x, y = position
            
            logger.info(f"📍 موقع العلامة المائية: ({x}, {y}), حجم: {watermark_width}x{watermark_height}")
            
            # معالجة الإطارات
            frame_count = 0
            batch_size = 30  # معالجة 30 إطار في المرة الواحدة لتحسين الأداء
            last_progress_report = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                try:
                    # التأكد من أن العلامة المائية تقع داخل حدود الإطار
                    if (x + watermark_width <= width and y + watermark_height <= height and
                        x >= 0 and y >= 0):
                        
                        # تطبيق العلامة المائية بحذر
                        roi = frame[y:y+watermark_height, x:x+watermark_width]
                        
                        if roi.shape[:2] == (watermark_height, watermark_width):
                            # إنشاء قناع للعلامة المائية
                            if watermark_opencv.shape[2] == 4:  # BGRA
                                alpha = watermark_opencv[:, :, 3] / 255.0
                                alpha = np.expand_dims(alpha, axis=2)
                                
                                # تطبيق العلامة المائية مع الشفافية
                                for c in range(3):  # BGR channels
                                    roi[:, :, c] = (alpha[:, :, 0] * watermark_opencv[:, :, c] + 
                                                   (1 - alpha[:, :, 0]) * roi[:, :, c])
                                
                                frame[y:y+watermark_height, x:x+watermark_width] = roi
                            else:
                                # معالجة بسيطة بدون شفافية
                                cv2.addWeighted(roi, 0.7, watermark_opencv[:, :, :3], 0.3, 0, roi)
                                frame[y:y+watermark_height, x:x+watermark_width] = roi
                
                except Exception as frame_error:
                    logger.debug(f"تخطي إطار {frame_count}: {frame_error}")
                
                # كتابة الإطار
                out.write(frame)
                frame_count += 1
                
                # إظهار التقدم كل 5%
                if total_frames > 0:
                    progress = (frame_count / total_frames) * 100
                    if progress - last_progress_report >= 5:
                        logger.info(f"📈 معالجة الفيديو: {progress:.1f}% ({frame_count}/{total_frames})")
                        last_progress_report = progress
            
            # إغلاق الملفات
            cap.release()
            out.release()
            
            # التحقق من نجاح العملية
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"✅ تم تطبيق العلامة المائية بـ OpenCV: {output_path}")
                return output_path
            else:
                logger.error("❌ فشل في إنشاء ملف الفيديو المعالج")
                return None
                
        except Exception as e:
            logger.error(f"خطأ في معالجة الفيديو بـ OpenCV: {e}")
            return None
        finally:
            # تنظيف الموارد
            try:
                if 'cap' in locals():
                    cap.release()
                if 'out' in locals():
                    out.release()
            except:
                pass

    def apply_watermark_to_video(self, video_path: str, watermark_settings: dict) -> Optional[str]:
        """تطبيق العلامة المائية على فيديو - المنطق الرئيسي مع اختيار أفضل طريقة"""
        try:
            logger.info(f"🎬 بدء تطبيق العلامة المائية على الفيديو: {os.path.basename(video_path)}")
            
            # التحقق من وجود الملف
            if not os.path.exists(video_path):
                logger.error(f"ملف الفيديو غير موجود: {video_path}")
                return None
            
            # التحقق من حجم الملف
            file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
            logger.info(f"📁 حجم الفيديو: {file_size_mb:.1f} MB")
            
            # محاولة استخدام FFmpeg أولاً (الأسرع)
            result = self.apply_watermark_to_video_ffmpeg(video_path, watermark_settings)
            
            if result and os.path.exists(result):
                logger.info("✅ تم استخدام FFmpeg بنجاح")
                return result
            
            # في حالة فشل FFmpeg، استخدم OpenCV
            logger.warning("⚠️ فشل FFmpeg، جاري المحاولة بـ OpenCV...")
            result = self.apply_watermark_to_video_opencv(video_path, watermark_settings)
            
            if result and os.path.exists(result):
                logger.info("✅ تم استخدام OpenCV بنجاح")
                return result
            
            logger.error("❌ فشل في تطبيق العلامة المائية بكلا الطريقتين")
            return None
            
        except Exception as e:
            logger.error(f"خطأ عام في تطبيق العلامة المائية على الفيديو: {e}")
            return None
    
    def should_apply_watermark(self, media_type: str, watermark_settings: dict) -> bool:
        """تحديد ما إذا كان يجب تطبيق العلامة المائية على نوع الوسائط"""
        if not watermark_settings.get('enabled', False):
            return False
        
        if media_type == 'photo' and not watermark_settings.get('apply_to_photos', True):
            return False
        
        if media_type == 'video' and not watermark_settings.get('apply_to_videos', True):
            return False
        
        if media_type == 'document' and not watermark_settings.get('apply_to_documents', False):
            return False
        
        return True
    
    def get_media_type_from_file(self, file_path: str) -> str:
        """تحديد نوع الوسائط من امتداد الملف"""
        ext = os.path.splitext(file_path.lower())[1]
        
        if ext in self.supported_image_formats:
            return 'photo'
        elif ext in self.supported_video_formats:
            return 'video'
        else:
            return 'document'
    
    def process_media_with_watermark(self, media_bytes: bytes, file_name: str, watermark_settings: dict) -> Optional[bytes]:
        """معالجة الوسائط وتطبيق العلامة المائية حسب النوع"""
        try:
            media_type = self.get_media_type_from_file(file_name)
            
            logger.info(f"🔍 معالجة الوسائط: {file_name} (النوع: {media_type}, الحجم: {len(media_bytes)} بايت)")
            logger.info(f"🔧 إعدادات العلامة المائية: مفعلة={watermark_settings.get('enabled')}, النوع={watermark_settings.get('watermark_type')}")
            
            if not self.should_apply_watermark(media_type, watermark_settings):
                logger.info(f"⏭️ تخطي العلامة المائية للملف {file_name} - غير مفعلة لنوع {media_type}")
                return media_bytes
            
            if media_type == 'photo':
                logger.info(f"🖼️ تطبيق العلامة المائية على الصورة: {file_name}")
                result = self.apply_watermark_to_image(media_bytes, watermark_settings)
                if result != media_bytes:
                    logger.info(f"✅ تم تطبيق العلامة المائية على الصورة بنجاح")
                else:
                    logger.warning(f"⚠️ لم يتم تعديل الصورة")
                return result
            
            elif media_type == 'video':
                logger.info(f"🎬 بدء معالجة الفيديو: {file_name}")
                logger.info(f"📊 حجم الفيديو: {len(media_bytes) / (1024*1024):.1f} MB")
                
                # حفظ الفيديو مؤقتاً
                temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_name)[1])
                temp_input.write(media_bytes)
                temp_input.close()
                
                logger.info(f"💾 حُفظ الفيديو المؤقت في: {temp_input.name}")
                
                try:
                    # تطبيق العلامة المائية
                    logger.info(f"🔧 بدء تطبيق العلامة المائية على الفيديو...")
                    watermarked_path = self.apply_watermark_to_video(temp_input.name, watermark_settings)
                    
                    if watermarked_path and os.path.exists(watermarked_path):
                        # قراءة الفيديو المعالج
                        with open(watermarked_path, 'rb') as f:
                            watermarked_bytes = f.read()
                        
                        original_size = len(media_bytes) / (1024*1024)
                        processed_size = len(watermarked_bytes) / (1024*1024)
                        
                        logger.info(f"✅ تم تطبيق العلامة المائية على الفيديو بنجاح")
                        logger.info(f"📊 الحجم الأصلي: {original_size:.1f} MB → الحجم المعالج: {processed_size:.1f} MB")
                        
                        # حذف الملفات المؤقتة
                        try:
                            os.unlink(temp_input.name)
                            os.unlink(watermarked_path)
                            logger.info(f"🗑️ تم حذف الملفات المؤقتة")
                        except Exception as cleanup_error:
                            logger.warning(f"⚠️ مشكلة في تنظيف الملفات المؤقتة: {cleanup_error}")
                        
                        return watermarked_bytes
                    else:
                        logger.error(f"❌ فشل في معالجة الفيديو، إرجاع الملف الأصلي")
                        try:
                            os.unlink(temp_input.name)
                        except:
                            pass
                        return media_bytes
                        
                except Exception as video_error:
                    logger.error(f"❌ خطأ في معالجة الفيديو: {video_error}")
                    import traceback
                    logger.error(f"🔍 تفاصيل الخطأ: {traceback.format_exc()}")
                    try:
                        os.unlink(temp_input.name)
                    except:
                        pass
                    return media_bytes
            
            else:
                # نوع وسائط غير مدعوم للعلامة المائية
                logger.info(f"⏭️ نوع الوسائط {media_type} غير مدعوم للعلامة المائية")
                return media_bytes
                
        except Exception as e:
            logger.error(f"❌ خطأ عام في معالجة الوسائط بالعلامة المائية: {e}")
            import traceback
            logger.error(f"🔍 تفاصيل الخطأ العام: {traceback.format_exc()}")
            return media_bytes

    def get_video_info(self, video_path: str) -> dict:
        """الحصول على معلومات الفيديو"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return {}
            
            info = {
                'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                'fps': cap.get(cv2.CAP_PROP_FPS),
                'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                'duration': cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS) if cap.get(cv2.CAP_PROP_FPS) > 0 else 0
            }
            
            cap.release()
            return info
            
        except Exception as e:
            logger.error(f"خطأ في الحصول على معلومات الفيديو: {e}")
            return {}

    def test_video_processing(self, video_path: str) -> bool:
        """اختبار قدرة النظام على معالجة الفيديوهات"""
        try:
            # اختبار OpenCV
            cap = cv2.VideoCapture(video_path)
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                if ret:
                    logger.info("✅ OpenCV يعمل بشكل صحيح")
                    return True
            
            logger.warning("⚠️ مشكلة في OpenCV")
            return False
            
        except Exception as e:
            logger.error(f"❌ خطأ في اختبار معالجة الفيديو: {e}")
            return False
