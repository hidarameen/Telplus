#!/usr/bin/env python3
"""
اختبار سريع لمقارنة السرعة بين المعالجة الإطارية والمعالجة السريعة
"""

import sys
import os
import time
import tempfile
import subprocess

# إضافة المسار للوحدات
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from watermark_processor import WatermarkProcessor
from watermark_processor_optimized import OptimizedWatermarkProcessor

def create_test_video():
    """إنشاء فيديو اختبار سريع"""
    temp_dir = tempfile.gettempdir()
    video_path = os.path.join(temp_dir, "speed_test_video.mp4")
    
    # إنشاء فيديو 10 ثانية بـ 30 FPS
    cmd = [
        'ffmpeg', '-y', '-f', 'lavfi', '-i', 
        'testsrc=duration=10:size=1280x720:rate=30',
        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
        video_path
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=30)
        return video_path
    except:
        print("❌ فشل في إنشاء فيديو اختبار")
        return None

def test_frame_by_frame_vs_fast():
    """مقارنة المعالجة الإطارية مع المعالجة السريعة"""
    print("🎯 مقارنة المعالجة الإطارية مع المعالجة السريعة")
    print("="*60)
    
    # إنشاء فيديو اختبار
    video_path = create_test_video()
    if not video_path:
        return
    
    video_size = os.path.getsize(video_path) / 1024 / 1024  # MB
    print(f"📹 حجم الفيديو: {video_size:.1f} MB")
    
    # إعدادات العلامة المائية
    watermark_settings = {
        'watermark_type': 'text',
        'watermark_text': 'اختبار السرعة',
        'font_size': 32,
        'text_color': '#FFFFFF',
        'opacity': 70,
        'position': 'bottom_right',
    }
    
    # اختبار المعالج الأصلي (إطار بإطار)
    print("\n🔄 اختبار المعالج الأصلي (إطار بإطار):")
    original_processor = WatermarkProcessor()
    
    start_time = time.time()
    try:
        result_original = original_processor.apply_watermark_to_video(video_path, watermark_settings)
        time_original = time.time() - start_time
        success_original = result_original is not None and os.path.exists(result_original)
    except Exception as e:
        time_original = time.time() - start_time
        success_original = False
        print(f"   ❌ خطأ: {e}")
    
    print(f"   ⏱️ الوقت: {time_original:.1f}s")
    print(f"   ✅ النجاح: {success_original}")
    
    # اختبار المعالج المحسن (جميع الإطارات مرة واحدة)
    print("\n⚡ اختبار المعالج المحسن (جميع الإطارات مرة واحدة):")
    optimized_processor = OptimizedWatermarkProcessor()
    
    start_time = time.time()
    try:
        result_optimized = optimized_processor.apply_watermark_to_video_fast(video_path, watermark_settings)
        time_optimized = time.time() - start_time
        success_optimized = result_optimized is not None and os.path.exists(result_optimized)
    except Exception as e:
        time_optimized = time.time() - start_time
        success_optimized = False
        print(f"   ❌ خطأ: {e}")
    
    print(f"   ⏱️ الوقت: {time_optimized:.1f}s")
    print(f"   ✅ النجاح: {success_optimized}")
    
    # تحليل النتائج
    print("\n📊 تحليل النتائج:")
    print("="*60)
    
    if success_original and success_optimized:
        speedup = time_original / time_optimized if time_optimized > 0 else 0
        time_saved = time_original - time_optimized
        percentage_improvement = ((time_original - time_optimized) / time_original) * 100
        
        print(f"🚀 تحسين السرعة: {speedup:.1f}x أسرع")
        print(f"⏰ الوقت المحفوظ: {time_saved:.1f}s")
        print(f"📈 نسبة التحسين: {percentage_improvement:.1f}%")
        
        if speedup >= 10:
            print("🎉 تحسين مذهل! السرعة 10x أسرع أو أكثر")
        elif speedup >= 5:
            print("🚀 تحسين ممتاز! السرعة 5x أسرع")
        elif speedup >= 2:
            print("✅ تحسين جيد! السرعة 2x أسرع")
        else:
            print("⚠️ التحسين محدود")
    
    # تنظيف الملفات
    try:
        if os.path.exists(video_path):
            os.remove(video_path)
        if success_original and result_original and os.path.exists(result_original):
            os.remove(result_original)
        if success_optimized and result_optimized and os.path.exists(result_optimized):
            os.remove(result_optimized)
    except:
        pass

if __name__ == "__main__":
    test_frame_by_frame_vs_fast()