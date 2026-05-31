# churn-prediction-mvp

# Структура

churn-prediction-mvp/

    01_data_collection/ - Шаг 1: Сбор сырых данных
        fetch_from_cdp.py - Скрипт: получение данных из CDP
        process_queue.py - Скрипт: обработка очереди
        config.py - Настройки (подключения к БД)
    
    02_database/ - Шаг 2: База данных
        create_tables.sql - Создание таблиц
        test_queries.sql - Проверочные запросы
    
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
    architecture.md - Описание архитектуры
    SECURITY.md - Инструкция по безопасности