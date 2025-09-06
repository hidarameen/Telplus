-- إنشاء الجداول المفقودة لإعدادات الصوت في PostgreSQL

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
