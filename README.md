# churn-prediction-mvp
**Проект - Regression (Регрессия)**

**Цель анализа:**
Вероятность оттока (Logistic Regression)

**На выходе результат:**
"Вероятность ухода клиента N: 73% в ближайшие 14 дней"

**Использование результата:**
Проактивная оценка, триггерные push-уведомления для реактивации клиента на платформе по доставке еды SaaS.

**Объект работы:**
Сложное поведение гостей

**Что есть на начальном этапе:**
- CDP Elasticsearch - собирает события от сайта и приложения по JS трекеру (15 событий выбрал: page-view, profile-traits-update, identification, product-details-page-view, cart-changes, checkout-started, cart-delete, sign-in, profile-update, promotion-viewed, promotion-clicked,promotion-close, message-status, message-opened, rating).
- Платформа по рассылкам - пуш в приложении, Мах, Телега, Баннеры в приложении и сайте.

# Структура

churn-prediction-mvp/

    01_data_collection/ - Шаг 1: Сбор сырых данных
        01_fetch_from_cdp.py - Скрипт: получение данных из CDP
        02_process_queue.py - Скрипт: обработка очереди
        03_config.py - Настройки (подключения к БД)
        04_test_pg_connection.py - Проверочное подключение к базе
    
    02_database/ - Шаг 2: База данных
        01_create_tables.sql - Создание таблиц
        02_create_partitions.sql - Партиционирование raw_events по месяцам для производительности на Timeweb Cloud
        03_create_indexes.sql - индексы для оптимизации производительности
        04_create_materialized_views.sql - Материализованные представления для Feature Store для мгновенных ответов на дашборде
        05_create_maintenance.sql - Регулярное обслуживание базы данных для Timeweb Cloud чтобы БД не деградировала со временем
        test_queries.sql - Проверочные запросы
        06_test_data.sql - Тестовые данные
    
    03_etl/ - Шаг 3: ETL (потом)
        calculate_features.py - Расчёт 16 признаков
    
    04_ml_model/ - Шаг 4: ML модель (потом)
        train_model.py - Обучение модели
    
    05_dashboard/ - Шаг 5: Дашборд (потом)
        metabase_queries.sql - Запросы для Metabase
        
    requirements.txt - Библиотеки Python
    .env - Секретные настройки (пароли)
    .env.example - Шаблон для Git (без паролей)
    .gitignore - Игнорировать секреты
    README.md - Инструкция для команды
    SECURITY.md - Инструкция по безопасности