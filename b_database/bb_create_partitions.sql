-- b_database/bb_create_partitions.sql
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
-- Партиции за последние 12 месяцев + 12 месяцев вперёд

DO $$
DECLARE
    start_date DATE := DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '12 months';
    partition_name TEXT;
    part_start DATE;
    part_end DATE;
    i INTEGER;
BEGIN
    FOR i IN 0..23 LOOP -- 24 месяца
        part_start := start_date + (i * INTERVAL '1 month');
        part_end := part_start + INTERVAL '1 month';
        partition_name := 'raw_events_' || TO_CHAR(part_start, 'YYYY_MM');

        EXECUTE FORMAT(
            'CREATE TABLE IF NOT EXISTS %I PARTITION OF raw_events FOR VALUES FROM (%L) TO (%L)',
            partition_name,
            part_start,
            part_end
        );
        
        RAISE NOTICE 'Created: % [% - %)', partition_name, part_start, part_end;
    END LOOP;
END $$;

