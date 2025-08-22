"""
نظام إدارة الحالة المتكامل
يحل مشكلة الاحتفاظ بحالة المستخدم بعد انتهاء العملية
"""

import logging
import time
import asyncio
from typing import Dict, Any, Optional, Callable
from .state_manager import StateManager, StateType
from .state_cancellation import (
    StateCancellationManager, 
    StateTimeoutHandler, 
    StateValidationHandler,
    StateRecoveryHandler,
    StateMonitoringHandler
)

logger = logging.getLogger(__name__)

class EnhancedStateManager:
    """نظام إدارة الحالة المتكامل"""
    
    def __init__(self):
        # المدير الأساسي للحالة
        self.state_manager = StateManager()
        
        # مديري الحالة المتخصصين
        self.cancellation_manager = StateCancellationManager(self.state_manager)
        self.timeout_handler = StateTimeoutHandler(self.state_manager)
        self.validation_handler = StateValidationHandler(self.state_manager)
        self.recovery_handler = StateRecoveryHandler(self.state_manager)
        self.monitoring_handler = StateMonitoringHandler(self.state_manager)
        
        # إعدادات النظام
        self.auto_cleanup_interval = 60  # ثانية
        self.cleanup_task = None
        
        # بدء مهمة التنظيف التلقائي
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """بدء مهمة التنظيف التلقائي"""
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(self.auto_cleanup_interval)
                    self._perform_cleanup()
                except Exception as e:
                    logger.error(f"خطأ في حلقة التنظيف: {e}")
        
        # إنشاء المهمة في الخلفية
        try:
            loop = asyncio.get_event_loop()
            self.cleanup_task = loop.create_task(cleanup_loop())
        except RuntimeError:
            # إذا لم يكن هناك حلقة نشطة، سنقوم بالتنظيف يدوياً
            logger.warning("لا توجد حلقة نشطة، سيتم التنظيف يدوياً")
    
    def _perform_cleanup(self):
        """تنفيذ التنظيف"""
        try:
            # تنظيف الحالات المنتهية الصلاحية
            expired_count = self.state_manager.cleanup_expired_states()
            
            # التحقق من صحة الحالات
            invalid_count = 0
            for user_id in list(self.state_manager.user_states.keys()):
                if self.validation_handler.validate_and_cleanup(user_id):
                    invalid_count += 1
            
            if expired_count > 0 or invalid_count > 0:
                logger.info(f"🧹 تم تنظيف {expired_count} حالة منتهية و {invalid_count} حالة غير صحيحة")
                
        except Exception as e:
            logger.error(f"خطأ في التنظيف: {e}")
    
    # دوال إدارة الحالة الأساسية
    def set_user_state(self, user_id: int, state: str, data: Dict[str, Any] = None, 
                      state_type: StateType = StateType.TEMPORARY, timeout: float = None):
        """تعيين حالة المستخدم مع المراقبة"""
        # حفظ الحالة للاستعادة
        self.recovery_handler.save_state_for_recovery(user_id, state, data or {})
        
        # تعيين الحالة
        self.state_manager.set_user_state(user_id, state, data, state_type, timeout)
        
        # بدء المراقبة
        self.monitoring_handler.start_monitoring(user_id, state)
        
        logger.info(f"✅ تم تعيين حالة محسنة للمستخدم {user_id}: {state}")
    
    def get_user_state(self, user_id: int) -> Optional[str]:
        """الحصول على حالة المستخدم مع التحقق"""
        # التحقق من صحة الحالة
        self.validation_handler.validate_and_cleanup(user_id)
        
        # الحصول على الحالة
        state = self.state_manager.get_user_state(user_id)
        
        # تحديث النشاط
        if state:
            self.monitoring_handler.update_activity(user_id)
        
        return state
    
    def get_user_data(self, user_id: int) -> Dict[str, Any]:
        """الحصول على بيانات المستخدم"""
        return self.state_manager.get_user_data(user_id)
    
    def clear_user_state(self, user_id: int):
        """مسح حالة المستخدم مع إيقاف المراقبة"""
        # إيقاف المراقبة
        self.monitoring_handler.stop_monitoring(user_id)
        
        # مسح بيانات الاستعادة
        self.recovery_handler.clear_recovery_data(user_id)
        
        # مسح الحالة
        self.state_manager.clear_user_state(user_id)
        
        logger.info(f"🗑️ تم مسح حالة محسنة للمستخدم {user_id}")
    
    # دوال إلغاء الحالة
    def cancel_state_if_needed(self, user_id: int, button_data: str) -> bool:
        """إلغاء الحالة إذا لزم الأمر"""
        return self.cancellation_manager.cancel_state_if_needed(user_id, button_data)
    
    def cancel_state_by_pattern(self, user_id: int, pattern: str) -> bool:
        """إلغاء الحالة حسب النمط"""
        return self.cancellation_manager.cancel_state_by_pattern(user_id, pattern)
    
    def cancel_all_states(self, user_id: int) -> bool:
        """إلغاء جميع الحالات"""
        return self.cancellation_manager.cancel_all_states(user_id)
    
    # دوال انتهاء الصلاحية
    def handle_timeout(self, user_id: int, state: str) -> str:
        """معالجة انتهاء الصلاحية"""
        return self.timeout_handler.handle_timeout(user_id, state)
    
    def get_timeout_message(self, state: str) -> str:
        """الحصول على رسالة انتهاء الصلاحية"""
        return self.timeout_handler.get_timeout_message(state)
    
    # دوال الاستعادة
    def recover_state(self, user_id: int) -> Optional[Dict]:
        """استعادة الحالة"""
        return self.recovery_handler.recover_state(user_id)
    
    # دوال المراقبة
    def get_monitoring_stats(self) -> Dict:
        """الحصول على إحصائيات المراقبة"""
        return self.monitoring_handler.get_monitoring_stats()
    
    # دوال مساعدة
    def is_state_active(self, user_id: int) -> bool:
        """التحقق من نشاط الحالة"""
        return self.state_manager.is_state_active(user_id)
    
    def get_active_states_count(self) -> int:
        """الحصول على عدد الحالات النشطة"""
        return self.state_manager.get_active_states_count()
    
    def get_expired_states_count(self) -> int:
        """الحصول على عدد الحالات المنتهية الصلاحية"""
        return self.state_manager.get_expired_states_count()
    
    def get_state_info(self, user_id: int):
        """الحصول على معلومات الحالة"""
        return self.state_manager.get_state_info(user_id)
    
    def get_all_states_info(self):
        """الحصول على معلومات جميع الحالات"""
        return self.state_manager.get_all_states_info()
    
    # دوال إضافية
    def force_cleanup(self):
        """تنظيف إجباري"""
        self._perform_cleanup()
    
    def get_system_stats(self) -> Dict:
        """الحصول على إحصائيات النظام"""
        return {
            'active_states': self.get_active_states_count(),
            'expired_states': self.get_expired_states_count(),
            'total_states': len(self.state_manager.user_states),
            'monitoring_stats': self.get_monitoring_stats(),
            'cleanup_interval': self.auto_cleanup_interval
        }

