"""
fb_inference_pipeline.py (Delivery Version)
Оркестратор инференс-пайплайна для заказчика.
Запускает полный цикл: Загрузка из БД - Предобработка - Предсказание - Сохранение в CSV/БД.
"""
import sys
import os
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import joblib
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Локальные импорты вместо проектных
from fa_preprocess_inference import InferencePreprocessor
from ml_config import RISK_THRESHOLDS, MODEL_VERSION, BATCH_SIZE_INFERENCE

# Пути относительно папки delivery
MODEL_DIR = Path(__file__).parent / "churn_model"
MODEL_PATH = MODEL_DIR / "model.skops" # Или model.joblib, model.pkl, в зависимости от экспорта MLflow
OUTPUT_DIR = Path(__file__).parent / "predictions"

def get_db_engine():
    """Создает подключение к БД заказчика через переменные окружения"""
    # Заказчик должен задать свои креды в .env или переменных окружения
    user = os.getenv("DB_USER", "your_db_user")
    password = os.getenv("DB_PASSWORD", "your_db_password")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    database = os.getenv("DB_NAME", "your_db_name")
    sslmode = os.getenv("DB_SSLMODE", "require")
    
    if not all([user, password, host, database]):
        raise ValueError("Не все переменные окружения БД установлены. Проверьте .env")
    
    connection_string = f"postgresql://{user}:{password}@{host}:{port}/{database}?sslmode={sslmode}"
    return create_engine(connection_string)
    
def get_risk_level(probability: float) -> str:
    if probability >= RISK_THRESHOLDS['CRITICAL']: return 'CRITICAL'
    elif probability >= RISK_THRESHOLDS['HIGH']: return 'HIGH'
    elif probability >= RISK_THRESHOLDS['MEDIUM']: return 'MEDIUM'
    else: return 'LOW'
    
def run_prediction(df_raw: pd.DataFrame, df_preprocessed: pd.DataFrame):
    print("\n - Запуск предсказания")
    
    # 1. Загрузка модели
    model = joblib.load(MODEL_PATH)
    
    # 2. Предсказание
    probabilities = model.predict_proba(df_preprocessed)[:, 1]
    risk_levels = [get_risk_level(p) for p in probabilities]
    
    # 3. Формирование результата
    df_results = pd.DataFrame({
        'profile_id': df_raw['profile_id'].values[:len(probabilities)],
        'churn_probability': np.round(probabilities, 4),
        'risk_level': risk_levels
    })
    
    # 4. Экспорт в CSV
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d")
    
    for level in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        df_level = df_results[df_results['risk_level'] == level]
        filepath = OUTPUT_DIR / f"churn_{level.lower()}_{timestamp}.csv"
        df_level.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"   - Сохранено {len(df_level)} записей: {filepath.name}")
        
    # 5. Обновление БД заказчика
    print("\n - Обновление таблицы ml_features в БД")
    engine = get_db_engine()
    update_query = """
        UPDATE ml_features
        SET churn_probability = :churn_probability,
            risk_level = :risk_level,
            computed_at = NOW(),
            model_version = :model_version
        WHERE profile_id = :profile_id
    """
    
    params_list = [
        {
            'churn_probability': float(row['churn_probability']),
            'risk_level': row['risk_level'],
            'model_version': MODEL_VERSION,
            'profile_id': str(row['profile_id'])
        }
        for _, row in df_results.iterrows()
    ]
    
    with engine.begin() as conn:
        for i in range(0, len(params_list), BATCH_SIZE_INFERENCE):
            batch = params_list[i : i + BATCH_SIZE_INFERENCE]
            conn.execute(text(update_query), batch)
            
    print(f"   - Успешно обновлено {len(params_list)} записей в БД.")
    return True
    
def main():
    parser = argparse.ArgumentParser(description='Инференс пайплайн (Delivery)')
    parser.add_argument('--skip-predict', action='store_true', help='Только предобработка')
    args = parser.parse_args()
    
    print("\n - Инференс пайплайн: Предсказание оттока клиентов")
    
    try:
        # Шаг 1: Загрузка из БД
        print("\n - Шаг 1: Загрузка данных из БД")
        engine = get_db_engine()
        query = "SELECT * FROM ml_features WHERE days_since_last_order < 900"
        df_raw = pd.read_sql(query, engine)
        print(f"   Загружено {len(df_raw)} записей")
        
        if len(df_raw) == 0:
            print("   Нет данных для обработки. Завершение.")
            return
            
        # Шаг 2: Предобработка
        print("\n - Шаг 2: Предобработка данных")
        preprocessor = InferencePreprocessor()
        df_preprocessed = preprocessor.transform(df_raw)
        print(f"   Готово {len(df_preprocessed)} записей с {len(df_preprocessed.columns)} признаками")
        
        # Шаг 3: Предсказание
        if not args.skip_predict:
            run_prediction(df_raw, df_preprocessed)
            
        print("\n - Инференс пайплайн завершен успешно!")
        
    except Exception as e:
        print(f"\n - Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
