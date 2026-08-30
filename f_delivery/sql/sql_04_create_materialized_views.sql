-- Materialized View для расчета 24 признаков
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
