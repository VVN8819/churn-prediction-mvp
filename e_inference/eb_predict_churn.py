# e_inference/eb_predict_churn.py
"""
e_inference/eb_predict_churn.py
Шаг 2 инференс-пайплайна: предсказание оттока и запись результатов в БД

Что делает:
1. Загружает обученную модель из gridsearch_cv_model.joblib
2. Применяет модель к предобработанным данным
3. Рассчитывает вероятность оттока (churn_probability)
4. Определяет уровень риска (risk_level: CRITICAL/HIGH/MEDIUM/LOW)
5. Сохраняет результаты в 4 отдельных CSV файла для бизнес-команд
6. Записывает результаты обратно в таблицу ml_features
"""

import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
import joblib
import warnings
warnings.filterwarnings('ignore')
from sqlalchemy import text

# Настройка путей
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from a_data_collection.ac_config import PG_CONFIG
from ml_config import RISK_THRESHOLDS, MODEL_VERSION, BATCH_SIZE_INFERENCE

# Пути к артефактам
MODEL_DIR = project_root / "d_ml_model" / "models"
MODEL_PATH = MODEL_DIR / "gridsearch_cv_model.joblib"
OUTPUT_DIR = project_root / "e_inference" / "predictions"

def get_db_engine():
    """Создает подключение к базе данных"""
    from sqlalchemy import create_engine
    
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
    return engine

def get_risk_level(probability: float) -> str:
    """
    Определяет уровень риска на основе вероятности оттока
    
    Args:
        probability: Вероятность оттока от 0.0 до 1.0
        
    Returns:
        str: 'CRITICAL', 'HIGH', 'MEDIUM' или 'LOW'
    """
    if probability >= RISK_THRESHOLDS['CRITICAL']:
        return 'CRITICAL'
    elif probability >= RISK_THRESHOLDS['HIGH']:
        return 'HIGH'
    elif probability >= RISK_THRESHOLDS['MEDIUM']:
            return 'MEDIUM'
    else:
        return 'LOW'

def run_prediction(df_raw: pd.DataFrame, df_preprocessed: pd.DataFrame) -> bool:
    """
    Главная функция предсказания и записи результатов в БД
    
    Args:
        df_raw: Сырой DataFrame из БД (содержит profile_id)
        df_preprocessed: Предобработанный DataFrame (готов для модели)
        
    Returns:
        bool: True если успешно, False если ошибка
    """
    print("\n ШАГ 2: Предсказание оттока и обновление БД")
    
    try:
        # 1. Загрузка модели
        print("\n - 1. Загрузка модели")
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"  - Модель не найдена по пути: {MODEL_PATH}")
        
        model = joblib.load(MODEL_PATH)
        print(f"  - Модель загружена: {MODEL_PATH.name}")
        
        # 2. Предсказание
        print("\n - 2. Выполнение предсказаний")
        probabilities = model.predict_proba(df_preprocessed)[:, 1]
        print(f"  - Сделано {len(probabilities)} предсказаний")
        
        # 3. Определение уровня риска
        risk_levels = [get_risk_level(p) for p in probabilities]
        
        # 4. Создание DataFrame с результатами
        df_results = pd.DataFrame({
            'profile_id': df_raw['profile_id'].values[:len(probabilities)],
            'churn_probability': np.round(probabilities, 4),
            'risk_level': risk_levels
        })
        
        # 5. Вывод примеров
        print("\n Результат первых 10 клиентов)")
        print(df_results.head(10).to_string(index=False))
        
        # 6. Статистика по уровням риска
        print("\n Статистика по уровням риска")
        risk_stats = df_results['risk_level'].value_counts()
        for level in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            count = risk_stats.get(level, 0)
            pct = count / len(df_results) * 100
            print(f'  - {level}: {count} клиентов {pct:.1f}%')
        
        # 7. Экспорт в CSV
        print("\n Сохранение результатов в CSV файлы для бизнес-команд")
        OUTPUT_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d")
        
        for level in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            df_level = df_results[df_results['risk_level'] == level]
            filename = f"churn_{level.lower()}_{timestamp}.csv"
            filepath = OUTPUT_DIR / filename
            
            # utf-8-sig
            df_level.to_csv(filepath, index=False, encoding='utf-8')
            print(f"  - Сохранено {len(df_level)} записей в: {filepath.name}")        
        
        # 8. Обновление БД
        print("\n Обновление таблицы ml_features в базе данных")
        engine = get_db_engine()
        
        update_query = f"""
            UPDATE ml_features
            SET churn_probability = :churn_probability,
                risk_level = :risk_level,
                computed_at = NOW(),
                model_version = :model_version
            WHERE profile_id = :profile_id
        """
        
        # Подготовка списка словарей
        params_list = [
            {
                'churn_probability': float(row['churn_probability']),
                'risk_level': row['risk_level'],
                'model_version': MODEL_VERSION,
                'profile_id': str(row['profile_id'])
            }
            for _, row in df_results.iterrows()
        ]
        
        total_records = len(params_list)
        updated_count = 0
        batch_count = 0
        
        print(f"  - Начало обновления (батч по {BATCH_SIZE_INFERENCE} записей)")
        
        with engine.begin() as conn:
            for i in range(0, total_records, BATCH_SIZE_INFERENCE):
                batch = params_list[i : i + BATCH_SIZE_INFERENCE]
                conn.execute(text(update_query), batch)
                
                updated_count += len(batch)
                batch_count += 1
                
                progress = (updated_count / total_records) * 100
                print(f"  - Батч {batch_count}: обновлено {updated_count:,} / {total_records:,} записей ({progress:.1f}%)")
                
        print(f"  - Успешно обновлено {updated_count} записей в ml_features")
        print(f"  - Модель: {MODEL_VERSION}")
        
        return True
        
    except Exception as e:
        print(f"\n Ошибка на шаге 2: {e}")
        import traceback
        traceback.print_exc()
        return False
    

if __name__ == "__main__":
    print("   Для запуска используйте: python e_inference/e_run_pipeline.py")
    




