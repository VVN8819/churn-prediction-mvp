# a_data_collection/a_run_pipeline.py
"""
a_run_pipeline.py
Главный файл запуска CDP pipeline

Использование:
    python a_run_pipeline.py  # Запустить все шаги
    python a_run_pipeline.py --skip-test                          # Без теста ES
    python a_run_pipeline.py --start 2026-01-01 --end 2026-01-31  # Только январь
"""

import sys
import argparse
from pathlib import Path

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Импортируем функции из модулей
from a_data_collection.ae_test_es_connection import test_es_connection
from a_data_collection.aa_fetch_from_cdp import fetch_from_cdp
from a_data_collection.ab_process_queue import process_queue

def main():
    """Главная функция"""
    
    # Парсим аргументы командной строки
    parser = argparse.ArgumentParser(description='Загрузка событий из ES в PostgreSQL')
    parser.add_argument('--start', type=str, help='Начальная дата (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, help='Конечная дата (YYYY-MM-DD)')
    parser.add_argument('--skip-test', action='store_true', help='Пропустить тест подключения')
    parser.add_argument('--skip-fetch', action='store_true', help='Пропустить загрузку из ES')
    parser.add_argument('--skip-process', action='store_true', help='Пропустить обработку очереди')
    
    args = parser.parse_args()
    
    # Шаг 1: Тест подключения к Elasticsearch CDP
    if not args.skip_test:
        print("\n----- Шаг 1: Тест подключения к ES -----")
        result = test_es_connection()
    
        if not result:
            print("\nОшибка при подключении к ES. Pipeline остановлен.")
            sys.exit(1)
    else:
        print("\n----- Шаг 1: Пропущен (--skip-test) -----")    
        
    # Шаг 2: Получение событий из ES и перемещение в events_queue
    if not args.skip_fetch:
        print("\n----- Шаг 2: Получение событий из CDP -----")
        result = fetch_from_cdp(start_date=args.start, end_date=args.end)
    
        if not result:
            print("\nОшибка при получении событий. Pipeline остановлен.")
            sys.exit(1)
            
    else:
        print("\n----- Шаг 2: Пропущен (--skip-fetch) -----")
        
    # Шаг 3: Обработка events_queue, перемещение в raw_events + profiles
    if not args.skip_process:
        print("\n----- Шаг 3: Обработка очереди -----")
        result = process_queue()
        
        if not result:
            print("\nОшибка при обработке очереди. Pipeline остановлен.")
            sys.exit(1)
    else:
        print("\n----- Шаг 3: Пропущен (--skip-process) -----")
        
    print("\n----- CDP pipeline завершён -----")


if __name__ == "__main__":
    main()
    
    
    