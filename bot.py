import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from database.database import Database
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
    elif query.data == 'settings':
        await show_settings_menu(query)
    elif query.data == 'change_language':
        await show_language_menu(query)
    elif query.data == 'change_timezone':
        await show_timezone_menu(query)
    elif query.data.startswith('set_language_'):
        language = query.data.split('_')[2]
        await set_user_language(query, language)
    elif query.data.startswith('set_timezone_'):
        timezone = query.data.replace('set_timezone_', '')
        await set_user_timezone(query, timezone)
    elif query.data.startswith('toggle_task_'):
        task_id = int(query.data.split('_')[2])
        await toggle_task(query, task_id)
    elif query.data.startswith('delete_task_'):
        task_id = int(query.data.split('_')[2])
        await delete_task(query, task_id)
    elif query.data == 'back_to_main':
        await show_main_menu(query)
    elif query.data == 'back_to_settings':
        await show_settings_menu(query)

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

async def show_settings_menu(query) -> None:
    """Show settings menu"""
    user_id = query.from_user.id
    user_settings = db.get_user_settings(user_id)
    
    text = f"""
⚙️ إعدادات البوت

🌐 اللغة الحالية: {get_language_name(user_settings['language'])}
🕐 المنطقة الزمنية الحالية: {user_settings['timezone']}

اختر الإعداد الذي تريد تغييره:
    """
    
    keyboard = [
        [InlineKeyboardButton("🌐 تغيير اللغة", callback_data='change_language')],
        [InlineKeyboardButton("🕐 تغيير المنطقة الزمنية", callback_data='change_timezone')],
        [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data='back_to_main')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)

async def show_language_menu(query) -> None:
    """Show language selection menu"""
    text = """
🌐 اختر اللغة المفضلة:
    """
    
    keyboard = [
        [InlineKeyboardButton("🇸🇦 العربية", callback_data='set_language_ar')],
        [InlineKeyboardButton("🇺🇸 English", callback_data='set_language_en')],
        [InlineKeyboardButton("🇫🇷 Français", callback_data='set_language_fr')],
        [InlineKeyboardButton("🇩🇪 Deutsch", callback_data='set_language_de')],
        [InlineKeyboardButton("🇪🇸 Español", callback_data='set_language_es')],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data='set_language_ru')],
        [InlineKeyboardButton("🔙 العودة للإعدادات", callback_data='back_to_settings')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)

async def show_timezone_menu(query) -> None:
    """Show timezone selection menu"""
    text = """
🕐 اختر المنطقة الزمنية:
    """
    
    keyboard = [
        [InlineKeyboardButton("🇸🇦 الرياض (Asia/Riyadh)", callback_data='set_timezone_Asia/Riyadh')],
        [InlineKeyboardButton("🇰🇼 الكويت (Asia/Kuwait)", callback_data='set_timezone_Asia/Kuwait')],
        [InlineKeyboardButton("🇦🇪 الإمارات (Asia/Dubai)", callback_data='set_timezone_Asia/Dubai')],
        [InlineKeyboardButton("🇶🇦 قطر (Asia/Qatar)", callback_data='set_timezone_Asia/Qatar')],
        [InlineKeyboardButton("🇧🇭 البحرين (Asia/Bahrain)", callback_data='set_timezone_Asia/Bahrain')],
        [InlineKeyboardButton("🇴🇲 عمان (Asia/Muscat)", callback_data='set_timezone_Asia/Muscat')],
        [InlineKeyboardButton("🇯🇴 الأردن (Asia/Amman)", callback_data='set_timezone_Asia/Amman')],
        [InlineKeyboardButton("🇱🇧 لبنان (Asia/Beirut)", callback_data='set_timezone_Asia/Beirut')],
        [InlineKeyboardButton("🇸🇾 سوريا (Asia/Damascus)", callback_data='set_timezone_Asia/Damascus')],
        [InlineKeyboardButton("🇮🇶 العراق (Asia/Baghdad)", callback_data='set_timezone_Asia/Baghdad')],
        [InlineKeyboardButton("🇪🇬 مصر (Africa/Cairo)", callback_data='set_timezone_Africa/Cairo')],
        [InlineKeyboardButton("🇲🇦 المغرب (Africa/Casablanca)", callback_data='set_timezone_Africa/Casablanca')],
        [InlineKeyboardButton("🇩🇿 الجزائر (Africa/Algiers)", callback_data='set_timezone_Africa/Algiers')],
        [InlineKeyboardButton("🇹🇳 تونس (Africa/Tunis)", callback_data='set_timezone_Africa/Tunis')],
        [InlineKeyboardButton("🇱🇾 ليبيا (Africa/Tripoli)", callback_data='set_timezone_Africa/Tripoli')],
        [InlineKeyboardButton("🇺🇸 نيويورك (America/New_York)", callback_data='set_timezone_America/New_York')],
        [InlineKeyboardButton("🇬🇧 لندن (Europe/London)", callback_data='set_timezone_Europe/London')],
        [InlineKeyboardButton("🇩🇪 برلين (Europe/Berlin)", callback_data='set_timezone_Europe/Berlin')],
        [InlineKeyboardButton("🇫🇷 باريس (Europe/Paris)", callback_data='set_timezone_Europe/Paris')],
        [InlineKeyboardButton("🇷🇺 موسكو (Europe/Moscow)", callback_data='set_timezone_Europe/Moscow')],
        [InlineKeyboardButton("🇯🇵 طوكيو (Asia/Tokyo)", callback_data='set_timezone_Asia/Tokyo')],
        [InlineKeyboardButton("🇨🇳 بكين (Asia/Shanghai)", callback_data='set_timezone_Asia/Shanghai')],
        [InlineKeyboardButton("🇮🇳 دلهي (Asia/Kolkata)", callback_data='set_timezone_Asia/Kolkata')],
        [InlineKeyboardButton("🇦🇺 سيدني (Australia/Sydney)", callback_data='set_timezone_Australia/Sydney')],
        [InlineKeyboardButton("🔙 العودة للإعدادات", callback_data='back_to_settings')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)

async def set_user_language(query, language: str) -> None:
    """Set user language preference"""
    user_id = query.from_user.id
    success = db.update_user_language(user_id, language)
    
    if success:
        language_name = get_language_name(language)
        await query.answer(f"✅ تم تغيير اللغة إلى {language_name}")
    else:
        await query.answer("❌ فشل في تغيير اللغة")
    
    await show_settings_menu(query)

async def set_user_timezone(query, timezone: str) -> None:
    """Set user timezone preference"""
    user_id = query.from_user.id
    success = db.update_user_timezone(user_id, timezone)
    
    if success:
        await query.answer(f"✅ تم تغيير المنطقة الزمنية إلى {timezone}")
    else:
        await query.answer("❌ فشل في تغيير المنطقة الزمنية")
    
    await show_settings_menu(query)

def get_language_name(language_code: str) -> str:
    """Get language name from code"""
    languages = {
        'ar': '🇸🇦 العربية',
        'en': '🇺🇸 English',
        'fr': '🇫🇷 Français',
        'de': '🇩🇪 Deutsch',
        'es': '🇪🇸 Español',
        'ru': '🇷🇺 Русский'
    }
    return languages.get(language_code, f'{language_code}')

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
