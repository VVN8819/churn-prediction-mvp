-- 02_create_partitions.sql
-- Партиционирование raw_events по месяцам

CREATE OR REPLACE FUNCTION create_monthly_partition(
    table_name TEXT,
    partition_date DATE
) RETURNS VOID AS $$
DECLARE
    partition_name TEXT;
    start_date DATE;
    end_date DATE;
BEGIN
    -- Формируем имя: raw_events_2026_05
    partition_name := table_name || '_' || TO_CHAR(partition_date, 'YYYY_MM');
    
    -- Границы месяца
    start_date := DATE_TRUNC('month', partition_date);
    end_date := start_date + INTERVAL '1 month';
    
    -- Создаём партицию, если ещё не существует
    EXECUTE FORMAT(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
        partition_name,
        table_name,
        start_date,
        end_date
    );
    
    RAISE NOTICE 'Создана партиция: % (% на %)', partition_name, start_date, end_date;
END;
$$ LANGUAGE plpgsql;

-- ============================
-- Партиции на 12 месяцев вперёд

DO $$
DECLARE
    i INTEGER;
    partition_date DATE;
BEGIN
    FOR i IN 0..11 LOOP
        partition_date := DATE_TRUNC('month', CURRENT_DATE + (i * INTERVAL '1 month'));
        PERFORM create_monthly_partition('raw_events', partition_date);
    END LOOP;
END $$;

-- ============================================
-- Триггер: если придут данные за месяц, который мы не предусмотрели

CREATE OR REPLACE FUNCTION ensure_partition_exists()
RETURNS TRIGGER AS $$
DECLARE
    partition_date DATE;
    partition_name TEXT;
BEGIN
    -- месяц нового события
    partition_date := DATE_TRUNC('month', NEW.inserted_at);
    partition_name := 'raw_events_' || TO_CHAR(partition_date, 'YYYY_MM');
    
    -- Проверяем существует ли партиция
    IF NOT EXISTS (
        SELECT 1 FROM pg_tables 
        WHERE tablename = partition_name 
        AND schemaname = 'public'
    ) THEN
        -- Создаём новую партицию
        PERFORM create_monthly_partition('raw_events', partition_date);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Привязываем триггер к таблице raw_events
CREATE TRIGGER trigger_ensure_partition
BEFORE INSERT ON raw_events
FOR EACH ROW
EXECUTE FUNCTION ensure_partition_exists();