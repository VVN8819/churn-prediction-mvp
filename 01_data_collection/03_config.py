import os
from dotenv import load_dotenv

load_dotenv()

# PostgreSQL
PG_CONFIG = {
    "host": os.getenv('PG_HOST', ''),
    "port": os.getenv('PG_PORT', ''),
    "database": os.getenv('PG_DATABASE', 'churn_db'),
    "user": os.getenv('PG_USER', 'churn_user'),
    "password": os.getenv('PG_PASSWORD')
}

# проверка пароля
if not PG_CONFIG["password"]:
    raise ValueError(
        "PG_PASSWORD не настроен!\n"
        "1. Скопируйте .env.example в .env\n"
        "2. Заполните PG_PASSWORD=ваш_пароль\n"
        "3. Перезапустите приложение"
    )

# CDP Elasticsearch
ES_CONFIG = {
    "host": [os.getenv('ES_HOST', '')],
    "basic_auth": (
        os.getenv('ES_USERNAME', 'elastic'),
        os.getenv('ES_PASSWORD')
    ),
    "varify_certs": os.getenv('ES_VERIFY_CERTS', 'true').lower() == 'true'
}

# проверка пароля
if not ES_CONFIG["basic_auth"][1]:
    raise ValueError(
        "ES_PASSWORD не настроен!\n"
        "Заполните ES_PASSWORD в файле .env"
    )

# сколько событий брать за раз
BATCH_SIZE=int(os.getenv('BATCH_SIZE', '1000'))
FETCH_HOURS=int(os.getenv('FETCH_HOURS', '24'))

# 15 событий
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
    'rating'
]
