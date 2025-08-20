#!/usr/bin/env python3
"""
سكريبت اختبار وظيفة العلامة المائية
يختبر جميع الوظائف المحسنة والمُصلحة
"""

import os
import sys
import logging
import tempfile
import io
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# إضافة المسار الحالي إلى Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from watermark_processor import WatermarkProcessor

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WatermarkTester:
    """مختبر وظيفة العلامة المائية"""
    
    def __init__(self):
        """تهيئة المختبر"""
        self.processor = WatermarkProcessor()
        self.test_results = {}
        
    def create_test_image(self, width=800, height=600, text="صورة اختبار"):
        """إنشاء صورة اختبار"""
        try:
            # إنشاء صورة بيضاء
            image = Image.new('RGB', (width, height), (255, 255, 255))
            draw = ImageDraw.Draw(image)
            
            # إضافة نص للصورة
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)
            except:
                font = ImageFont.load_default()
            
            # حساب موقع النص
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (width - text_width) // 2
            y = (height - text_height) // 2
            
            # رسم النص
            draw.text((x, y), text, fill=(0, 0, 0), font=font)
            
            # تحويل إلى bytes
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=95)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء صورة الاختبار: {e}")
            return None
    
    def test_text_watermark_creation(self):
        """اختبار إنشاء علامة مائية نصية"""
        logger.info("🧪 اختبار إنشاء علامة مائية نصية...")
        
        try:
            # إعدادات العلامة المائية
            settings = {
                'watermark_type': 'text',
                'watermark_text': 'اختبار العلامة المائية',
                'font_size': 32,
                'text_color': '#FF0000',
                'opacity': 80,
                'position': 'bottom_right',
                'size_percentage': 20,
                'offset_x': 0,
                'offset_y': 0
            }
            
            # إنشاء صورة اختبار
            test_image = self.create_test_image(800, 600, "صورة اختبار")
            if not test_image:
                return False
            
            # تطبيق العلامة المائية
            result = self.processor.apply_watermark_to_image(test_image, settings)
            
            if result and result != test_image:
                logger.info("✅ نجح اختبار إنشاء العلامة المائية النصية")
                self.test_results['text_watermark'] = True
                return True
            else:
                logger.error("❌ فشل اختبار إنشاء العلامة المائية النصية")
                self.test_results['text_watermark'] = False
                return False
                
        except Exception as e:
            logger.error(f"❌ خطأ في اختبار العلامة المائية النصية: {e}")
            self.test_results['text_watermark'] = False
            return False
    
    def test_image_watermark_loading(self):
        """اختبار تحميل علامة مائية من صورة"""
        logger.info("🧪 اختبار تحميل علامة مائية من صورة...")
        
        try:
            # إنشاء صورة اختبار كعلامة مائية
            watermark_image = self.create_test_image(200, 100, "علامة")
            if not watermark_image:
                return False
            
            # حفظ الصورة مؤقتاً
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            temp_file.write(watermark_image)
            temp_file.close()
            
            try:
                # اختبار تحميل العلامة المائية
                result = self.processor.load_image_watermark(
                    temp_file.name,
                    size_percentage=30,
                    opacity=70,
                    base_image_size=(800, 600),
                    position='bottom_right'
                )
                
                if result:
                    logger.info("✅ نجح اختبار تحميل العلامة المائية من صورة")
                    self.test_results['image_watermark'] = True
                    return True
                else:
                    logger.error("❌ فشل اختبار تحميل العلامة المائية من صورة")
                    self.test_results['image_watermark'] = False
                    return False
                    
            finally:
                # تنظيف الملف المؤقت
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
                    
        except Exception as e:
            logger.error(f"❌ خطأ في اختبار تحميل العلامة المائية: {e}")
            self.test_results['image_watermark'] = False
            return False
    
    def test_media_type_detection(self):
        """اختبار تحديد نوع الوسائط"""
        logger.info("🧪 اختبار تحديد نوع الوسائط...")
        
        try:
            test_cases = [
                ('test.jpg', 'photo'),
                ('test.png', 'photo'),
                ('test.mp4', 'video'),
                ('test.avi', 'video'),
                ('test.pdf', 'document'),
                ('test.txt', 'document')
            ]
            
            all_passed = True
            
            for filename, expected_type in test_cases:
                detected_type = self.processor.get_media_type_from_file(filename)
                if detected_type == expected_type:
                    logger.info(f"✅ {filename}: {expected_type} ✓")
                else:
                    logger.error(f"❌ {filename}: متوقع {expected_type}, تم اكتشاف {detected_type}")
                    all_passed = False
            
            self.test_results['media_type_detection'] = all_passed
            return all_passed
            
        except Exception as e:
            logger.error(f"❌ خطأ في اختبار تحديد نوع الوسائط: {e}")
            self.test_results['media_type_detection'] = False
            return False
    
    def test_watermark_application_logic(self):
        """اختبار منطق تطبيق العلامة المائية"""
        logger.info("🧪 اختبار منطق تطبيق العلامة المائية...")
        
        try:
            # اختبار 1: العلامة المائية معطلة
            disabled_settings = {
                'enabled': False,
                'apply_to_photos': True,
                'apply_to_videos': True,
                'apply_to_documents': False
            }
            
            should_apply = self.processor.should_apply_watermark('photo', disabled_settings)
            if not should_apply:
                logger.info("✅ العلامة المائية المعطلة لا تطبق ✓")
            else:
                logger.error("❌ العلامة المائية المعطلة تطبق")
                return False
            
            # اختبار 2: العلامة المائية مفعلة للصور
            enabled_photo_settings = {
                'enabled': True,
                'apply_to_photos': True,
                'apply_to_videos': False,
                'apply_to_documents': False
            }
            
            should_apply = self.processor.should_apply_watermark('photo', enabled_photo_settings)
            if should_apply:
                logger.info("✅ العلامة المائية المفعلة تطبق على الصور ✓")
            else:
                logger.error("❌ العلامة المائية المفعلة لا تطبق على الصور")
                return False
            
            # اختبار 3: العلامة المائية لا تطبق على الفيديوهات
            should_apply = self.processor.should_apply_watermark('video', enabled_photo_settings)
            if not should_apply:
                logger.info("✅ العلامة المائية لا تطبق على الفيديوهات ✓")
            else:
                logger.error("❌ العلامة المائية تطبق على الفيديوهات")
                return False
            
            logger.info("✅ نجح اختبار منطق تطبيق العلامة المائية")
            self.test_results['watermark_logic'] = True
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في اختبار منطق تطبيق العلامة المائية: {e}")
            self.test_results['watermark_logic'] = False
            return False
    
    def test_cache_functionality(self):
        """اختبار وظائف الذاكرة المؤقتة"""
        logger.info("🧪 اختبار وظائف الذاكرة المؤقتة...")
        
        try:
            # اختبار إحصائيات الذاكرة المؤقتة
            stats = self.processor.get_cache_stats()
            initial_size = stats['cache_size']
            
            logger.info(f"📊 حجم الذاكرة المؤقتة الأولي: {initial_size}")
            
            # اختبار مسح الذاكرة المؤقتة
            self.processor.clear_cache()
            
            stats_after_clear = self.processor.get_cache_stats()
            if stats_after_clear['cache_size'] == 0:
                logger.info("✅ نجح مسح الذاكرة المؤقتة ✓")
            else:
                logger.error("❌ فشل مسح الذاكرة المؤقتة")
                return False
            
            logger.info("✅ نجح اختبار وظائف الذاكرة المؤقتة")
            self.test_results['cache_functionality'] = True
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في اختبار وظائف الذاكرة المؤقتة: {e}")
            self.test_results['cache_functionality'] = False
            return False
    
    def test_ffmpeg_availability(self):
        """اختبار توفر FFmpeg"""
        logger.info("🧪 اختبار توفر FFmpeg...")
        
        try:
            if self.processor.ffmpeg_available:
                logger.info("✅ FFmpeg متوفر ✓")
                self.test_results['ffmpeg_available'] = True
                return True
            else:
                logger.warning("⚠️ FFmpeg غير متوفر")
                self.test_results['ffmpeg_available'] = False
                return False
                
        except Exception as e:
            logger.error(f"❌ خطأ في اختبار توفر FFmpeg: {e}")
            self.test_results['ffmpeg_available'] = False
            return False
    
    def run_all_tests(self):
        """تشغيل جميع الاختبارات"""
        logger.info("🚀 بدء تشغيل جميع اختبارات العلامة المائية...")
        
        tests = [
            ('إنشاء علامة مائية نصية', self.test_text_watermark_creation),
            ('تحميل علامة مائية من صورة', self.test_image_watermark_loading),
            ('تحديد نوع الوسائط', self.test_media_type_detection),
            ('منطق تطبيق العلامة المائية', self.test_watermark_application_logic),
            ('وظائف الذاكرة المؤقتة', self.test_cache_functionality),
            ('توفر FFmpeg', self.test_ffmpeg_availability)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            logger.info(f"\n{'='*50}")
            logger.info(f"🧪 اختبار: {test_name}")
            logger.info(f"{'='*50}")
            
            try:
                if test_func():
                    passed += 1
                    logger.info(f"✅ نجح اختبار: {test_name}")
                else:
                    logger.error(f"❌ فشل اختبار: {test_name}")
            except Exception as e:
                logger.error(f"❌ خطأ في اختبار {test_name}: {e}")
        
        # عرض النتائج النهائية
        logger.info(f"\n{'='*50}")
        logger.info("📊 النتائج النهائية")
        logger.info(f"{'='*50}")
        
        for test_name, result in self.test_results.items():
            status = "✅ نجح" if result else "❌ فشل"
            logger.info(f"{test_name}: {status}")
        
        logger.info(f"\nالنتيجة الإجمالية: {passed}/{total} اختبارات نجحت")
        
        if passed == total:
            logger.info("🎉 جميع الاختبارات نجحت!")
            return True
        else:
            logger.warning(f"⚠️ {total - passed} اختبارات فشلت")
            return False

def main():
    """الدالة الرئيسية"""
    logger.info("🚀 بدء اختبار وظيفة العلامة المائية...")
    
    try:
        tester = WatermarkTester()
        success = tester.run_all_tests()
        
        if success:
            logger.info("🎉 تم إكمال جميع الاختبارات بنجاح!")
            sys.exit(0)
        else:
            logger.error("❌ بعض الاختبارات فشلت")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ خطأ عام في الاختبار: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()