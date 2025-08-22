
#!/usr/bin/env python3
"""
فاحص تلقائي لحالة UserBot
يتحقق من صحة الجلسات ويعيد تشغيلها عند الحاجة
"""

import asyncio
import logging
from userbot_service.userbot import userbot_instance, start_userbot_service

logger = logging.getLogger(__name__)

class UserbotAutoChecker:
    def __init__(self):
        self.running = False
        self.check_interval = 30  # فحص كل 30 ثانية
    
    async def start_auto_checker(self):
        """بدء الفاحص التلقائي"""
        self.running = True
        logger.info("🔄 بدء الفاحص التلقائي للـ UserBot...")
        
        while self.running:
            try:
                await asyncio.sleep(self.check_interval)
                await self.check_and_restart_userbot()
            except Exception as e:
                logger.error(f"خطأ في الفاحص التلقائي: {e}")
    
    async def check_and_restart_userbot(self):
        """فحص وإعادة تشغيل UserBot عند الحاجة"""
        try:
            # فحص إذا كان UserBot يعمل
            if not userbot_instance.clients:
                logger.warning("⚠️ UserBot غير نشط - محاولة إعادة التشغيل التلقائي...")
                
                # محاولة إعادة التشغيل التلقائي
                success = await self._restart_userbot_automatically()
                if success:
                    logger.info("✅ تم إعادة تشغيل UserBot تلقائياً بنجاح")
                else:
                    logger.warning("❌ فشل في إعادة التشغيل التلقائي")
            else:
                # فحص صحة الجلسات الموجودة
                healthy_sessions = 0
                total_sessions = len(userbot_instance.clients)
                unhealthy_users = []
                
                for user_id in list(userbot_instance.clients.keys()):
                    try:
                        is_healthy = await userbot_instance.check_user_session_health(user_id)
                        if is_healthy:
                            healthy_sessions += 1
                        else:
                            logger.warning(f"⚠️ جلسة غير صحية للمستخدم {user_id}")
                            unhealthy_users.append(user_id)
                    except Exception as e:
                        logger.error(f"خطأ في فحص الجلسة للمستخدم {user_id}: {e}")
                        unhealthy_users.append(user_id)
                
                # إعادة تشغيل الجلسات غير الصحية
                if unhealthy_users:
                    logger.info(f"🔄 إعادة تشغيل {len(unhealthy_users)} جلسة غير صحية...")
                    for user_id in unhealthy_users:
                        await self._restart_single_user_session(user_id)
                
                if healthy_sessions == 0 and total_sessions > 0:
                    logger.warning("⚠️ جميع الجلسات غير صحية - إعادة تشغيل شامل...")
                    await self._restart_userbot_automatically()
                elif healthy_sessions < total_sessions:
                    logger.info(f"📊 {healthy_sessions}/{total_sessions} جلسة صحية")
                else:
                    logger.debug(f"✅ جميع الجلسات صحية ({healthy_sessions}/{total_sessions})")
                    
        except Exception as e:
            logger.error(f"خطأ في فحص UserBot: {e}")
    
    async def _restart_userbot_automatically(self):
        """إعادة تشغيل UserBot تلقائياً"""
        try:
            logger.info("🔄 بدء إعادة التشغيل التلقائي لـ UserBot...")
            
            # استيراد الوحدات المطلوبة
            from userbot_service.userbot import start_userbot_service
            from database.database import Database
            
            db = Database()
            
            # الحصول على جميع الجلسات المحفوظة
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, session_string, phone_number
                    FROM user_sessions
                    WHERE is_authenticated = TRUE AND session_string IS NOT NULL AND session_string != ''
                ''')
                saved_sessions = cursor.fetchall()
            
            if not saved_sessions:
                logger.warning("📝 لا توجد جلسات محفوظة للإعادة التشغيل")
                return False
            
            logger.info(f"📱 إعادة تشغيل {len(saved_sessions)} جلسة محفوظة...")
            
            # إيقاف الجلسات الحالية أولاً
            await userbot_instance.stop_all()
            await asyncio.sleep(5)  # انتظار قصير
            
            # تشغيل الجلسات المحفوظة
            success_count = 0
            for i, (user_id, session_string, phone_number) in enumerate(saved_sessions):
                try:
                    logger.info(f"🔄 إعادة تشغيل جلسة المستخدم {user_id} ({phone_number})...")
                    
                    # تأخير بين الجلسات لتجنب التضارب
                    if i > 0:
                        await asyncio.sleep(10)
                    
                    success = await userbot_instance.start_with_session(user_id, session_string)
                    if success:
                        success_count += 1
                        await userbot_instance.refresh_user_tasks(user_id)
                        logger.info(f"✅ تم إعادة تشغيل جلسة المستخدم {user_id} بنجاح")
                    else:
                        logger.warning(f"⚠️ فشل في إعادة تشغيل جلسة المستخدم {user_id}")
                        
                except Exception as e:
                    logger.error(f"❌ خطأ في إعادة تشغيل جلسة المستخدم {user_id}: {e}")
            
            logger.info(f"🎉 تم إعادة تشغيل {success_count} من أصل {len(saved_sessions)} جلسة")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"❌ خطأ في إعادة التشغيل التلقائي: {e}")
            return False
    
    async def _restart_single_user_session(self, user_id: int):
        """إعادة تشغيل جلسة مستخدم واحد"""
        try:
            logger.info(f"🔄 إعادة تشغيل جلسة المستخدم {user_id}...")
            
            from database.database import Database
            db = Database()
            
            # الحصول على جلسة المستخدم
            session_string = db.get_user_session_string(user_id)
            if not session_string:
                logger.warning(f"❌ لا توجد جلسة محفوظة للمستخدم {user_id}")
                return False
            
            # إيقاف الجلسة الحالية
            await userbot_instance.stop_user_session(user_id)
            await asyncio.sleep(3)
            
            # إعادة تشغيل الجلسة
            success = await userbot_instance.start_with_session(user_id, session_string)
            if success:
                await userbot_instance.refresh_user_tasks(user_id)
                logger.info(f"✅ تم إعادة تشغيل جلسة المستخدم {user_id} بنجاح")
                return True
            else:
                logger.warning(f"⚠️ فشل في إعادة تشغيل جلسة المستخدم {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ خطأ في إعادة تشغيل جلسة المستخدم {user_id}: {e}")
            return False
    
    def stop_auto_checker(self):
        """إيقاف الفاحص التلقائي"""
        self.running = False
        logger.info("⏹️ تم إيقاف الفاحص التلقائي للـ UserBot")

# مثيل عام للفاحص التلقائي
auto_checker = UserbotAutoChecker()
