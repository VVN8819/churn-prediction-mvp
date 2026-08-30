"""
fd_sync_cdp_data.py
Первичная загрузка данных из CDP Elasticsearch в PostgreSQL.
Объединяет fetch + process_queue для первичной синхронизации.
"""
import os
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values
from elasticsearch import Elasticsearch, ElasticsearchWarning
from elasticsearch.helpers import scan
import warnings
from dotenv import load_dotenv

warnings.filterwarnings("ignore", category=ElasticsearchWarning)
load_dotenv()

# Конфигурация
PG_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "sslmode": os.getenv("DB_SSLMODE", "require")
}

ES_HOST = os.getenv("ES_HOST", "")
ES_INDEX_PATTERN = os.getenv("ES_INDEX_PATTERN", "events-*")
ES_VERIFY_CERTS = os.getenv("ES_VERIFY_CERTS", "false").lower() == "true"
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1000"))

EVENT_TYPES = [
    'page-view', 'profile-traits-update', 'identification',
    'product-details-page-view', 'cart-changes', 'checkout-started',
    'cart-delete', 'sign-in', 'profile-update', 'promotion-viewed',
    'promotion-clicked', 'promotion-close', 'message-status',
    'message-opened', 'rating', 'personal-view', 'copy-promocode'
]

def is_valid_uuid(val):
    if not val:
        return False
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, AttributeError):
        return False

def transform_event(hit):
    source = hit['_source']
    event_data = {"event": source}
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
            except:
                inserted_at = datetime.now(timezone.utc)
        else:
            inserted_at = datetime.now(timezone.utc)
    else:
        inserted_at = datetime.now(timezone.utc)
    
    event_data_json = json.dumps(event_data, ensure_ascii=False)
    return (event_id, event_type, profile_id, session_id, event_data_json, inserted_at)

def main():
    print("- Начало первичной синхронизации данных из CDP")
    
    try:
        # Подключение к ES
        print(" - Подключение к Elasticsearch")
        es = Elasticsearch(hosts=[ES_HOST], verify_certs=ES_VERIFY_CERTS)
        if not es.ping():
            print(" - Кластер ES недоступен!")
            return
        
        print(" - ES подключен")
        
        # Подключение к PostgreSQL
        print(" -  Подключение к PostgreSQL")
        conn = psycopg2.connect(**PG_CONFIG)
        conn.autocommit = True
        print(" - PostgreSQL подключен")
        
        # Запрос событий
        print(f"\n - Загрузка событий из индекса {ES_INDEX_PATTERN}")
        query = {"query": {"bool": {"must": [{"terms": {"type": EVENT_TYPES}}]}}}
        
        count_result = es.count(index=ES_INDEX_PATTERN, body=query)
        total_count = count_result['count']
        print(f"  - Найдено событий: {total_count:,}")
        
        if total_count == 0:
            print("  - Нет событий для загрузки.")
            return
        
        # Обработка батчами
        events = scan(es, query=query, index=ES_INDEX_PATTERN, size=BATCH_SIZE, scroll='5m')
        
        total_fetched = 0
        total_inserted = 0
        total_skipped = 0
        batch_count = 0
        current_batch = []
        
        print(f"\n - Обработка батчами по {BATCH_SIZE}")
        
        for hit in events:
            event_data = transform_event(hit)
            current_batch.append(event_data)
            total_fetched += 1
            
            if len(current_batch) >= BATCH_SIZE:
                batch_count += 1
                
                with conn.cursor() as cursor:
                    insert_query = """
                        INSERT INTO events_queue (event_id, event_type, profile_id, session_id, event_data, status)
                        VALUES %s ON CONFLICT (event_id) DO NOTHING
                    """
                    values = [(eid, etype, pid, sid, edata, 'pending') for eid, etype, pid, sid, edata, _ in current_batch]
                    execute_values(cursor, insert_query, values)
                    inserted = cursor.rowcount
                    conn.commit()
                    
                skipped = len(current_batch) - inserted
                total_inserted += inserted
                total_skipped += skipped
                
                progress = (total_fetched / total_count * 100)
                print(f"   Батч {batch_count}: +{inserted} (пропущено {skipped}) | {total_fetched:,}/{total_count:,} ({progress:.1f}%)")
                
                current_batch = []
                
        # Последний батч
        if current_batch:
            batch_count += 1
            with conn.cursor() as cursor:
                insert_query = """
                    INSERT INTO events_queue (event_id, event_type, profile_id, session_id, event_data, status)
                    VALUES %s ON CONFLICT (event_id) DO NOTHING
                """
                values = [(eid, etype, pid, sid, edata, 'pending') for eid, etype, pid, sid, edata, _ in current_batch]
                execute_values(cursor, insert_query, values)
                inserted = cursor.rowcount
                conn.commit()
            
            total_inserted += inserted
            total_skipped += len(current_batch) - inserted
            print(f"   Батч {batch_count} (финальный): +{inserted}")
        
        print(f"\n Итого:")
        print(f"  - Загружено из ES: {total_fetched:,}")
        print(f"  - Вставлено в очередь: {total_inserted:,}")
        print(f"  - Пропущено (дубликаты): {total_skipped:,}")
        
        print("\n Первичная загрузка завершена!")
        print(" - Следующий шаг: Запустите fe_refresh_features.py для расчета признаков.")
        
    except Exception as e:
        print(f" Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
