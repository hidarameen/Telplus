"""
مساعد لإرسال الملفات مع اسم مخصص في Telethon
يحل مشكلة إرسال البيانات الخام (bytes) مع اسم ملف صحيح
"""
import io
import logging
from typing import Union, Optional

logger = logging.getLogger(__name__)

class TelethonFileSender:
    """مساعد لإرسال الملفات مع أسماء صحيحة"""
    
    @staticmethod
    async def send_file_with_name(client, entity, file_data: Union[bytes, any], filename: str, **kwargs):
        """
        إرسال ملف مع اسم مخصص
        يحل مشكلة Telethon مع البيانات الخام والأسماء المخصصة
        """
        try:
            # إذا كانت البيانات هي bytes، استخدم BytesIO مع name attribute
            if isinstance(file_data, bytes):
                logger.info(f"📤 إرسال ملف bytes مع اسم: {filename}")
                logger.info(f"📊 حجم البيانات: {len(file_data)} bytes")
                
                # إنشاء BytesIO stream مع اسم الملف
                file_stream = io.BytesIO(file_data)
                file_stream.name = filename  # تعيين اسم الملف
                
                logger.info(f"🔧 تم إنشاء BytesIO stream مع الاسم: {file_stream.name}")
                
                # إرسال الملف مع stream
                result = await client.send_file(entity, file_stream, **kwargs)
                logger.info(f"✅ تم إرسال الملف {filename} بنجاح باستخدام BytesIO")
                return result
            else:
                # للأنواع الأخرى، استخدم الطريقة العادية
                logger.info(f"📤 إرسال ملف عادي مع اسم: {filename}")
                return await client.send_file(entity, file_data, file_name=filename, **kwargs)
                
        except Exception as e:
            logger.error(f"❌ خطأ في إرسال الملف {filename}: {e}")
            import traceback
            logger.error(f"❌ تفاصيل الخطأ: {traceback.format_exc()}")
            # في حالة الخطأ، جرب upload_file أولاً
            try:
                if isinstance(file_data, bytes):
                    logger.info("🔄 محاولة بديلة باستخدام upload_file")
                    file_handle = await client.upload_file(
                        file=io.BytesIO(file_data),
                        file_name=filename
                    )
                    return await client.send_file(entity, file_handle, **kwargs)
                else:
                    return await client.send_file(entity, file_data, **kwargs)
            except Exception as e2:
                logger.error(f"❌ فشل حتى في الإرسال البديل: {e2}")
                raise e