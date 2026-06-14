-- 05_create_maintenance.sql
-- 1. Записываем начало операции в лог
INSERT INTO events_processing_log (batch_id, source, status, started_at)
VALUES (gen_random_uuid(), 'maintenance', 'running', NOW())
RETURNING batch_id AS v_batch_id \gset

-- 2. Обновляем materialized_views через UNIQUE индекс
-- CONCURRENTLY позволяет читать данные во время обновления
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_ml_features;

-- 3. Переносим данные из mv_ml_features (materialized_views) в основную таблицу ml_features
-- UPSERT: если профиль уже есть — обновляем, если нет — добавляем
INSERT INTO ml_features (
    profile_id,
    snapshot_date,
    days_since_last_order,
    cart_abandonment_rate_30d,
    checkout_completion_rate,
    checkout_frustration_index,
    personal_offer_conversion_rate,
    promo_ignore_rate_14d,
    session_engagement_score,
    message_open_rate_30d,
    cart_browse_abandon_rate_30d,
    personal_views_count_30d,
    push_channel_available,
    phone_changed_90d,
    churn_probability,
    risk_level,
    computed_at,
    model_version
)
SELECT
    profile_id,
    snapshot_date,
    days_since_last_order,
    cart_abandonment_rate_30d,
    checkout_completion_rate,
    checkout_frustration_index,
    personal_offer_conversion_rate,
    promo_ignore_rate_14d,
    session_engagement_score,
    message_open_rate_30d,
    cart_browse_abandon_rate_30d,
    personal_views_count_30d,
    push_channel_available,
    phone_changed_90d,
    churn_probability,
    risk_level,
    computed_at,
    model_version
FROM mv_ml_features
ON CONFLICT (profile_id)
DO UPDATE SET
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
    computed_at = NOW();

-- 4. Записываем завершение операции в лог
UPDATE events_processing_log
SET
    events_inserted = (SELECT COUNT(*) FROM ml_features),
    events_fetched = (SELECT COUNT(*) FROM mv_ml_features),
    events_failed = 0,
    status = 'completed',
    completed_at = NOW()
WHERE batch_id = :'v_batch_id';

-- 5. Обновляем статистику для оптимизатора запросов
VACUUM ANALYZE ml_features;
VACUUM ANALYZE mv_ml_features;
VACUUM ANALYZE raw_events;
VACUUM ANALYZE profiles;
VACUUM ANALYZE events_queue;