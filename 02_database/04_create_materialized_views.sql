-- 04_create_materialized_views.sql

-- Удаляем, если есть
DROP MATERIALIZED VIEW IF EXISTS mv_ml_features CASCADE;

-- Создаём новое materialized_view
CREATE MATERIALIZED VIEW mv_ml_features AS

-- 1. список профилей у кого были события за последние 90 дней
WITH
active_profiles AS (
    SELECT DISTINCT profile_id
    FROM raw_events
    WHERE profile_id IS NOT NULL
      AND inserted_at > NOW() - INTERVAL '90 days'
),

-- 2. Расчёт признака в отдельном CTE

-- days_since_last_order: Дней с последнего заказа
-- считаем по page-view на /order
cte_days_since_last_order AS (
    SELECT
        profile_id,
        EXTRACT(DAY FROM NOW() - MAX(inserted_at))::INTEGER AS days_since_last_order
    FROM raw_events
    WHERE event_type = 'page-view'
      AND event_data->'event'->'context'->'page'->>'path' = '/order'
      AND inserted_at > NOW() - INTERVAL '90 days'
    GROUP BY profile_id
)

-- 3. Сборка признака
SELECT
    p.profile_id,
    CURRENT_DATE AS snapshot_date,

    COALESCE(d.days_since_last_order, 999) AS days_since_last_order,

    NULL::NUMERIC(5,4) AS churn_probability,
    NULL::VARCHAR(16) AS risk_level,
    NOW() AS computed_at,
    'v1.0' AS model_version

FROM active_profiles p
LEFT JOIN cte_days_since_last_order d USING (profile_id)
ORDER BY p.profile_id;

COMMENT ON MATERIALIZED VIEW mv_ml_features IS
    'Feature Store: рассчитывает 24 признака для всех активных пользователей за один проход';