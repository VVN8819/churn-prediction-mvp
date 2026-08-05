# e_inference/e_run_pipeline.py
"""
e_inference/e_run_pipeline.py
Оркестратор инференс-пайплайна

Использование:
    python e_inference/e_run_pipeline.py                    # Запустить все шаги
    python e_inference/e_run_pipeline.py --skip-preprocess  # Только предсказание
    python e_inference/e_run_pipeline.py --skip-predict     # Только предобработка
"""

import sys
import argparse
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Настройка путей
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from e_inference.ea_preprocess_inference import preprocess_for_inference

def main():
    """Главная функция оркестратора"""
    
    parser = argparse.ArgumentParser(
        description='Инференс пайплайн: предсказание оттока клиентов',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python e_inference/e_run_pipeline.py                    # Все шаги
  python e_inference/e_run_pipeline.py --skip-preprocess  # Только предсказание
  python e_inference/e_run_pipeline.py --skip-predict     # Только предобработка
        """
    )
    
    parser.add_argument('--skip-preprocess', action='store_true',
                        help='Пропустить предобработку (если данные уже обработаны)')
    parser.add_argument('--skip-predict', action='store_true',
                        help='Пропустить предсказание (только предобработка)')
    
    args = parser.parse_args()
    
    print("\n - Инференс пайплайн: Предсказание оттока клиентов")
    
    # Шаг 1: Предобработка
    if not args.skip_preprocess:
        print("\n ШАГ 1: Предобработка данных")
        
        try:
            # Загружаем данные из БД
            from a_data_collection.ac_config import PG_CONFIG
            from sqlalchemy import create_engine
            import pandas as pd
                
            # Берем настройки из конфига
            user = PG_CONFIG['user']
            password = PG_CONFIG['password']
            host = PG_CONFIG['host']
            port = PG_CONFIG['port']
            database = PG_CONFIG['database']
            sslmode = PG_CONFIG.get('sslmode', 'require')
            sslrootcert = PG_CONFIG.get('sslrootcert', '')
            
            # Формируем строку подключения
            if sslrootcert:
                # С SSL сертификатом
                connection_string = (
                    f"postgresql://{user}:{password}@{host}:{port}/{database}?"
                    f"sslmode={sslmode}&sslrootcert={sslrootcert}"
                )
            else:
                # Без сертификата
                connection_string = (
                    f"postgresql://{user}:{password}@{host}:{port}/{database}?"
                    f"sslmode={sslmode}"
                )
                
            engine = create_engine(connection_string)
            
            query = "SELECT * FROM ml_features WHERE days_since_last_order < 900"
            df_raw = pd.read_sql(query, engine)
            
            df_preprocessed = preprocess_for_inference(df_raw)
            
            if df_preprocessed is None:
                print("\n Ошибка на шаге 1: Предобработка не удалась")
                sys.exit(1)
                
            print("\n- Шаг 1 завершен успешно")
            
        except Exception as e:
            print(f"\n Ошибка на шаге 1: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
    else:
        print("\n- Шаг 1 пропущен (--skip-preprocess)")

if __name__ == "__main__":
    main()


