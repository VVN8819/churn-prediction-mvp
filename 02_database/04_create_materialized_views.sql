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

-- days_since_last_order: Дней с последнего заказа 1
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

-- cart_abandonment_rate_30d: % отказов на /checkout 2
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

-- checkout_completion_rate: Конверсия оформления заказа (/order) 3
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

-- checkout_frustration_index: (удаления на /checkout + низкие рейтинги) / начатые оформления 4
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

-- personal_offer_conversion_rate: Конверсия персонального предложения 5
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

-- promo_ignore_rate_14d: % игнорирования баннерных акций 6
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
),

-- session_engagement_score: Вовлечённость сессии 7
cte_engagement AS (
    SELECT
        profile_id,
        ROUND(SUM(
            CASE
                WHEN event_data->'event'->'context'->'page'->>'path' = '/' THEN 0.1
                WHEN event_data->'event'->'context'->'page'->>'path' LIKE '/catalog%' THEN 0.3
                WHEN event_data->'event'->'context'->'page'->>'path' = '/profile' THEN 0.5
                WHEN event_data->'event'->'context'->'page'->>'path' = '/actions' THEN 0.5
                WHEN event_data->'event'->'context'->'page'->>'path' = '/reviews' THEN 0.6
                WHEN event_data->'event'->'context'->'page'->>'path' = '/checkout' THEN 0.8
                WHEN event_data->'event'->'context'->'page'->>'path' = '/order' THEN 1.0
                ELSE 0.0
            END
        ), 4) AS session_engagement_score
    FROM raw_events
    WHERE event_type = 'page-view'
      AND inserted_at > NOW() - INTERVAL '30 days'
    GROUP BY profile_id
),

-- message_open_rate_30d: % открытых сообщений 8
cte_message_open AS (
    SELECT
        profile_id,
        ROUND(
            (COUNT(*) FILTER (WHERE event_type = 'message-opened') +
             COUNT(*) FILTER (
                WHERE event_type = 'message-status'
                AND event_data->'event'->'properties'->>'status' = 'clicked'
             ))::NUMERIC /
            NULLIF(COUNT(*) FILTER (
                WHERE event_type = 'message-status'
                AND event_data->'event'->'properties'->>'status' IN ('delivered', 'clicked')
            ), 0),
            4
        ) AS message_open_rate_30d
    FROM raw_events
    WHERE event_type IN ('message-status', 'message-opened')
      AND inserted_at > NOW() - INTERVAL '30 days'
    GROUP BY profile_id
),

-- cart_browse_abandon_rate_30d: % отказов в каталоге/на главной 9
cte_browse_abandon AS (
    SELECT
        profile_id,
        ROUND(
            COUNT(*) FILTER (
                WHERE event_type = 'cart-delete'
                AND (event_data->'event'->'context'->'page'->>'path' LIKE '/catalog%'
                     OR event_data->'event'->'context'->'page'->>'path' = '/')
            )::NUMERIC /
            NULLIF(COUNT(*) FILTER (WHERE event_type = 'cart-changes'), 0),
            4
        ) AS cart_browse_abandon_rate_30d
    FROM raw_events
    WHERE event_type IN ('cart-delete', 'cart-changes')
      AND inserted_at > NOW() - INTERVAL '30 days'
    GROUP BY profile_id
),

-- personal_views_count_30d: Количество просмотров персонального предложения 10
cte_personal_views AS (
    SELECT
        profile_id,
        COUNT(*) AS personal_views_count_30d
    FROM raw_events
    WHERE event_type = 'personal-view'
      AND inserted_at > NOW() - INTERVAL '30 days'
    GROUP BY profile_id
),

-- push_channel_available: Доступен ли push-канал 11
cte_push_available AS (
    SELECT
        profile_id,
        BOOL_OR(event_data->'event'->'properties'->>'push_id' IS NOT NULL) AS push_channel_available
    FROM raw_events
    WHERE event_type = 'profile-traits-update'
      AND inserted_at > NOW() - INTERVAL '90 days'
    GROUP BY profile_id
),

