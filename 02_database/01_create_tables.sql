-- Генерация UUID
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ТАБЛИЦА 1: events_queue
-- Временная очередь для новых событий из CDP
-- Забирает из CDP - кладёт сюда - другой скрипт забирает отсюда

CREATE TABLE IF NOT EXISTS events_queue (
    id BIGSERIAL PRIMARY KEY,
    event_id UUID NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    profile_id UUID,
    session_id UUID,
    event_data JSONB NOT NULL, -- Всё событие целиком
    status VARCHAR(16) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    error_message TEXT,
    
    -- Индексы для быстрого поиска
    INDEX idx_queue_status (status),
    INDEX idx_queue_event_type (event_type),
    INDEX idx_queue_event_id (event_id)  -- не дублировать события
);

COMMENT ON TABLE events_queue IS 'Временная очередь для событий из CDP Elasticsearch';

-- ==================================================
-- ТАБЛИЦА 2: raw_events (с партиционированием)
-- Хранятся все события для последующего расчёта признаков и производительности

-- Создаём основную (родительскую) таблицу
CREATE TABLE IF NOT EXISTS raw_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    profile_id UUID,
    session_id UUID,
    event_data JSONB NOT NULL,
    inserted_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Индексы будут добавлены отдельно
    -- Партиции будут добавлены отдельно
) PARTITION BY RANGE (inserted_at);

COMMENT ON TABLE raw_events IS 'Основное хранилище сырых событий, партиционировано по месяцам';

-- =================================================
-- ТАБЛИЦА 3: profiles (справочник пользователей)
-- Хранить агрегированную информацию о пользователях
-- Заполняется из событий identification, profile-update

CREATE TABLE IF NOT EXISTS profiles (
    profile_id UUID PRIMARY KEY,
    phone VARCHAR(20),
    firstname VARCHAR(128),
    birthday DATE,
    last_purchase TIMESTAMPTZ,
    total_orders INTEGER DEFAULT 0,
    total_spent NUMERIC(12,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Индекс для быстрого поиска по телефону (для связи с отзывами)
    INDEX idx_profiles_phone (phone)
);

COMMENT ON TABLE profiles IS 'Справочник пользователей для расчёта признаков';

-- ====================================
-- ТАБЛИЦА 4: events_processing_log (лог обработки)
-- Помогает мониторить.

CREATE TABLE IF NOT EXISTS events_processing_log (
    id BIGSERIAL PRIMARY KEY,
    batch_id UUID DEFAULT gen_random_uuid(),
    source VARCHAR(32) DEFAULT 'elasticsearch',
    events_fetched INTEGER,
    events_inserted INTEGER,
    events_failed INTEGER,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status VARCHAR(16) DEFAULT 'running',
    error_message TEXT,
    
    INDEX idx_log_batch (batch_id),
    INDEX idx_log_status (status),
    INDEX idx_log_time (started_at)
);

COMMENT ON TABLE events_processing_log IS 'Лог обработки батчей из CDP';
    