# c_eda/ce_clean_data.py
"""
ce_clean_data.py
Очистка и подготовка данных для ML-модели

Что делает:
1. Обрабатывает выбросы (логарифмирование)
2. Кодирует категориальные признаки (One-Hot Encoding)
3. Сохраняет чистый DataFrame в CSV
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Импортируем функцию загрузки из CSV
from c_eda.ca_load_data import load_from_csv

# =========== Обработка выбросов (логарифмирование) =======
def handle_outliers(df):
    """
    Обрабатывает выбросы методом логарифмирования
    
    Логарифмируем признаки с большим диапазоном:
    - days_since_last_order: 1-999 → 0.69-6.91
    - avg_cart_value_30d: 0-1080 → 0-6.99
    - avg_copy_reaction_seconds: 0-30 → 0-3.43
    - personal_views_count_30d: 0-1 → 0-0.69
    """
    
    print("\nОбработка выбросов (логарифмирование)")
    
    df_clean = df.copy()
    
    log_columns = [
        'days_since_last_order',
        'avg_cart_value_30d',
        'avg_copy_reaction_seconds',
        'personal_views_count_30d'
    ]
    
    for col in log_columns:
        if col in df_clean.columns:
            df_clean[col] = np.log1p(df_clean[col])
            print(f'- {col}: применено log(1+x)')
            print(f'Было: min={df[col].min():.2f}, max={df[col].max():.2f}')
            print(f'Стало: min={df_clean[col].min():.2f}, max={df_clean[col].max():.2f}')
    
    return df_clean

# ========== Кодирование категориальных признаков ========
def encode_categorical(df):
    """
    Превращает категориальные признаки в числа (One-Hot Encoding)
    """
    
    print("\nКодирование категориальных признаков")
    
    df_clean = df.copy()
    
    # Удаляем бесполезную колонку версии модели, если она есть
    if 'model_version' in df_clean.columns:
        df_clean = df_clean.drop(columns=['model_version'])
        print("   - Удалена колонка 'model_version' (нулевая дисперсия)")
    
    # One-Hot Encoding для reviews_reading_behavior
    if 'reviews_reading_behavior' in df_clean.columns:
        dummies = pd.get_dummies(df_clean['reviews_reading_behavior'], prefix='behavior')
        df_clean = pd.concat([df_clean, dummies], axis=1)
        df_clean = df_clean.drop('reviews_reading_behavior', axis=1)
        print(f'- reviews_reading_behavior {list(dummies.columns)}')
    
    return df_clean

# ============ Главная функция очистки ==========
def clean_data():
    """
    Главная функция: запускает все этапы очистки
    """
    
    print("\n5. Очистка данных")
    
    try:
        # Загружаем данные из CSV (быстрее, чем из БД)
        print(f'Загрузка данных из CSV')
        df = load_from_csv("df_features_raw.csv")
        
        print(f"Исходный размер: {df.shape}")
        
        # 1: Обработка выбросов (логарифмирование)
        df_clean = handle_outliers(df)
        
        # 2: Кодирование категорий
        df_clean = encode_categorical(df_clean)
        
        print(f"\nФинальный размер: {df_clean.shape}")
        
        # Сохраняем очищенные данные
        data_dir = Path(__file__).parent / "data"
        data_dir.mkdir(exist_ok=True)
        
        filepath = data_dir / "df_features_clean.csv"
        df_clean.to_csv(filepath, index=False)
        
        print(f"\nОчищенные данные сохранены: {filepath}")
        
        print(f"\nОчистка данных. Успешно!")
        
        
        return df_clean
        
    except Exception as e:
        print(f"\nОшибка: {e}")
        print("\nПодробности:")
        import traceback
        traceback.print_exc()
        
        return None

if __name__ == "__main__":
    clean_data()
    
    
    
    
    