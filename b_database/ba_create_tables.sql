-- b_database/ba_create_table.sql
-- Генерация UUID
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ТАБЛИЦА 1: events_queue
-- Временная очередь для новых событий из CDP
-- Забирает из CDP - кладёт сюда - другой скрипт забирает отсюда

-- Удалить старую таблицу events_queue
-- DROP TABLE IF EXISTS events_queue CASCADE;

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
    error_message TEXT
);
COMMENT ON TABLE events_queue IS 'Временная очередь для событий из CDP Elasticsearch';

-- ==================================================
-- ТАБЛИЦА 2: raw_events (с партиционированием)
-- Хранятся все события для последующего расчёта признаков и производительности

-- Удалить старую таблицу raw_events
-- DROP TABLE IF EXISTS raw_events CASCADE;

-- Создаём основную (родительскую) таблицу
CREATE TABLE IF NOT EXISTS raw_events (
    id UUID DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    profile_id UUID,
    session_id UUID,
    event_data JSONB NOT NULL,
    inserted_at TIMESTAMPTZ DEFAULT NOW()
) PARTITION BY RANGE (inserted_at);
COMMENT ON TABLE raw_events IS 'Основное хранилище сырых событий, партиционировано по месяцам';

-- =================================================
-- ТАБЛИЦА 3: profiles (справочник пользователей)
-- Хранить агрегированную информацию о пользователях
-- Заполняется из событий identification, profile-update

-- Удалить старую таблицу profiles
-- DROP TABLE IF EXISTS profiles CASCADE;

CREATE TABLE IF NOT EXISTS profiles (
    profile_id UUID PRIMARY KEY,
    phone VARCHAR(20),
    firstname VARCHAR(128),
    birthday DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ
);
COMMENT ON TABLE profiles IS 'Справочник пользователей для расчёта признаков';

-- =============================
-- ТАБЛИЦА 4: ml_features (24 признака)

-- Удалить старую таблицу ml_features
-- DROP TABLE IF EXISTS ml_features CASCADE;

CREATE TABLE IF NOT EXISTS ml_features (
    profile_id UUID PRIMARY KEY,
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,

    days_since_last_order INTEGER,
    checkout_value_trend NUMERIC(10,4),
    avg_cart_value_30d NUMERIC(10,2),
    cart_to_checkout_ratio NUMERIC(5,2),

    cart_abandonment_rate_30d NUMERIC(5,4),
    cart_browse_abandon_rate_30d NUMERIC(5,4),
    checkout_frustration_index NUMERIC(5,4),
    checkout_completion_rate NUMERIC(5,4),
    auth_on_checkout_flag BOOLEAN,

    coupon_dependency_ratio NUMERIC(5,4),
    promo_ignore_rate_14d NUMERIC(5,4),
    promo_interest_rate NUMERIC(5,4),
    message_open_rate_30d NUMERIC(5,4),
    push_channel_available BOOLEAN,

    personal_offer_conversion_rate NUMERIC(5,4),
    personal_views_count_30d INTEGER DEFAULT 0,
    avg_copy_reaction_seconds NUMERIC(8,2),
    
    session_engagement_score NUMERIC(5,4),
    delta_page_views_14d NUMERIC(7,4),
    phone_changed_90d BOOLEAN,
    profile_completeness_score NUMERIC(5,4),
    avg_rating_90d NUMERIC(3,2),
    has_unpublished_review BOOLEAN,
    reviews_reading_behavior VARCHAR(32),

    churn_probability NUMERIC(5,4),
    risk_level VARCHAR(16),
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    model_version VARCHAR(16) DEFAULT 'v1.0'
);
COMMENT ON TABLE ml_features IS 'Feature Store: 18 признаков + предсказание оттока';


-- ====================================
-- ТАБЛИЦА 5: events_processing_log (лог обработки)
-- Помогает мониторить.

-- Удалить старую таблицу events_processing_log
-- DROP TABLE IF EXISTS events_processing_log CASCADE;

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
    error_message TEXT
);

COMMENT ON TABLE events_processing_log IS 'Лог обработки батчей из CDP';
    