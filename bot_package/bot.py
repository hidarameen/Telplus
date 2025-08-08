"""
Main Telegram Bot Handler
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import logging
from database.database import Database
from conversation_handlers.auth_handler import AuthHandler
from conversation_handlers.task_handler import TaskHandler
from bot_package.config import BOT_TOKEN

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize database
db = Database()

# Initialize handlers
auth_handler = AuthHandler()
task_handler = TaskHandler()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id
    
    # Check if user is authenticated
    if db.is_user_authenticated(user_id):
        # Show main menu
        keyboard = [
            [InlineKeyboardButton("📝 إدارة مهام التوجيه", callback_data="manage_tasks")],
            [InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings")],
            [InlineKeyboardButton("ℹ️ حول البوت", callback_data="about")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🎉 أهلاً بك في بوت التوجيه التلقائي!\n\n"
            f"👋 مرحباً {update.effective_user.first_name}\n"
            f"🔑 أنت مسجل دخولك بالفعل\n\n"
            f"اختر ما تريد فعله:",
            reply_markup=reply_markup
        )
    else:
        # Show authentication menu
        keyboard = [
            [InlineKeyboardButton("📱 تسجيل الدخول برقم الهاتف", callback_data="auth_phone")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🤖 مرحباً بك في بوت التوجيه التلقائي!\n\n"
            f"📋 هذا البوت يساعدك في:\n"
            f"• توجيه الرسائل تلقائياً بين المجموعات والقنوات\n"
            f"• إدارة مهام التوجيه بسهولة\n"
            f"• مراقبة حالة التوجيه\n\n"
            f"🔐 للبدء، يجب تسجيل الدخول برقم هاتفك:",
            reply_markup=reply_markup
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "auth_phone":
        await auth_handler.start_phone_auth(update, context)
    elif data == "manage_tasks":
        if db.is_user_authenticated(user_id):
            await task_handler.show_tasks_menu(update, context)
        else:
            await query.edit_message_text("❌ يجب تسجيل الدخول أولاً")
    elif data == "create_task":
        if db.is_user_authenticated(user_id):
            await task_handler.start_create_task(update, context)
        else:
            await query.edit_message_text("❌ يجب تسجيل الدخول أولاً")
    elif data == "list_tasks":
        if db.is_user_authenticated(user_id):
            await task_handler.list_tasks(update, context)
        else:
            await query.edit_message_text("❌ يجب تسجيل الدخول أولاً")
    elif data.startswith("task_"):
        if db.is_user_authenticated(user_id):
            await task_handler.handle_task_action(update, context, data)
        else:
            await query.edit_message_text("❌ يجب تسجيل الدخول أولاً")
    elif data == "settings":
        await show_settings_menu(update, context)
    elif data == "about":
        await show_about(update, context)
    elif data == "back_main":
        await show_main_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu"""
    keyboard = [
        [InlineKeyboardButton("📝 إدارة مهام التوجيه", callback_data="manage_tasks")],
        [InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings")],
        [InlineKeyboardButton("ℹ️ حول البوت", callback_data="about")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "🏠 القائمة الرئيسية\n\nاختر ما تريد فعله:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "🏠 القائمة الرئيسية\n\nاختر ما تريد فعله:",
            reply_markup=reply_markup
        )

async def show_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show settings menu"""
    keyboard = [
        [InlineKeyboardButton("🔄 إعادة تسجيل الدخول", callback_data="auth_phone")],
        [InlineKeyboardButton("🗑️ حذف جميع المهام", callback_data="delete_all_tasks")],
        [InlineKeyboardButton("🏠 العودة للرئيسية", callback_data="back_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        "⚙️ الإعدادات\n\nاختر إعداد:",
        reply_markup=reply_markup
    )

async def show_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show about information"""
    keyboard = [
        [InlineKeyboardButton("🏠 العودة للرئيسية", callback_data="back_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        "ℹ️ حول البوت\n\n"
        "🤖 بوت التوجيه التلقائي\n"
        "📋 يساعدك في توجيه الرسائل تلقائياً بين المجموعات والقنوات\n\n"
        "🔧 الميزات:\n"
        "• توجيه تلقائي للرسائل\n"
        "• إدارة مهام التوجيه\n"
        "• مراقبة الحالة\n"
        "• واجهة عربية سهلة الاستخدام\n\n"
        "💻 تطوير: نظام بوت تليجرام",
        reply_markup=reply_markup
    )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    user_id = update.effective_user.id
    
    # Check if user is in authentication process
    if await auth_handler.handle_message(update, context):
        return
    
    # Check if user is in task creation process
    if await task_handler.handle_message(update, context):
        return
    
    # Default response
    await update.message.reply_text(
        "👋 أهلاً! استخدم /start لعرض القائمة الرئيسية"
    )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Exception while handling an update: {context.error}")

def run_bot():
    """Run the bot"""
    logger.info("🤖 بدء تشغيل البوت...")
    
    if not BOT_TOKEN or BOT_TOKEN == 'your_bot_token_here':
        logger.error("❌ BOT_TOKEN غير محدد في متغيرات البيئة")
        return
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    logger.info("✅ البوت جاهز!")
    
    # Run the bot
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    run_bot()