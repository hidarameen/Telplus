import logging
from database.database import Database
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

class TaskManager:
    def __init__(self):
        self.db = Database()
    
    def create_main_menu_keyboard(self):
        """Create main menu keyboard"""
        keyboard = [
            [InlineKeyboardButton("📋 قائمة المهام", callback_data='list_tasks')],
            [InlineKeyboardButton("➕ إنشاء مهمة جديدة", callback_data='create_task_start')],
            [InlineKeyboardButton("⚙️ إعدادات", callback_data='settings')],
            [InlineKeyboardButton("🔐 تسجيل الدخول", callback_data='login_start')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_main_menu_text(self):
        """Get main menu welcome text"""
        return """
🤖 مرحباً بك في بوت التوجيه التلقائي

يمكنك من خلال هذا البوت:
• إنشاء مهام توجيه تلقائي
• مراقبة المحادثات المصدر
• توجيه الرسائل إلى المحادثات المستهدفة
• إدارة المهام (تفعيل/تعطيل/حذف)

اختر من القائمة أدناه:
        """
    
    def get_tasks_list_keyboard(self, tasks=None):
        """Create tasks list keyboard"""
        if tasks is None:
            tasks = self.db.get_all_tasks()
        
        if not tasks:
            keyboard = [
                [InlineKeyboardButton("➕ إنشاء مهمة جديدة", callback_data='create_task_start')],
                [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data='back_to_main')]
            ]
        else:
            keyboard = []
            for task in tasks[:10]:  # Show only first 10 tasks
                status_icon = "🟢" if task['is_active'] else "🔴"
                keyboard.append([
                    InlineKeyboardButton(
                        f"{status_icon} {task['name']}", 
                        callback_data=f'task_details_{task["id"]}'
                    )
                ])
            
            # Add navigation buttons
            if len(tasks) > 10:
                keyboard.append([InlineKeyboardButton("📄 المزيد...", callback_data='tasks_page_2')])
            
            keyboard.append([
                InlineKeyboardButton("➕ إنشاء مهمة جديدة", callback_data='create_task_start'),
                InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='back_to_main')
            ])
        
        return InlineKeyboardMarkup(keyboard)
    
    def get_tasks_list_text(self, tasks=None):
        """Get tasks list text"""
        if tasks is None:
            tasks = self.db.get_all_tasks()
        
        if not tasks:
            return "📋 لا توجد مهام حالياً\n\nيمكنك إنشاء مهمة جديدة من الأزرار أدناه:"
        
        text = "📋 قائمة المهام:\n\n"
        active_count = sum(1 for task in tasks if task['is_active'])
        inactive_count = len(tasks) - active_count
        
        text += f"📊 الإحصائيات:\n"
        text += f"• إجمالي المهام: {len(tasks)}\n"
        text += f"• نشط: {active_count}\n"
        text += f"• معطل: {inactive_count}\n\n"
        
        text += "اختر مهمة لعرض التفاصيل:\n"
        
        return text
    
    def get_task_details_keyboard(self, task_id):
        """Create task details keyboard"""
        task = self.db.get_task(task_id)
        if not task:
            return self.create_main_menu_keyboard()
        
        keyboard = [
            [
                InlineKeyboardButton("✏️ تعديل", callback_data=f'edit_task_{task_id}'),
                InlineKeyboardButton(
                    "⏸️ تعطيل" if task['is_active'] else "▶️ تفعيل", 
                    callback_data=f'toggle_task_{task_id}'
                )
            ],
            [
                InlineKeyboardButton("🗑️ حذف", callback_data=f'delete_task_confirm_{task_id}'),
                InlineKeyboardButton("📊 الإحصائيات", callback_data=f'task_stats_{task_id}')
            ],
            [
                InlineKeyboardButton("🔙 قائمة المهام", callback_data='list_tasks'),
                InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='back_to_main')
            ]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    def get_task_details_text(self, task_id):
        """Get task details text"""
        task = self.db.get_task(task_id)
        if not task:
            return "❌ المهمة غير موجودة"
        
        status = "🟢 نشط" if task['is_active'] else "🔴 معطل"
        
        text = f"📋 تفاصيل المهمة\n\n"
        text += f"🏷️ الاسم: {task['name']}\n"
        text += f"📊 الحالة: {status}\n"
        text += f"📅 تاريخ الإنشاء: {task['created_at'][:16]}\n\n"
        
        text += f"📥 المحادثات المصدر ({len(task['source_chats'])}):\n"
        for i, chat in enumerate(task['source_chats'][:5], 1):
            text += f"  {i}. {chat}\n"
        if len(task['source_chats']) > 5:
            text += f"  ... و {len(task['source_chats']) - 5} محادثة أخرى\n"
        
        text += f"\n📤 المحادثات المستهدفة ({len(task['target_chats'])}):\n"
        for i, chat in enumerate(task['target_chats'][:5], 1):
            text += f"  {i}. {chat}\n"
        if len(task['target_chats']) > 5:
            text += f"  ... و {len(task['target_chats']) - 5} محادثة أخرى\n"
        
        return text
    
    def create_task(self, name, source_chats, target_chats):
        """Create a new task"""
        try:
            # Clean and validate chats
            source_chats = [chat.strip() for chat in source_chats if chat.strip()]
            target_chats = [chat.strip() for chat in target_chats if chat.strip()]
            
            if not source_chats or not target_chats:
                return False, "يجب تحديد محادثات المصدر والهدف"
            
            task_id = self.db.create_task(name, source_chats, target_chats)
            logger.info(f"تم إنشاء المهمة {task_id}: {name}")
            return True, f"تم إنشاء المهمة '{name}' بنجاح"
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء المهمة: {e}")
            return False, f"حدث خطأ: {str(e)}"
    
    def update_task(self, task_id, name, source_chats, target_chats):
        """Update existing task"""
        try:
            # Clean and validate chats
            source_chats = [chat.strip() for chat in source_chats if chat.strip()]
            target_chats = [chat.strip() for chat in target_chats if chat.strip()]
            
            if not source_chats or not target_chats:
                return False, "يجب تحديد محادثات المصدر والهدف"
            
            self.db.update_task(task_id, name, source_chats, target_chats)
            logger.info(f"تم تحديث المهمة {task_id}: {name}")
            return True, f"تم تحديث المهمة '{name}' بنجاح"
            
        except Exception as e:
            logger.error(f"خطأ في تحديث المهمة: {e}")
            return False, f"حدث خطأ: {str(e)}"
    
    def toggle_task(self, task_id):
        """Toggle task active status"""
        try:
            task = self.db.get_task(task_id)
            if not task:
                return False, "المهمة غير موجودة"
            
            self.db.toggle_task(task_id)
            new_status = "تم تفعيل" if not task['is_active'] else "تم تعطيل"
            logger.info(f"{new_status} المهمة {task_id}: {task['name']}")
            return True, f"{new_status} المهمة '{task['name']}'"
            
        except Exception as e:
            logger.error(f"خطأ في تغيير حالة المهمة: {e}")
            return False, f"حدث خطأ: {str(e)}"
    
    def delete_task(self, task_id):
        """Delete a task"""
        try:
            task = self.db.get_task(task_id)
            if not task:
                return False, "المهمة غير موجودة"
            
            self.db.delete_task(task_id)
            logger.info(f"تم حذف المهمة {task_id}: {task['name']}")
            return True, f"تم حذف المهمة '{task['name']}'"
            
        except Exception as e:
            logger.error(f"خطأ في حذف المهمة: {e}")
            return False, f"حدث خطأ: {str(e)}"
    
    def get_active_tasks(self):
        """Get active tasks for userbot"""
        return self.db.get_active_tasks()