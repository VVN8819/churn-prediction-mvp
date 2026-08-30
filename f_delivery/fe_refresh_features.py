"""
fe_refresh_features.py
Обновление материализованного представления и перенос данных в ml_features.
Выполняет SQL из sql_05_maintenance.sql.
"""
import os
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        sslmode=os.getenv("DB_SSLMODE", "require")
    )

def main():
    print("- Начало обновления признаков")
    
    sql_file = Path(__file__).parent / "sql" / "sql_05_maintenance.sql"
    
    if not sql_file.exists():
        print(f" - SQL-файл не найден: {sql_file}")
        return
    
    try:
        conn = get_db_connection()
        conn.autocommit = True
        
        with conn.cursor() as cursor:
            print("- Подключение к БД успешно.")
            print("  - Выполнение sql_05_maintenance.sql")
            
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_script = f.read()
            
            cursor.execute(sql_script)
            
        print("- Признаки успешно обновлены")
        print(" Следующий шаг: Запустите fb_inference_pipeline.py для предсказания оттока.")
        
    except Exception as e:
        print(f" Ошибка при обновлении признаков: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
