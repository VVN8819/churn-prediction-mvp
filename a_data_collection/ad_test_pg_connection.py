# a_data_collection/ad_test_pg_connection.py
"""
a_data_collection/ad_test_pg_connection.py
Тест подключения к PostgreSQL. 
Использует конфигурацию из ac_config.py, чтобы избежать дублирования кода.
"""
import sys
from pathlib import Path

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from a_data_collection.ac_config import config, PG_CONFIG

# PostgreSQL
print("Подключаемся к PostgreSQL")
print(f"- Хост: {PG_CONFIG['host']}:{PG_CONFIG['port']}")
print(f"- База: {PG_CONFIG['database']}")
print(f"- Пользователь: {PG_CONFIG['user']}")
print(f"- SSL: {PG_CONFIG['sslmode']}")

try:
    import psycopg2
    conn = psycopg2.connect(**PG_CONFIG)

    with conn.cursor() as cursor:
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"Успешно подключено!")
        print(f"PostgreSQL: {version}")

    conn.close()
    print("Подключение закрыто")

except ImportError:
    print("Библиотека psycopg2 не установлена!")
    print("Выполните: pip install psycopg2-binary")
    sys.exit(1)

except psycopg2.OperationalError as e:
    error = str(e).lower()
    print(f"Ошибка подключения: {e}")

    if "certificate" in error or "ssl" in error:
        print("\nВозможные решения:")
        print("1. Проверьте путь к сертификату в .env")
        print("2. Убедитесь что файл ca.crt существует")
        print("3. Попробуйте временно: PG_SSL_MODE=require")
        print("4. Скачайте актуальный сертификат из панели Timeweb")

    elif "host" in error or "connection" in error:
        print("\nПроверьте:")
        print("• Ваш внешний IP добавлен в файрвол Timeweb?")
        print("• Хост PG_HOST правильный?")

    elif "password" in error:
        print("\nПроверьте пароль в .env")

except Exception as e:
    print(f"Неожиданная ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