-- phone_changed_90d: Менялся ли телефон за 90 дней 12
-- (исключаем identification на /checkout это валидация, не изменение)
cte_phone_changed AS (
    SELECT
        profile_id,
        CASE WHEN COUNT(DISTINCT COALESCE(
            event_data->'event'->'properties'->'phone'->>'main',
            event_data->'event'->'properties'->'contact'->'phone'->>'main'
        )) > 1 THEN TRUE ELSE FALSE END AS phone_changed_90d
    FROM raw_events
    WHERE (
        event_type IN ('sign-in', 'profile-update')
        OR (event_type = 'identification' AND event_data->'event'->'context'->'page'->>'path' != '/checkout')
    )
    AND inserted_at > NOW() - INTERVAL '90 days'
    GROUP BY profile_id
),

-- avg_rating_90d: Средняя оценка за 90 дней 13
cte_avg_rating AS (
    SELECT
        profile_id,
        ROUND(AVG(CAST(event_data->'event'->'properties'->>'rate' AS NUMERIC)), 2) AS avg_rating_90d
    FROM raw_events
    WHERE event_type = 'rating'
      AND inserted_at > NOW() - INTERVAL '90 days'
    GROUP BY profile_id
),

-- coupon_dependency_ratio: Доля заказов с купоном за 90 дней 14
cte_coupon_dependency AS (
    SELECT
        profile_id,
        ROUND(
            COUNT(*) FILTER (WHERE event_data->'event'->'properties'->>'coupon' IS NOT NULL)::NUMERIC /
            NULLIF(COUNT(*), 0),
            4
        ) AS coupon_dependency_ratio
    FROM raw_events
    WHERE event_type = 'checkout-started'
      AND inserted_at > NOW() - INTERVAL '90 days'
    GROUP BY profile_id
),

-- avg_cart_value_30d: Средняя сумма корзины за 30 дней 15
cte_avg_cart AS (
    SELECT
        profile_id,
        ROUND(AVG(CAST(event_data->'event'->'properties'->>'total' AS NUMERIC)), 2) AS avg_cart_value_30d
    FROM raw_events
    WHERE event_type = 'cart-changes'
      AND inserted_at > NOW() - INTERVAL '30 days'
    GROUP BY profile_id
),

-- profile_completeness_score: Заполненность профиля 16
-- (телефон 0.4 + имя 0.3 + день рождения 0.3)
cte_profile_completeness AS (
    SELECT
        profile_id,
        ROUND(
            CASE WHEN COALESCE(
                event_data->'event'->'properties'->'phone'->>'main',
                event_data->'event'->'properties'->'contact'->'phone'->>'main'
            ) IS NOT NULL THEN 0.4 ELSE 0 END +
            CASE WHEN COALESCE(
                event_data->'event'->'properties'->'pii'->>'firstname',
                event_data->'event'->'properties'->>'firstname'
            ) IS NOT NULL THEN 0.3 ELSE 0 END +
            CASE WHEN COALESCE(
                event_data->'event'->'properties'->>'birthday',
                event_data->'event'->'properties'->'pii'->>'birthday'
            ) IS NOT NULL THEN 0.3 ELSE 0 END
        , 2) AS profile_completeness_score
    FROM (
        SELECT DISTINCT ON (profile_id) profile_id, event_data
        FROM raw_events
        WHERE event_type IN ('identification', 'profile-update')
        ORDER BY profile_id,
                CASE
                    WHEN event_type = 'identification' AND event_data->'event'->'context'->'page'->>'path' = '/checkout' THEN 1
                    WHEN event_type = 'profile-update' THEN 2
                    ELSE 3
                END,
                inserted_at DESC
    ) latest_profile
),

-- delta_page_views_14d: Дельта просмотров (последние 14 дней vs предыдущие 14) 17
cte_delta_views AS (
    WITH recent AS (
        SELECT profile_id, COUNT(*) AS v14
        FROM raw_events
        WHERE event_type = 'page-view'
          AND inserted_at > NOW() - INTERVAL '14 days'
        GROUP BY profile_id
    ),
    previous AS (
        SELECT profile_id, COUNT(*) AS v_prev
        FROM raw_events
        WHERE event_type = 'page-view'
          AND inserted_at BETWEEN NOW() - INTERVAL '28 days' AND NOW() - INTERVAL '14 days'
        GROUP BY profile_id
    )
    SELECT
        r.profile_id,
        ROUND((r.v14 - COALESCE(p.v_prev, 0))::NUMERIC / NULLIF(p.v_prev, 0), 4) AS delta_page_views_14d
    FROM recent r
    LEFT JOIN previous p USING (profile_id)
),