class StateManagerDecorator:
    """مزين لإدارة الحالة مع وظائف إضافية"""
    
    def __init__(self, enhanced_state_manager: EnhancedStateManager):
        self.state_manager = enhanced_state_manager
        self.state_callbacks: Dict[str, Callable] = {}
    
    def register_state_callback(self, state_pattern: str, callback: Callable):
        """تسجيل callback للحالة"""
        self.state_callbacks[state_pattern] = callback
        logger.info(f"🔧 تم تسجيل callback للحالة: {state_pattern}")
    
    def unregister_state_callback(self, state_pattern: str):
        """إلغاء تسجيل callback للحالة"""
        if state_pattern in self.state_callbacks:
            del self.state_callbacks[state_pattern]
            logger.info(f"🔧 تم إلغاء تسجيل callback للحالة: {state_pattern}")
    
    def execute_state_callbacks(self, user_id: int, state: str, data: Any = None):
        """تنفيذ callbacks الحالة"""
        for pattern, callback in self.state_callbacks.items():
            if state.startswith(pattern):
                try:
                    callback(user_id, state, data)
                except Exception as e:
                    logger.error(f"خطأ في تنفيذ callback للحالة {pattern}: {e}")
    
    def set_user_state_with_callback(self, user_id: int, state: str, data: Dict[str, Any] = None, 
                                   state_type: StateType = StateType.TEMPORARY, timeout: float = None):
        """تعيين حالة المستخدم مع تنفيذ callbacks"""
        # تعيين الحالة
        self.state_manager.set_user_state(user_id, state, data, state_type, timeout)
        
        # تنفيذ callbacks
        self.execute_state_callbacks(user_id, state, data)
    
    def clear_user_state_with_callback(self, user_id: int):
        """مسح حالة المستخدم مع تنفيذ callbacks"""
        # الحصول على الحالة قبل المسح
        state = self.state_manager.get_user_state(user_id)
        data = self.state_manager.get_user_data(user_id)
        
        # مسح الحالة
        self.state_manager.clear_user_state(user_id)
        
        # تنفيذ callbacks الإلغاء
        if state:
            self.execute_state_callbacks(user_id, f"cancelled_{state}", data)

class StateManagerFactory:
    """مصنع لإدارة الحالة"""
    
    @staticmethod
    def create_enhanced_manager() -> EnhancedStateManager:
        """إنشاء مدير حالة محسن"""
        return EnhancedStateManager()
    
    @staticmethod
    def create_decorated_manager(enhanced_manager: EnhancedStateManager) -> StateManagerDecorator:
        """إنشاء مدير حالة مزين"""
        return StateManagerDecorator(enhanced_manager)
    
    @staticmethod
    def create_complete_manager() -> tuple[EnhancedStateManager, StateManagerDecorator]:
        """إنشاء نظام إدارة حالة كامل"""
        enhanced_manager = StateManagerFactory.create_enhanced_manager()
        decorated_manager = StateManagerFactory.create_decorated_manager(enhanced_manager)
        return enhanced_manager, decorated_manager

# دوال مساعدة للاستخدام السريع
def create_state_manager() -> EnhancedStateManager:
    """إنشاء مدير حالة سريع"""
    return StateManagerFactory.create_enhanced_manager()

def create_complete_state_system() -> tuple[EnhancedStateManager, StateManagerDecorator]:
    """إنشاء نظام حالة كامل"""
    return StateManagerFactory.create_complete_manager()

# دوال مساعدة للتعامل مع الحالات
def create_temporary_state_enhanced(state: str, data: Dict[str, Any] = None, timeout: float = 300) -> Dict[str, Any]:
    """إنشاء حالة مؤقتة محسنة"""
    return {
        'state': state,
        'data': data or {},
        'state_type': StateType.TEMPORARY,
        'timeout': timeout
    }

def create_persistent_state_enhanced(state: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
    """إنشاء حالة دائمة محسنة"""
    return {
        'state': state,
        'data': data or {},
        'state_type': StateType.PERSISTENT,
        'timeout': None
    }

def create_timeout_state_enhanced(state: str, data: Dict[str, Any] = None, timeout: float = 600) -> Dict[str, Any]:
    """إنشاء حالة تنتهي بعد وقت محدد محسنة"""
    return {
        'state': state,
        'data': data or {},
        'state_type': StateType.TIMEOUT,
        'timeout': timeout
    }