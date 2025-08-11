
#!/usr/bin/env python3
"""اختبار شامل لتطبيق العلامة المائية على الفيديوهات"""

import sys
sys.path.append('.')

from watermark_processor import WatermarkProcessor
from database.database import Database
import tempfile
import os
import time

def create_test_video():
    """إنشاء فيديو اختبار بسيط"""
    try:
        import cv2
        import numpy as np
        
        # إنشاء فيديو اختبار بسيط
        temp_video = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        temp_video.close()
        
        # إعداد كاتب الفيديو
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_video.name, fourcc, 20.0, (640, 480))
        
        # إنشاء 100 إطار (5 ثوان)
        for i in range(100):
            # إنشاء إطار ملون
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            
            # تدرج لوني
            frame[:, :, 0] = (i * 2) % 255  # أزرق
            frame[:, :, 1] = (i * 3) % 255  # أخضر
            frame[:, :, 2] = (i * 4) % 255  # أحمر
            
            # إضافة نص
            cv2.putText(frame, f'Frame {i}', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            out.write(frame)
        
        out.release()
        print(f"✅ تم إنشاء فيديو اختبار: {temp_video.name}")
        return temp_video.name
        
    except Exception as e:
        print(f"❌ فشل في إنشاء فيديو الاختبار: {e}")
        return None

def test_video_watermark():
    """اختبار تطبيق العلامة المائية على الفيديو"""
    print("🎬 بدء اختبار العلامة المائية للفيديوهات")
    
    # إنشاء فيديو اختبار
    test_video_path = create_test_video()
    if not test_video_path:
        return
    
    try:
        # تهيئة المعالج وقاعدة البيانات
        processor = WatermarkProcessor()
        db = Database()
        
        # الحصول على إعدادات العلامة المائية الفعلية
        settings = db.get_watermark_settings(7)
        
        print(f"🔧 إعدادات العلامة المائية:")
        print(f"   - مفعلة: {settings.get('enabled')}")
        print(f"   - النوع: {settings.get('watermark_type')}")
        print(f"   - النص: {settings.get('watermark_text')}")
        print(f"   - الحجم: {settings.get('size_percentage')}%")
        print(f"   - الموضع: {settings.get('position')}")
        print(f"   - الشفافية: {settings.get('opacity')}%")
        print(f"   - للفيديوهات: {settings.get('apply_to_videos')}")
        
        # اختبار معلومات الفيديو
        video_info = processor.get_video_info(test_video_path)
        print(f"\n📊 معلومات الفيديو:")
        print(f"   - الأبعاد: {video_info.get('width')}x{video_info.get('height')}")
        print(f"   - FPS: {video_info.get('fps')}")
        print(f"   - عدد الإطارات: {video_info.get('frame_count')}")
        print(f"   - المدة: {video_info.get('duration'):.1f} ثانية")
        
        # اختبار قدرة النظام على معالجة الفيديو
        can_process = processor.test_video_processing(test_video_path)
        print(f"\n🔬 قدرة النظام على المعالجة: {'✅ نعم' if can_process else '❌ لا'}")
        
        if not can_process:
            print("⚠️ النظام غير قادر على معالجة الفيديوهات")
            return
        
        # تطبيق العلامة المائية
        print(f"\n🎯 بدء تطبيق العلامة المائية...")
        start_time = time.time()
        
        result_path = processor.apply_watermark_to_video(test_video_path, settings)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        if result_path and os.path.exists(result_path):
            result_size = os.path.getsize(result_path) / (1024 * 1024)
            original_size = os.path.getsize(test_video_path) / (1024 * 1024)
            
            print(f"✅ تم تطبيق العلامة المائية بنجاح!")
            print(f"📁 الملف الأصلي: {original_size:.1f} MB")
            print(f"📁 الملف المعالج: {result_size:.1f} MB")
            print(f"⏱️ وقت المعالجة: {processing_time:.1f} ثانية")
            print(f"💾 مسار النتيجة: {result_path}")
            
            # التحقق من صحة الفيديو المعالج
            result_info = processor.get_video_info(result_path)
            print(f"\n📊 معلومات الفيديو المعالج:")
            print(f"   - الأبعاد: {result_info.get('width')}x{result_info.get('height')}")
            print(f"   - FPS: {result_info.get('fps')}")
            print(f"   - عدد الإطارات: {result_info.get('frame_count')}")
            
            # حذف الملف المعالج
            try:
                os.unlink(result_path)
                print("🗑️ تم حذف الملف المعالج")
            except:
                pass
        else:
            print("❌ فشل في تطبيق العلامة المائية")
            
    except Exception as e:
        print(f"❌ خطأ في الاختبار: {e}")
        import traceback
        print(f"🔍 تفاصيل الخطأ: {traceback.format_exc()}")
        
    finally:
        # حذف فيديو الاختبار
        try:
            os.unlink(test_video_path)
            print("🗑️ تم حذف فيديو الاختبار")
        except:
            pass

def test_with_real_video():
    """اختبار مع فيديو حقيقي إذا كان متاحاً"""
    print("\n🎭 اختبار مع فيديو حقيقي...")
    
    # البحث عن فيديوهات في المجلد
    video_files = []
    for ext in ['.mp4', '.avi', '.mov', '.mkv']:
        import glob
        video_files.extend(glob.glob(f"*{ext}"))
    
    if not video_files:
        print("⚠️ لا توجد ملفات فيديو للاختبار")
        return
    
    test_video = video_files[0]
    print(f"🎬 اختبار مع: {test_video}")
    
    try:
        processor = WatermarkProcessor()
        db = Database()
        
        # قراءة الفيديو كـ bytes
        with open(test_video, 'rb') as f:
            video_bytes = f.read()
        
        # الحصول على الإعدادات
        settings = db.get_watermark_settings(7)
        
        # معالجة الفيديو
        result_bytes = processor.process_media_with_watermark(video_bytes, test_video, settings)
        
        if result_bytes and result_bytes != video_bytes:
            # حفظ النتيجة
            result_path = f"watermarked_{test_video}"
            with open(result_path, 'wb') as f:
                f.write(result_bytes)
            
            print(f"✅ تم تطبيق العلامة المائية وحفظ النتيجة في: {result_path}")
        else:
            print("❌ لم يتم تطبيق العلامة المائية")
            
    except Exception as e:
        print(f"❌ خطأ في اختبار الفيديو الحقيقي: {e}")

if __name__ == "__main__":
    # تشغيل الاختبارات
    test_video_watermark()
    test_with_real_video()
    
    print("\n🎉 انتهى الاختبار")
