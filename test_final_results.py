#!/usr/bin/env python3
"""اختبار النتائج النهائية للتأكد من أن العلامة المائية تعمل بحجم كبير"""

import sys
sys.path.append('.')

from watermark_processor import WatermarkProcessor
from database.database import Database
from PIL import Image, ImageDraw, ImageFont
import io
import os

def create_test_image_and_apply_watermark():
    """إنشاء صورة اختبار وتطبيق العلامة المائية"""
    processor = WatermarkProcessor()
    db = Database()
    
    # الحصول على الإعدادات الفعلية
    settings = db.get_watermark_settings(7)
    
    # إنشاء صورة اختبار بحجم شائع
    test_img = Image.new('RGB', (1280, 720), 'lightblue')
    draw = ImageDraw.Draw(test_img)
    
    # رسم شبكة
    for x in range(0, 1280, 100):
        draw.line([(x, 0), (x, 720)], fill='white', width=1)
    for y in range(0, 720, 100):
        draw.line([(0, y), (1280, y)], fill='white', width=1)
    
    # كتابة أبعاد الصورة
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
    except:
        font = ImageFont.load_default()
    
    draw.text((400, 300), "1280 x 720", fill='darkblue', font=font)
    draw.text((400, 350), "اختبار العلامة المائية", fill='darkblue', font=font)
    
    # تحويل إلى bytes
    test_bytes = io.BytesIO()
    test_img.save(test_bytes, format='PNG')
    test_image_bytes = test_bytes.getvalue()
    
    print("🧪 تطبيق العلامة المائية على صورة اختبار...")
    print(f"📐 أبعاد الصورة: {test_img.size}")
    print(f"🔧 إعدادات العلامة المائية: حجم {settings.get('size_percentage')}%")
    
    # تطبيق العلامة المائية
    result = processor.apply_watermark_to_image(test_image_bytes, settings)
    
    if result:
        with open('test_final_watermark_result.png', 'wb') as f:
            f.write(result)
        print("✅ تم حفظ النتيجة في: test_final_watermark_result.png")
        
        # تحليل النتيجة
        result_img = Image.open(io.BytesIO(result))
        print(f"📊 أبعاد الصورة النهائية: {result_img.size}")
        
        return True
    else:
        print("❌ فشل في تطبيق العلامة المائية")
        return False

if __name__ == "__main__":
    print("🚀 اختبار النتائج النهائية...")
    success = create_test_image_and_apply_watermark()
    if success:
        print("🎉 تم الاختبار بنجاح! تحقق من الصورة المحفوظة.")
    else:
        print("💥 فشل الاختبار!")