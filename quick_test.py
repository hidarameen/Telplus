
#!/usr/bin/env python3
"""اختبار سريع للتحديثات الجديدة في خوارزمية تحديد حجم العلامة المائية"""

import sys
sys.path.append('.')

from watermark_processor import WatermarkProcessor
from database.database import Database
from PIL import Image, ImageDraw, ImageFont
import io
import os

def test_size_calculation():
    """اختبار حسابات الحجم الجديدة مقارنة مع القديمة"""
    processor = WatermarkProcessor()
    
    # صورة افتراضية 1280x720 (نفس الحجم من الـ logs)
    base_image_size = (1280, 720)
    watermark_size = (1280, 720)  # نفس حجم العلامة المائية من الـ logs
    
    print("🧮 اختبار حسابات الحجم الجديدة:")
    print(f"📐 أبعاد الصورة الأساسية: {base_image_size}")
    print(f"🏷️ أبعاد العلامة المائية الأصلية: {watermark_size}")
    print()
    
    # اختبار أحجام مختلفة
    for size_percentage in [25, 50, 75, 100]:
        calculated_size = processor.calculate_smart_watermark_size(
            base_image_size, watermark_size, size_percentage, 'bottom'
        )
        
        # حساب النسبة الفعلية من العرض
        actual_percentage = (calculated_size[0] / base_image_size[0]) * 100
        
        print(f"📊 حجم {size_percentage}%:")
        print(f"   ➤ الحجم المحسوب: {calculated_size}")
        print(f"   ➤ النسبة الفعلية من العرض: {actual_percentage:.1f}%")
        print(f"   ➤ متوقع أم لا: {'✅ متوقع' if actual_percentage >= size_percentage * 0.9 else '❌ صغير جداً'}")
        print()

def test_with_real_settings():
    """اختبار مع الإعدادات الفعلية من قاعدة البيانات"""
    db = Database()
    processor = WatermarkProcessor()
    
    settings = db.get_watermark_settings(7)
    print("🔧 الإعدادات الفعلية من قاعدة البيانات:")
    print(f"   - نسبة الحجم: {settings.get('size_percentage', 'غير محدد')}%")
    print(f"   - الموضع: {settings.get('position', 'غير محدد')}")
    print(f"   - الإزاحة: ({settings.get('offset_x', 0)}, {settings.get('offset_y', 0)})")
    print()
    
    # اختبار حساب الحجم مع الإعدادات الفعلية
    if settings.get('watermark_image_path') and os.path.exists(settings['watermark_image_path']):
        watermark_img = Image.open(settings['watermark_image_path'])
        watermark_size = watermark_img.size
        
        test_image_size = (1280, 720)  # من الـ logs الفعلية
        
        calculated_size = processor.calculate_smart_watermark_size(
            test_image_size, 
            watermark_size, 
            settings.get('size_percentage', 100), 
            settings.get('position', 'bottom')
        )
        
        print(f"🎯 النتيجة مع الإعدادات الفعلية:")
        print(f"   ➤ حجم العلامة الأصلي: {watermark_size}")
        print(f"   ➤ الحجم المحسوب: {calculated_size}")
        print(f"   ➤ نسبة التغيير: {(calculated_size[0]/watermark_size[0]*100):.1f}%")
    else:
        print("⚠️ لا توجد علامة مائية صورة في الإعدادات")

def test_video_capabilities():
    """اختبار قدرات معالجة الفيديو"""
    print("\n🎬 اختبار قدرات معالجة الفيديو:")
    
    try:
        import cv2
        print("✅ OpenCV متاح")
        
        # اختبار إنشاء فيديو بسيط
        import tempfile
        import numpy as np
        
        temp_video = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        temp_video.close()
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_video.name, fourcc, 20.0, (320, 240))
        
        # إنشاء 10 إطارات
        for i in range(10):
            frame = np.zeros((240, 320, 3), dtype=np.uint8)
            frame[:, :, i % 3] = 255  # لون مختلف لكل إطار
            out.write(frame)
        
        out.release()
        
        # قراءة الفيديو للتأكد
        cap = cv2.VideoCapture(temp_video.name)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        
        print(f"✅ تم إنشاء فيديو اختبار بـ {frame_count} إطار")
        
        # تنظيف
        os.unlink(temp_video.name)
        
    except ImportError:
        print("❌ OpenCV غير متاح")
    except Exception as e:
        print(f"❌ خطأ في اختبار الفيديو: {e}")
    
    # اختبار FFmpeg
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ FFmpeg متاح")
        else:
            print("⚠️ FFmpeg غير متاح")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("⚠️ FFmpeg غير مثبت")
    except Exception as e:
        print(f"❌ خطأ في فحص FFmpeg: {e}")

if __name__ == "__main__":
    print("🚀 بدء الاختبار السريع...")
    
    test_size_calculation()
    test_with_real_settings() 
    test_video_capabilities()
    
    print("\n🎉 انتهى الاختبار السريع")
