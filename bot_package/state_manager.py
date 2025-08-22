"""
مدير حالة المستخدم المحسن
يحل مشكلة الاحتفاظ بحالة المستخدم بعد انتهاء العملية
"""

import time
import logging
from typing import Dict, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class StateType(Enum):
    """أنواع الحالات"""
    TEMPORARY = "temporary"  # مؤقتة - تنتهي تلقائياً
    PERSISTENT = "persistent"  # دائمة - تحتاج إلغاء يدوي
    TIMEOUT = "timeout"  # تنتهي بعد وقت محدد

@dataclass
class UserState:
    """حالة المستخدم"""
    state: str
    data: Dict[str, Any]
    state_type: StateType
    created_at: float
    timeout: Optional[float] = None
    max_retries: int = 3
    current_retries: int = 0
    last_activity: float = None

class StateManager:
    """مدير حالة المستخدم المحسن"""
    
    def __init__(self):
        self.user_states: Dict[int, UserState] = {}
        self.state_handlers: Dict[str, Callable] = {}
        self.default_timeout = 300  # 5 دقائق افتراضياً
        self.cleanup_interval = 60  # تنظيف كل دقيقة
        
    def set_user_state(self, user_id: int, state: str, data: Dict[str, Any] = None, 
                      state_type: StateType = StateType.TEMPORARY, timeout: float = None) -> None:
        """تعيين حالة المستخدم"""
        current_time = time.time()
        
        # تنظيف الحالة القديمة إذا كانت موجودة
        if user_id in self.user_states:
            old_state = self.user_states[user_id]
            logger.info(f"🧹 تنظيف الحالة القديمة للمستخدم {user_id}: {old_state.state}")
        
        # إنشاء حالة جديدة
        user_state = UserState(
            state=state,
            data=data or {},
            state_type=state_type,
            created_at=current_time,
            timeout=timeout or self.default_timeout,
            last_activity=current_time
        )
        
        self.user_states[user_id] = user_state
        logger.info(f"✅ تم تعيين حالة المستخدم {user_id}: {state} (نوع: {state_type.value})")
    
    def get_user_state(self, user_id: int) -> Optional[str]:
        """الحصول على حالة المستخدم"""
        if user_id not in self.user_states:
            return None
            
        user_state = self.user_states[user_id]
        
        # التحقق من انتهاء الصلاحية
        if self._is_state_expired(user_state):
            logger.info(f"⏰ انتهت صلاحية حالة المستخدم {user_id}: {user_state.state}")
            self.clear_user_state(user_id)
            return None
            
        # تحديث آخر نشاط
        user_state.last_activity = time.time()
        return user_state.state
    
    def get_user_data(self, user_id: int) -> Dict[str, Any]:
        """الحصول على بيانات المستخدم"""
        if user_id not in self.user_states:
            return {}
            
        user_state = self.user_states[user_id]
        
        # التحقق من انتهاء الصلاحية
        if self._is_state_expired(user_state):
            self.clear_user_state(user_id)
            return {}
            
        # تحديث آخر نشاط
        user_state.last_activity = time.time()
        return user_state.data
    
    def clear_user_state(self, user_id: int) -> None:
        """مسح حالة المستخدم"""
        if user_id in self.user_states:
            state = self.user_states[user_id].state
            del self.user_states[user_id]
            logger.info(f"🗑️ تم مسح حالة المستخدم {user_id}: {state}")
    
    def clear_all_states(self) -> None:
        """مسح جميع الحالات"""
        count = len(self.user_states)
        self.user_states.clear()
        logger.info(f"🗑️ تم مسح جميع حالات المستخدمين: {count} حالة")
    
    def _is_state_expired(self, user_state: UserState) -> bool:
        """التحقق من انتهاء صلاحية الحالة"""
        current_time = time.time()
        
        # التحقق من نوع الحالة
        if user_state.state_type == StateType.PERSISTENT:
            return False  # الحالات الدائمة لا تنتهي تلقائياً
            
        # التحقق من انتهاء الوقت
        if user_state.timeout:
            time_since_activity = current_time - user_state.last_activity
            if time_since_activity > user_state.timeout:
                return True
                
        # التحقق من عدد المحاولات
        if user_state.current_retries >= user_state.max_retries:
            return True
            
        return False
    
    def increment_retry(self, user_id: int) -> int:
        """زيادة عدد المحاولات"""
        if user_id in self.user_states:
            user_state = self.user_states[user_id]
            user_state.current_retries += 1
            user_state.last_activity = time.time()
            
            logger.info(f"🔄 محاولة {user_state.current_retries}/{user_state.max_retries} للمستخدم {user_id}")
            
            # مسح الحالة إذا تجاوزت الحد الأقصى
            if user_state.current_retries >= user_state.max_retries:
                logger.warning(f"❌ تجاوز الحد الأقصى للمحاولات للمستخدم {user_id}")
                self.clear_user_state(user_id)
                
            return user_state.current_retries
        return 0
    
    def reset_retry(self, user_id: int) -> None:
        """إعادة تعيين عدد المحاولات"""
        if user_id in self.user_states:
            user_state = self.user_states[user_id]
            user_state.current_retries = 0
            user_state.last_activity = time.time()
            logger.info(f"🔄 إعادة تعيين المحاولات للمستخدم {user_id}")
    
    def cleanup_expired_states(self) -> int:
        """تنظيف الحالات المنتهية الصلاحية"""
        expired_count = 0
        current_time = time.time()
        
        # إنشاء قائمة بالحالات المنتهية
        expired_users = []
        for user_id, user_state in self.user_states.items():
            if self._is_state_expired(user_state):
                expired_users.append(user_id)
        
        # مسح الحالات المنتهية
        for user_id in expired_users:
            state = self.user_states[user_id].state
            del self.user_states[user_id]
            logger.info(f"🧹 تنظيف حالة منتهية الصلاحية للمستخدم {user_id}: {state}")
            expired_count += 1
        
        if expired_count > 0:
            logger.info(f"🧹 تم تنظيف {expired_count} حالة منتهية الصلاحية")
            
        return expired_count
    
    def get_state_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """الحصول على معلومات الحالة"""
        if user_id not in self.user_states:
            return None
            
        user_state = self.user_states[user_id]
        current_time = time.time()
        
        return {
            'state': user_state.state,
            'data': user_state.data,
            'state_type': user_state.state_type.value,
            'created_at': user_state.created_at,
            'last_activity': user_state.last_activity,
            'timeout': user_state.timeout,
            'current_retries': user_state.current_retries,
            'max_retries': user_state.max_retries,
            'is_expired': self._is_state_expired(user_state),
            'time_since_activity': current_time - user_state.last_activity if user_state.last_activity else 0
        }
    
    def get_all_states_info(self) -> Dict[int, Dict[str, Any]]:
        """الحصول على معلومات جميع الحالات"""
        return {user_id: self.get_state_info(user_id) for user_id in self.user_states.keys()}
    
    def set_state_handler(self, state_prefix: str, handler: Callable) -> None:
        """تعيين معالج للحالة"""
        self.state_handlers[state_prefix] = handler
        logger.info(f"🔧 تم تعيين معالج للحالة: {state_prefix}")
    
    def get_state_handler(self, state: str) -> Optional[Callable]:
        """الحصول على معالج الحالة"""
        for prefix, handler in self.state_handlers.items():
            if state.startswith(prefix):
                return handler
        return None
    
    def is_state_active(self, user_id: int) -> bool:
        """التحقق من نشاط الحالة"""
        if user_id not in self.user_states:
            return False
        return not self._is_state_expired(self.user_states[user_id])
    
    def get_active_states_count(self) -> int:
        """الحصول على عدد الحالات النشطة"""
        return sum(1 for user_id in self.user_states.keys() if self.is_state_active(user_id))
    
    def get_expired_states_count(self) -> int:
        """الحصول على عدد الحالات المنتهية الصلاحية"""
        return sum(1 for user_id in self.user_states.keys() if not self.is_state_active(user_id))

