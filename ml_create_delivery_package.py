# ml_create_delivery_package.py
"""
ml_create_delivery_package.py
Скрипт для автоматической сборки пакета для прода (Delivery Package)

Создает папку f_delivery/ со всем необходимым:
- SQL-скрипты для инициализации БД (таблицы, партиции, индексы, MV)
- Скрипты для первичной загрузки данных из CDP (ETL)
- Скрипт для обновления признаков (maintenance)
- ML-модель и инференс-пайплайн
- Конфигурация и документация
"""

import shutil
import mlflow
import mlflow.sklearn
from pathlib import Path

def create_delivery_package():
    """Создает папку f_delivery со всеми необходимыми файлами"""
    
    delivery_dir = Path("f_delivery")
    delivery_dir.mkdir(exist_ok=True)
    
    print("- Начало сборки f_delivery-пакета\n")
    
    # 1. SQL-скрипты для инициализации БД
    create_sql_scripts(delivery_dir)
    print("- Созданы SQL-скрипты для БД")
    
    # 2. Скрипт инициализации БД
    create_bootstrap_script(delivery_dir)
    print("- Создан скрипт инициализации БД")
    
    # 3. Скрипт первичной загрузки данных из CDP
    create_sync_cdp_script(delivery_dir)
    print("- Создан скрипт синхронизации с CDP")
    
    # 4. Скрипт обновления признаков (maintenance)
    create_refresh_features_script(delivery_dir)
    print("- Создан скрипт обновления признаков")
    
    # 5. Копируем ml_config.py
    shutil.copy("ml_config.py", delivery_dir / "ml_config.py")
    print(" - Скопирован ml_config.py")
    
    # 6. Копируем и адаптируем класс предобработки
    create_adapted_preprocessor(delivery_dir)
    print(" - Скопирован класс предобработки")
    
    #    Копируем и адаптируем оркестратор инференса
    create_adapted_inference_pipeline(delivery_dir)
    print(" - Скопирован оркестратор инференса")
    
    # 7. Экспортируем лучшую модель и scaler из MLflow
    export_model_and_scaler(delivery_dir / "churn_model")
    print(" - Экспортированы модель и scaler из MLflow")
    
    # 8. Зависимости (с elasticsearch)
    create_requirements(delivery_dir)
    print("- Создан requirements.txt")
    
    # 9. Создаем .env.example для заказчика
    create_env_example(delivery_dir)
    print(" - Создан .env.example")
    
    # 10. Создаем README для прода
    create_readme(delivery_dir)
    print(" - Создан README.md")
    
    # 11. Создаем .gitignore для папки f_delivery
    create_gitignore(delivery_dir)
    print(" - Создан .gitignore")
    
    print(f"\n- Delivery пакет успешно создан в папке: {delivery_dir.absolute()}")
    print("Теперь эту папку можно передать на прод (архивом или через Git).")

