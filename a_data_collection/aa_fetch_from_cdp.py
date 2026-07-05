# a_data_collection/aa_fetch_from_cdp.py
"""
aa_fetch_from_cdp.py
Получение событий из Elasticsearch CDP и вставка в events_queue

Что делает:
1. Подключается к ES и PostgreSQL
2. Забирает события нужных типов через Scroll API
3. Преобразует структуру (добавляет обёртку "event")
4. Вставляет в events_queue (без дубликатов)
5. Логирует процесс в events_processing_log

Использование:
    python aa_fetch_from_cdp.py # За весь период (с начала года)
    python aa_fetch_from_cdp.py --start 2026-01-01 --end 2026-01-31 # Только январь
"""

import sys
import json
import argparse
import uuid
from datetime import datetime, timezone
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from a_data_collection.ac_config import (
    PG_CONFIG, ES_CONFIG, BATCH_SIZE, ES_INDEX_PATTERN, EVENT_TYPES
)

# ======== Подключение к PostgreSQL ========
def connect_to_postgres():
    """Создаёт подключение к PostgreSQL"""
    print("\n1. Подключение к PostgreSQL")
    
    try:
        conn = psycopg2.connect(**PG_CONFIG)
        print("PostgreSQL подключён")
        return conn
    except Exception as e:
        print(f"Ошибка подключения к PostgreSQL: {e}")
        raise

# ========= Подключение к Elasticsearch CDP =====
def connect_to_elasticsearch():
    """Создаёт подключение к CDP"""
    print("\n2. Подключение к CDP")
    
    try:  
        from elasticsearch import Elasticsearch, ElasticsearchWarning
        import warnings
        
        # Подавляем предупреждения о безопасности (CDP внутри корпоративной сети)
        warnings.filterwarnings("ignore", category=ElasticsearchWarning)
        
        # Создаём подключение
        es = Elasticsearch(
            hosts=ES_CONFIG['host'],
            verify_certs=ES_CONFIG['verify_certs']
        )
        
        # Проверяем, что кластер доступен
        if not es.ping():
            print("\nКластер недоступен!")
            print("\nВозможные причины:")
            print(" 1. OpenVPN не подключён")
            print(" 2. Хост ES_HOST неправильный")
            print(" 3. Elasticsearch не запущен")
            return False
        
        print("Кластер доступен!")
        return es

    except Exception as e:
        print(f"Ошибка подключения к CDP: {e}")
        raise

# ========== Получение событий из ES через Scroll API ========
def fetch_events_from_es(es, start_date=None, end_date=None):
    """
    Получает события из ES через Scroll API
    
    Args:
        es: Elasticsearch client
        start_date: начальная дата (YYYY-MM-DD) или None для всего периода
        end_date: конечная дата (YYYY-MM-DD) или None для всего периода
        
    Returns:
        generator: генератор событий
    """
    from elasticsearch.helpers import scan
    
    print(f"\nЗапрос событий из ES CDP")
    print(f"Индекс: {ES_INDEX_PATTERN}")
    print(f"Количество событий: {len(EVENT_TYPES)}")
    
    if start_date:
        print(f"\nПериод загрузки: {start_date}", end="")
        if end_date:
            print(f" до {end_date}")
        else:
            print(f" по сейчас")
    else:
        print(f"\nПериод загрузки: весь")
        
    # Формируем query
    must_clauses = [
        {"terms":{"type":EVENT_TYPES}}
    ]
    
    # Добавляем фильтр по датам, если указаны
    if start_date or end_date:
        date_range = {}
        if start_date:
            date_range["gte"] = f"{start_date}T00:00:00"
        if end_date:
            date_range["lte"] = f"{end_date}T23:59:59"
        
        must_clauses.append({
            "range": {
                "metadata.time.insert": date_range
            }
        })
        
    query = {
        "query": {
            "bool": {
                "must": must_clauses
            }
        }
    }
    
    # Сначала считаем количество событий
    count_result = es.count(index=ES_INDEX_PATTERN, body=query)
    total_count = count_result['count']
    print(f"\nНайдено событий для загрузки: {total_count:,}")
    
    if total_count == 0:
        print("\nНет событий для загрузки!")
        return iter([])
    
    # Используем scan() для эффективной пагинации
    events = scan(
        es,
        query=query,
        index=ES_INDEX_PATTERN,
        size=BATCH_SIZE,
        scroll='5m',
        preserve_order=True
    )
    
    return events, total_count

