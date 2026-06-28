#c_eda/c_run_pipeline.py
"""
c_eda/c_run_pipeline.py
Главный файл запуска всего EDA пайплайна

Использование:
    python c_run_pipeline.py # Запустить все шаги
"""

import sys
from pathlib import Path

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Импортируем функции из модулей
from c_eda.ca_load_data import load_save_ml_features
from c_eda.cb_explore_data import explore_data
from c_eda.cc_quality_check import run_quality_check
from c_eda.cd_visualize import visualize_data

def main():
    """Главная функция"""
    
    # Шаг 1: Загрузка данных из БД и сохранение в CSV
    print("\n----- Шаг 1: Загрузка данных -----")
    df = load_save_ml_features()
    
    if df is None:
        print("\nОшибка при загрузке данных. Пайплайн остановлен.")
        sys.exit(1)
    
    # Шаг 2: Первичный анализ данных
    print("\n----- Шаг 2: Первичный анализ -----")
    result = explore_data()
    
    if result is None:
        print("\nОшибка при анализе данных. Пайплайн остановлен.")
        sys.exit(1)
    
    # Шаг 3: Проверка качества данных
    print("\n----- Шаг 3: Проверка качества -----")
    result = run_quality_check()
    
    if result is None:
        print("\nОшибка при проверке качества. Пайплайн остановлен.")
        sys.exit(1)
        
    # Шаг 4: Визуализация данных
    print("\n----- Шаг 4: Визуализация данных -----")
    result = visualize_data()
    
    if result is None:
        print("\nОшибка при при визуализации. Пайплайн остановлен.")
        sys.exit(1)
    
    print("\nEDA пайплайн завершён")
    
if __name__ == "__main__":
    main()
    
    
    