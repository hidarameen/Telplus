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

logger = logging.getLogger(__name__)

class WatermarkProcessor:
    """معالج العلامة المائية للصور والفيديوهات"""
    
    def __init__(self):
        """تهيئة معالج العلامة المائية"""
        self.supported_image_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
        self.supported_video_formats = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv']
        
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
        
        # حساب المساحة المتاحة للعلامة المائية مع التحسين الذكي
        if size_percentage == 100:
            # للحجم 100%، أعطِ الأولوية للعرض الكامل
            new_width = int(base_width * 0.95)  # 95% من عرض الصورة الأساسية
            new_height = int(new_width / aspect_ratio)
            
            # تحقق من الارتفاع - إذا كان كبيراً جداً، استخدم استراتيجية مختلفة
            max_height_limit = base_height * 0.6  # حد أكثر مرونة - 60% من الارتفاع
            if new_height > max_height_limit:
                # بدلاً من تصغير العلامة، نبقي العرض ونقلل الارتفاع قليلاً
                new_height = int(max_height_limit)
                # لكن نحتفظ بعرض كبير حتى لو كسرنا النسبة قليلاً
                new_width = int(base_width * 0.90)  # عرض 90% في كل الأحوال
        else:
            # للنسب المئوية الأخرى، احسب حسب النسبة المطلوبة مباشرة
            scale_factor = size_percentage / 100.0
            
            # حساب الحجم بناءً على عرض الصورة مباشرة
            if position in ['top', 'bottom', 'center']:
                # للمواضع الأفقية، استخدم النسبة المئوية كاملة من العرض
                new_width = int(base_width * scale_factor)
            else:
                # للمواضع الركنية، استخدم نسبة أقل قليلاً
                new_width = int(base_width * scale_factor * 0.8)
            
            new_height = int(new_width / aspect_ratio)
        
        # تأكد من عدم تجاوز حدود الصورة الأساسية - للحجم 100% نتساهل أكثر
        if size_percentage == 100:
            # للحجم 100%، لا نطبق قيود صارمة على الارتفاع
            max_allowed_width = base_width * 0.99  # الحد الأقصى 99% من عرض الصورة
            max_allowed_height = base_height * 0.8   # الحد الأقصى 80% من ارتفاع الصورة للحجم 100%
        else:
            # للأحجام الأخرى، حدود معقولة
            max_allowed_width = base_width * 0.95  
            max_allowed_height = base_height * 0.6
        
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
    
    def apply_watermark_to_video(self, video_path: str, watermark_settings: dict) -> Optional[str]:
        """تطبيق العلامة المائية على فيديو"""
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
            
            # إنشاء ملف مؤقت للفيديو الجديد
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, f"watermarked_{os.path.basename(video_path)}")
            
            # إعداد كاتب الفيديو
            fourcc = cv2.VideoWriter.fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            # تحضير العلامة المائية
            watermark_img = None
            
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
                    watermark_img = cv2.cvtColor(np.array(watermark_pil), cv2.COLOR_RGBA2BGRA)
            
            elif watermark_settings['watermark_type'] == 'image' and watermark_settings['watermark_image_path']:
                watermark_pil = self.load_image_watermark(
                    watermark_settings['watermark_image_path'],
                    watermark_settings['size_percentage'],
                    watermark_settings['opacity'],
                    (width, height),
                    watermark_settings.get('position', 'bottom_right')
                )
                if watermark_pil:
                    watermark_img = cv2.cvtColor(np.array(watermark_pil), cv2.COLOR_RGBA2BGRA)
            
            if watermark_img is None:
                cap.release()
                out.release()
                return video_path
            
            # حساب موقع العلامة المائية مع الإزاحة اليدوية
            watermark_height, watermark_width = watermark_img.shape[:2]
            offset_x = watermark_settings.get('offset_x', 0)
            offset_y = watermark_settings.get('offset_y', 0)
            position = self.calculate_position((width, height), (watermark_width, watermark_height), watermark_settings['position'], offset_x, offset_y)
            x, y = position
            
            # معالجة كل إطار
            frame_count = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # تطبيق العلامة المائية على الإطار
                try:
                    # إنشاء قناع للعلامة المائية
                    alpha = watermark_img[:, :, 3] / 255.0
                    
                    # تطبيق العلامة المائية
                    for c in range(0, 3):
                        frame[y:y+watermark_height, x:x+watermark_width, c] = (
                            alpha * watermark_img[:, :, c] + 
                            (1 - alpha) * frame[y:y+watermark_height, x:x+watermark_width, c]
                        )
                except Exception as e:
                    logger.warning(f"خطأ في تطبيق العلامة المائية على الإطار {frame_count}: {e}")
                
                # كتابة الإطار
                out.write(frame)
                frame_count += 1
                
                # إظهار التقدم كل 100 إطار
                if frame_count % 100 == 0:
                    progress = (frame_count / total_frames) * 100
                    logger.info(f"معالجة الفيديو: {progress:.1f}% ({frame_count}/{total_frames})")
            
            # إغلاق الملفات
            cap.release()
            out.release()
            
            logger.info(f"تم تطبيق العلامة المائية على الفيديو: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"خطأ في تطبيق العلامة المائية على الفيديو: {e}")
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
            
            if not self.should_apply_watermark(media_type, watermark_settings):
                return media_bytes
            
            if media_type == 'photo':
                return self.apply_watermark_to_image(media_bytes, watermark_settings)
            
            elif media_type == 'video':
                # حفظ الفيديو مؤقتاً
                temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_name)[1])
                temp_input.write(media_bytes)
                temp_input.close()
                
                # تطبيق العلامة المائية
                watermarked_path = self.apply_watermark_to_video(temp_input.name, watermark_settings)
                
                if watermarked_path and os.path.exists(watermarked_path):
                    # قراءة الفيديو المعالج
                    with open(watermarked_path, 'rb') as f:
                        watermarked_bytes = f.read()
                    
                    # حذف الملفات المؤقتة
                    os.unlink(temp_input.name)
                    os.unlink(watermarked_path)
                    
                    return watermarked_bytes
                else:
                    os.unlink(temp_input.name)
                    return media_bytes
            
            else:
                # نوع وسائط غير مدعوم للعلامة المائية
                return media_bytes
                
        except Exception as e:
            logger.error(f"خطأ في معالجة الوسائط بالعلامة المائية: {e}")
            return media_bytes