# ============ Валидация UUID ==========
def is_valid_uuid(val):
    """
    Проверяет, является ли значение валидным UUID
    
    Примеры:
    - "5adcfe0a-3bfb-498b-97cb-33b49bccd0bd" → True (валидный UUID)
    - "shd-68c2a925-b804-a967-3ac5-6e19a8e633b9" → False (префикс shd-)
    - "undefined" → False (строка)
    - None → False
    - "" → False
    
    Args:
        val: значение для проверки
        
    Returns:
        bool: True если валидный UUID, False если нет
    """
    if not val:
        return False
    
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, AttributeError):
        return False

# ============ Преобразование структуры события ==========   
def transform_event(hit):
    """
    Преобразует структуру события из CDP в формат для БД
    
    CDP:   {id, type, properties, ...}
    БД:    {"event": {id, type, properties, ...}}
    """
    source = hit['_source']
    
    # Оборачиваем в {"event": {...}}
    event_data = {"event": source}
    
    # Извлекаем ключевые поля
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
        except Exception as e:
            print(f"Ошибка парсинга даты {inserted_at}: {e}")
            inserted_at = datetime.now(timezone.utc)
    else:
        inserted_at = datetime.now(timezone.utc)
    
    event_data_json = json.dumps(event_data, ensure_ascii=False)
    
    return (event_id, event_type, profile_id, session_id, event_data_json, inserted_at)
    
def insert_to_events_queue(conn, events_data):
    """
    Вставляет события в events_queue с защитой от дубликатов
    """
    inserted_count = 0
    
    with conn.cursor() as cursor:
        insert_query = """
            INSERT INTO events_queue (event_id, event_type, profile_id, session_id, event_data, status)
            VALUES %s
            ON CONFLICT (event_id) DO NOTHING
        """
        
        values = [
            (event_id, event_type, profile_id, session_id, event_data, 'pending')
            for event_id, event_type, profile_id, session_id, event_data, inserted_at in events_data
        ]
        
        try:
            execute_values(cursor, insert_query, values)
            inserted_count = cursor.rowcount
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Ошибка вставки: {e}")
            raise
    
    skipped_count = len(events_data) - inserted_count
    
    return inserted_count, skipped_count
        
# ============ Логирование ==========
def log_processing(conn, batch_id, events_fetched, events_inserted, events_failed, status='completed'):
    """Записывает статистику обработки в events_processing_log"""
    
    with conn.cursor() as cursor:
        cursor.execute("""
            UPDATE events_processing_log
            SET events_fetched = %s,
                events_inserted = %s,
                events_failed = %s,
                status = %s,
                completed_at = NOW()
            WHERE batch_id = %s
        """, (events_fetched, events_inserted, events_failed, status, batch_id))
        conn.commit()
    
# ======== Очистка старых событий =======
def cleanup_old_processed(conn):
    """Удаляет старые обработанные события (> 6 месяцев)"""
    
    print("\nОчистка старых обработанных событий")
    
    with conn.cursor() as cursor:
        cursor.execute("""
            DELETE FROM events_queue
            WHERE status = 'processed'
            AND processed_at < NOW() - INTERVAL '6 months'
        """)
        deleted_count = cursor.rowcount
        conn.commit()
        
    print(f"Удалено {deleted_count} старых событий")
    return deleted_count