def create_sql_scripts(delivery_dir):
    """Создает папку sql/ с SQL-скриптами для инициализации БД"""
    sql_dir = delivery_dir / "sql"
    sql_dir.mkdir(exist_ok=True)
    
    # sql_01_create_tables.sql
    sql_01 = """-- Создание таблиц для Churn Prediction System
-- Запускать первым

-- Генерация UUID
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ТАБЛИЦА 1: events_queue (временная очередь)
CREATE TABLE IF NOT EXISTS events_queue (
    id BIGSERIAL PRIMARY KEY,
    event_id UUID NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    profile_id UUID,
    session_id UUID,
    event_data JSONB NOT NULL,
    status VARCHAR(16) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    error_message TEXT
);
COMMENT ON TABLE events_queue IS 'Временная очередь для событий из CDP Elasticsearch';

-- ТАБЛИЦА 2: raw_events (с партиционированием)
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

-- ТАБЛИЦА 3: profiles (справочник пользователей)
CREATE TABLE IF NOT EXISTS profiles (
    profile_id UUID PRIMARY KEY,
    phone VARCHAR(50),
    firstname VARCHAR(128),
    birthday DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ
);
COMMENT ON TABLE profiles IS 'Справочник пользователей для расчёта признаков';

-- ТАБЛИЦА 4: ml_features (24 признака + предсказания)
CREATE TABLE IF NOT EXISTS ml_features (
    profile_id UUID PRIMARY KEY,
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,
    days_since_last_order INTEGER,
    checkout_value_trend NUMERIC(10,4),
    avg_cart_value_30d NUMERIC(10,2),
    cart_to_checkout_ratio NUMERIC(10,4),
    cart_abandonment_rate_30d NUMERIC(10,4),
    cart_browse_abandon_rate_30d NUMERIC(10,4),
    checkout_frustration_index NUMERIC(10,4),
    checkout_completion_rate NUMERIC(10,4),
    auth_on_checkout_flag BOOLEAN,
    coupon_dependency_ratio NUMERIC(5,4),
    promo_ignore_rate_14d NUMERIC(5,4),
    promo_interest_rate NUMERIC(5,4),
    message_open_rate_30d NUMERIC(5,4),
    push_channel_available BOOLEAN,
    personal_offer_conversion_rate NUMERIC(5,4),
    personal_views_count_30d INTEGER DEFAULT 0,
    avg_copy_reaction_seconds NUMERIC(8,2),
    session_engagement_score NUMERIC(10,4),
    delta_page_views_14d NUMERIC(10,4),
    phone_changed_90d BOOLEAN,
    profile_completeness_score NUMERIC(5,4),
    avg_rating_90d NUMERIC(3,2),
    has_unpublished_review BOOLEAN,
    reviews_reading_behavior VARCHAR(32),
    is_churned BOOLEAN DEFAULT FALSE,
    churn_probability NUMERIC(5,4),
    risk_level VARCHAR(16),
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    model_version VARCHAR(50) DEFAULT 'v1.0'
);
COMMENT ON TABLE ml_features IS 'Feature Store: 24 признака + предсказание оттока';

-- ТАБЛИЦА 5: events_processing_log (лог обработки)
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
"""
    with open(sql_dir / "sql_01_create_tables.sql", "w", encoding="utf-8") as f:
        f.write(sql_01)

    # sql_02_create_partitions.sql
    sql_02 = """-- Партиционирование raw_events по месяцам
-- Создаем партиции за последние 12 месяцев + 12 месяцев вперед

CREATE OR REPLACE FUNCTION create_monthly_partition(
    table_name TEXT,
    partition_date DATE
) RETURNS VOID AS $$
DECLARE
    partition_name TEXT;
    start_date DATE;
    end_date DATE;
BEGIN
    partition_name := table_name || '_' || TO_CHAR(partition_date, 'YYYY_MM');
    start_date := DATE_TRUNC('month', partition_date);
    end_date := start_date + INTERVAL '1 month';
    
    EXECUTE FORMAT(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
        partition_name, table_name, start_date, end_date
    );
    
    RAISE NOTICE 'Создана партиция: % (% на %)', partition_name, start_date, end_date;
END;
$$ LANGUAGE plpgsql;

-- Создаем 24 партиции (12 назад + 12 вперед)
DO $$
DECLARE
    start_date DATE := DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '12 months';
    partition_name TEXT;
    part_start DATE;
    part_end DATE;
    i INTEGER;
BEGIN
    FOR i IN 0..23 LOOP
        part_start := start_date + (i * INTERVAL '1 month');
        part_end := part_start + INTERVAL '1 month';
        partition_name := 'raw_events_' || TO_CHAR(part_start, 'YYYY_MM');

        EXECUTE FORMAT(
            'CREATE TABLE IF NOT EXISTS %I PARTITION OF raw_events FOR VALUES FROM (%L) TO (%L)',
            partition_name, part_start, part_end
        );
        
        RAISE NOTICE 'Created: % [% - %)', partition_name, part_start, part_end;
    END LOOP;
END $$;
"""
    with open(sql_dir / "sql_02_create_partitions.sql", "w", encoding="utf-8") as f:
        f.write(sql_02)
    
    # sql_03_create_indexes.sql
    sql_03 = """-- Индексы для оптимизации производительности

-- events_queue
CREATE UNIQUE INDEX IF NOT EXISTS idx_queue_event_id ON events_queue (event_id);
CREATE INDEX IF NOT EXISTS idx_queue_status ON events_queue (status);
CREATE INDEX IF NOT EXISTS idx_queue_event_type ON events_queue (event_type);
CREATE INDEX IF NOT EXISTS idx_queue_pending_time ON events_queue (status, created_at) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_queue_processed_cleanup ON events_queue (processed_at) WHERE status = 'processed';

-- raw_events
CREATE UNIQUE INDEX IF NOT EXISTS idx_raw_event_id_unique ON raw_events (event_id, inserted_at);
CREATE INDEX IF NOT EXISTS idx_raw_profile_time ON raw_events (profile_id, inserted_at DESC) WHERE profile_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_raw_type_time ON raw_events (event_type, inserted_at DESC);
CREATE INDEX IF NOT EXISTS idx_raw_type_profile_time ON raw_events (event_type, profile_id, inserted_at DESC) WHERE profile_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_raw_event_data_gin ON raw_events USING GIN (event_data);
CREATE INDEX IF NOT EXISTS idx_raw_rating ON raw_events (CAST(event_data->'event'->'properties'->>'rate' AS INTEGER)) WHERE event_type = 'rating' AND event_data->'event'->'properties'->>'rate' IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_raw_cart_total ON raw_events (CAST(event_data->'event'->'properties'->>'total' AS NUMERIC)) WHERE event_type = 'cart-changes' AND event_data->'event'->'properties'->>'total' IS NOT NULL;

-- profiles
CREATE INDEX IF NOT EXISTS idx_profiles_phone ON profiles (phone);
CREATE INDEX IF NOT EXISTS idx_profiles_updated ON profiles (updated_at);

-- ml_features
CREATE INDEX IF NOT EXISTS idx_features_risk ON ml_features (risk_level);
CREATE INDEX IF NOT EXISTS idx_features_churn_prob ON ml_features (churn_probability);
CREATE INDEX IF NOT EXISTS idx_features_snapshot ON ml_features (snapshot_date);
CREATE INDEX IF NOT EXISTS idx_features_risk_profile ON ml_features (risk_level, profile_id) WHERE risk_level IN ('HIGH', 'MEDIUM');
CREATE INDEX IF NOT EXISTS idx_features_churn_desc ON ml_features (churn_probability DESC) WHERE churn_probability IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_features_cart_value ON ml_features (avg_cart_value_30d DESC) WHERE avg_cart_value_30d IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_features_cart_ratio ON ml_features (cart_to_checkout_ratio) WHERE cart_to_checkout_ratio IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_features_is_churned ON ml_features (is_churned) WHERE is_churned = TRUE;

-- events_processing_log
CREATE INDEX IF NOT EXISTS idx_log_batch ON events_processing_log (batch_id);
CREATE INDEX IF NOT EXISTS idx_log_status ON events_processing_log (status);
CREATE INDEX IF NOT EXISTS idx_log_time ON events_processing_log (started_at);

-- Обновить статистику
ANALYZE events_queue;
ANALYZE raw_events;
ANALYZE profiles;
ANALYZE ml_features;
ANALYZE events_processing_log;
"""
    with open(sql_dir / "sql_03_create_indexes.sql", "w", encoding="utf-8") as f:
        f.write(sql_03)
    
    # sql_04_create_materialized_views.sql
    sql_04 = """-- Materialized View для расчета 24 признаков
-- Это основной Feature Store

DROP MATERIALIZED VIEW IF EXISTS mv_ml_features CASCADE;

CREATE MATERIALIZED VIEW mv_ml_features AS
WITH
active_profiles AS (
    SELECT DISTINCT profile_id
    FROM raw_events
    WHERE profile_id IS NOT NULL
      AND inserted_at > NOW() - INTERVAL '180 days'
),
cte_days_since_last_order AS (
    SELECT profile_id,
        EXTRACT(DAY FROM NOW() - MAX(inserted_at))::INTEGER AS days_since_last_order
    FROM raw_events
    WHERE event_type = 'page-view'
      AND event_data->'event'->'context'->'page'->>'path' = '/order'
      AND inserted_at > NOW() - INTERVAL '180 days'
    GROUP BY profile_id
),
cte_cart_abandonment_rate AS (
    SELECT profile_id,
        ROUND(COUNT(*) FILTER (WHERE event_type = 'cart-delete' AND event_data->'event'->'context'->'page'->>'path' = '/checkout')::NUMERIC /
              NULLIF(COUNT(*) FILTER (WHERE event_type = 'cart-changes'), 0), 4) AS cart_abandonment_rate_30d
    FROM raw_events
    WHERE event_type IN ('cart-delete', 'cart-changes') AND inserted_at > NOW() - INTERVAL '30 days'
    GROUP BY profile_id
),
cte_checkout_completion AS (
    SELECT profile_id,
        ROUND(COUNT(*) FILTER (WHERE event_type = 'page-view' AND event_data->'event'->'context'->'page'->>'path' = '/order')::NUMERIC /
              NULLIF(COUNT(*) FILTER (WHERE event_type = 'checkout-started'), 0), 4) AS checkout_completion_rate
    FROM raw_events
    WHERE event_type IN ('checkout-started', 'page-view') AND inserted_at > NOW() - INTERVAL '30 days'
    GROUP BY profile_id
),
cte_frustration AS (
    SELECT profile_id,
        ROUND((COUNT(*) FILTER (WHERE event_type = 'cart-delete' AND event_data->'event'->'context'->'page'->>'path' = '/checkout') +
               COUNT(*) FILTER (WHERE event_type = 'rating' AND CAST(event_data->'event'->'properties'->>'rate' AS INTEGER) <= 3))::NUMERIC /
              NULLIF(COUNT(*) FILTER (WHERE event_type IN ('cart-changes', 'checkout-started')), 0), 4) AS checkout_frustration_index
    FROM raw_events
    WHERE event_type IN ('cart-changes', 'checkout-started', 'cart-delete', 'rating') AND inserted_at > NOW() - INTERVAL '30 days'
    GROUP BY profile_id
),
cte_personal_conversion AS (
    WITH funnel AS (
        SELECT profile_id, session_id, event_data->'event'->'properties'->>'id' AS offer_id,
            MAX(CASE WHEN event_type = 'personal-view' THEN 1 ELSE 0 END) AS viewed,
            MAX(CASE WHEN event_type = 'copy-promocode' THEN 1 ELSE 0 END) AS copied
        FROM raw_events
        WHERE event_type IN ('personal-view', 'copy-promocode') AND inserted_at > NOW() - INTERVAL '30 days'
        GROUP BY profile_id, session_id, offer_id
    )
    SELECT profile_id,
        ROUND(COUNT(*) FILTER (WHERE copied = 1)::NUMERIC / NULLIF(COUNT(*) FILTER (WHERE viewed = 1), 0), 4) AS personal_offer_conversion_rate
    FROM funnel GROUP BY profile_id
),
cte_promo_ignore AS (
    SELECT profile_id,
        ROUND(COUNT(*) FILTER (WHERE event_type = 'promotion-close')::NUMERIC /
              NULLIF(COUNT(*) FILTER (WHERE event_type IN ('promotion-viewed', 'promotion-close')), 0), 4) AS promo_ignore_rate_14d
    FROM raw_events
    WHERE event_type IN ('promotion-viewed', 'promotion-close') AND inserted_at > NOW() - INTERVAL '14 days'
    GROUP BY profile_id
),
cte_engagement AS (
    SELECT profile_id,
        ROUND(SUM(CASE
            WHEN event_data->'event'->'context'->'page'->>'path' = '/' THEN 0.1
            WHEN event_data->'event'->'context'->'page'->>'path' LIKE '/catalog%' THEN 0.3
            WHEN event_data->'event'->'context'->'page'->>'path' = '/profile' THEN 0.5
            WHEN event_data->'event'->'context'->'page'->>'path' = '/actions' THEN 0.5
            WHEN event_data->'event'->'context'->'page'->>'path' = '/reviews' THEN 0.6
            WHEN event_data->'event'->'context'->'page'->>'path' = '/checkout' THEN 0.8
            WHEN event_data->'event'->'context'->'page'->>'path' = '/order' THEN 1.0
            ELSE 0.0 END), 4) AS session_engagement_score
    FROM raw_events
    WHERE event_type = 'page-view' AND inserted_at > NOW() - INTERVAL '30 days'
    GROUP BY profile_id
),
cte_message_open AS (
    SELECT profile_id,
        ROUND((COUNT(*) FILTER (WHERE event_type = 'message-opened') +
               COUNT(*) FILTER (WHERE event_type = 'message-status' AND event_data->'event'->'properties'->>'status' = 'clicked'))::NUMERIC /
              NULLIF(COUNT(*) FILTER (WHERE event_type = 'message-status' AND event_data->'event'->'properties'->>'status' IN ('delivered', 'clicked')), 0), 4) AS message_open_rate_30d
    FROM raw_events
    WHERE event_type IN ('message-status', 'message-opened') AND inserted_at > NOW() - INTERVAL '30 days'
    GROUP BY profile_id
),
cte_browse_abandon AS (
    SELECT profile_id,
        ROUND(COUNT(*) FILTER (WHERE event_type = 'cart-delete' AND (event_data->'event'->'context'->'page'->>'path' LIKE '/catalog%' OR event_data->'event'->'context'->'page'->>'path' = '/'))::NUMERIC /
              NULLIF(COUNT(*) FILTER (WHERE event_type = 'cart-changes'), 0), 4) AS cart_browse_abandon_rate_30d
    FROM raw_events
    WHERE event_type IN ('cart-delete', 'cart-changes') AND inserted_at > NOW() - INTERVAL '30 days'
    GROUP BY profile_id
),
cte_personal_views AS (
    SELECT profile_id, COUNT(*) AS personal_views_count_30d
    FROM raw_events
    WHERE event_type = 'personal-view' AND inserted_at > NOW() - INTERVAL '30 days'
    GROUP BY profile_id
),
cte_push_available AS (
    SELECT profile_id,
        BOOL_OR(event_data->'event'->'properties'->>'push_id' IS NOT NULL) AS push_channel_available
    FROM raw_events
    WHERE event_type = 'profile-traits-update' AND inserted_at > NOW() - INTERVAL '180 days'
    GROUP BY profile_id
),
cte_phone_changed AS (
    SELECT profile_id,
        CASE WHEN COUNT(DISTINCT COALESCE(event_data->'event'->'properties'->'phone'->>'main', event_data->'event'->'properties'->'contact'->'phone'->>'main')) > 1 THEN TRUE ELSE FALSE END AS phone_changed_90d
    FROM raw_events
    WHERE (event_type IN ('sign-in', 'profile-update') OR (event_type = 'identification' AND event_data->'event'->'context'->'page'->>'path' != '/checkout'))
      AND inserted_at > NOW() - INTERVAL '90 days'
    GROUP BY profile_id
),
cte_avg_rating AS (
    SELECT profile_id, ROUND(AVG(CAST(event_data->'event'->'properties'->>'rate' AS NUMERIC)), 2) AS avg_rating_90d
    FROM raw_events
    WHERE event_type = 'rating' AND inserted_at > NOW() - INTERVAL '90 days'
    GROUP BY profile_id
),
cte_coupon_dependency AS (
    SELECT profile_id,
        ROUND(COUNT(*) FILTER (WHERE event_data->'event'->'properties'->>'coupon' IS NOT NULL)::NUMERIC / NULLIF(COUNT(*), 0), 4) AS coupon_dependency_ratio
    FROM raw_events
    WHERE event_type = 'checkout-started' AND inserted_at > NOW() - INTERVAL '90 days'
    GROUP BY profile_id
),
cte_avg_cart AS (
    SELECT profile_id, ROUND(AVG(CAST(event_data->'event'->'properties'->>'total' AS NUMERIC)), 2) AS avg_cart_value_30d
    FROM raw_events
    WHERE event_type = 'cart-changes' AND inserted_at > NOW() - INTERVAL '30 days'
    GROUP BY profile_id
),
cte_profile_completeness AS (
    SELECT profile_id,
        ROUND(CASE WHEN COALESCE(event_data->'event'->'properties'->'phone'->>'main', event_data->'event'->'properties'->'contact'->'phone'->>'main') IS NOT NULL THEN 0.4 ELSE 0 END +
              CASE WHEN COALESCE(event_data->'event'->'properties'->'pii'->>'firstname', event_data->'event'->'properties'->>'firstname') IS NOT NULL THEN 0.3 ELSE 0 END +
              CASE WHEN COALESCE(event_data->'event'->'properties'->>'birthday', event_data->'event'->'properties'->'pii'->>'birthday') IS NOT NULL THEN 0.3 ELSE 0 END, 2) AS profile_completeness_score
    FROM (SELECT DISTINCT ON (profile_id) profile_id, event_data FROM raw_events
          WHERE event_type IN ('identification', 'profile-update')
          ORDER BY profile_id, CASE WHEN event_type = 'identification' AND event_data->'event'->'context'->'page'->>'path' = '/checkout' THEN 1 WHEN event_type = 'profile-update' THEN 2 ELSE 3 END, inserted_at DESC) latest_profile
),
cte_delta_views AS (
    WITH recent AS (SELECT profile_id, COUNT(*) AS v14 FROM raw_events WHERE event_type = 'page-view' AND inserted_at > NOW() - INTERVAL '14 days' GROUP BY profile_id),
         previous AS (SELECT profile_id, COUNT(*) AS v_prev FROM raw_events WHERE event_type = 'page-view' AND inserted_at BETWEEN NOW() - INTERVAL '28 days' AND NOW() - INTERVAL '14 days' GROUP BY profile_id)
    SELECT r.profile_id, ROUND((r.v14 - COALESCE(p.v_prev, 0))::NUMERIC / NULLIF(p.v_prev, 0), 4) AS delta_page_views_14d
    FROM recent r LEFT JOIN previous p USING (profile_id)
),
cte_unpublished_review AS (
    SELECT profile_id, BOOL_OR(CAST(event_data->'event'->'properties'->>'rate' AS INTEGER) <= 2) AS has_unpublished_review
    FROM raw_events
    WHERE event_type = 'rating' AND inserted_at > NOW() - INTERVAL '90 days' AND event_data->'event'->'properties'->>'rate' IS NOT NULL
    GROUP BY profile_id
),
cte_cart_checkout_ratio AS (
    WITH cart AS (SELECT profile_id, session_id, AVG(CAST(event_data->'event'->'properties'->>'total' AS NUMERIC)) AS avg_cart FROM raw_events WHERE event_type = 'cart-changes' AND inserted_at > NOW() - INTERVAL '30 days' GROUP BY profile_id, session_id),
         checkout AS (SELECT profile_id, session_id, MAX(CAST(event_data->'event'->'properties'->>'value' AS NUMERIC)) AS chk_val FROM raw_events WHERE event_type = 'checkout-started' AND inserted_at > NOW() - INTERVAL '30 days' GROUP BY profile_id, session_id)
    SELECT c.profile_id, ROUND(AVG(c.avg_cart / NULLIF(ch.chk_val, 0)), 2) AS cart_to_checkout_ratio
    FROM cart c JOIN checkout ch USING (profile_id, session_id) GROUP BY c.profile_id
),
cte_copy_reaction AS (
    WITH funnel AS (SELECT profile_id, session_id, event_data->'event'->'properties'->>'id' AS offer_id,
            MIN(inserted_at) FILTER (WHERE event_type = 'personal-view') AS viewed_at,
            MIN(inserted_at) FILTER (WHERE event_type = 'copy-promocode') AS copied_at
        FROM raw_events WHERE event_type IN ('personal-view', 'copy-promocode') AND inserted_at > NOW() - INTERVAL '30 days'
        GROUP BY profile_id, session_id, offer_id)
    SELECT profile_id, ROUND(AVG(EXTRACT(EPOCH FROM (copied_at - viewed_at))), 2) AS avg_copy_reaction_seconds
    FROM funnel WHERE viewed_at IS NOT NULL AND copied_at IS NOT NULL AND copied_at > viewed_at GROUP BY profile_id
),
cte_reviews_behavior AS (
    WITH behavior AS (SELECT profile_id,
            COUNT(*) FILTER (WHERE event_type = 'page-view' AND event_data->'event'->'context'->'page'->>'path' = '/reviews') AS read_cnt,
            COUNT(*) FILTER (WHERE event_type = 'rating') AS written_cnt,
            COUNT(*) FILTER (WHERE event_type = 'page-view' AND event_data->'event'->'context'->'page'->>'path' = '/order') AS order_cnt
        FROM raw_events WHERE event_type IN ('page-view', 'rating') AND inserted_at > NOW() - INTERVAL '180 days' GROUP BY profile_id)
    SELECT profile_id, CASE
        WHEN read_cnt > 2 AND written_cnt = 0 THEN 'researcher'
        WHEN written_cnt > 0 THEN 'active_reviewer'
        WHEN read_cnt = 0 AND order_cnt > 0 THEN 'impulsive_buyer'
        ELSE 'casual_browser' END AS reviews_reading_behavior
    FROM behavior
),
cte_promo_interest AS (
    WITH behavior AS (SELECT profile_id,
            COUNT(*) FILTER (WHERE event_type = 'promotion-viewed') AS views,
            COUNT(*) FILTER (WHERE event_type = 'promotion-clicked') AS clicks,
            COUNT(*) FILTER (WHERE event_type = 'page-view' AND event_data->'event'->'context'->'page'->>'path' = '/actions') AS actions_visits
        FROM raw_events WHERE event_type IN ('promotion-viewed', 'promotion-clicked', 'page-view') AND inserted_at > NOW() - INTERVAL '30 days' GROUP BY profile_id)
    SELECT profile_id, ROUND((clicks + actions_visits)::NUMERIC / NULLIF(views + actions_visits, 0), 4) AS promo_interest_rate FROM behavior
),
cte_value_trend AS (
    SELECT profile_id, ROUND(REGR_SLOPE(CAST(event_data->'event'->'properties'->>'value' AS NUMERIC), EXTRACT(EPOCH FROM inserted_at))::NUMERIC, 4) AS checkout_value_trend
    FROM raw_events WHERE event_type = 'checkout-started' AND inserted_at > NOW() - INTERVAL '30 days' AND event_data->'event'->'properties'->>'value' IS NOT NULL
    GROUP BY profile_id HAVING COUNT(*) >= 2
),
cte_auth_flag AS (
    SELECT profile_id, BOOL_OR(event_data->'event'->'context'->'page'->>'path' = '/checkout' AND event_data->'event'->'properties'->>'is_authenticated' = 'false') AS auth_on_checkout_flag
    FROM raw_events WHERE event_type = 'page-view' AND inserted_at > NOW() - INTERVAL '30 days' GROUP BY profile_id
),
cte_churn_label AS (
    SELECT profile_id, CASE WHEN d.days_since_last_order IS NOT NULL AND d.days_since_last_order > 60 THEN TRUE ELSE FALSE END AS is_churned
    FROM active_profiles p LEFT JOIN cte_days_since_last_order d USING (profile_id)
)
SELECT
    p.profile_id, CURRENT_DATE AS snapshot_date,
    COALESCE(d.days_since_last_order, 999) AS days_since_last_order,
    COALESCE(a.avg_cart_value_30d, 0.0) AS avg_cart_value_30d,
    COALESCE(r.cart_to_checkout_ratio, 1.0) AS cart_to_checkout_ratio,
    COALESCE(t.checkout_value_trend, 0.0) AS checkout_value_trend,
    COALESCE(ab.cart_abandonment_rate_30d, 0.0) AS cart_abandonment_rate_30d,
    COALESCE(cc.checkout_completion_rate, 0.0) AS checkout_completion_rate,
    COALESCE(f.checkout_frustration_index, 0.0) AS checkout_frustration_index,
    COALESCE(ba.cart_browse_abandon_rate_30d, 0.0) AS cart_browse_abandon_rate_30d,
    COALESCE(af.auth_on_checkout_flag, FALSE) AS auth_on_checkout_flag,
    COALESCE(pc.personal_offer_conversion_rate, 0.0) AS personal_offer_conversion_rate,
    COALESCE(pv.personal_views_count_30d, 0) AS personal_views_count_30d,
    COALESCE(cr.avg_copy_reaction_seconds, 0.0) AS avg_copy_reaction_seconds,
    COALESCE(pi.promo_ignore_rate_14d, 0.0) AS promo_ignore_rate_14d,
    COALESCE(mo.message_open_rate_30d, 0.0) AS message_open_rate_30d,
    COALESCE(pa.push_channel_available, FALSE) AS push_channel_available,
    COALESCE(cd.coupon_dependency_ratio, 0.0) AS coupon_dependency_ratio,
    COALESCE(pir.promo_interest_rate, 0.0) AS promo_interest_rate,
    COALESCE(e.session_engagement_score, 0.0) AS session_engagement_score,
    COALESCE(ph.phone_changed_90d, FALSE) AS phone_changed_90d,
    COALESCE(ar.avg_rating_90d, 5.0) AS avg_rating_90d,
    COALESCE(cpl.profile_completeness_score, 0.0) AS profile_completeness_score,
    COALESCE(dv.delta_page_views_14d, 0.0) AS delta_page_views_14d,
    COALESCE(ur.has_unpublished_review, FALSE) AS has_unpublished_review,
    COALESCE(rb.reviews_reading_behavior, 'casual_browser') AS reviews_reading_behavior,
    cl.is_churned,
    NULL::NUMERIC(5,4) AS churn_probability, NULL::VARCHAR(16) AS risk_level,
    NOW() AS computed_at, 'v1.0' AS model_version
FROM active_profiles p
LEFT JOIN cte_days_since_last_order d USING (profile_id)
LEFT JOIN cte_cart_abandonment_rate ab USING (profile_id)
LEFT JOIN cte_checkout_completion cc USING (profile_id)
LEFT JOIN cte_frustration f USING (profile_id)
LEFT JOIN cte_personal_conversion pc USING (profile_id)
LEFT JOIN cte_promo_ignore pi USING (profile_id)
LEFT JOIN cte_engagement e USING (profile_id)
LEFT JOIN cte_message_open mo USING (profile_id)
LEFT JOIN cte_browse_abandon ba USING (profile_id)
LEFT JOIN cte_personal_views pv USING (profile_id)
LEFT JOIN cte_push_available pa USING (profile_id)
LEFT JOIN cte_phone_changed ph USING (profile_id)
LEFT JOIN cte_avg_rating ar USING (profile_id)
LEFT JOIN cte_coupon_dependency cd USING (profile_id)
LEFT JOIN cte_avg_cart a USING (profile_id)
LEFT JOIN cte_profile_completeness cpl USING (profile_id)
LEFT JOIN cte_delta_views dv USING (profile_id)
LEFT JOIN cte_unpublished_review ur USING (profile_id)
LEFT JOIN cte_cart_checkout_ratio r USING (profile_id)
LEFT JOIN cte_copy_reaction cr USING (profile_id)
LEFT JOIN cte_reviews_behavior rb USING (profile_id)
LEFT JOIN cte_promo_interest pir USING (profile_id)
LEFT JOIN cte_value_trend t USING (profile_id)
LEFT JOIN cte_auth_flag af USING (profile_id)
LEFT JOIN cte_churn_label cl USING (profile_id)
ORDER BY p.profile_id;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_ml_features_profile ON mv_ml_features (profile_id);
CREATE INDEX IF NOT EXISTS idx_mv_ml_features_snapshot ON mv_ml_features (snapshot_date);
COMMENT ON MATERIALIZED VIEW mv_ml_features IS 'Feature Store: 24 признака для всех активных пользователей';
"""
    with open(sql_dir / "sql_04_create_materialized_views.sql", "w", encoding="utf-8") as f:
        f.write(sql_04)
    
    # sql_05_maintenance.sql
    sql_05 = """-- Обновление материализованного представления и перенос в ml_features

-- 1. Записываем начало операции в лог
INSERT INTO events_processing_log (batch_id, source, status, started_at)
VALUES (gen_random_uuid(), 'maintenance', 'running', NOW())
RETURNING batch_id AS v_batch_id \\gset

-- 2. Обновляем materialized view
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_ml_features;

-- 3. Переносим данные в ml_features (UPSERT)
INSERT INTO ml_features (
    profile_id, snapshot_date, days_since_last_order, cart_abandonment_rate_30d,
    checkout_completion_rate, checkout_frustration_index, personal_offer_conversion_rate,
    promo_ignore_rate_14d, session_engagement_score, message_open_rate_30d,
    cart_browse_abandon_rate_30d, personal_views_count_30d, push_channel_available,
    phone_changed_90d, avg_rating_90d, coupon_dependency_ratio, avg_cart_value_30d,
    profile_completeness_score, delta_page_views_14d, has_unpublished_review,
    cart_to_checkout_ratio, avg_copy_reaction_seconds, reviews_reading_behavior,
    promo_interest_rate, checkout_value_trend, auth_on_checkout_flag, is_churned,
    churn_probability, risk_level, computed_at, model_version
)
SELECT
    profile_id, snapshot_date, days_since_last_order, cart_abandonment_rate_30d,
    checkout_completion_rate, checkout_frustration_index, personal_offer_conversion_rate,
    promo_ignore_rate_14d, session_engagement_score, message_open_rate_30d,
    cart_browse_abandon_rate_30d, personal_views_count_30d, push_channel_available,
    phone_changed_90d, avg_rating_90d, coupon_dependency_ratio, avg_cart_value_30d,
    profile_completeness_score, delta_page_views_14d, has_unpublished_review,
    cart_to_checkout_ratio, avg_copy_reaction_seconds, reviews_reading_behavior,
    promo_interest_rate, checkout_value_trend, auth_on_checkout_flag, is_churned,
    churn_probability, risk_level, computed_at, model_version
FROM mv_ml_features
ON CONFLICT (profile_id) DO UPDATE SET
    snapshot_date = EXCLUDED.snapshot_date,
    days_since_last_order = EXCLUDED.days_since_last_order,
    cart_abandonment_rate_30d = EXCLUDED.cart_abandonment_rate_30d,
    checkout_completion_rate = EXCLUDED.checkout_completion_rate,
    checkout_frustration_index = EXCLUDED.checkout_frustration_index,
    personal_offer_conversion_rate = EXCLUDED.personal_offer_conversion_rate,
    promo_ignore_rate_14d = EXCLUDED.promo_ignore_rate_14d,
    session_engagement_score = EXCLUDED.session_engagement_score,
    message_open_rate_30d = EXCLUDED.message_open_rate_30d,
    cart_browse_abandon_rate_30d = EXCLUDED.cart_browse_abandon_rate_30d,
    personal_views_count_30d = EXCLUDED.personal_views_count_30d,
    push_channel_available = EXCLUDED.push_channel_available,
    phone_changed_90d = EXCLUDED.phone_changed_90d,
    avg_rating_90d = EXCLUDED.avg_rating_90d,
    coupon_dependency_ratio = EXCLUDED.coupon_dependency_ratio,
    avg_cart_value_30d = EXCLUDED.avg_cart_value_30d,
    profile_completeness_score = EXCLUDED.profile_completeness_score,
    delta_page_views_14d = EXCLUDED.delta_page_views_14d,
    has_unpublished_review = EXCLUDED.has_unpublished_review,
    cart_to_checkout_ratio = EXCLUDED.cart_to_checkout_ratio,
    avg_copy_reaction_seconds = EXCLUDED.avg_copy_reaction_seconds,
    reviews_reading_behavior = EXCLUDED.reviews_reading_behavior,
    promo_interest_rate = EXCLUDED.promo_interest_rate,
    checkout_value_trend = EXCLUDED.checkout_value_trend,
    auth_on_checkout_flag = EXCLUDED.auth_on_checkout_flag,
    is_churned = EXCLUDED.is_churned,
    computed_at = NOW();
    
-- 4. Записываем завершение
UPDATE events_processing_log
SET events_inserted = (SELECT COUNT(*) FROM ml_features),
    events_fetched = (SELECT COUNT(*) FROM mv_ml_features),
    events_failed = 0, status = 'completed', completed_at = NOW()
WHERE batch_id = :'v_batch_id';

-- 5. Обновляем статистику
VACUUM ANALYZE ml_features;
VACUUM ANALYZE mv_ml_features;
VACUUM ANALYZE raw_events;
VACUUM ANALYZE profiles;
VACUUM ANALYZE events_queue;
"""
    with open(sql_dir / "sql_05_maintenance.sql", "w", encoding="utf-8") as f:
        f.write(sql_05)