class StateTimeoutManager:
    """مدير انتهاء صلاحية الحالات"""
    
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.last_cleanup = time.time()
    
    def should_cleanup(self) -> bool:
        """التحقق من الحاجة للتنظيف"""
        current_time = time.time()
        return current_time - self.last_cleanup >= self.state_manager.cleanup_interval
    
    def cleanup_if_needed(self) -> int:
        """التنظيف إذا لزم الأمر"""
        if self.should_cleanup():
            self.last_cleanup = time.time()
            return self.state_manager.cleanup_expired_states()
        return 0

# دوال مساعدة للتعامل مع الحالات
def create_temporary_state(state: str, data: Dict[str, Any] = None, timeout: float = 300) -> Dict[str, Any]:
    """إنشاء حالة مؤقتة"""
    return {
        'state': state,
        'data': data or {},
        'state_type': StateType.TEMPORARY,
        'timeout': timeout
    }

def create_persistent_state(state: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
    """إنشاء حالة دائمة"""
    return {
        'state': state,
        'data': data or {},
        'state_type': StateType.PERSISTENT,
        'timeout': None
    }

def create_timeout_state(state: str, data: Dict[str, Any] = None, timeout: float = 600) -> Dict[str, Any]:
    """إنشاء حالة تنتهي بعد وقت محدد"""
    return {
        'state': state,
        'data': data or {},
        'state_type': StateType.TIMEOUT,
        'timeout': timeout
    }