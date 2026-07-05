# a_data_collection/ac_config.py
import os
from dotenv import load_dotenv
from pathlib import Path

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
    if not PG_CONFIG.get(field):
        raise ValueError(
            f"PG_{field.upper()} не настроен!\n"
            f"1. Скопируйте .env.example в .env\n"
            f"2. Заполните {field.upper()}\n"
            f"3. Перезапустите приложение"
        )

# CDP Elasticsearch
ES_CONFIG = {
    "host": [os.getenv('ES_HOST', '')],
    "verify_certs": os.getenv('ES_VERIFY_CERTS', 'false').lower() == 'true'
}

# проверка хоста
if not ES_CONFIG["host"][0]:
    raise ValueError(
        "ES_HOST не настроен!\n"
        "Заполните ES_HOST в файле .env"
    )

# сколько событий брать за раз
BATCH_SIZE=int(os.getenv('BATCH_SIZE', '5000'))
FETCH_HOURS=int(os.getenv('FETCH_HOURS', '24'))
ES_INDEX_PATTERN = os.getenv('ES_INDEX_PATTERN', 'events-*')

# 17 событий
EVENT_TYPES = [
    'page-view',
    'profile-traits-update',
    'identification',
    'product-details-page-view',
    'cart-changes',
    'checkout-started',
    'cart-delete',
    'sign-in',
    'profile-update',
    'promotion-viewed',
    'promotion-clicked',
    'promotion-close',
    'message-status',
    'message-opened',
    'rating',
    'personal-view',
    'copy-promocode' 
]


