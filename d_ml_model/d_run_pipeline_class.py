# d_ml_model/d_run_pipeline_class.py
"""
d_ml_model/d_run_pipeline_class.py
Запуск ML-пайплайна через class DataPreprocessor
Проверка гипотез через class HypothesisTester

Использование:
    python d_ml_model/d_run_pipeline_class.py --use-cache  # для запуска с кэшом
    python d_ml_model/d_run_pipeline_class.py  # для первого запуска (без кэша)
    python d_ml_model/d_run_pipeline_class.py --use-cache --force-cache  #Принудительно пересоздай кэш
    python d_ml_model/d_run_pipeline_class.py --skip-correlation
    python d_ml_model/d_run_pipeline_class.py --skip-hypothesis-1
    python d_ml_model/d_run_pipeline_class.py --skip-all-hypotheses
"""
import sys
import argparse
import pandas as pd
from pathlib import Path

# Настройка путей
# Добавляем корень проекта в системные пути, чтобы Python мог находить модули
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from d_ml_model.db_class_data_preprocessor import DataPreprocessor
from d_ml_model.di_hypothesis_test import HypothesisTester

def main():
    parser = argparse.ArgumentParser(
        description='ML Churn Prediction Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python d_ml_model/d_run_pipeline_class.py --use-cache
  python d_ml_model/d_run_pipeline_class.py --skip-correlation
  python d_ml_model/d_run_pipeline_class.py --skip-hypothesis-1
  python d_ml_model/d_run_pipeline_class.py --skip-all-hypotheses
  python d_ml_model/d_run_pipeline_class.py --use-cache --force-cache
        """
    )
    parser.add_argument('--skip-correlation', action='store_true',
                        help='Пропустить базовый анализ корреляции')
    parser.add_argument('--use-cache', action='store_true',
                        help='Использовать кэш подготовленных данных')
    parser.add_argument('--force-cache', action='store_true',
                        help='Принудительно пересоздать кэш')
    
    # Аргументы для гипотез
    parser.add_argument('--skip-hypothesis-1', action='store_true',
                        help='Пропустить тестирование Гипотезы 1')
    parser.add_argument('--skip-all-hypotheses', action='store_true',
                        help='Пропустить все гипотезы')
    
    args = parser.parse_args()
    
    # ======= ШАГ 1: Подготовка данных ====
    preprocessor = DataPreprocessor(
        use_cache=args.use_cache,
        force_cache=args.force_cache,
        skip_correlation=args.skip_correlation
    )
    
    data = preprocessor.prepare()
    
    print(f"\n X_train: {data['X_train_scaled'].shape}")
    print(f" X_test:  {data['X_test_scaled'].shape}")
    print(f" y_train: {data['y_train'].shape[0]} значений")
    print(f" y_test:  {data['y_test'].shape[0]} значений")
    print(f" Признаков: {len(data['feature_names'])}")
    
    # ========== ШАГ 2: Тестирование гипотез ==========
    # Гипотезы запускаем только если не используем кэш 
    # (или если данные свежие)
    if not args.use_cache or args.force_cache:
        # Собираем список гипотез для пропуска
        skip_hypotheses = []
        if args.skip_all_hypotheses:
            skip_hypotheses = ['hypothesis_1']
        else:
            if args.skip_hypothesis_1:
                skip_hypotheses.append('hypothesis_1')
                
        # Загружаем данные для тестирования гипотез
        from ml_config import MAX_DAYS_SINCE_ORDER
        
        print("\n- Запуск тестирования гипотез")
        
        # Читаем CSV для гипотез (нужен исходный DataFrame)
        df_for_hypotheses = pd.read_csv(preprocessor.clean_csv)
        
        # Фильтрация "холодных" пользователей (как в DataPreprocessor)
        df_for_hypotheses = df_for_hypotheses[
            df_for_hypotheses['days_since_last_order'] < MAX_DAYS_SINCE_ORDER
        ].copy()
        
        # Перевод bool в int
        bool_cols = df_for_hypotheses.select_dtypes(include=['bool']).columns
        if len(bool_cols) > 0:
            df_for_hypotheses[bool_cols] = df_for_hypotheses[bool_cols].astype(int)
        
        # Запускаем тестирование гипотез
        tester = HypothesisTester(skip_hypotheses=skip_hypotheses)
        tester.run_all(df_for_hypotheses)
    else:
        print("\n-  Тестирование гипотез пропущено (используется кэш)")
        print("   Для запуска гипотез используйте: python d_ml_model/d_run_pipeline_class.py --force-cache")
  
if __name__ == "__main__":
    main()
    