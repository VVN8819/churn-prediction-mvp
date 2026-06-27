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
    
    print('\nИтог:')
    if len(problems) == 0:
        print('Все проверки пройдены!')
    else:
        print(f'Найдено {len(problems)} проблем:')
        for problem in problems:
            print(f'{problem}')
            
    return problems
        
    

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
        #outliers_iqr = find_outliers_iqr(df, numerical_cols)
        #outliers_zscore = find_outliers_zscore(df, numerical_cols, threshold=2)
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
    
    