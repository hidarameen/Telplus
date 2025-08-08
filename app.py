from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import asyncio
import threading
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import PhoneNumberInvalidError, PhoneCodeInvalidError, SessionPasswordNeededError
from database import Database
import config
from userbot import start_userbot, reload_userbot_tasks
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

db = Database()

# Global variables for temporary client during authentication
temp_client = None
temp_phone = None

@app.route('/')
def index():
    """Home page - redirect to login or dashboard"""
    if 'authenticated' in session and session['authenticated']:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page for phone authentication"""
    global temp_client, temp_phone
    
    if request.method == 'POST':
        if 'phone' in request.form:
            # Step 1: Send verification code
            phone = request.form['phone']
            
            try:
                temp_client = TelegramClient(
                    StringSession(), 
                    config.API_ID, 
                    config.API_HASH
                )
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def send_code():
                    await temp_client.connect()
                    return await temp_client.send_code_request(phone)
                
                result = loop.run_until_complete(send_code())
                temp_phone = phone
                
                flash('تم إرسال رمز التحقق إلى هاتفك', 'info')
                return render_template('login.html', show_code_form=True, phone=phone)
            
            except PhoneNumberInvalidError:
                flash('رقم الهاتف غير صحيح', 'error')
            except Exception as e:
                flash(f'حدث خطأ: {str(e)}', 'error')
        
        elif 'code' in request.form:
            # Step 2: Verify code and create session
            code = request.form['code']
            password = request.form.get('password', '')
            
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def verify_code():
                    try:
                        await temp_client.sign_in(temp_phone, code)
                    except SessionPasswordNeededError:
                        if password:
                            await temp_client.sign_in(password=password)
                        else:
                            return 'password_required'
                    
                    # Get session string
                    session_string = temp_client.session.save()
                    await temp_client.disconnect()
                    
                    return session_string
                
                result = loop.run_until_complete(verify_code())
                
                if result == 'password_required':
                    flash('مطلوب كلمة المرور للمصادقة الثنائية', 'info')
                    return render_template('login.html', show_password_form=True, 
                                        phone=temp_phone, code=code)
                
                # Save session to database
                db.save_user_session(temp_phone, result)
                
                # Set session variables
                session['authenticated'] = True
                session['phone'] = temp_phone
                session['session_string'] = result
                
                # Start userbot with this session
                threading.Thread(
                    target=lambda: asyncio.run(start_userbot(result))
                ).start()
                
                flash('تم تسجيل الدخول بنجاح', 'success')
                return redirect(url_for('dashboard'))
            
            except PhoneCodeInvalidError:
                flash('رمز التحقق غير صحيح', 'error')
                return render_template('login.html', show_code_form=True, phone=temp_phone)
            except Exception as e:
                flash(f'حدث خطأ: {str(e)}', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    flash('تم تسجيل الخروج بنجاح', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    """Main dashboard"""
    if 'authenticated' not in session or not session['authenticated']:
        return redirect(url_for('login'))
    
    tasks = db.get_all_tasks()
    return render_template('dashboard.html', tasks=tasks)

@app.route('/create_task', methods=['GET', 'POST'])
def create_task():
    """Create new forwarding task"""
    if 'authenticated' not in session or not session['authenticated']:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form['name']
        source_chats = [chat.strip() for chat in request.form['source_chats'].split('\n') if chat.strip()]
        target_chats = [chat.strip() for chat in request.form['target_chats'].split('\n') if chat.strip()]
        
        if not source_chats or not target_chats:
            flash('يجب تحديد محادثات المصدر والهدف', 'error')
            return render_template('create_task.html')
        
        task_id = db.create_task(name, source_chats, target_chats)
        
        # Reload userbot tasks
        threading.Thread(
            target=lambda: asyncio.run(reload_userbot_tasks())
        ).start()
        
        flash('تم إنشاء المهمة بنجاح', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('create_task.html')

@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
def edit_task(task_id):
    """Edit existing task"""
    if 'authenticated' not in session or not session['authenticated']:
        return redirect(url_for('login'))
    
    task = db.get_task(task_id)
    if not task:
        flash('المهمة غير موجودة', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        name = request.form['name']
        source_chats = [chat.strip() for chat in request.form['source_chats'].split('\n') if chat.strip()]
        target_chats = [chat.strip() for chat in request.form['target_chats'].split('\n') if chat.strip()]
        
        if not source_chats or not target_chats:
            flash('يجب تحديد محادثات المصدر والهدف', 'error')
            return render_template('edit_task.html', task=task)
        
        db.update_task(task_id, name, source_chats, target_chats)
        
        # Reload userbot tasks
        threading.Thread(
            target=lambda: asyncio.run(reload_userbot_tasks())
        ).start()
        
        flash('تم تحديث المهمة بنجاح', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('edit_task.html', task=task)

@app.route('/toggle_task/<int:task_id>')
def toggle_task(task_id):
    """Toggle task active status"""
    if 'authenticated' not in session or not session['authenticated']:
        return redirect(url_for('login'))
    
    db.toggle_task(task_id)
    
    # Reload userbot tasks
    threading.Thread(
        target=lambda: asyncio.run(reload_userbot_tasks())
    ).start()
    
    flash('تم تغيير حالة المهمة', 'success')
    return redirect(url_for('dashboard'))

@app.route('/delete_task/<int:task_id>')
def delete_task(task_id):
    """Delete a task"""
    if 'authenticated' not in session or not session['authenticated']:
        return redirect(url_for('login'))
    
    db.delete_task(task_id)
    
    # Reload userbot tasks
    threading.Thread(
        target=lambda: asyncio.run(reload_userbot_tasks())
    ).start()
    
    flash('تم حذف المهمة', 'success')
    return redirect(url_for('dashboard'))

@app.route('/api/tasks')
def api_tasks():
    """API endpoint to get tasks"""
    if 'authenticated' not in session or not session['authenticated']:
        return jsonify({'error': 'غير مسموح'}), 401
    
    tasks = db.get_all_tasks()
    return jsonify(tasks)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
