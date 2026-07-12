#c_eda/c_run_pipeline.py
"""
c_eda/c_run_pipeline.py
Главный файл запуска всего EDA пайплайна

Использование:
    python c_run_pipeline.py # Запустить все шаги
    python c_run_pipeline.py --skip-visualize         # Без визуализации (быстро!)
    python c_run_pipeline.py --skip-load              # Загрузить из CSV (без БД)
    python c_run_pipeline.py --skip-load --skip-visualize  # Самый быстрый запуск
    python c_run_pipeline.py --only-clean             # Только очистка данных
"""

import sys
from pathlib import Path
import argparse

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Импортируем функции из модулей
from c_eda.ca_load_data import load_save_ml_features
from c_eda.cb_explore_data import explore_data
from c_eda.cc_quality_check import run_quality_check
from c_eda.cd_visualize import visualize_data
from c_eda.ce_clean_data import clean_data

# Пути к файлам данных
DATA_DIR = project_root / "c_eda" / "data"
RAW_CSV = DATA_DIR / "df_features_raw.csv"
CLEAN_CSV = DATA_DIR / "df_features_clean.csv"
PLOTS_DIR = project_root / "c_eda" / "plots"

def check_file_exists(file_path: Path, description: str) -> bool:
    """Проверяет существование файла и выводит понятное сообщение"""
    if not file_path.exists():
        print(f"\nОшибка: {description} не найден: {file_path}")
        return False
    print(f"{description}: {file_path}")
    return True

def main():
    """Главная функция"""
    
    # Парсим аргументы командной строки
    parser = argparse.ArgumentParser(
        description='EDA Pipeline: анализ данных для ML-модели',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python c_run_pipeline.py                          # Все шаги
  python c_run_pipeline.py --skip-visualize         # Без визуализации (быстро!)
  python c_run_pipeline.py --skip-load              # Загрузить из CSV (без БД)
  python c_run_pipeline.py --only-clean             # Только очистка данных
        """
    )
    
    parser.add_argument('--skip-load', action='store_true', 
                        help='Пропустить загрузку из БД (использовать существующий CSV)')
    parser.add_argument('--skip-explore', action='store_true', 
                        help='Пропустить первичный анализ')
    parser.add_argument('--skip-quality', action='store_true', 
                        help='Пропустить проверку качества')
    parser.add_argument('--skip-visualize', action='store_true', 
                        help='Пропустить визуализацию (самый долгий шаг!)')
    parser.add_argument('--skip-clean', action='store_true', 
                        help='Пропустить очистку данных')
    parser.add_argument('--only-clean', action='store_true',
                        help='Запустить только очистку данных (все остальные шаги пропущены)')
    
    args = parser.parse_args()
    
    # Обработка режима --only-clean
    if args.only_clean:
        args.skip_load = True
        args.skip_explore = True
        args.skip_quality = True
        args.skip_visualize = True
        # args.skip_clean остаётся False
    
    # Шаг 1: Загрузка данных из БД и сохранение в CSV
    if not args.skip_load:
        print("\n----- Шаг 1: Загрузка данных из БД -----")
        df = load_save_ml_features()
        
        if df is None:
            print("\nОшибка при загрузке данных. Пайплайн остановлен.")
            sys.exit(1)
    else:
        print("\n----- Шаг 1: Пропущен (--skip-load) -----")
        if not check_file_exists(RAW_CSV, "Сырой CSV"):
            print("   Сначала запустите без --skip-load, чтобы создать CSV из БД.")
            sys.exit(1)
    
    # Шаг 2: Первичный анализ данных
    if not args.skip_explore:
        print("\n----- Шаг 2: Первичный анализ -----")
        result = explore_data()
        
        if result is None:
            print("\nОшибка при анализе данных. Пайплайн остановлен.")
            sys.exit(1)
    else:
        print("\n----- Шаг 2: Пропущен (--skip-explore) -----")
    
    # Шаг 3: Проверка качества данных
    if not args.skip_quality:
        print("\n----- Шаг 3: Проверка качества -----")
        result = run_quality_check()
        
        if result is None:
            print("\nОшибка при проверке качества. Пайплайн остановлен.")
            sys.exit(1)
    else:
        print("\n----- Шаг 3: Пропущен (--skip-quality) -----")
        
    # Шаг 4: Визуализация данных
    if not args.skip_visualize:
        print("\n----- Шаг 4: Визуализация данных -----")
        result = visualize_data()
        
        if result is None:
            print("\nОшибка при визуализации. Пайплайн остановлен.")
            sys.exit(1)
    else:
        print("\n----- Шаг 4: Пропущен (--skip-visualize) -----")
        
    # Шаг 5: Очистка данных
    if not args.skip_clean:
        print("\n----- Шаг 5: Очистка данных -----")
        result = clean_data()
        
        if result is None:
            print("\nОшибка при очистке данных. Пайплайн остановлен.")
            sys.exit(1)
    else:
        print("\n----- Шаг 5: Пропущен (--skip-clean) -----")
    
    print("\n----- EDA пайплайн завершён -----")
    
if __name__ == "__main__":
    main()
    
    
    