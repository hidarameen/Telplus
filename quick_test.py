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
        
        actual_percentage = (calculated_size[0] / test_image_size[0]) * 100
        
        print("📈 النتيجة مع الإعدادات الفعلية:")
        print(f"   ➤ العلامة المائية الأصلية: {watermark_size}")
        print(f"   ➤ الحجم المحسوب: {calculated_size}")
        print(f"   ➤ النسبة الفعلية: {actual_percentage:.1f}%")
        print(f"   ➤ مقارنة مع الـ logs السابقة: {'✅ تحسن كبير' if actual_percentage > 50 else '❌ ما زال صغيراً'}")

if __name__ == "__main__":
    print("🚀 بدء اختبار الحسابات الجديدة...")
    print("=" * 50)
    test_size_calculation()
    print("=" * 50)
    test_with_real_settings()
    print("=" * 50)
    print("✅ انتهى الاختبار")