def create_bootstrap_script(delivery_dir):
    """Создает скрипт инициализации БД"""
    code = '''"""
fc_bootstrap_database.py
Скрипт первичной инициализации базы данных PostgreSQL.
Выполняет SQL-скрипты в порядке: Таблицы - Партиции - Индексы - MV.
"""
import os
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        sslmode=os.getenv("DB_SSLMODE", "require")
    )

def execute_sql_file(cursor, filepath):
    print(f"   - Выполнение: {filepath.name}")
    with open(filepath, 'r', encoding='utf-8') as f:
        sql_script = f.read()
    cursor.execute(sql_script)

def main():
    print("- Начало инициализации базы данных PostgreSQL...")
    
    sql_dir = Path(__file__).parent / "sql"
    sql_files = sorted([f for f in sql_dir.glob("*.sql")])
    
    if not sql_files:
        print("- Ошибка: Папка sql/ пуста или не найдена.")
        return

    try:
        conn = get_db_connection()
        conn.autocommit = True
        
        with conn.cursor() as cursor:
            print("- Подключение к БД успешно.")
            for sql_file in sql_files:
                execute_sql_file(cursor, sql_file)
                
        print("- База данных успешно инициализирована!")
        print("- Следующий шаг: Запустите fd_sync_cdp_data.py для первичной загрузки данных из CDP.")
        
    except Exception as e:
        print(f"- Ошибка при инициализации БД: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
'''
    with open(delivery_dir / "fc_bootstrap_database.py", "w", encoding="utf-8") as f:
        f.write(code)

