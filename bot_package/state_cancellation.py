"""
نظام إلغاء الحالة التلقائي
يحل مشكلة الاحتفاظ بحالة المستخدم بعد انتهاء العملية
"""

import logging
import time
from typing import Dict, Set, Optional
from .state_manager import StateManager, StateType

logger = logging.getLogger(__name__)

class StateCancellationManager:
    """مدير إلغاء الحالة التلقائي"""
    
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.cancellation_triggers: Dict[str, Set[str]] = {}
        self.setup_cancellation_triggers()
        
    def setup_cancellation_triggers(self):
        """إعداد محفزات الإلغاء"""
        # الأزرار التي تلغي الحالة عند الضغط عليها
        self.cancellation_triggers = {
            # الأزرار الرئيسية
            'start': {'*'},  # يلغي جميع الحالات
            'tasks': {'*'},  # يلغي جميع الحالات
            'advanced_features': {'*'},  # يلغي جميع الحالات
            
            # أزرار المهام
            'task_settings': {'*'},  # يلغي جميع الحالات
            'back_to_tasks': {'*'},  # يلغي جميع الحالات
            
            # أزرار الإعدادات
            'character_limit_settings': {'editing_char_*'},
            'rate_limit_settings': {'editing_rate_*'},
            'forwarding_delay_settings': {'editing_forwarding_*'},
            'sending_interval_settings': {'editing_sending_*'},
            
            # أزرار الوسوم الصوتية
            'audio_metadata_settings': {'editing_audio_tag_*'},
            'audio_template_settings': {'editing_audio_tag_*'},
            
            # أزرار العلامة المائية
            'watermark_settings': {'watermark_text_input_*', 'watermark_image_input_*'},
            
            # أزرار الرفع
            'album_art_settings': {'awaiting_album_art_upload'},
            'audio_merge_settings': {'awaiting_intro_audio_upload', 'awaiting_outro_audio_upload'},
            
            # أزرار إدارة القنوات
            'manage_channels': {'*'},
            'list_channels': {'*'},
            
            # أزرار الرجوع
            'back': {'*'},  # يلغي جميع الحالات
            'cancel': {'*'},  # يلغي جميع الحالات
            'exit': {'*'},  # يلغي جميع الحالات
        }
    
    def should_cancel_state(self, button_data: str, current_state: str) -> bool:
        """التحقق من الحاجة لإلغاء الحالة"""
        if not current_state:
            return False
            
        # البحث عن محفزات الإلغاء
        for trigger, affected_states in self.cancellation_triggers.items():
            if button_data.startswith(trigger):
                # التحقق من تطابق الحالة المتأثرة
                for affected_state in affected_states:
                    if affected_state == '*':  # يلغي جميع الحالات
                        return True
                    elif affected_state.endswith('*'):  # نمط مع wildcard
                        pattern = affected_state[:-1]  # إزالة *
                        if current_state.startswith(pattern):
                            return True
                    elif current_state == affected_state:  # تطابق دقيق
                        return True
                        
        return False
    
    def cancel_state_if_needed(self, user_id: int, button_data: str) -> bool:
        """إلغاء الحالة إذا لزم الأمر"""
        current_state = self.state_manager.get_user_state(user_id)
        
        if self.should_cancel_state(button_data, current_state):
            logger.info(f"🔄 إلغاء الحالة للمستخدم {user_id} بسبب الضغط على {button_data}")
            self.state_manager.clear_user_state(user_id)
            return True
            
        return False
    
    def cancel_state_by_pattern(self, user_id: int, pattern: str) -> bool:
        """إلغاء الحالة حسب النمط"""
        current_state = self.state_manager.get_user_state(user_id)
        
        if current_state and current_state.startswith(pattern):
            logger.info(f"🔄 إلغاء الحالة للمستخدم {user_id} حسب النمط {pattern}")
            self.state_manager.clear_user_state(user_id)
            return True
            
        return False
    
    def cancel_all_states(self, user_id: int) -> bool:
        """إلغاء جميع الحالات"""
        if self.state_manager.get_user_state(user_id):
            logger.info(f"🔄 إلغاء جميع الحالات للمستخدم {user_id}")
            self.state_manager.clear_user_state(user_id)
            return True
            
        return False

class StateTimeoutHandler:
    """معالج انتهاء صلاحية الحالات"""
    
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.timeout_messages = {
            'editing_audio_tag_': "⏰ انتهت مهلة تعديل الوسم الصوتي",
            'editing_char_': "⏰ انتهت مهلة تعديل حدود الأحرف",
            'editing_rate_': "⏰ انتهت مهلة تعديل حدود المعدل",
            'editing_forwarding_': "⏰ انتهت مهلة تعديل تأخير التوجيه",
            'editing_sending_': "⏰ انتهت مهلة تعديل فترات الإرسال",
            'editing_signature_': "⏰ انتهت مهلة تعديل توقيع المشرف",
            'awaiting_': "⏰ انتهت مهلة رفع الملف",
            'watermark_text_input_': "⏰ انتهت مهلة إدخال نص العلامة المائية",
            'watermark_image_input_': "⏰ انتهت مهلة رفع صورة العلامة المائية",
        }
    
    def get_timeout_message(self, state: str) -> str:
        """الحصول على رسالة انتهاء الصلاحية"""
        for pattern, message in self.timeout_messages.items():
            if state.startswith(pattern):
                return message
        return "⏰ انتهت مهلة العملية"
    
    def handle_timeout(self, user_id: int, state: str) -> str:
        """معالجة انتهاء الصلاحية"""
        message = self.get_timeout_message(state)
        self.state_manager.clear_user_state(user_id)
        return message

