# a_data_collection/ab_process_queue.py
"""
ab_process_queue.py
Обработка событий из events_queue

Что делает:
1. Выбирает события со статусом 'pending' батчами по 1000
2. Вставляет в raw_events (с партиционированием по месяцам)
3. Обновляет profiles из событий identification/profile-update
4. Помечает события как 'processed'
5. Логирует процесс в events_processing_log
6. Автоматически переподключается при разрыве соединения

Использование:
    python ab_process_queue.py  # Обработать всю очередь
"""

import sys
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from a_data_collection.ac_config import PG_CONFIG, BATCH_SIZE

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

# ============ Выборка событий pending ===========
def select_pending_events(conn, batch_size):
    """
    Выбирает батч событий со статусом 'pending'
    
    Args:
        conn: подключение к PostgreSQL
        batch_size: размер батча
        
    Returns:
        list: список кортежей (id, event_id, event_type, profile_id, session_id, event_data, inserted_at)
    """
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT 
                id,
                event_id,
                event_type,
                profile_id,
                session_id,
                event_data,
                (event_data->'event'->'metadata'->'time'->>'insert')::timestamptz AS inserted_at
            FROM events_queue
            WHERE status = 'pending'
            ORDER BY id
            LIMIT %s
        """, (batch_size,))
        
        return cursor.fetchall()
    
# ============ Вставка в raw_events ===========
def insert_to_raw_events(conn, events):
    """
    Вставляет события в raw_events с защитой от дубликатов (ON CONFLICT DO NOTHING).
    
    Это делает операцию идемпотентной: если событие уже было вставлено 
    (например, после разрыва соединения), оно будет просто пропущено.
    
    Args:
        conn: подключение к PostgreSQL
        events: список событий из events_queue
        
    Returns:
        int: количество вставленных событий (без учета пропущенных дубликатов)
    """
    if not events:
        return 0
        
    with conn.cursor() as cursor:
        insert_query = """
            INSERT INTO raw_events (event_id, event_type, profile_id, session_id, event_data, inserted_at)
            VALUES %s
            ON CONFLICT (event_id, inserted_at) DO NOTHING
        """
        
        # Подготавливаем данные: пропускаем id из events_queue
        values = [
            (
                event_id, event_type, profile_id, session_id,
                json.dumps(event_data) if isinstance(event_data, dict) else event_data,
                inserted_at
            )
            for queue_id, event_id, event_type, profile_id, session_id, event_data, inserted_at in events
        ]
        
        try:
            execute_values(cursor, insert_query, values)
            inserted_count = cursor.rowcount
            conn.commit()
            return inserted_count
        except Exception as e:
            conn.rollback()
            print(f"Ошибка вставки в raw_events: {e}")
            raise

# ============ Извлечение данных для profiles ===========
def extract_profile_data(event_data):
    """
    Извлекает данные пользователя из события identification/profile-update
    
    Ищем в разных местах (для гибкости):
    - event_data->'event'->'profile'->'traits'->>'phone'
    - event_data->'event'->'properties'->>'phone'
    
    Args:
        event_data: JSON события
        
    Returns:
        dict: {'phone': ..., 'firstname': ..., 'birthday': ...}
    """
    if isinstance(event_data, str):
        try:
            event_data = json.loads(event_data)
        except:
            return {}
        
    event = event_data.get('event', {})
    profile = event.get('profile', {})
    traits = profile.get('traits', {})
    properties = event.get('properties', {})
    
    def extract_string(value):
        """
        Извлекает строковое значение из различных форматов
        
        Примеры:
        - "+79991234567" - "+79991234567"
        - {"value": "+79991234567"} - "+79991234567"
        - {"first": "Иван", "last": "Иванов"} - "Иван Иванов"
        - None - None
        """
        if value is None:
            return None
        
        # Если это строка — возвращаем как есть
        if isinstance(value, str):
            return value.strip() if value.strip() else None
        
        # Если это словарь — пытаемся извлечь значение
        if isinstance(value, dict):
            # Пробуем разные ключи
            for key in ['value', 'text', 'name', 'first', 'last']:
                if key in value:
                    val = value[key]
                    if isinstance(val, str) and val.strip():
                        return val.strip()
            
            # Если есть first и last — объединяем
            if 'first' in value and 'last' in value:
                first = value.get('first', '')
                last = value.get('last', '')
                if first or last:
                    return f"{first} {last}".strip()
            
            # Если ничего не нашли — преобразуем в строку
            return str(value)
        
        # Если это число или другой тип — преобразуем в строку
        return str(value) if value else None
    
    def normalize_phone(phone):
        """
        Нормализует номер телефона: убирает префиксы, пробелы, скобки
        
        Примеры:
        - "tel:+79991234567" → "+79991234567"
        - "+7 (999) 123-45-67" → "+79991234567"
        - "89991234567" → "89991234567"
        """
        if not phone:
            return None
        
        # Убираем префиксы tel:, tel=, phone:
        phone = phone.lower()
        for prefix in ['tel:', 'tel=', 'phone:', 'phone=']:
            if phone.startswith(prefix):
                phone = phone[len(prefix):]
        
        # Убираем пробелы, скобки, дефисы
        phone = phone.replace(' ', '').replace('(', '').replace(')', '').replace('-', '')
        
        # Ограничиваем длину до 50 символов
        return phone[:50] if phone else None
    
    # Извлекаем поля (пробуем разные пути)
    phone = normalize_phone(
        extract_string(traits.get('phone')) or 
        extract_string(properties.get('phone')) or 
        extract_string(profile.get('phone'))
    )
    
    firstname = extract_string(
        traits.get('firstname') or 
        traits.get('firstName') or
        traits.get('first_name') or
        traits.get('name') or
        properties.get('firstname') or
        properties.get('firstName')
    )
    
    birthday = extract_string(
        traits.get('birthday') or 
        traits.get('birthDate') or
        traits.get('birth_date') or
        properties.get('birthday')
    )
    
    return {
        'phone': phone,
        'firstname': firstname,
        'birthday': birthday
    }

# ============ Обновление profiles ===========
def update_profiles(conn, events):
    """
    Обновляет справочник profiles из событий identification/profile-update
    Использует batch INSERT через execute_values для скорости
    
    Если в батче несколько событий для одного profile_id, 
    берётся только последнее (по inserted_at) — это и логически правильно.
    
    Args:
        conn: подключение к PostgreSQL
        events: список событий
        
    Returns:
        int: количество обновлённых профилей
    """
    # Фильтруем только нужные типы событий
    profile_events = [
        event for event in events 
        if event[2] in ('identification', 'profile-update') and event[3] is not None
    ]
    
    if not profile_events:
        return 0
        
    # Дедупликация: для каждого profile_id оставляем только последнее событие
    profile_events_sorted = sorted(profile_events, key=lambda e: e[6])
    
    # Собираем данные для батчевой вставки (словарь для дедупликации по profile_id)
    profiles_dict = {}
    
    for queue_id, event_id, event_type, profile_id, session_id, event_data, inserted_at in profile_events_sorted:
        # Извлекаем данные пользователя
        profile_data = extract_profile_data(event_data)
        
        # Если нет данных — пропускаем
        if not any(profile_data.values()):
            continue
        
        profiles_dict[profile_id] = (
            profile_id,
            profile_data['phone'],
            profile_data['firstname'],
            profile_data['birthday'],
            inserted_at
        )
        
    if not profiles_dict:
        return 0
    
    # Преобразуем словарь в список кортежей
    values_list = list(profiles_dict.values())
    
    # Батчевый UPSERT через execute_values
    with conn.cursor() as cursor:
        insert_query = """
            INSERT INTO profiles (profile_id, phone, firstname, birthday, last_seen)
            VALUES %s
            ON CONFLICT (profile_id) DO UPDATE SET
                phone = COALESCE(EXCLUDED.phone, profiles.phone),
                firstname = COALESCE(EXCLUDED.firstname, profiles.firstname),
                birthday = COALESCE(EXCLUDED.birthday, profiles.birthday),
                last_seen = EXCLUDED.last_seen,
                updated_at = NOW()
        """
        try:
            execute_values(cursor, insert_query, values_list)
            conn.commit()
            return len(values_list)
        except Exception as e:
            conn.rollback()
            print(f"Ошибка батчевой вставки profiles: {e}")
            raise

# ============ Пометка как processed ===========
def mark_as_processed(conn, event_ids):
    """
    Помечает события как 'processed'
    
    Args:
        conn: подключение к PostgreSQL
        event_ids: список id событий из events_queue
        
    Returns:
        int: количество помеченных событий
    """
    if not event_ids:
        return 0
    
    with conn.cursor() as cursor:
        cursor.execute("""
            UPDATE events_queue
            SET status = 'processed', processed_at = NOW()
            WHERE id = ANY(%s)
        """, (event_ids,))
        
        updated_count = cursor.rowcount
        conn.commit()
        
        return updated_count

# ======== Логирование ========
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

# ========= Главная функция =========
def process_queue():
    """
    Главная функция: обрабатывает всю очередь событий
    """
    print("\nОбработка очередей событий")
    
    conn = None
    batch_id = None
    max_retries = 5  # Максимальное количество попыток переподключения
    
    total_fetched = 0
    total_inserted_raw = 0
    total_updated_profiles = 0
    total_marked_processed = 0
    batch_count = 0
        
    try:
        # 1. Подключение
        conn = connect_to_postgres()
        
        # 2. Проверяем количество pending событий
        print("\n2. Проверка очереди")
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM events_queue WHERE status = 'pending'")
            pending_count = cursor.fetchone()[0]
            print(f"Событий в очереди (pending): {pending_count:,}")
        
        if pending_count == 0:
            print("\nОчередь пуста")
            return True
        
        # 3. Создаём запись в логе
        print("\n3. Создание записи в events_processing_log")
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO events_processing_log (source, status)
                VALUES ('queue_processing', 'running')
                RETURNING batch_id
            """)
            batch_id = cursor.fetchone()[0]
            conn.commit()
        print(f"Batch ID: {batch_id}")
        
        # 4. Обрабатываем батчами
        print(f"\n4. Начало обработки (батч по {BATCH_SIZE})")
        
        retry_count = 0
        
        while True:
            try:
                # Выбираем батч
                print(f"\n  Выборка батча", end='', flush=True)
                events = select_pending_events(conn, BATCH_SIZE)
                print(f" получено {len(events)} событий", flush=True)
                
                if not events:
                    print("\n - Очередь полностью обработана")
                    break
                
                batch_count += 1
                current_batch_size = len(events)
                total_fetched += current_batch_size
                retry_count = 0  # Сбрасываем счетчик retry при успешной операции
                
                # Получаем id событий для пометки
                event_ids = [event[0] for event in events]
                
                # Вставляем в raw_events
                print(f"  Батч {batch_count}: вставка в raw_events", end='', flush=True)
                inserted_raw = insert_to_raw_events(conn, events)
                total_inserted_raw += inserted_raw
                print(f" +{inserted_raw:,}", flush=True)
                
                # Обновляем profiles
                print(f"  Батч {batch_count}: обновление profiles...", end='', flush=True)
                updated_profiles = update_profiles(conn, events)
                total_updated_profiles += updated_profiles
                print(f" +{updated_profiles:,}", flush=True)
                
                # Помечаем как processed
                print(f"  Батч {batch_count}: пометка processed...", end='', flush=True)
                marked_processed = mark_as_processed(conn, event_ids)
                total_marked_processed += marked_processed
                print(f" +{marked_processed:,}", flush=True)
                
                # Логируем прогресс
                progress = (total_fetched / pending_count * 100) if pending_count > 0 else 0
                print(f" - Батч {batch_count} завершен: {current_batch_size:,} событий | "
                      f"Всего: {total_fetched:,}/{pending_count:,} ({progress:.1f}%)", flush=True)
                
            except psycopg2.OperationalError as e:
                # Разрыв соединения - пытаемся переподключиться
                retry_count += 1
                print(f"\n -  Разрыв соединения (попытка {retry_count}/{max_retries}): {e}", flush=True)
                
                if retry_count >= max_retries:
                    print(f" -  Превышено максимальное количество попыток ({max_retries})", flush=True)
                    raise
                
                print(" Ждем 3 секунды перед переподключением к PostgreSQL", flush=True)
                time.sleep(3)  # Ждем 2 секунды перед переподключением
                
                try:
                    if conn:
                        conn.close()
                except:
                    pass
                
                print(" - Переподключение к PostgreSQL", flush=True)
                conn = connect_to_postgres()
                print(" - Переподключение успешно", flush=True)
                
                continue
            
        # 5. Логируем результат
        print(f"\n5. Запись статистики в events_processing_log")
        log_processing(
            conn, batch_id,
            events_fetched=total_fetched,
            events_inserted=total_inserted_raw,
            events_failed=0,
            status='completed'
        )
        
        # 6. Итоговый отчёт
        print("\nИтого:")
        print(f"Всего обработано: {total_fetched:>12,}")
        print(f"Вставлено в raw_events: {total_inserted_raw:>12,}")
        print(f"Обновлено profiles: {total_updated_profiles:>12,}")
        print(f"Помечено processed: {total_marked_processed:>12,}")
        print(f"Батчей обработано: {batch_count:>12,}")
        
        print("\nОбработка очереди завершена успешно")
        
        return True
        
    except Exception as e:
        print(f"\nОшибка: {e}")
        
        if conn and batch_id:
            try:
                log_processing(
                    conn, batch_id,
                    events_fetched=total_fetched if 'total_fetched' in locals() else 0,
                    events_inserted=total_inserted_raw if 'total_inserted_raw' in locals() else 0,
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
            try:
                conn.close()
                print("\n   Подключение к PostgreSQL закрыто")
            except:
                pass

if __name__ == "__main__":
    process_queue()
    
    