def create_sync_cdp_script(delivery_dir):
    """Создает скрипт первичной загрузки данных из CDP"""
    code = '''"""
fd_sync_cdp_data.py
Первичная загрузка данных из CDP Elasticsearch в PostgreSQL.
Объединяет fetch + process_queue для первичной синхронизации.
"""
import os
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values
from elasticsearch import Elasticsearch, ElasticsearchWarning
from elasticsearch.helpers import scan
import warnings
from dotenv import load_dotenv

warnings.filterwarnings("ignore", category=ElasticsearchWarning)
load_dotenv()

# Конфигурация
PG_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "sslmode": os.getenv("DB_SSLMODE", "require")
}

ES_HOST = os.getenv("ES_HOST", "")
ES_INDEX_PATTERN = os.getenv("ES_INDEX_PATTERN", "events-*")
ES_VERIFY_CERTS = os.getenv("ES_VERIFY_CERTS", "false").lower() == "true"
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1000"))

EVENT_TYPES = [
    'page-view', 'profile-traits-update', 'identification',
    'product-details-page-view', 'cart-changes', 'checkout-started',
    'cart-delete', 'sign-in', 'profile-update', 'promotion-viewed',
    'promotion-clicked', 'promotion-close', 'message-status',
    'message-opened', 'rating', 'personal-view', 'copy-promocode'
]

def is_valid_uuid(val):
    if not val:
        return False
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, AttributeError):
        return False

def transform_event(hit):
    source = hit['_source']
    event_data = {"event": source}
    event_id = source.get('id')
    event_type = source.get('type')
    
    profile_id = None
    if source.get('profile') and source['profile'].get('id'):
        raw_profile_id = source['profile']['id']
        if raw_profile_id != 'undefined' and is_valid_uuid(raw_profile_id):
            profile_id = raw_profile_id
    
    session_id = None
    if source.get('session') and source['session'].get('id'):
        raw_session_id = source['session']['id']
        if raw_session_id != 'undefined' and is_valid_uuid(raw_session_id):
            session_id = raw_session_id
    
    inserted_at = None
    if source.get('metadata') and source['metadata'].get('time'):
        inserted_at = source['metadata']['time'].get('insert')
        if inserted_at:
            try:
                inserted_at = datetime.fromisoformat(inserted_at.replace('Z', '+00:00'))
            except:
                inserted_at = datetime.now(timezone.utc)
        else:
            inserted_at = datetime.now(timezone.utc)
    else:
        inserted_at = datetime.now(timezone.utc)
    
    event_data_json = json.dumps(event_data, ensure_ascii=False)
    return (event_id, event_type, profile_id, session_id, event_data_json, inserted_at)

def main():
    print("- Начало первичной синхронизации данных из CDP")
    
    try:
        # Подключение к ES
        print(" - Подключение к Elasticsearch")
        es = Elasticsearch(hosts=[ES_HOST], verify_certs=ES_VERIFY_CERTS)
        if not es.ping():
            print(" - Кластер ES недоступен!")
            return
        
        print(" - ES подключен")
        
        # Подключение к PostgreSQL
        print(" -  Подключение к PostgreSQL")
        conn = psycopg2.connect(**PG_CONFIG)
        conn.autocommit = True
        print(" - PostgreSQL подключен")
        
        # Запрос событий
        print(f"\\n - Загрузка событий из индекса {ES_INDEX_PATTERN}")
        query = {"query": {"bool": {"must": [{"terms": {"type": EVENT_TYPES}}]}}}
        
        count_result = es.count(index=ES_INDEX_PATTERN, body=query)
        total_count = count_result['count']
        print(f"  - Найдено событий: {total_count:,}")
        
        if total_count == 0:
            print("  - Нет событий для загрузки.")
            return
        
        # Обработка батчами
        events = scan(es, query=query, index=ES_INDEX_PATTERN, size=BATCH_SIZE, scroll='5m')
        
        total_fetched = 0
        total_inserted = 0
        total_skipped = 0
        batch_count = 0
        current_batch = []
        
        print(f"\\n - Обработка батчами по {BATCH_SIZE}")
        
        for hit in events:
            event_data = transform_event(hit)
            current_batch.append(event_data)
            total_fetched += 1
            
            if len(current_batch) >= BATCH_SIZE:
                batch_count += 1
                
                with conn.cursor() as cursor:
                    insert_query = """
                        INSERT INTO events_queue (event_id, event_type, profile_id, session_id, event_data, status)
                        VALUES %s ON CONFLICT (event_id) DO NOTHING
                    """
                    values = [(eid, etype, pid, sid, edata, 'pending') for eid, etype, pid, sid, edata, _ in current_batch]
                    execute_values(cursor, insert_query, values)
                    inserted = cursor.rowcount
                    conn.commit()
                    
                skipped = len(current_batch) - inserted
                total_inserted += inserted
                total_skipped += skipped
                
                progress = (total_fetched / total_count * 100)
                print(f"   Батч {batch_count}: +{inserted} (пропущено {skipped}) | {total_fetched:,}/{total_count:,} ({progress:.1f}%)")
                
                current_batch = []
                
        # Последний батч
        if current_batch:
            batch_count += 1
            with conn.cursor() as cursor:
                insert_query = """
                    INSERT INTO events_queue (event_id, event_type, profile_id, session_id, event_data, status)
                    VALUES %s ON CONFLICT (event_id) DO NOTHING
                """
                values = [(eid, etype, pid, sid, edata, 'pending') for eid, etype, pid, sid, edata, _ in current_batch]
                execute_values(cursor, insert_query, values)
                inserted = cursor.rowcount
                conn.commit()
            
            total_inserted += inserted
            total_skipped += len(current_batch) - inserted
            print(f"   Батч {batch_count} (финальный): +{inserted}")
        
        print(f"\\n Итого:")
        print(f"  - Загружено из ES: {total_fetched:,}")
        print(f"  - Вставлено в очередь: {total_inserted:,}")
        print(f"  - Пропущено (дубликаты): {total_skipped:,}")
        
        print("\\n Первичная загрузка завершена!")
        print(" - Следующий шаг: Запустите fe_refresh_features.py для расчета признаков.")
        
    except Exception as e:
        print(f" Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
'''
    with open(delivery_dir / "fd_sync_cdp_data.py", "w", encoding="utf-8") as f:
        f.write(code)    
    