class StateValidationHandler:
    """معالج التحقق من صحة الحالة"""
    
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.valid_states = {
            # حالات تعديل الوسوم الصوتية
            'editing_audio_tag_title',
            'editing_audio_tag_artist',
            'editing_audio_tag_album_artist',
            'editing_audio_tag_album',
            'editing_audio_tag_year',
            'editing_audio_tag_genre',
            'editing_audio_tag_composer',
            'editing_audio_tag_comment',
            'editing_audio_tag_track',
            'editing_audio_tag_length',
            'editing_audio_tag_lyrics',
            
            # حالات تعديل حدود الأحرف
            'editing_char_min',
            'editing_char_max',
            
            # حالات تعديل حدود المعدل
            'editing_rate_count',
            'editing_rate_period',
            
            # حالات تعديل التوجيه
            'editing_forwarding_delay',
            'editing_sending_interval',
            
            # حالات تعديل التوقيع
            'editing_signature_',
            
            # حالات الرفع
            'awaiting_album_art_upload',
            'awaiting_intro_audio_upload',
            'awaiting_outro_audio_upload',
            
            # حالات العلامة المائية
            'watermark_text_input_',
            'watermark_image_input_',
        }
    
    def is_valid_state(self, state: str) -> bool:
        """التحقق من صحة الحالة"""
        # التحقق من الحالات المحددة
        for valid_state in self.valid_states:
            if state.startswith(valid_state):
                return True
        return False
    
    def validate_and_cleanup(self, user_id: int) -> bool:
        """التحقق من صحة الحالة وتنظيفها إذا لزم الأمر"""
        current_state = self.state_manager.get_user_state(user_id)
        
        if current_state and not self.is_valid_state(current_state):
            logger.warning(f"🧹 تنظيف حالة غير صحيحة للمستخدم {user_id}: {current_state}")
            self.state_manager.clear_user_state(user_id)
            return True
            
        return False

class StateRecoveryHandler:
    """معالج استعادة الحالة"""
    
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.recovery_data: Dict[int, Dict] = {}
    
    def save_state_for_recovery(self, user_id: int, state: str, data: Dict):
        """حفظ الحالة للاستعادة"""
        self.recovery_data[user_id] = {
            'state': state,
            'data': data,
            'timestamp': time.time()
        }
        logger.info(f"💾 حفظ الحالة للاستعادة للمستخدم {user_id}")
    
    def recover_state(self, user_id: int) -> Optional[Dict]:
        """استعادة الحالة"""
        if user_id in self.recovery_data:
            recovery_info = self.recovery_data[user_id]
            # التحقق من أن البيانات ليست قديمة جداً (أقل من ساعة)
            if time.time() - recovery_info['timestamp'] < 3600:
                logger.info(f"🔄 استعادة الحالة للمستخدم {user_id}")
                return recovery_info
            else:
                # حذف البيانات القديمة
                del self.recovery_data[user_id]
                
        return None
    
    def clear_recovery_data(self, user_id: int):
        """مسح بيانات الاستعادة"""
        if user_id in self.recovery_data:
            del self.recovery_data[user_id]
            logger.info(f"🗑️ مسح بيانات الاستعادة للمستخدم {user_id}")

class StateMonitoringHandler:
    """معالج مراقبة الحالات"""
    
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.monitoring_data: Dict[int, Dict] = {}
    
    def start_monitoring(self, user_id: int, state: str):
        """بدء مراقبة الحالة"""
        self.monitoring_data[user_id] = {
            'state': state,
            'start_time': time.time(),
            'last_activity': time.time(),
            'activity_count': 0
        }
        logger.info(f"👁️ بدء مراقبة الحالة للمستخدم {user_id}: {state}")
    
    def update_activity(self, user_id: int):
        """تحديث النشاط"""
        if user_id in self.monitoring_data:
            self.monitoring_data[user_id]['last_activity'] = time.time()
            self.monitoring_data[user_id]['activity_count'] += 1
    
    def stop_monitoring(self, user_id: int):
        """إيقاف المراقبة"""
        if user_id in self.monitoring_data:
            monitoring_info = self.monitoring_data[user_id]
            duration = time.time() - monitoring_info['start_time']
            logger.info(f"👁️ إيقاف مراقبة الحالة للمستخدم {user_id}: {monitoring_info['activity_count']} نشاط في {duration:.1f} ثانية")
            del self.monitoring_data[user_id]
    
    def get_monitoring_stats(self) -> Dict:
        """الحصول على إحصائيات المراقبة"""
        stats = {
            'total_monitored': len(self.monitoring_data),
            'active_states': self.state_manager.get_active_states_count(),
            'expired_states': self.state_manager.get_expired_states_count(),
            'monitoring_details': {}
        }
        
        for user_id, info in self.monitoring_data.items():
            stats['monitoring_details'][user_id] = {
                'state': info['state'],
                'duration': time.time() - info['start_time'],
                'activity_count': info['activity_count'],
                'last_activity': time.time() - info['last_activity']
            }
            
        return stats