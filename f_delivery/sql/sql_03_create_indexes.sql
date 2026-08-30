-- Индексы для оптимизации производительности

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
