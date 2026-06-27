-- ПРОВЕРКА ТЕСТОВЫХ ДАННЫХ

-- Проверка количества событий по типам
SELECT
    event_type,
    COUNT(*) AS event_count
FROM raw_events
GROUP BY event_type
ORDER BY event_count DESC;

-- Проверка количества событий по пользователям
SELECT
    profile_id,
    COUNT(*) AS event_count,
    MIN(inserted_at) AS first_event,
    MAX(inserted_at) AS last_event
FROM raw_events
GROUP BY profile_id
ORDER BY event_count DESC;

-- Проверка параллельных событий
SELECT
    event_type,
    inserted_at,
    event_data->'event'->'session'->>'id' AS session_id
FROM raw_events
WHERE event_type IN ('identification', 'checkout-started')
  AND profile_id = 'e9922810-0a85-43c1-8e78-be8343c1f8ed'
ORDER BY inserted_at;