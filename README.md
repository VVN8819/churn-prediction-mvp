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

    a_data_collection/ - Шаг 1: Сбор сырых данных
        aa_fetch_from_cdp.py - Скрипт: получение данных из CDP
        ab_process_queue.py - Скрипт: обработка очереди
        ac_config.py - Настройки (подключения к БД)
        ad_test_pg_connection.py - Проверочное подключение к базе
    
    b_database/ - Шаг 2: База данных
        ba_create_tables.sql - Создание таблиц
        bb_create_partitions.sql - Партиционирование raw_events по месяцам для производительности на Timeweb Cloud
        bc_create_indexes.sql - индексы для оптимизации производительности
        bd_create_materialized_views.sql - Материализованные представления для Feature Store для мгновенных ответов на дашборде
        be_create_maintenance.sql - Регулярное обслуживание базы данных для Timeweb Cloud чтобы БД не деградировала со временем
        bf_test_data.sql - Тестовые данные
        bg_test_data_testing - Дополнительные тесты
    
    c_eda/ - Шаг 3: ETL
        data/
            df_features_raw.csv - Сырые данные
            df_features_clean.csv - Очищенные данные
        plots/
            01_categories_distribution.png
            02_clients_comparison.png
            03_correlation_heatmap.png
            04_boxplots.png
        c_run_pipeline.py - Главный скрипт EDA (5 шагов)
        ca_load_data.py - Шаг 1: Загрузка из БД
        cb_explore_data.py - Шаг 2: Первичный анализ
        cc_quality_check.py - Шаг 3: Проверка качества (IQR, Z-score)
        cd_visualize.py - Шаг 4: Визуализация
        ce_clean_data.py - Шаг 5: Очистка (логарифмирование + encoding)
    
    d_ml_model/ - Шаг 4: ML модель (потом)
        train_model.py - Обучение модели
    
    05_dashboard/ - Шаг 5: Дашборд (потом)
        metabase_queries.sql - Запросы для Metabase
        
    requirements.txt - Библиотеки Python
    .env - Секретные настройки (пароли)
    .env.example - Шаблон для Git (без паролей)
    .gitignore - Игнорировать секреты
    README.md - Инструкция для команды
    SECURITY.md - Инструкция по безопасности