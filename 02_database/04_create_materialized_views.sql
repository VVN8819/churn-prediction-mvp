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
),

-- cart_abandonment_rate_30d: % отказов на /checkout
cte_cart_abandonment_rate AS (
    SELECT
        profile_id,
        ROUND(
            COUNT(*) FILTER (
                WHERE event_type = 'cart-delete'
                AND event_data->'event'->'context'->'page'->>'path' = '/checkout'
            )::NUMERIC /
            NULLIF(COUNT(*) FILTER (WHERE event_type = 'cart-changes'), 0),
            4
        ) AS cart_abandonment_rate_30d
    FROM raw_events
    WHERE event_type IN ('cart-delete', 'cart-changes')
      AND inserted_at > NOW() - INTERVAL '30 days'
    GROUP BY profile_id
),

-- checkout_completion_rate: Конверсия оформления заказа (/order)
cte_checkout_completion AS (
    SELECT
        profile_id,
        ROUND(
            COUNT(*) FILTER (
                WHERE event_type = 'page-view'
                AND event_data->'event'->'context'->'page'->>'path' = '/order'
            )::NUMERIC /
            NULLIF(COUNT(*) FILTER (WHERE event_type = 'checkout-started'), 0),
            4
        ) AS checkout_completion_rate
    FROM raw_events
    WHERE event_type IN ('checkout-started', 'page-view')
      AND inserted_at > NOW() - INTERVAL '30 days'
    GROUP BY profile_id
),

-- checkout_frustration_index: (удаления на /checkout + низкие рейтинги) / начатые оформления
cte_frustration AS (
    SELECT 
        profile_id,
        ROUND(
            (COUNT(*) FILTER (
                WHERE event_type = 'cart-delete' 
                AND event_data->'event'->'context'->'page'->>'path' = '/checkout'
            ) +
            COUNT(*) FILTER (
                WHERE event_type = 'rating' 
                AND CAST(event_data->'event'->'properties'->>'rate' AS INTEGER) <= 3
            ))::NUMERIC / 
            NULLIF(COUNT(*) FILTER (WHERE event_type IN ('cart-changes', 'checkout-started')), 0),
            4
        ) AS checkout_frustration_index
    FROM raw_events
    WHERE event_type IN ('cart-changes', 'checkout-started', 'cart-delete', 'rating')
      AND inserted_at > NOW() - INTERVAL '30 days'
    GROUP BY profile_id
),

-- personal_offer_conversion_rate: Конверсия персонального предложения
-- (увидел personal-view и скопировал copy-promocode)
cte_personal_conversion AS (
    WITH funnel AS (
        SELECT
            profile_id,
            session_id,
            event_data->'event'->'properties'->>'id' AS offer_id,
            MAX(CASE WHEN event_type = 'personal-view' THEN 1 ELSE 0 END) AS viewed,
            MAX(CASE WHEN event_type = 'copy-promocode' THEN 1 ELSE 0 END) AS copied
        FROM raw_events
        WHERE event_type IN ('personal-view', 'copy-promocode')
          AND inserted_at > NOW() - INTERVAL '30 days'
        GROUP BY profile_id, session_id, offer_id
    )
    SELECT
        profile_id,
        ROUND(
            COUNT(*) FILTER (WHERE copied = 1)::NUMERIC /
            NULLIF(COUNT(*) FILTER (WHERE viewed = 1), 0),
            4
        ) AS personal_offer_conversion_rate
    FROM funnel
    GROUP BY profile_id
),

-- promo_ignore_rate_14d: % игнорирования баннерных акций
cte_promo_ignore AS (
    SELECT
        profile_id,
        ROUND(
            COUNT(*) FILTER (WHERE event_type = 'promotion-close')::NUMERIC /
            NULLIF(COUNT(*) FILTER (WHERE event_type IN ('promotion-viewed', 'promotion-close')), 0),
            4
        ) AS promo_ignore_rate_14d
    FROM raw_events
    WHERE event_type IN ('promotion-viewed', 'promotion-close')
      AND inserted_at > NOW() - INTERVAL '14 days'
    GROUP BY profile_id
)

-- 3. Сборка признака
SELECT
    p.profile_id,
    CURRENT_DATE AS snapshot_date,

    -- 1: Временные и транзакционные
    COALESCE(d.days_since_last_order, 999) AS days_since_last_order,

    -- 2: Отказы
    COALESCE(ab.cart_abandonment_rate_30d, 0.0) AS cart_abandonment_rate_30d,
    COALESCE(cc.checkout_completion_rate, 0.0) AS checkout_completion_rate,
    COALESCE(f.checkout_frustration_index, 0.0) AS checkout_frustration_index,

    -- 3: Персональные предложения
    COALESCE(pc.personal_offer_conversion_rate, 0.0) AS personal_offer_conversion_rate,

    -- 4: Маркетинг и коммуникации
    COALESCE(pi.promo_ignore_rate_14d, 0.0) AS promo_ignore_rate_14d,

    NULL::NUMERIC(5,4) AS churn_probability,
    NULL::VARCHAR(16) AS risk_level,
    NOW() AS computed_at,
    'v1.0' AS model_version

FROM active_profiles p
LEFT JOIN cte_days_since_last_order d USING (profile_id)
LEFT JOIN cte_cart_abandonment_rate ab USING (profile_id)
LEFT JOIN cte_checkout_completion cc USING (profile_id)
LEFT JOIN cte_frustration f USING (profile_id)
LEFT JOIN cte_personal_conversion pc USING (profile_id)
LEFT JOIN cte_promo_ignore pi USING (profile_id)
ORDER BY p.profile_id;

-- Индексы для быстрого доступа idx_mv_
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_ml_features_profile ON mv_ml_features (profile_id);
CREATE INDEX IF NOT EXISTS idx_mv_ml_features_snapshot ON mv_ml_features (snapshot_date);

COMMENT ON MATERIALIZED VIEW mv_ml_features IS
    'Feature Store: рассчитывает 24 признака для всех активных пользователей за один проход';