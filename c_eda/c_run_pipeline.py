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

def main():
    """Главная функция"""
    
    # Шаг 1: Загрузка данных из БД и сохранение в CSV
    print("\nШаг 1: Загрузка данных")
    df = load_save_ml_features()
    
    if df is None:
        print("\nОшибка при загрузке данных. Пайплайн остановлен.")
        sys.exit(1)
    
    # Шаг 2: Первичный анализ данных
    print("\nШаг 2: Первичный анализ")
    result = explore_data()
    
    if result is None:
        print("\nОшибка при анализе данных. Пайплайн остановлен.")
        sys.exit(1)
    
    print("\nEDA пайплайн завершён")
    
if __name__ == "__main__":
    main()
    
    
    