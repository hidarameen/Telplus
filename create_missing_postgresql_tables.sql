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

-- جدول إعدادات هيدر/فوتر الوسوم الصوتية
CREATE TABLE IF NOT EXISTS task_audio_tag_header_footer_settings (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL UNIQUE,
    header_enabled BOOLEAN DEFAULT FALSE,
    header_text TEXT DEFAULT '',
    footer_enabled BOOLEAN DEFAULT FALSE,
    footer_text TEXT DEFAULT '',
    apply_to_title BOOLEAN DEFAULT TRUE,
    apply_to_artist BOOLEAN DEFAULT TRUE,
    apply_to_album_artist BOOLEAN DEFAULT TRUE,
    apply_to_album BOOLEAN DEFAULT TRUE,
    apply_to_year BOOLEAN DEFAULT FALSE,
    apply_to_genre BOOLEAN DEFAULT TRUE,
    apply_to_composer BOOLEAN DEFAULT TRUE,
    apply_to_comment BOOLEAN DEFAULT TRUE,
    apply_to_track BOOLEAN DEFAULT FALSE,
    apply_to_lyrics BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
);

-- جداول فلاتر الكلمات (قوائم بيضاء/سوداء) للوسوم
CREATE TABLE IF NOT EXISTS task_audio_tag_word_filters (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL,
    filter_type TEXT NOT NULL CHECK (filter_type IN ('whitelist','blacklist')),
    is_enabled BOOLEAN DEFAULT FALSE,
    apply_to_title BOOLEAN DEFAULT TRUE,
    apply_to_artist BOOLEAN DEFAULT TRUE,
    apply_to_album_artist BOOLEAN DEFAULT TRUE,
    apply_to_album BOOLEAN DEFAULT TRUE,
    apply_to_year BOOLEAN DEFAULT TRUE,
    apply_to_genre BOOLEAN DEFAULT TRUE,
    apply_to_composer BOOLEAN DEFAULT TRUE,
    apply_to_comment BOOLEAN DEFAULT TRUE,
    apply_to_track BOOLEAN DEFAULT TRUE,
    apply_to_lyrics BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
    UNIQUE(task_id, filter_type)
);

CREATE TABLE IF NOT EXISTS audio_tag_word_filter_entries (
    id SERIAL PRIMARY KEY,
    filter_id INTEGER NOT NULL,
    word_or_phrase TEXT NOT NULL,
    is_case_sensitive BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (filter_id) REFERENCES task_audio_tag_word_filters (id) ON DELETE CASCADE
);

-- جدول إعدادات الاستبدال النصي للوسوم + جدول العناصر
CREATE TABLE IF NOT EXISTS task_audio_tag_text_replacements (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL UNIQUE,
    is_enabled BOOLEAN DEFAULT FALSE,
    apply_to_title BOOLEAN DEFAULT TRUE,
    apply_to_artist BOOLEAN DEFAULT TRUE,
    apply_to_album_artist BOOLEAN DEFAULT TRUE,
    apply_to_album BOOLEAN DEFAULT TRUE,
    apply_to_year BOOLEAN DEFAULT TRUE,
    apply_to_genre BOOLEAN DEFAULT TRUE,
    apply_to_composer BOOLEAN DEFAULT TRUE,
    apply_to_comment BOOLEAN DEFAULT TRUE,
    apply_to_track BOOLEAN DEFAULT TRUE,
    apply_to_lyrics BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audio_tag_text_replacement_entries (
    id SERIAL PRIMARY KEY,
    replacement_id INTEGER NOT NULL,
    find_text TEXT NOT NULL,
    replace_text TEXT NOT NULL,
    is_case_sensitive BOOLEAN DEFAULT FALSE,
    is_whole_word BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (replacement_id) REFERENCES task_audio_tag_text_replacements (id) ON DELETE CASCADE
);

-- جدول اختيار الوسوم لمعالجة النصوص
CREATE TABLE IF NOT EXISTS task_audio_tag_selection_settings (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL UNIQUE,
    selected_tags TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
);

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

DROP TRIGGER IF EXISTS update_task_audio_tag_header_footer_updated_at ON task_audio_tag_header_footer_settings;
CREATE TRIGGER update_task_audio_tag_header_footer_updated_at
    BEFORE UPDATE ON task_audio_tag_header_footer_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_task_audio_tag_word_filters_updated_at ON task_audio_tag_word_filters;
CREATE TRIGGER update_task_audio_tag_word_filters_updated_at
    BEFORE UPDATE ON task_audio_tag_word_filters
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_task_audio_tag_text_replacements_updated_at ON task_audio_tag_text_replacements;
CREATE TRIGGER update_task_audio_tag_text_replacements_updated_at
    BEFORE UPDATE ON task_audio_tag_text_replacements
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

INSERT INTO task_audio_tag_header_footer_settings (task_id)
SELECT id FROM tasks
WHERE id NOT IN (SELECT task_id FROM task_audio_tag_header_footer_settings);

INSERT INTO task_audio_tag_text_replacements (task_id)
SELECT id FROM tasks
WHERE id NOT IN (SELECT task_id FROM task_audio_tag_text_replacements);

-- إنشاء دالة لإضافة إعدادات افتراضية للمهام الجديدة
CREATE OR REPLACE FUNCTION create_default_audio_settings()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO task_audio_text_cleaning_settings (task_id, enabled) VALUES (NEW.id, FALSE);
    INSERT INTO task_audio_text_replacements_settings (task_id, enabled) VALUES (NEW.id, FALSE);
    INSERT INTO task_audio_tag_cleaning_settings (task_id, enabled) VALUES (NEW.id, FALSE);
    INSERT INTO task_audio_tag_header_footer_settings (task_id) VALUES (NEW.id);
    INSERT INTO task_audio_tag_text_replacements (task_id) VALUES (NEW.id);
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
