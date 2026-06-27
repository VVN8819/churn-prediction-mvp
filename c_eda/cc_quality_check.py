# c_eda/cc_quality_check.py
"""
cc_quality_check.py
Проверка качества данных (Data Quality Check)

Что делает:
1. Проверяет Accuracy — правильные ли диапазоны значений
2. Ищет выбросы методом IQR (межквартильный размах)
3. Ищет выбросы методом Z-score (стандартное отклонение)
4. Проверяет Consistency — логическую согласованность
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

# ============ Проверка Accuracy ==========
def check_accuracy(df):
    """
    Проверяет, что значения признаков в правильных диапазонах
    
    Например:
    - rates должны быть от 0 до 1
    - ratings должны быть от 1 до 5
    - days_since_last_order должен быть >= 0
    """
    
    print('\nПроверка Accuracy')
    
    problems = []
    
    # 1. Проверяем rates (должны быть от 0 до 1)
    rate_columns = [
        'cart_abandonment_rate_30d',
        'checkout_completion_rate',
        'personal_offer_conversion_rate',
        'promo_ignore_rate_14d',
        'message_open_rate_30d',
        'coupon_dependency_ratio',
        'profile_completeness_score',
        'promo_interest_rate',
        'cart_browse_abandon_rate_30d',
        'cart_to_checkout_ratio'
    ]
    
    print('\nПроверяем rates (должны быть от 0 до 1):')
    for col in rate_columns:
        if col in df.columns:
            invalid = df[(df[col] < 0) | (df[col] > 1)]
            if len(invalid) > 0:
              problems.append(f"{col}: {len(invalid)} значений вне диапазона [0, 1]")
              print(f"{col}: {len(invalid)} значений вне диапазона")
            else:
                print(f"{col}: всё в порядке")
                
    # 2. Проверяем avg_rating (должен быть от 1 до 5)
    print("\nПроверка avg_rating_90d (должен быть от 1 до 5):")
    if "avg_rating_90d" in df.columns:
            invalid = df[(df["avg_rating_90d"] < 1) | (df["avg_rating_90d"] > 5)]
            if len(invalid) > 0:
                problems.append(f"avg_rating_90d: {len(invalid)} значений вне диапазона [1, 5]")
                print(f"Найдено {len(invalid)} значений вне диапазона")
            else:
                print(f"Всё в порядке")
    
    # 3. Проверяем days_since_last_order (должен быть >= 0)
    print("\nПроверка days_since_last_order (должен быть >= 0):")
    if "days_since_last_order" in df.columns:
        invalid = df[(df["days_since_last_order"]) < 0]
        if len(invalid) > 0:
            problems.append(f"days_since_last_order: {len(invalid)} отрицательных значений")
            print(f"Найдено {len(invalid)} отрицательных значений")
        else:
            print(f"Всё в порядке")
       
    # 4. Проверяем reviews_reading_behavior (должен быть из списка)
    print("\nПроверка reviews_reading_behavior (должен быть из списка):")
    if "reviews_reading_behavior" in df.columns:
        valid_values = ['researcher', 'active_reviewer', 'impulsive_buyer', 'casual_browser']
        invalid = df[~df["reviews_reading_behavior"].isin(valid_values)]
        if len(invalid) > 0:
            problems.append(f"reviews_reading_behavior: {len(invalid)} невалидных значений")
            print(f"Найдено {len(invalid)} невалидных значений")
        else:
            print(f"Всё в порядке")
    
    print('\nИтог:')
    if len(problems) == 0:
        print('Все проверки пройдены!')
    else:
        print(f'Найдено {len(problems)} проблем:')
        for problem in problems:
            print(f'{problem}')
            
    return problems
        
# ============ Поиск выбросов методом IQR ==========
def find_outliers_iqr(df, numerical_cols):
    """
    Ищет выбросы методом IQR (Interquartile Range)
    
    Как работает:
    - Находим Q1 (25-й процентиль) и Q3 (75-й процентиль)
    - IQR = Q3 - Q1 (межквартильный размах)
    - Границы: [Q1 - 1.5*IQR, Q3 + 1.5*IQR]
    - Всё, что за границами — выбросы
    """
    
    print("\nПоиск выбросов методом IQR")
    
    # Исключаем служебные колонки
    service_cols = ['profile_id', 'snapshot_date', 'computed_at', 
                    'churn_probability', 'risk_level']
    feature_cols = [c for c in numerical_cols if c not in service_cols]
    
    outliers_summary = {}
    
    for col in feature_cols:
        # Считаем Q1 и Q3
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        
        # Считаем границы
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        # Ищем выбросы
        outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
        if len(outliers) > 0:
            outliers_summary[col] = {
                'count': len(outliers),
                'percent': round(len(outliers) / len(df) * 100, 1),
                'lower': round(lower_bound, 2),
                'upper': round(upper_bound, 2),
                'values': outliers[col].tolist()
            }
        
    # Выводим результаты
    if len(outliers_summary) == 0:
        print("\nВыбросов не найдено (IQR)!")
    else:
        print(f"\nНайдены выбросы в {len(outliers_summary)} признаках (IQR):")
        for col, info in outliers_summary.items():
            print(f"\n{col}:")
            print(f"Количество: {info['count']} ({info['percent']}%)")
            print(f"Границы: [{info['lower']}, {info['upper']}]")
            print(f"Значения: {info['values']}")
    
    return outliers_summary

# ============= Поиск выбросов методом Z-score =============
def find_outliers_zscore(df, numerical_cols, threshold=2):
    """
    Ищет выбросы методом Z-score
    
    Как работает:
    - Z-score = (значение - среднее) / стандартное отклонение
    - Если |Z-score| > threshold (обычно 2 или 3) — это выброс
    """
    
    print("\nПоиск выбросов методом Z-score")

    # Исключаем служебные колонки
    service_cols = ['profile_id', 'snapshot_date', 'computed_at', 
                    'churn_probability', 'risk_level']
    feature_cols = [c for c in numerical_cols if c not in service_cols]
    
    outliers_summary = {}
      
    for col in feature_cols:
        # Считаем среднее и стандартное отклонение
        mean = df[col].mean()
        std = df[col].std()
        
        # Пропускаем, если std = 0 (все значения одинаковые)
        if std == 0:
            continue
        
        # Считаем Z-score для каждого значения
        z_scores = np.abs((df[col] - mean) / std)
        
        # Ищем выбросы
        outliers = df[z_scores > threshold]
        
        if len(outliers) > 0:
            outliers_summary[col] = {
                'count': len(outliers),
                'percent': round(len(outliers) / len(df) * 100, 1),
                'values': outliers[col].tolist()
            }
            
    # Выводим результаты
    if len(outliers_summary) == 0:
        print("\nВыбросов не найдено (Z-score)!")
    else:
        print(f"\nНайдены выбросы в {len(outliers_summary)} признаках (Z-score):")
        for col, info in outliers_summary.items():
            print(f"\n{col}:")
            print(f"Количество: {info['count']} ({info['percent']}%)")
            print(f"Значения: {info['values']}")
    
    return outliers_summary

# запускает все проверки качества
def run_quality_check():
    """Главная функция: запускает все проверки качества"""
    
    print("\n3. Проверка качества")
    
    try:
        # Загружаем данные из CSV (быстрее, чем из БД)
        print(f'Загрузка данных из CSV')
        df = load_from_csv("df_features_raw.csv")
        
        # Определяем числовые колонки
        numerical_cols = df.select_dtypes(include=['number']).columns.to_list()
        
        # Запускаем все проверки
        accuracy_problems = check_accuracy(df)
        outliers_iqr = find_outliers_iqr(df, numerical_cols)
        outliers_zscore = find_outliers_zscore(df, numerical_cols, threshold=2)
        #consistency_problems = check_consistency(df)
        
        # Итоговый отчёт
        print(f'\nИтоговый отчёт проверки качества')
        print(f'\nAccuracy: {len(accuracy_problems)} проблем')
        
        print(f'\nПроверка качества. Успешно!')
        
        return df
        
    except Exception as e:
        print(f"\nОшибка: {e}")
        print("\nПодробности:")
        import traceback
        traceback.print_exc()
        
        return None

if __name__ == "__main__":
    run_quality_check()
    
    