-- has_unpublished_review: Есть ли негативный отзыв за 90 дней 18
cte_unpublished_review AS (
    SELECT
        profile_id,
        BOOL_OR(CAST(event_data->'event'->'properties'->>'rate' AS INTEGER) <= 2) AS has_unpublished_review
    FROM raw_events
    WHERE event_type = 'rating'
      AND inserted_at > NOW() - INTERVAL '90 days'
      AND event_data->'event'->'properties'->>'rate' IS NOT NULL
    GROUP BY profile_id
),

-- cart_to_checkout_ratio: Соотношение суммы корзины к сумме чекаута 19
cte_cart_checkout_ratio AS (
    WITH cart AS (
        SELECT
            profile_id,
            session_id,
            AVG(CAST(event_data->'event'->'properties'->>'total' AS NUMERIC)) AS avg_cart
        FROM raw_events
        WHERE event_type = 'cart-changes'
          AND inserted_at > NOW() - INTERVAL '30 days'
        GROUP BY profile_id, session_id
    ),
    checkout AS (
        SELECT
            profile_id,
            session_id,
            MAX(CAST(event_data->'event'->'properties'->>'value' AS NUMERIC)) AS chk_val
        FROM raw_events
        WHERE event_type = 'checkout-started'
          AND inserted_at > NOW() - INTERVAL '30 days'
        GROUP BY profile_id, session_id
    )
    SELECT
        c.profile_id,
        ROUND(AVG(c.avg_cart / NULLIF(ch.chk_val, 0)), 2) AS cart_to_checkout_ratio
    FROM cart c
    JOIN checkout ch USING (profile_id, session_id)
    GROUP BY c.profile_id
)

-- 3. Сборка признака
SELECT
    p.profile_id,
    CURRENT_DATE AS snapshot_date,

    -- 1: Временные и транзакционные
    COALESCE(d.days_since_last_order, 999) AS days_since_last_order,
    COALESCE(a.avg_cart_value_30d, 0.0) AS avg_cart_value_30d,
    COALESCE(r.cart_to_checkout_ratio, 1.0) AS cart_to_checkout_ratio,

    -- 2: Отказы
    COALESCE(ab.cart_abandonment_rate_30d, 0.0) AS cart_abandonment_rate_30d,
    COALESCE(cc.checkout_completion_rate, 0.0) AS checkout_completion_rate,
    COALESCE(f.checkout_frustration_index, 0.0) AS checkout_frustration_index,
    COALESCE(ba.cart_browse_abandon_rate_30d, 0.0) AS cart_browse_abandon_rate_30d,

    -- 3: Персональные предложения
    COALESCE(pc.personal_offer_conversion_rate, 0.0) AS personal_offer_conversion_rate,
    COALESCE(pv.personal_views_count_30d, 0) AS personal_views_count_30d,

    -- 4: Маркетинг и коммуникации
    COALESCE(pi.promo_ignore_rate_14d, 0.0) AS promo_ignore_rate_14d,
    COALESCE(mo.message_open_rate_30d, 0.0) AS message_open_rate_30d,
    COALESCE(pa.push_channel_available, FALSE) AS push_channel_available,
    COALESCE(cd.coupon_dependency_ratio, 0.0) AS coupon_dependency_ratio,

    -- 5: Поведенческие и профильные
    COALESCE(e.session_engagement_score, 0.0) AS session_engagement_score,
    COALESCE(ph.phone_changed_90d, FALSE) AS phone_changed_90d,
    COALESCE(ar.avg_rating_90d, 5.0) AS avg_rating_90d,
    COALESCE(cpl.profile_completeness_score, 0.0) AS profile_completeness_score,
    COALESCE(dv.delta_page_views_14d, 0.0) AS delta_page_views_14d,
    COALESCE(ur.has_unpublished_review, FALSE) AS has_unpublished_review,

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
ORDER BY p.profile_id;

-- Индексы для быстрого доступа idx_mv_
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_ml_features_profile ON mv_ml_features (profile_id);
CREATE INDEX IF NOT EXISTS idx_mv_ml_features_snapshot ON mv_ml_features (snapshot_date);

COMMENT ON MATERIALIZED VIEW mv_ml_features IS
    'Feature Store: рассчитывает 24 признака для всех активных пользователей за один проход';