def create_refresh_features_script(delivery_dir):
    """Создает скрипт обновления признаков (maintenance)"""
    code = '''"""
fe_refresh_features.py
Обновление материализованного представления и перенос данных в ml_features.
Выполняет SQL из sql_05_maintenance.sql.
"""
import os
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        sslmode=os.getenv("DB_SSLMODE", "require")
    )

def main():
    print("- Начало обновления признаков")
    
    sql_file = Path(__file__).parent / "sql" / "sql_05_maintenance.sql"
    
    if not sql_file.exists():
        print(f" - SQL-файл не найден: {sql_file}")
        return
    
    try:
        conn = get_db_connection()
        conn.autocommit = True
        
        with conn.cursor() as cursor:
            print("- Подключение к БД успешно.")
            print("  - Выполнение sql_05_maintenance.sql")
            
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_script = f.read()
            
            cursor.execute(sql_script)
            
        print("- Признаки успешно обновлены")
        print(" Следующий шаг: Запустите fb_inference_pipeline.py для предсказания оттока.")
        
    except Exception as e:
        print(f" Ошибка при обновлении признаков: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
'''
    with open(delivery_dir / "fe_refresh_features.py", "w", encoding="utf-8") as f:
        f.write(code)
 
def create_adapted_preprocessor(delivery_dir):
    """Создает упрощенную версию preprocess_inference.py для папки f_delivery"""
    code = '''"""
fa_preprocess_inference.py (Delivery Version)
Класс для предобработки данных перед инференсом.
Адаптирован для автономной работы в папке f_delivery
"""
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from ml_config import MAX_DAYS_SINCE_ORDER, LOG_COLUMNS, COLS_TO_DROP

# Путь к scaler теперь относительный (в той же папке)
SCALER_PATH = Path(__file__).parent / "churn_model" / "scaler.joblib"

class InferencePreprocessor:
    def __init__(self, scaler_path: str = SCALER_PATH):
        if not Path(scaler_path).exists():
            raise FileNotFoundError(f"Scaler не найден: {scaler_path}")
        
        self.scaler = joblib.load(scaler_path)
        self.expected_features = list(self.scaler.feature_names_in_)
        
    def transform(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        df = df_raw.copy()

        # 1. Фильтрация
        df = df[df['days_since_last_order'] < MAX_DAYS_SINCE_ORDER].copy()
    
        # 2. Исключение колонок
        cols_to_drop = [col for col in COLS_TO_DROP if col in df.columns]
        df = df.drop(columns=cols_to_drop)

        # 3. Bool в Int
        bool_cols = df.select_dtypes(include=['bool']).columns
        if len(bool_cols) > 0:
            df[bool_cols] = df[bool_cols].astype(int)
        
        # 4. Логарифмирование
        for col in LOG_COLUMNS:
            if col in df.columns:
                df[col] = np.log1p(df[col])
        
        # 5. One-Hot Encoding
        if 'reviews_reading_behavior' in df.columns:
            dummies = pd.get_dummies(df['reviews_reading_behavior'], prefix='behavior')
            df = pd.concat([df, dummies], axis=1)
            df = df.drop(columns=['reviews_reading_behavior'])
        
        # 6. Удаление model_version
        if 'model_version' in df.columns:
            df = df.drop(columns=['model_version'])
        
        # 7. Winsorization (1%-99%)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            lower_bound = df[col].quantile(0.01)
            upper_bound = df[col].quantile(0.99)
            df[col] = df[col].clip(lower=lower_bound, upper=upper_bound)

        # 8. Alignment (приведение к ожидаемым признакам)
        missing_features = set(self.expected_features) - set(df.columns)
        extra_features = set(df.columns) - set(self.expected_features)
        
        for col in missing_features:
            df[col] = 0
        if extra_features:
            df = df.drop(columns=list(extra_features))
                
        df = df[self.expected_features]
    
        # 9. StandardScaler
        df_scaled = pd.DataFrame(
            self.scaler.transform(df),
            columns=self.expected_features,
            index=df.index
        )

        return df_scaled
'''
    with open(delivery_dir / "fa_preprocess_inference.py", "w", encoding="utf-8") as f:
        f.write(code)
    
