import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from database import Database
import config

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

db = Database()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command handler"""
    keyboard = [
        [InlineKeyboardButton("📋 قائمة المهام", callback_data='list_tasks')],
        [InlineKeyboardButton("➕ إنشاء مهمة جديدة", callback_data='create_task')],
        [InlineKeyboardButton("⚙️ إعدادات", callback_data='settings')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = """
🤖 مرحباً بك في بوت التوجيه التلقائي

يمكنك من خلال هذا البوت:
• إنشاء مهام توجيه تلقائي
• مراقبة المحادثات المصدر
• توجيه الرسائل إلى المحادثات المستهدفة
• إدارة المهام (تفعيل/تعطيل/حذف)

اختر من القائمة أدناه:
    """
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'list_tasks':
        await show_tasks(query)
    elif query.data == 'create_task':
        await show_create_task_info(query)
    elif query.data.startswith('toggle_task_'):
        task_id = int(query.data.split('_')[2])
        await toggle_task(query, task_id)
    elif query.data.startswith('delete_task_'):
        task_id = int(query.data.split('_')[2])
        await delete_task(query, task_id)
    elif query.data == 'back_to_main':
        await show_main_menu(query)

async def show_tasks(query) -> None:
    """Show list of all tasks"""
    tasks = db.get_all_tasks()
    
    if not tasks:
        text = "📋 لا توجد مهام حالياً\n\nيمكنك إنشاء مهمة جديدة من الرابط أدناه:"
        keyboard = [
            [InlineKeyboardButton("➕ إنشاء مهمة جديدة", callback_data='create_task')],
            [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data='back_to_main')]
        ]
    else:
        text = "📋 قائمة المهام:\n\n"
        keyboard = []
        
        for task in tasks:
            status = "🟢 نشط" if task['is_active'] else "🔴 معطل"
            text += f"🔸 {task['name']} - {status}\n"
            text += f"   المصادر: {len(task['source_chats'])} محادثة\n"
            text += f"   الأهداف: {len(task['target_chats'])} محادثة\n\n"
            
            # Add task control buttons
            toggle_text = "⏸️ تعطيل" if task['is_active'] else "▶️ تفعيل"
            keyboard.append([
                InlineKeyboardButton(toggle_text, callback_data=f'toggle_task_{task["id"]}'),
                InlineKeyboardButton("🗑️ حذف", callback_data=f'delete_task_{task["id"]}')
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data='back_to_main')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)

async def show_create_task_info(query) -> None:
    """Show information about creating tasks"""
    text = """
➕ لإنشاء مهمة جديدة:

يجب عليك استخدام لوحة التحكم الويب لإنشاء وإدارة المهام.

🌐 يمكنك الوصول للوحة التحكم من خلال:
http://localhost:5000

📝 خطوات الإنشاء:
1. قم بتسجيل الدخول برقم هاتفك
2. أدخل كود التفعيل من تطبيق تليجرام
3. أنشئ مهمة جديدة وحدد المحادثات
4. فعّل المهمة لبدء التوجيه التلقائي

⚡ سيتم تشغيل المهام تلقائياً في الخلفية
    """
    
    keyboard = [
        [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data='back_to_main')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)

async def toggle_task(query, task_id: int) -> None:
    """Toggle task status"""
    db.toggle_task(task_id)
    await query.answer("✅ تم تغيير حالة المهمة")
    await show_tasks(query)

async def delete_task(query, task_id: int) -> None:
    """Delete a task"""
    db.delete_task(task_id)
    await query.answer("🗑️ تم حذف المهمة")
    await show_tasks(query)

async def show_main_menu(query) -> None:
    """Show main menu"""
    keyboard = [
        [InlineKeyboardButton("📋 قائمة المهام", callback_data='list_tasks')],
        [InlineKeyboardButton("➕ إنشاء مهمة جديدة", callback_data='create_task')],
        [InlineKeyboardButton("⚙️ إعدادات", callback_data='settings')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = """
🤖 لوحة التحكم الرئيسية

اختر من القائمة أدناه:
    """
    
    await query.edit_message_text(welcome_text, reply_markup=reply_markup)

def run_bot():
    """Run the Telegram bot"""
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Start the bot
    print("🤖 تم تشغيل البوت...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    run_bot()