# ============ Главная функция ==========
def fetch_from_cdp(start_date=None, end_date=None):
    """
    Главная функция: получает события из CDP и вставляет в events_queue
    
    Args:
        start_date: начальная дата (YYYY-MM-DD) или None
        end_date: конечная дата (YYYY-MM-DD) или None
    """
    print(f'\n------ Получение событий из CDP ------')
    
    if start_date:
        print(f"\nПериод загрузки: {start_date}", end="")
        if end_date:
            print(f" до {end_date}")
        else:
            print(f" по сейчас")
    else:
        print(f"\nПериод загрузки: весь")
        
    conn = None
    batch_id = None
    
    try:
        # 1. Подключение
        conn = connect_to_postgres()
        es = connect_to_elasticsearch()
        
        # 2. Создаём запись в логе
        print("\nСоздание записи в events_processing_log...")
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO events_processing_log (source, status)
                VALUES ('elasticsearch', 'running')
                RETURNING batch_id
            """)
            batch_id = cursor.fetchone()[0]
            conn.commit()
        print(f"Batch ID: {batch_id}")
        
        # 3. Получаем события из ES
        result = fetch_events_from_es(es, start_date, end_date)
        
        # Проверяем, есть ли события
        if isinstance(result, tuple):
            events_generator, total_expected = result
        else:
            events_generator = result
            total_expected = 0
        
        if total_expected == 0:
            print("\nНет событий для загрузки. Завершаем.")
            log_processing(conn, batch_id, 0, 0, 0, 'completed')
            return True
        
        # 4. Обрабатываем батчами
        print(f"\nНачало обработки событий (батч по {BATCH_SIZE})...")
        
        total_fetched = 0
        total_inserted = 0
        total_skipped = 0
        batch_count = 0
        current_batch = []
        
        for hit in events_generator:
            event_data = transform_event(hit)
            current_batch.append(event_data)
            total_fetched += 1
            
            # Когда батч заполнен — вставляем
            if len(current_batch) >= BATCH_SIZE:
                batch_count += 1
                inserted, skipped = insert_to_events_queue(conn, current_batch)
                total_inserted += inserted
                total_skipped += skipped
                
                progress = (total_fetched / total_expected * 100) if total_expected > 0 else 0
                print(f"Батч {batch_count}: +{inserted} (пропущено {skipped}) | Всего: {total_fetched:,}/{total_expected:,} ({progress:.1f}%)")
                
                current_batch = []
                
        # 5. Вставляем последний батч
        if current_batch:
            batch_count += 1
            inserted, skipped = insert_to_events_queue(conn, current_batch)
            total_inserted += inserted
            total_skipped += skipped
            print(f"Батч {batch_count} (финальный): +{inserted} (пропущено {skipped})")
            
        # 6. Логируем результат
        print(f"\nЗапись статистики в events_processing_log")
        log_processing(
            conn, batch_id,
            events_fetched=total_fetched,
            events_inserted=total_inserted,
            events_failed=total_skipped,
            status='completed'
        )
        
        # 7. Очистка старых событий
        deleted = cleanup_old_processed(conn)
        
        # 8. Итоговый отчёт
        print("\nИтого:")
        print(f"Всего получено из ES: {total_fetched:>10,}")
        print(f"Вставлено в events_queue: {total_inserted:>10,}")
        print(f"Пропущено (дубликаты): {total_skipped:>10,}")
        print(f"Удалено старых: {deleted:>10,}")
        print(f"Батчей обработано: {batch_count:>10,}")
        
        print("\nПолучение событий из CDP завершено успешно!")
        
        return True
        
    except Exception as e:
        print(f"\nОшибка: {e}")
        
        if conn and batch_id:
            try:
                log_processing(
                    conn, batch_id,
                    events_fetched=0,
                    events_inserted=0,
                    events_failed=0,
                    status='failed'
                )
            except:
                pass
        
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if conn:
            conn.close()
            print("\n   Подключение к PostgreSQL закрыто")
        
if __name__ == "__main__":
    # Парсим аргументы командной строки
    parser = argparse.ArgumentParser(description='Загрузка событий из ES в PostgreSQL')
    parser.add_argument('--start', type=str, help='Начальная дата (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, help='Конечная дата (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    fetch_from_cdp(start_date=args.start, end_date=args.end)
    
    
