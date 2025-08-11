
#!/usr/bin/env python3
"""اختبار تطبيق العلامة المائية على الصور"""

import sys
sys.path.append('.')

from watermark_processor import WatermarkProcessor
from database.database import Database
from PIL import Image, ImageDraw, ImageFont
import io
import os
import logging

# تفعيل السجلات
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def create_test_image():
    """إنشاء صورة اختبار"""
    # إنشاء صورة اختبار
    test_img = Image.new('RGB', (800, 600), 'lightblue')
    draw = ImageDraw.Draw(test_img)
    
    # رسم شبكة
    for x in range(0, 800, 50):
        draw.line([(x, 0), (x, 600)], fill='white', width=1)
    for y in range(0, 600, 50):
        draw.line([(0, y), (800, y)], fill='white', width=1)
    
    # كتابة نص
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
    except:
        font = ImageFont.load_default()
    
    draw.text((250, 250), "اختبار العلامة المائية", fill='darkblue', font=font)
    draw.text((300, 300), "800 x 600", fill='darkblue', font=font)
    
    # تحويل إلى bytes
    output = io.BytesIO()
    test_img.save(output, format='PNG')
    return output.getvalue()

def test_watermark_on_image():
    """اختبار تطبيق العلامة المائية"""
    print("🧪 بدء اختبار العلامة المائية على الصور...")
    
    # إنشاء معالج العلامة المائية
    processor = WatermarkProcessor()
    db = Database()
    
    # الحصول على إعدادات العلامة المائية للمهمة 7
    watermark_settings = db.get_watermark_settings(7)
    print(f"🔧 إعدادات العلامة المائية: {watermark_settings}")
    
    # التأكد من تفعيل العلامة المائية
    if not watermark_settings.get('enabled', False):
        print("⚠️ العلامة المائية غير مفعلة - سأقوم بتفعيلها")
        db.update_watermark_settings(7, enabled=True)
        watermark_settings = db.get_watermark_settings(7)
    
    # إنشاء صورة اختبار
    test_image_bytes = create_test_image()
    print(f"📷 تم إنشاء صورة اختبار - الحجم: {len(test_image_bytes)} بايت")
    
    # تطبيق العلامة المائية
    print("🔧 تطبيق العلامة المائية...")
    result_bytes = processor.process_media_with_watermark(
        test_image_bytes,
        "test_image.png",
        watermark_settings
    )
    
    if result_bytes and result_bytes != test_image_bytes:
        print("✅ تم تطبيق العلامة المائية بنجاح!")
        print(f"📊 الحجم الأصلي: {len(test_image_bytes)} بايت")
        print(f"📊 الحجم بعد العلامة المائية: {len(result_bytes)} بايت")
        
        # حفظ النتيجة
        with open("test_watermark_image_result.png", "wb") as f:
            f.write(result_bytes)
        print("💾 تم حفظ النتيجة في: test_watermark_image_result.png")
        
        return True
    else:
        print("❌ لم يتم تطبيق العلامة المائية")
        return False

if __name__ == "__main__":
    success = test_watermark_on_image()
    if success:
        print("\n🎉 الاختبار نجح! العلامة المائية تعمل على الصور.")
    else:
        print("\n💔 الاختبار فشل! هناك مشكلة في العلامة المائية.")
