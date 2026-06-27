# a_data_collection/ad_test_pg_connection.py
"""
Тест подключения к Timeweb Cloud PostgreSQL с SSL
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

# PostgreSQL
PG_CONFIG = {
    "host": os.getenv('PG_HOST'),
    "port": os.getenv('PG_PORT', '5432'),
    "database": os.getenv('PG_DATABASE'),
    "user": os.getenv('PG_USER'),
    "password": os.getenv('PG_PASSWORD'),
    
    # SSL для облачного подключения
    "sslmode": os.getenv('PG_SSL_MODE', 'require')
}

# Обработка пути к SSL сертификату
ssl_root_cert = os.getenv('PG_SSL_ROOT_CERT')
if ssl_root_cert and PG_CONFIG['sslmode'] in ('verify-ca', 'verify-full'):
    # Нормализуем путь для кросс-платформенности
    cert_path = Path(ssl_root_cert).resolve()
    if not cert_path.exists():
        raise FileNotFoundError(
            f"SSL сертификат не найден: {cert_path}\n"
            f"Проверьте путь в .env: PG_SSL_ROOT_CERT"
        )
    PG_CONFIG["sslrootcert"] = str(cert_path)
    
# проверка пароля
required_fields = ["host", "database", "user", "password"]
for field in required_fields:
    if not PG_CONFIG["password"]:
        raise ValueError(
            "PG_PASSWORD не настроен!\n"
            "1. Скопируйте .env.example в .env\n"
            "2. Заполните PG_PASSWORD=ваш_пароль\n"
            "3. Перезапустите приложение"
    )    


print("Подключаемся к PostgreSQL...")
print(f"Хост: {PG_CONFIG['host']}:{PG_CONFIG['port']}")
print(f"База: {PG_CONFIG['database']}")
print(f"SSL: {PG_CONFIG['sslmode']}")

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


