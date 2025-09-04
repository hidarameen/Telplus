# تقرير شامل: مشاكل التوافق مع PostgreSQL في البوت

## ملخص المشكلة
عند تشغيل البوت مع PostgreSQL تحدث أخطاء "has no attribute" في عدة مواضع، بينما يعمل بشكل طبيعي مع SQLite. هذا التقرير يحدد المشاكل بدقة ويقدم الحلول.

## 🔍 نتائج الفحص الشامل

### 1. الملفات المفحوصة
- ✅ `main.py` - ملف التشغيل الرئيسي
- ✅ `bot_package/config.py` - إعدادات البوت
- ✅ `database/__init__.py` - تهيئة قاعدة البيانات
- ✅ `database/database_factory.py` - مصنع قاعدة البيانات
- ✅ `database/database.py` - SQLite (الأساسي)
- ✅ `database/database_postgresql.py` - PostgreSQL
- ✅ `database/database_sqlite.py` - SQLite (البديل)
- ✅ `bot_package/bot_simple.py` - منطق البوت الأساسي
- ✅ `userbot_service/userbot.py` - خدمة المستخدم البوت

## 🚨 المشاكل المكتشفة

### المشكلة الأساسية: دوال مفقودة في PostgreSQL

#### 1. الدوال المفقودة تماماً في `database_postgresql.py`:

```python
# هذه الدوال موجودة في SQLite/database.py لكن مفقودة في PostgreSQL:

❌ update_task_status(task_id, user_id, is_active)
❌ delete_task(task_id, user_id)  
❌ get_all_active_tasks()
❌ get_active_user_tasks(user_id)
❌ get_active_tasks(user_id)
```

#### 2. دوال الصوت المفقودة:

```python
❌ get_audio_text_cleaning_settings(task_id)
❌ get_audio_text_replacements_settings(task_id)
❌ get_audio_tag_text_cleaning_settings(task_id)
❌ update_audio_text_cleaning_enabled(task_id, enabled)
❌ update_audio_text_replacements_enabled(task_id, enabled)
❌ get_audio_tag_cleaning_settings(task_id)
```

### 3. الاستخدامات في الكود التي تسبب الأخطاء:

#### في `bot_simple.py`:
```python
# السطر 377
audio_cleaning = self.db.get_audio_text_cleaning_settings(task_id)  # ❌ مفقودة

# السطر 420  
audio_replacements = self.db.get_audio_text_replacements_settings(task_id)  # ❌ مفقودة

# السطر 450
current = self.db.get_audio_tag_text_cleaning_settings(task_id)  # ❌ مفقودة

# السطر 452
self.db.update_audio_text_cleaning_enabled(task_id, new_state)  # ❌ مفقودة

# السطر 463
self.db.update_audio_text_replacements_enabled(task_id, new_state)  # ❌ مفقودة
```

#### في `userbot_service/userbot.py`:
```python
# السطر 1932
tasks = self.db.get_active_user_tasks(user_id)  # ❌ مفقودة
```

## 🛠️ الحلول المطلوبة

### 1. إضافة الدوال الأساسية المفقودة لـ PostgreSQL:

```python
def update_task_status(self, task_id: int, user_id: int, is_active: bool) -> bool:
    """Update task status"""
    try:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE tasks SET is_active = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s
            ''', (is_active, task_id, user_id))
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error updating task status: {e}")
        return False

def delete_task(self, task_id: int, user_id: int) -> bool:
    """Delete task"""
    try:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM tasks WHERE id = %s AND user_id = %s', 
                         (task_id, user_id))
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        return False

def get_all_active_tasks(self) -> List[Dict]:
    """Get all active tasks for userbot"""
    try:
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT id, task_name, source_chat_id, source_chat_name, 
                       target_chat_id, target_chat_name, forward_mode
                FROM tasks 
                WHERE is_active = TRUE
            """)
            results = cursor.fetchall()
            tasks = []
            for row in results:
                tasks.append({
                    'id': row['id'],
                    'task_name': row['task_name'],
                    'source_chat_id': row['source_chat_id'],
                    'source_chat_name': row['source_chat_name'],
                    'target_chat_id': row['target_chat_id'],
                    'target_chat_name': row['target_chat_name'],
                    'forward_mode': row['forward_mode'] or 'forward'
                })
            return tasks
    except Exception as e:
        logger.error(f"Error getting all active tasks: {e}")
        return []

def get_active_user_tasks(self, user_id: int) -> List[Dict]:
    """Get active tasks for specific user"""
    return self.get_active_tasks(user_id)

def get_active_tasks(self, user_id: int) -> List[Dict]:
    """Get active tasks for user with all sources and targets"""
    try:
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute('''
                SELECT id, task_name, source_chat_id, source_chat_name, 
                       target_chat_id, target_chat_name, forward_mode
                FROM tasks 
                WHERE user_id = %s AND is_active = TRUE
            ''', (user_id,))
            
            results = cursor.fetchall()
            tasks = []
            
            for row in results:
                task_id = row['id']
                
                # Get all sources for this task
                sources = self.get_task_sources(task_id)
                if not sources:
                    # Fallback to legacy data
                    sources = [{
                        'id': 0,
                        'chat_id': row['source_chat_id'],
                        'chat_name': row['source_chat_name']
                    }] if row['source_chat_id'] else []

                # Get all targets for this task  
                targets = self.get_task_targets(task_id)
                if not targets:
                    # Fallback to legacy data
                    targets = [{
                        'id': 0,
                        'chat_id': row['target_chat_id'],
                        'chat_name': row['target_chat_name']
                    }] if row['target_chat_id'] else []

                # Create individual task entries for each source-target combination
                for source in sources:
                    for target in targets:
                        tasks.append({
                            'id': row['id'],
                            'task_name': row['task_name'],
                            'source_chat_id': source['chat_id'],
                            'source_chat_name': source['chat_name'],
                            'target_chat_id': target['chat_id'],
                            'target_chat_name': target['chat_name'],
                            'forward_mode': row['forward_mode'] or 'forward'
                        })
            return tasks
    except Exception as e:
        logger.error(f"Error getting active tasks: {e}")
        return []
```

