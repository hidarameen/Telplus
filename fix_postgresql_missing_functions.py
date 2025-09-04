#!/usr/bin/env python3
"""
إصلاح الدوال المفقودة في PostgreSQL
يضيف الدوال المطلوبة لجعل البوت يعمل مع PostgreSQL بدون أخطاء
"""

import os
import logging

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_missing_functions_to_postgresql():
    """إضافة الدوال المفقودة إلى ملف database_postgresql.py"""
    
    postgresql_file = "/workspace/database/database_postgresql.py"
    
    if not os.path.exists(postgresql_file):
        logger.error(f"ملف PostgreSQL غير موجود: {postgresql_file}")
        return False
    
    # قراءة الملف الحالي
    with open(postgresql_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # الدوال المفقودة للإضافة
    missing_functions = """
    # ===== الدوال الأساسية المفقودة =====
    
    def update_task_status(self, task_id: int, user_id: int, is_active: bool) -> bool:
        \"\"\"Update task status\"\"\"
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(\"\"\"
                    UPDATE tasks SET is_active = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND user_id = %s
                \"\"\", (is_active, task_id, user_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating task status: {e}")
            return False

    def delete_task(self, task_id: int, user_id: int) -> bool:
        \"\"\"Delete task\"\"\"
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
        \"\"\"Get all active tasks for userbot\"\"\"
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute(\"\"\"
                    SELECT id, task_name, source_chat_id, source_chat_name, 
                           target_chat_id, target_chat_name, forward_mode
                    FROM tasks 
                    WHERE is_active = TRUE
                \"\"\")
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
        \"\"\"Get active tasks for specific user\"\"\"
        return self.get_active_tasks(user_id)

    def get_active_tasks(self, user_id: int) -> List[Dict]:
        \"\"\"Get active tasks for user with all sources and targets\"\"\"
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute(\"\"\"
                    SELECT id, task_name, source_chat_id, source_chat_name, 
                           target_chat_id, target_chat_name, forward_mode
                    FROM tasks 
                    WHERE user_id = %s AND is_active = TRUE
                \"\"\", (user_id,))
                
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

    # ===== دوال إعدادات الصوت المفقودة =====
    
    def get_audio_text_cleaning_settings(self, task_id: int) -> Optional[Dict]:
        \"\"\"Get audio text cleaning settings\"\"\"
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute(\"\"\"
                    SELECT * FROM task_audio_text_cleaning_settings WHERE task_id = %s
                \"\"\", (task_id,))
                result = cursor.fetchone()
                return dict(result) if result else {'enabled': False, 'task_id': task_id}
        except Exception as e:
            logger.error(f"Error getting audio text cleaning settings: {e}")
            return {'enabled': False, 'task_id': task_id}

    def get_audio_text_replacements_settings(self, task_id: int) -> Optional[Dict]:
        \"\"\"Get audio text replacements settings\"\"\"
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute(\"\"\"
                    SELECT * FROM task_audio_text_replacements_settings WHERE task_id = %s
                \"\"\", (task_id,))
                result = cursor.fetchone()
                return dict(result) if result else {'enabled': False, 'task_id': task_id}
        except Exception as e:
            logger.error(f"Error getting audio text replacements settings: {e}")
            return {'enabled': False, 'task_id': task_id}

    def get_audio_tag_text_cleaning_settings(self, task_id: int) -> Optional[Dict]:
        \"\"\"Get audio tag text cleaning settings\"\"\"
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute(\"\"\"
                    SELECT * FROM task_audio_tag_cleaning_settings WHERE task_id = %s
                \"\"\", (task_id,))
                result = cursor.fetchone()
                return dict(result) if result else {'enabled': False, 'task_id': task_id}
        except Exception as e:
            logger.error(f"Error getting audio tag text cleaning settings: {e}")
            return {'enabled': False, 'task_id': task_id}

    def update_audio_text_cleaning_enabled(self, task_id: int, enabled: bool) -> bool:
        \"\"\"Update audio text cleaning enabled status\"\"\"
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(\"\"\"
                    INSERT INTO task_audio_text_cleaning_settings (task_id, enabled)
                    VALUES (%s, %s)
                    ON CONFLICT (task_id)
                    DO UPDATE SET enabled = EXCLUDED.enabled, updated_at = CURRENT_TIMESTAMP
                \"\"\", (task_id, enabled))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating audio text cleaning enabled: {e}")
            return False

    def update_audio_text_replacements_enabled(self, task_id: int, enabled: bool) -> bool:
        \"\"\"Update audio text replacements enabled status\"\"\"
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(\"\"\"
                    INSERT INTO task_audio_text_replacements_settings (task_id, enabled)
                    VALUES (%s, %s)
                    ON CONFLICT (task_id)
                    DO UPDATE SET enabled = EXCLUDED.enabled, updated_at = CURRENT_TIMESTAMP
                \"\"\", (task_id, enabled))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating audio text replacements enabled: {e}")
            return False

    def get_audio_tag_cleaning_settings(self, task_id: int) -> Optional[Dict]:
        \"\"\"Alias for get_audio_tag_text_cleaning_settings\"\"\"
        return self.get_audio_tag_text_cleaning_settings(task_id)
"""
    
    # البحث عن نقطة الإدراج (نهاية الكلاس)
    if content.rstrip().endswith('"""'):
        # إذا كان الملف ينتهي بـ docstring، أضف قبلها
        insertion_point = content.rfind('"""')
        new_content = content[:insertion_point] + missing_functions + '\n' + content[insertion_point:]
    else:
        # أضف في نهاية الملف
        new_content = content + missing_functions
    
    # كتابة الملف المحدث
    try:
        with open(postgresql_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        logger.info("✅ تم إضافة الدوال المفقودة إلى PostgreSQL بنجاح")
        return True
    except Exception as e:
        logger.error(f"خطأ في كتابة الملف: {e}")
        return False

def create_missing_tables_sql():
    """إنشاء ملف SQL لإنشاء الجداول المفقودة"""
    
    sql_content = """-- إنشاء الجداول المفقودة لإعدادات الصوت في PostgreSQL

-- جدول إعدادات تنظيف النص الصوتي
CREATE TABLE IF NOT EXISTS task_audio_text_cleaning_settings (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL,
    enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
);

-- إنشاء فهرس فريد على task_id
CREATE UNIQUE INDEX IF NOT EXISTS idx_task_audio_text_cleaning_task_id 
ON task_audio_text_cleaning_settings (task_id);

-- جدول إعدادات استبدال النص الصوتي
CREATE TABLE IF NOT EXISTS task_audio_text_replacements_settings (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL,
    enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
);

-- إنشاء فهرس فريد على task_id
CREATE UNIQUE INDEX IF NOT EXISTS idx_task_audio_text_replacements_task_id 
ON task_audio_text_replacements_settings (task_id);

-- جدول إعدادات تنظيف علامات الصوت
CREATE TABLE IF NOT EXISTS task_audio_tag_cleaning_settings (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL,
    enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
);

-- إنشاء فهرس فريد على task_id
CREATE UNIQUE INDEX IF NOT EXISTS idx_task_audio_tag_cleaning_task_id 
ON task_audio_tag_cleaning_settings (task_id);

-- تحديث الطوابع الزمنية تلقائياً
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- إنشاء المشغلات للجداول الجديدة
DROP TRIGGER IF EXISTS update_task_audio_text_cleaning_settings_updated_at ON task_audio_text_cleaning_settings;
CREATE TRIGGER update_task_audio_text_cleaning_settings_updated_at
    BEFORE UPDATE ON task_audio_text_cleaning_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_task_audio_text_replacements_settings_updated_at ON task_audio_text_replacements_settings;
CREATE TRIGGER update_task_audio_text_replacements_settings_updated_at
    BEFORE UPDATE ON task_audio_text_replacements_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_task_audio_tag_cleaning_settings_updated_at ON task_audio_tag_cleaning_settings;
CREATE TRIGGER update_task_audio_tag_cleaning_settings_updated_at
    BEFORE UPDATE ON task_audio_tag_cleaning_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- إدراج بيانات افتراضية للمهام الموجودة
INSERT INTO task_audio_text_cleaning_settings (task_id, enabled)
SELECT id, FALSE FROM tasks 
WHERE id NOT IN (SELECT task_id FROM task_audio_text_cleaning_settings);

INSERT INTO task_audio_text_replacements_settings (task_id, enabled)
SELECT id, FALSE FROM tasks 
WHERE id NOT IN (SELECT task_id FROM task_audio_text_replacements_settings);

INSERT INTO task_audio_tag_cleaning_settings (task_id, enabled)
SELECT id, FALSE FROM tasks 
WHERE id NOT IN (SELECT task_id FROM task_audio_tag_cleaning_settings);

-- إنشاء دالة لإضافة إعدادات افتراضية للمهام الجديدة
CREATE OR REPLACE FUNCTION create_default_audio_settings()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO task_audio_text_cleaning_settings (task_id, enabled) VALUES (NEW.id, FALSE);
    INSERT INTO task_audio_text_replacements_settings (task_id, enabled) VALUES (NEW.id, FALSE);
    INSERT INTO task_audio_tag_cleaning_settings (task_id, enabled) VALUES (NEW.id, FALSE);
    RETURN NEW;
END;
$$ language 'plpgsql';

-- إنشاء مشغل لإضافة الإعدادات تلقائياً عند إنشاء مهمة جديدة
DROP TRIGGER IF EXISTS create_default_audio_settings_trigger ON tasks;
CREATE TRIGGER create_default_audio_settings_trigger
    AFTER INSERT ON tasks
    FOR EACH ROW EXECUTE FUNCTION create_default_audio_settings();

-- تحقق من نجاح الإنشاء
SELECT 'تم إنشاء الجداول بنجاح!' as status;
"""
    
    sql_file = "/workspace/create_missing_postgresql_tables.sql"
    try:
        with open(sql_file, 'w', encoding='utf-8') as f:
            f.write(sql_content)
        logger.info(f"✅ تم إنشاء ملف SQL: {sql_file}")
        return True
    except Exception as e:
        logger.error(f"خطأ في إنشاء ملف SQL: {e}")
        return False

def main():
    """تشغيل الإصلاح الشامل"""
    logger.info("🚀 بدء إصلاح الدوال المفقودة في PostgreSQL...")
    
    success_count = 0
    
    # إضافة الدوال المفقودة
    if add_missing_functions_to_postgresql():
        success_count += 1
        logger.info("✅ تم إضافة الدوال المفقودة")
    else:
        logger.error("❌ فشل في إضافة الدوال المفقودة")
    
    # إنشاء ملف SQL للجداول
    if create_missing_tables_sql():
        success_count += 1
        logger.info("✅ تم إنشاء ملف SQL للجداول المفقودة")
    else:
        logger.error("❌ فشل في إنشاء ملف SQL")
    
    # النتيجة النهائية
    if success_count == 2:
        logger.info("🎉 تم الإصلاح بنجاح! البوت الآن متوافق مع PostgreSQL")
        logger.info("📝 الخطوات التالية:")
        logger.info("   1. قم بتشغيل ملف create_missing_postgresql_tables.sql في قاعدة البيانات")
        logger.info("   2. اختبر البوت مع PostgreSQL")
        logger.info("   3. تحقق من عدم وجود أخطاء 'has no attribute'")
    else:
        logger.error("❌ فشل الإصلاح الشامل")
    
    return success_count == 2

if __name__ == "__main__":
    main()