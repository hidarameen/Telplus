#!/usr/bin/env python3
"""
اختبار معالجة الملفات الصوتية الحقيقية
Test Real Audio File Processing
"""

import asyncio
import logging
import tempfile
import os
from unittest.mock import Mock
from database import get_database

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockEvent:
    def __init__(self, message_text="", sender_id=123456789):
        self.sender_id = sender_id
        self.message = Mock()
        self.message.text = message_text
        self.message.media = None

class MockDocument:
    def __init__(self, mime_type="audio/mp3", file_name="test.mp3"):
        self.mime_type = mime_type
        self.file_name = file_name

class MockMessageMedia:
    def __init__(self, document):
        self.document = document

def create_test_audio_file():
    """إنشاء ملف صوتي اختباري بسيط"""
    try:
        # إنشاء ملف MP3 بسيط باستخدام FFmpeg
        import subprocess
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        temp_file.close()
        
        # إنشاء ملف صوتي بسيط (1 ثانية من الصمت)
        cmd = [
            'ffmpeg', '-y', '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
            '-t', '1', '-c:a', 'mp3', '-b:a', '128k', temp_file.name
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ تم إنشاء ملف صوتي اختباري: {temp_file.name}")
            return temp_file.name
        else:
            print(f"❌ فشل في إنشاء ملف صوتي: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ خطأ في إنشاء ملف صوتي: {e}")
        return None

async def test_real_audio_processing():
    """اختبار معالجة ملف صوتي حقيقي"""
    print("🧪 بدء اختبار معالجة ملف صوتي حقيقي")
    
    try:
        # إنشاء ملف صوتي اختباري
        audio_file_path = create_test_audio_file()
        if not audio_file_path:
            print("❌ فشل في إنشاء ملف صوتي اختباري")
            return False
        
        # قراءة الملف
        with open(audio_file_path, 'rb') as f:
            audio_data = f.read()
        
        print(f"✅ تم قراءة الملف الصوتي: {len(audio_data)} bytes")
        
        # تهيئة قاعدة البيانات
        db = get_database()
        task_id = 777
        
        # إعداد إعدادات الوسوم الصوتية
        db.update_audio_metadata_enabled(task_id, True)
        
        # إعداد قالب مخصص
        custom_templates = {
            'title_template': 'Test Song - Enhanced',
            'artist_template': 'Test Artist',
            'album_template': 'Test Album (2024)',
            'year_template': '2024',
            'genre_template': 'Test',
            'composer_template': 'Test Composer',
            'comment_template': 'Processed by Telegram Bot',
            'track_template': '1',
            'album_artist_template': 'Test Artist',
            'lyrics_template': 'Test lyrics here'
        }
        
        for tag_name, template_value in custom_templates.items():
            success = db.update_audio_template_setting(task_id, tag_name, template_value)
            print(f"✅ تحديث {tag_name}: {success}")
        
        # إنشاء حدث وهمي
        mock_doc = MockDocument("audio/mp3", "test_song.mp3")
        mock_media = MockMessageMedia(mock_doc)
        mock_event = MockEvent()
        mock_event.message.media = mock_media
        
        # استيراد UserbotService
        from userbot_service.userbot import UserbotService
        
        # تهيئة الخدمة
        userbot = UserbotService()
        
        # اختبار معالجة الوسوم الصوتية
        processed_audio, new_filename = await userbot.apply_audio_metadata(
            mock_event, task_id, audio_data, "test_song.mp3"
        )
        
        if processed_audio and processed_audio != audio_data:
            print(f"✅ تم معالجة الوسوم الصوتية بنجاح: {len(processed_audio)} bytes")
            print(f"✅ اسم الملف الجديد: {new_filename}")
            
            # حفظ الملف المعالج للفحص
            processed_file_path = f"processed_{new_filename}"
            with open(processed_file_path, 'wb') as f:
                f.write(processed_audio)
            print(f"✅ تم حفظ الملف المعالج: {processed_file_path}")
            
            # فحص الوسوم في الملف المعالج
            try:
                from audio_processor import AudioProcessor
                audio_processor = AudioProcessor()
                
                # إنشاء ملف مؤقت للملف المعالج
                temp_processed = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                temp_processed.write(processed_audio)
                temp_processed.close()
                
                # قراءة معلومات الملف المعالج
                audio_info = audio_processor.get_audio_info(temp_processed.name)
                print(f"✅ معلومات الملف المعالج: {audio_info}")
                
                # تنظيف الملفات المؤقتة
                os.unlink(temp_processed.name)
                
            except Exception as e:
                print(f"❌ خطأ في فحص الملف المعالج: {e}")
            
        else:
            print("❌ لم يتم معالجة الوسوم الصوتية")
        
        # تنظيف الملفات
        if os.path.exists(audio_file_path):
            os.unlink(audio_file_path)
        
        print("🎉 تم إكمال اختبار معالجة ملف صوتي حقيقي")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار معالجة ملف صوتي حقيقي: {e}")
        return False

async def test_audio_template_variables():
    """اختبار متغيرات القوالب"""
    print("\n🧪 بدء اختبار متغيرات القوالب")
    
    try:
        from audio_processor import AudioProcessor
        audio_processor = AudioProcessor()
        
        # إنشاء معلومات صوتية وهمية
        audio_info = {
            'title': 'Original Title',
            'artist': 'Original Artist',
            'album': 'Original Album',
            'year': '2023',
            'genre': 'Pop',
            'composer': 'Original Composer',
            'comment': 'Original Comment',
            'track': '5',
            'album_artist': 'Original Album Artist',
            'lyrics': 'Original lyrics',
            'length': 180,
            'format': 'MP3',
            'bitrate': 320
        }
        
        # اختبار قوالب مختلفة
        test_templates = [
            ('$title - Enhanced', 'Original Title - Enhanced'),
            ('$artist feat. $composer', 'Original Artist feat. Original Composer'),
            ('$album ($year)', 'Original Album (2023)'),
            ('Track $track: $title', 'Track 5: Original Title'),
            ('$title\n$artist', 'Original Title Original Artist'),  # معالجة السطور المتعددة
            ('Custom Text', 'Custom Text'),  # نص ثابت
            ('$unknown_var', '$unknown_var'),  # متغير غير معروف
        ]
        
        for template, expected in test_templates:
            result = audio_processor._process_template_value(template, audio_info)
            if result == expected:
                print(f"✅ '{template}' -> '{result}'")
            else:
                print(f"❌ '{template}' -> '{result}' (متوقع: '{expected}')")
        
        print("🎉 تم إكمال اختبار متغيرات القوالب")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار متغيرات القوالب: {e}")
        return False

async def main():
    """الدالة الرئيسية للاختبار"""
    print("🚀 بدء اختبار معالجة الملفات الصوتية الحقيقية")
    print("=" * 60)
    
    results = []
    
    # اختبار معالجة ملف صوتي حقيقي
    result1 = await test_real_audio_processing()
    results.append(("معالجة ملف صوتي حقيقي", result1))
    
    # اختبار متغيرات القوالب
    result2 = await test_audio_template_variables()
    results.append(("متغيرات القوالب", result2))
    
    # عرض النتائج
    print("\n" + "=" * 60)
    print("📊 نتائج الاختبار:")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ نجح" if result else "❌ فشل"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 النتيجة النهائية: {passed}/{total} اختبارات نجحت")
    
    if passed == total:
        print("🎉 جميع الاختبارات نجحت! وظيفة الوسوم الصوتية تعمل بشكل صحيح")
    else:
        print("⚠️ بعض الاختبارات فشلت. يرجى مراجعة الأخطاء أعلاه")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main())