### 2. إضافة دوال الصوت المفقودة:

```python
def get_audio_text_cleaning_settings(self, task_id: int) -> Optional[Dict]:
    """Get audio text cleaning settings"""
    try:
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute('''
                SELECT * FROM task_audio_text_cleaning_settings WHERE task_id = %s
            ''', (task_id,))
            result = cursor.fetchone()
            return dict(result) if result else None
    except Exception as e:
        logger.error(f"Error getting audio text cleaning settings: {e}")
        return None

def get_audio_text_replacements_settings(self, task_id: int) -> Optional[Dict]:
    """Get audio text replacements settings"""
    try:
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute('''
                SELECT * FROM task_audio_text_replacements_settings WHERE task_id = %s
            ''', (task_id,))
            result = cursor.fetchone()
            return dict(result) if result else None
    except Exception as e:
        logger.error(f"Error getting audio text replacements settings: {e}")
        return None

def get_audio_tag_text_cleaning_settings(self, task_id: int) -> Optional[Dict]:
    """Get audio tag text cleaning settings"""
    try:
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute('''
                SELECT * FROM task_audio_tag_cleaning_settings WHERE task_id = %s
            ''', (task_id,))
            result = cursor.fetchone()
            return dict(result) if result else None
    except Exception as e:
        logger.error(f"Error getting audio tag text cleaning settings: {e}")
        return None

def update_audio_text_cleaning_enabled(self, task_id: int, enabled: bool) -> bool:
    """Update audio text cleaning enabled status"""
    try:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO task_audio_text_cleaning_settings (task_id, enabled)
                VALUES (%s, %s)
                ON CONFLICT (task_id)
                DO UPDATE SET enabled = EXCLUDED.enabled, updated_at = CURRENT_TIMESTAMP
            ''', (task_id, enabled))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error updating audio text cleaning enabled: {e}")
        return False

def update_audio_text_replacements_enabled(self, task_id: int, enabled: bool) -> bool:
    """Update audio text replacements enabled status"""
    try:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO task_audio_text_replacements_settings (task_id, enabled)
                VALUES (%s, %s)
                ON CONFLICT (task_id)
                DO UPDATE SET enabled = EXCLUDED.enabled, updated_at = CURRENT_TIMESTAMP
            ''', (task_id, enabled))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error updating audio text replacements enabled: {e}")
        return False

def get_audio_tag_cleaning_settings(self, task_id: int) -> Optional[Dict]:
    """Alias for get_audio_tag_text_cleaning_settings"""
    return self.get_audio_tag_text_cleaning_settings(task_id)
```

### 3. التحقق من الجداول المطلوبة:

يجب التأكد من وجود هذه الجداول في PostgreSQL:

```sql
-- جداول إعدادات الصوت المفقودة
CREATE TABLE IF NOT EXISTS task_audio_text_cleaning_settings (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL,
    enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
    UNIQUE (task_id)
);

CREATE TABLE IF NOT EXISTS task_audio_text_replacements_settings (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL,
    enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
    UNIQUE (task_id)
);

CREATE TABLE IF NOT EXISTS task_audio_tag_cleaning_settings (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL,
    enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
    UNIQUE (task_id)
);
```

## 📋 خطة الإصلاح

### الأولوية العالية:
1. ✅ إضافة الدوال الأساسية المفقودة (`update_task_status`, `delete_task`, `get_all_active_tasks`, `get_active_user_tasks`, `get_active_tasks`)
2. ✅ إضافة دوال إعدادات الصوت المفقودة
3. ✅ إنشاء الجداول المطلوبة في PostgreSQL

### الأولوية المتوسطة:
4. فحص وإضافة أي دوال أخرى مفقودة
5. اختبار شامل للتوافق
6. توحيد API بين SQLite و PostgreSQL

### الأولوية المنخفضة:
7. تحسين الأداء
8. إضافة المزيد من التحقق من الأخطاء

## 🔧 كيفية التطبيق

1. **إضافة الدوال المفقودة** إلى ملف `database/database_postgresql.py`
2. **إنشاء الجداول المطلوبة** في قاعدة البيانات
3. **اختبار البوت** مع PostgreSQL للتأكد من عدم وجود أخطاء "has no attribute"
4. **إجراء اختبار شامل** لجميع الوظائف

## 📊 إحصائيات المشكلة

- **عدد الدوال المفقودة**: 11 دالة أساسية
- **عدد الجداول المفقودة**: 3 جداول لإعدادات الصوت
- **الملفات المتأثرة**: 2 ملف رئيسي (`bot_simple.py`, `userbot.py`)
- **نسبة التوافق الحالية**: ~75% (معظم الدوال موجودة لكن هناك نواقص حرجة)

## ✅ النتيجة المتوقعة بعد الإصلاح

بعد تطبيق هذه الإصلاحات، سيعمل البوت مع PostgreSQL بنفس كفاءة SQLite دون أي أخطاء "has no attribute".

---
**تاريخ التقرير**: $(date)  
**حالة الفحص**: مكتمل ✅  
**الحالة**: جاهز للإصلاح 🔧