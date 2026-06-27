# c_eda/ca_load_data.py
"""
ca_load_data.py
Загрузка данных из PostgreSQL в CSV файл

Что делает:
1. Подключается к базе данных (Timeweb Cloud)
2. Загружает таблицу ml_features
3. Сохраняет в CSV файл в папке data/
"""

import sys
import pandas as pd
from pathlib import Path

# Добавляем корень проекта в путь для импорта конфига
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Импортируем настройки подключения к БД
############################ from a_data_collection.ac_config import PG_CONFIG

# =============== TEST CONNECTION =====================
from a_data_collection.ad_test_pg_connection import PG_CONFIG 
# ======================================================

# ============= подключение к базе данных с SSL=========
def get_db_connection():
    """Создает подключение к базе данных с SSL"""
    from sqlalchemy import create_engine
    
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
        
    print(f"Строка подключения: postgresql://{user}:***@{host}:{port}/{database}")
    
    engine = create_engine(connection_string)
    return engine

# ============= Загружает таблицу ml_features ================
def load_ml_features():
    """Загружает таблицу ml_features из базы данных"""
    
    print("\nПодключаемся к базе")
    print(f"   Хост: {PG_CONFIG['host']}:{PG_CONFIG['port']}")
    print(f"   База: {PG_CONFIG['database']}")
    print(f"   Пользователь: {PG_CONFIG['user']}")
    print(f"   SSL: {PG_CONFIG.get('sslmode', 'require')}")
    
    # Подключаемся
    engine = get_db_connection()
    
    print(f'\nЗагружаем ml_features')
    query = "SELECT * FROM ml_features ORDER BY profile_id"
    df = pd.read_sql(query, engine)
    
    print(f"Загружено строк: {len(df)}")
    print(f"Загружено столбцов: {len(df.columns)}")
    
    return df

# ========= Сохраняет DataFrame в CSV файл ===========
def save_to_csv(df, filename="df_features_raw.csv"):
    """Сохраняет DataFrame в CSV файл"""
    
    # Создаем папку data если её нет
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)
    
    # Путь к файлу
    filepath = data_dir / filename
    
    # Сохраняем
    df.to_csv(filepath, index=False)
    
    print(f'\nДанные сохранены в файл: {filepath}')
    
    return filepath

# ============ загрузка и сохранение ==========
def load_save_ml_features():
    """Главная функция шага 1: загрузка и сохранение"""
    
    print(f'\nЗагрузка и сохранение из базы')
    
    try:
        # Загружаем из БД
        df = load_ml_features()
        
        # Сохраняем в CSV
        filepath = save_to_csv(df, "df_features_raw.csv")
        
        print(f'\nПервые 5 строк')
        print(df.head(5).to_string())
        print(f'\nУспешно!')
        
        return df
    
    except Exception as e:
        print(f"\nОшибка: {e}")
        print("\nВозможные причины:")
        print("   1. Неверные настройки в .env файле")
        print("   2. Проблемы с SSL сертификатом")
        print("   3. База данных недоступна")
        print("\nПодробности:")
        import traceback
        traceback.print_exc()
        
        return None
        

if __name__ == "__main__":
    load_save_ml_features()
    
    
    