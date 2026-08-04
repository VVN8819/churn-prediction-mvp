# c_eda/cb_explore_data.py
"""
cb_explore_data.py
Первичный анализ данных (EDA)

Что делает:
1. Загружает данные из CSV (не из БД — это быстрее)
2. Показывает размер данных
3. Показывает типы признаков
4. Считает пропуски
5. Ищет дубликаты
6. Показывает статистику
"""

import sys
import pandas as pd
from pathlib import Path

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Импортируем функцию загрузки из CSV
from c_eda.ca_load_data import load_from_csv

# ============ Показывает размер данных =========
def show_data_shape(df):
    """Показывает сколько строк и столбцов в данных"""
    
    print("\nВ данных:")
    print(f"   Строк: {df.shape[0]}")
    print(f"   Столбцов: {df.shape[1]}")

# ========= какие типы данных есть в таблице ==========
def show_data_types(df):
    """Показывает какие типы данных есть в таблице"""
    
    print("\nТипы данных:")
    
    # Служебные колонки (исключаем их из анализа)
    service_cols = ['profile_id', 'snapshot_date', 'computed_at', 
                    'churn_probability', 'risk_level']
    
    # Разделяем признаки по типам
    numerical_cols = df.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
    boolean_cols = df.select_dtypes(include=['bool']).columns.tolist()
    datetime_cols = df.select_dtypes(include=['datetime']).columns.tolist()
    
    # Исключаем служебные колонки из числовых
    feature_cols = [c for c in numerical_cols if c not in service_cols]
    
    # Исключаем служебные колонки из категориальных
    categorical_cols = [c for c in categorical_cols if c not in service_cols]
    
    print(f"\nЧисловые признаки (для ML): {len(feature_cols)}")
    for col in feature_cols:
        print(f" - {col}")
    
    print(f"\nКатегориальные признаки: {len(categorical_cols)}")
    for col in categorical_cols:
        print(f" - {col}: {df[col].nunique()} значений")
    
    print(f"\nБулевые признаки (True/False): {len(boolean_cols)}")
    for col in boolean_cols:
        print(f" - {col}")
    
    if datetime_cols:
        print(f"\nДата/время: {len(datetime_cols)}")
        for col in datetime_cols:
            print(f" - {col}")
    
    return numerical_cols, categorical_cols, boolean_cols

# ============= Считает пропуски =============
def show_missing_values(df):
    """Показывает где есть пропуски (NULL)"""
    
    print("\nГде есть пропуски:")
    
    # Считаем пропуски по каждому столбцу
    missing = df.isnull().sum()
    missing_percent = (missing / len(df) * 100).round(2)
    
    # Создаём таблицу с результатами
    missing_df = pd.DataFrame({
        'Пропусков': missing,
        'Процент': missing_percent
    })
    
    # Показываем только те, где есть пропуски
    missing_df = missing_df[missing_df['Пропусков'] > 0]
    
    if len(missing_df) > 0:
        print("\n   Completeness (Raw) - Найдены пропуски:")
        print(missing_df.to_string())
    else:
        print("\n   Completeness (Raw): Отлично! Пропусков нет.")

# ============ Ищет дубликаты ==========
def show_duplicates(df):
    """Ищет дубликаты строк"""
    
    print("\nИщет дубликаты строк:")
    # Полные дубликаты (все столбцы совпадают)
    duplicates = df.duplicated().sum()
    print(f"\nДубликатов: {duplicates}")
    
    # Проверка уникальности profile_id
    if 'profile_id' in df.columns:
        unique_profiles = df['profile_id'].nunique()
        total_rows = len(df)
        print(f"Уникальных profile_id: {unique_profiles} из {total_rows}")
        
        if unique_profiles == total_rows:
            print("Все profile_id уникальны")
        else:
            print(f'Найдено {total_rows - unique_profiles} дубликатов profile_id')

# ============ Показывает статистику ===========
def show_statistics(df, numerical_cols):
    """Показывает базовую статистику для числовых признаков"""
    
    print("\nБазовая статистика для числовых признаков:")
    
    # Выбираем только признаки для ML (без служебных)
    service_cols = ['profile_id', 'snapshot_date', 'computed_at', 
                    'churn_probability', 'risk_level']
    feature_cols = [c for c in numerical_cols if c not in service_cols]
    
    # Показываем статистику
    stats = df[feature_cols].describe().round(4)
    print('\n', stats.to_string())

# ========== Показывает распределение категорий ===========
def show_categorical_distributions(df, categorical_cols):
    """Показывает сколько значений каждой категории"""
    
    print("\nСколько значений каждой категории:")
    
    for col in categorical_cols:
        print(f"\n{col}:")
        counts = df[col].value_counts()
        for value, count in counts.items():
            percent = round(count / len(df) * 100)
            print(f"- {value}: {count} ({percent}%)")

def explore_data():
    """Главная функция: запускает все проверки"""
    
    print("\n2. Первичный анализ данных")
    
    try:
        # Загружаем данные из CSV (быстрее, чем из БД)
        print(f'Загрузка данных из CSV')
        df = load_from_csv("df_features_raw.csv")
        
        # Запускаем все проверки
        show_data_shape(df)
        numerical_cols, categorical_cols, boolean_cols = show_data_types(df)
        show_missing_values(df)
        show_duplicates(df)
        show_statistics(df, numerical_cols)
        show_categorical_distributions(df, categorical_cols)

        print("\nРаспределение целевой переменной (is_churned)")
        if 'is_churned' in df.columns:
            churn_counts = df['is_churned'].value_counts()
            churn_pct = df['is_churned'].value_counts(normalize=True) * 100
            print(f"- Активные клиенты (is_churned=False): {churn_counts.get(False, 0):,} ({churn_pct.get(False, 0):.1f}%)")
            print(f"- Ушедшие клиенты  (is_churned=True):  {churn_counts.get(True, 0):,} ({churn_pct.get(True, 0):.1f}%)")
        else:
            print("\nКолонка 'is_churned' не найдена в данных!")
        
        print(f'\nПервичный анализ данных из CSV. Успешно!')
        
        return df
        
    except Exception as e:
        print(f"\nОшибка: {e}")
        print("\nПодробности:")
        import traceback
        traceback.print_exc()
        
        return None
        
if __name__ == "__main__":
    explore_data()
    
    
    