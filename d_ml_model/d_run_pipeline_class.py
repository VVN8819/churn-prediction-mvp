# d_ml_model/d_run_pipeline_class.py
"""
d_ml_model/d_run_pipeline_class.py
Запуск ML-пайплайна черех class DataPreprocessor

Использование:
    python d_ml_model/d_run_pipeline_class.py --use-cache  # для запуска с кэшом
    python d_ml_model/d_run_pipeline_class.py  # для первого запуска (без кэша)
    python d_ml_model/d_run_pipeline_class.py --use-cache --force-cache  #Принудительно пересоздай кэш
"""
import sys
import argparse
from pathlib import Path

# Настройка путей
# Добавляем корень проекта в системные пути, чтобы Python мог находить модули
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from d_ml_model.db_class_data_preprocessor import DataPreprocessor

def main():
    parser = argparse.ArgumentParser(description='ML Churn Prediction Pipeline')
    parser.add_argument('--skip-correlation', action='store_true')
    parser.add_argument('--use-cache', action='store_true')
    parser.add_argument('--force-cache', action='store_true')
    args = parser.parse_args()
    
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
    
if __name__ == "__main__":
    main()
    