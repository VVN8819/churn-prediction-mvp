"""
fc_bootstrap_database.py
Скрипт первичной инициализации базы данных PostgreSQL.
Выполняет SQL-скрипты в порядке: Таблицы - Партиции - Индексы - MV.
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

def execute_sql_file(cursor, filepath):
    print(f"   - Выполнение: {filepath.name}")
    with open(filepath, 'r', encoding='utf-8') as f:
        sql_script = f.read()
    cursor.execute(sql_script)

def main():
    print("- Начало инициализации базы данных PostgreSQL...")
    
    sql_dir = Path(__file__).parent / "sql"
    sql_files = sorted([f for f in sql_dir.glob("*.sql")])
    
    if not sql_files:
        print("- Ошибка: Папка sql/ пуста или не найдена.")
        return

    try:
        conn = get_db_connection()
        conn.autocommit = True
        
        with conn.cursor() as cursor:
            print("- Подключение к БД успешно.")
            for sql_file in sql_files:
                execute_sql_file(cursor, sql_file)
                
        print("- База данных успешно инициализирована!")
        print("- Следующий шаг: Запустите fd_sync_cdp_data.py для первичной загрузки данных из CDP.")
        
    except Exception as e:
        print(f"- Ошибка при инициализации БД: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