def create_adapted_inference_pipeline(delivery_dir):
    """Создает упрощенную версию e_run_pipeline.py для папки delivery"""
    code = '''"""
fb_inference_pipeline.py (Delivery Version)
Оркестратор инференс-пайплайна для заказчика.
Запускает полный цикл: Загрузка из БД - Предобработка - Предсказание - Сохранение в CSV/БД.
"""
import sys
import os
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import joblib
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Локальные импорты вместо проектных
from fa_preprocess_inference import InferencePreprocessor
from ml_config import RISK_THRESHOLDS, MODEL_VERSION, BATCH_SIZE_INFERENCE

# Пути относительно папки delivery
MODEL_DIR = Path(__file__).parent / "churn_model"
MODEL_PATH = MODEL_DIR / "model.skops" # Или model.joblib, model.pkl, в зависимости от экспорта MLflow
OUTPUT_DIR = Path(__file__).parent / "predictions"

def get_db_engine():
    """Создает подключение к БД заказчика через переменные окружения"""
    # Заказчик должен задать свои креды в .env или переменных окружения
    user = os.getenv("DB_USER", "your_db_user")
    password = os.getenv("DB_PASSWORD", "your_db_password")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    database = os.getenv("DB_NAME", "your_db_name")
    sslmode = os.getenv("DB_SSLMODE", "require")
    
    if not all([user, password, host, database]):
        raise ValueError("Не все переменные окружения БД установлены. Проверьте .env")
    
    connection_string = f"postgresql://{user}:{password}@{host}:{port}/{database}?sslmode={sslmode}"
    return create_engine(connection_string)
    
def get_risk_level(probability: float) -> str:
    if probability >= RISK_THRESHOLDS['CRITICAL']: return 'CRITICAL'
    elif probability >= RISK_THRESHOLDS['HIGH']: return 'HIGH'
    elif probability >= RISK_THRESHOLDS['MEDIUM']: return 'MEDIUM'
    else: return 'LOW'
    
def run_prediction(df_raw: pd.DataFrame, df_preprocessed: pd.DataFrame):
    print("\\n - Запуск предсказания")
    
    # 1. Загрузка модели
    model = joblib.load(MODEL_PATH)
    
    # 2. Предсказание
    probabilities = model.predict_proba(df_preprocessed)[:, 1]
    risk_levels = [get_risk_level(p) for p in probabilities]
    
    # 3. Формирование результата
    df_results = pd.DataFrame({
        'profile_id': df_raw['profile_id'].values[:len(probabilities)],
        'churn_probability': np.round(probabilities, 4),
        'risk_level': risk_levels
    })
    
    # 4. Экспорт в CSV
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d")
    
    for level in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        df_level = df_results[df_results['risk_level'] == level]
        filepath = OUTPUT_DIR / f"churn_{level.lower()}_{timestamp}.csv"
        df_level.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"   - Сохранено {len(df_level)} записей: {filepath.name}")
        
    # 5. Обновление БД заказчика
    print("\\n - Обновление таблицы ml_features в БД")
    engine = get_db_engine()
    update_query = """
        UPDATE ml_features
        SET churn_probability = :churn_probability,
            risk_level = :risk_level,
            computed_at = NOW(),
            model_version = :model_version
        WHERE profile_id = :profile_id
    """
    
    params_list = [
        {
            'churn_probability': float(row['churn_probability']),
            'risk_level': row['risk_level'],
            'model_version': MODEL_VERSION,
            'profile_id': str(row['profile_id'])
        }
        for _, row in df_results.iterrows()
    ]
    
    with engine.begin() as conn:
        for i in range(0, len(params_list), BATCH_SIZE_INFERENCE):
            batch = params_list[i : i + BATCH_SIZE_INFERENCE]
            conn.execute(text(update_query), batch)
            
    print(f"   - Успешно обновлено {len(params_list)} записей в БД.")
    return True
    
def main():
    parser = argparse.ArgumentParser(description='Инференс пайплайн (Delivery)')
    parser.add_argument('--skip-predict', action='store_true', help='Только предобработка')
    args = parser.parse_args()
    
    print("\\n - Инференс пайплайн: Предсказание оттока клиентов")
    
    try:
        # Шаг 1: Загрузка из БД
        print("\\n - Шаг 1: Загрузка данных из БД")
        engine = get_db_engine()
        query = "SELECT * FROM ml_features WHERE days_since_last_order < 900"
        df_raw = pd.read_sql(query, engine)
        print(f"   Загружено {len(df_raw)} записей")
        
        if len(df_raw) == 0:
            print("   Нет данных для обработки. Завершение.")
            return
            
        # Шаг 2: Предобработка
        print("\\n - Шаг 2: Предобработка данных")
        preprocessor = InferencePreprocessor()
        df_preprocessed = preprocessor.transform(df_raw)
        print(f"   Готово {len(df_preprocessed)} записей с {len(df_preprocessed.columns)} признаками")
        
        # Шаг 3: Предсказание
        if not args.skip_predict:
            run_prediction(df_raw, df_preprocessed)
            
        print("\\n - Инференс пайплайн завершен успешно!")
        
    except Exception as e:
        print(f"\\n - Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
    with open(delivery_dir / "fb_inference_pipeline.py", "w", encoding="utf-8") as f:
        f.write(code)
    
def export_model_and_scaler(output_dir):
    """Экспортирует модель и scaler из MLflow в папку delivery"""
    output_dir.mkdir(exist_ok=True)
    
    # Настраиваем URI на локальную базу MLflow проекта
    mlflow.set_tracking_uri("sqlite:///mlflow.db")
    
    # Загружаем зарегистрированную модель по имени
    # Убедись, что ты зарегистрировал модель в UI как "churn_prediction_best"
    model_uri = "models:/churn_prediction_best/1"
    
    try:
        # Загружаем модель
        model = mlflow.sklearn.load_model(model_uri)
        
        # Сохраняем в формате, понятном заказчику
        mlflow.sklearn.save_model(model, str(output_dir))
        
        # Явно копируем scaler, если он не был включен в pipeline MLflow
        project_scaler_path = Path("d_ml_model/models/scaler.joblib")
        if project_scaler_path.exists():
            shutil.copy(project_scaler_path, output_dir / "scaler.joblib")
    
    except Exception as e:
        print(f"- Не удалось загрузить модель из MLflow: {e}")
        print("- Убедись, что модель зарегистрирована в MLflow UI как 'churn_prediction_best'")
        # Fallback: копируем напрямую из папки проекта
        shutil.copy("d_ml_model/models/gridsearch_cv_model.joblib", output_dir / "model.joblib")
        shutil.copy("d_ml_model/models/scaler.joblib", output_dir / "scaler.joblib")

def create_requirements(delivery_dir):
    """Создает requirements.txt с полными зависимостями"""
    requirements = """pandas>=2.1.4
numpy>=1.26.3
scikit-learn>=1.4.0
joblib>=1.3.2
sqlalchemy>=2.0.25
psycopg2-binary>=2.9.9
python-dotenv>=1.0.0
elasticsearch>=8.0.0
mlflow>=2.0.0
"""
    with open(delivery_dir / "requirements.txt", "w", encoding="utf-8") as f:
        f.write(requirements)

# Функция создания .env.example
def create_env_example(delivery_dir):
    """Создает файл .env.example с примерами переменных окружения для БД"""
    env_example_content = """
# Конфигурация подключения к базе данных
# Скопируйте этот файл в .env и заполните реальными значениями:
#   cp f_delivery/.env.example .env
#
# ВАЖНО: Никогда не коммитьте файл .env в Git

# Основные параметры подключения PostgreSQL
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database_name

# SSL-настройки (опционально)
# Для продакшена рекомендуется использовать sslmode=require
# Для локальной разработки можно использовать sslmode=disable
DB_SSLMODE=require

# CDP Elasticsearch
ES_HOST=http://your_es_host:9200
ES_INDEX_PATTERN=events-*
ES_VERIFY_CERTS=false

# Настройки обработки
BATCH_SIZE=1000
"""
    with open(delivery_dir / ".env.example", "w", encoding="utf-8") as f:
        f.write(env_example_content)

def create_readme(delivery_dir):
    """Создает полную документацию"""
    readme_content = """# - Churn Prediction Model - Delivery Package

Этот пакет содержит обученную ML-модель для прогнозирования оттока клиентов и все необходимые скрипты для её запуска.

## - Структура пакета
```bash
f_delivery/
├── sql/ # SQL-скрипты для БД
├── fc_bootstrap_database.py # Инициализация БД
├── fd_sync_cdp_data.py # Первичная загрузка из CDP
├── fe_refresh_features.py # Обновление признаков
├── fa_preprocess_inference.py # ML-препроцессор
├── fb_inference_pipeline.py # ML-инференс
├── ml_config.py # ML-константы
├── churn_model/ # Модель + scaler
├── predictions/ # сюда будут сохраняться CSV-файлы с результатами.
├── requirements.txt # Зависимости
├── .env.example # Шаблон переменных
├── README.md # Документация
└── .gitignore # Git исключения
```
## Что включено

### Фаза 1: Инициализация инфраструктуры
- **SQL-скрипты** (`sql/`) — создание таблиц, партиций, индексов, материализованных представлений
- **fc_bootstrap_database.py** — автоматическая инициализация БД
- **fd_sync_cdp_data.py** — первичная загрузка данных из CDP Elasticsearch
- **fe_refresh_features.py** — расчет 24 признаков и обновление Feature Store

### Фаза 2: ML-инференс
- **fa_preprocess_inference.py** — предобработка данных (9 шагов трансформации)
- **fb_inference_pipeline.py** — оркестратор инференса (загрузка - предобработка - предсказание - сохранение)
- **churn_model/** — обученная модель
- **ml_config.py** — ML-константы и пороги

## Инструкция по запуску

### 1. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 2. Настройка переменных окружения для подключения к БД
```bash
cp f_delivery/.env.example .env
```
*Заполните `.env` своими настройками*

### 3. Фаза 1: Инициализация БД
```bash
python fc_bootstrap_database.py
```
*Создаст все таблицы, индексы и материализованные представления.

### 4. Фаза 1: Первичная загрузка данных из CDP
```bash
python fd_sync_cdp_data.py
```
* Загрузит исторические события из Elasticsearch в PostgreSQL.

### 5. Фаза 1: Расчет признаков
```bash
python fe_refresh_features.py
```
* Рассчитает 24 признака для всех активных пользователей и сохранит в `ml_features`.

### 6. Фаза 2: Запуск инференса
```bash
python fb_inference_pipeline.py
```
* Загрузит данные из `ml_features`, сделает предсказания, сохранит CSV и обновит БД.

### Результаты
Предсказания сохраняются в папку `predictions/`:
```bash
churn_critical_YYYYMM.csv — клиенты с риском оттока ≥70%
churn_high_YYYYMM.csv — риск 50-70%
churn_medium_YYYYMM.csv — риск 30-50%
churn_low_YYYYMM.csv — риск <30%
```
Каждый CSV содержит: `profile_id`, `churn_probability`, `risk_level`

### Ежедневное обслуживание
Для ежедневного обновления признаков или предсказаний:
```bash
# 1. Загрузить новые события из CDP (опционально, если есть новые данные)
python fd_sync_cdp_data.py

# 2. Обновить признаки
python fe_refresh_features.py

# 3. Сделать предсказания
python fb_inference_pipeline.py
```

### Безопасность
- Файл `.env` с паролями никогда не коммитится в Git
- Модель использует только агрегированные признаки, персональные данные не обрабатываются
- Все SQL-запросы используют параметризованные запросы (защита от SQL-инъекций)

### Поддержка
При возникновении проблем:
1. Проверьте подключение к БД: `psql -h $DB_HOST -U $DB_USER -d $DB_NAME`
2. Проверьте подключение к ES: `curl $ES_HOST`
3. Проверьте логи в таблице `events_processing_log`
"""
    with open(delivery_dir / "README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
   
def create_gitignore(delivery_dir):
    """Создает .gitignore для папки f_delivery, чтобы исключить чувствительные файлы"""
    gitignore_content = """# Чувствительные данные - никогда не коммитить!
.env

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Виртуальное окружение
venv/
ENV/
env/
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Результаты предсказаний (могут содержать бизнес-данные)
predictions/

# OS
.DS_Store
Thumbs.db

# MLflow
mlruns/
mlflow.db
"""
    with open(delivery_dir / ".gitignore", "w", encoding="utf-8") as f:
        f.write(gitignore_content)
    
if __name__ == "__main__":
    create_delivery_package()

    
    
    
    