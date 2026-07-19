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
- CDP Elasticsearch - собирает события от сайта и приложения по JS трекеру (17 событий выбрал: page-view, profile-traits-update, identification, product-details-page-view, cart-changes, checkout-started, cart-delete, sign-in, profile-update, promotion-viewed, promotion-clicked,promotion-close, message-status, message-opened, rating).
- Платформа по рассылкам - пуш в приложении, Мах, Телега, Баннеры в приложении и сайте.

# Структура

churn-prediction-mvp/

    a_data_collection/ - Шаг 1: Сбор сырых данных
        a_run_pipeline.py - запуск aa_fetch_from_cdp.py и ab_process_queue.py
        aa_fetch_from_cdp.py - Скрипт: получение данных из CDP и помещение в БД PostgreSQL
        ab_process_queue.py - Скрипт: обработка очереди
        ac_config.py - Настройки (подключения к CDP Elasticsearch и БД PostgreSQL)
        ad_test_pg_connection.py - Проверочное подключение к базе PostgreSQL на Timeweb Cloud
        ae_test_es_connection.py - Проверочное подключение к CDP Elasticsearch
    
    b_database/ - Шаг 2: База данных
        ba_create_tables.sql - Создание таблиц events_queue, raw_events, profiles, ml_features, events_processing_log
        bb_create_partitions.sql - Партиционирование raw_events по месяцам для производительности на Timeweb Cloud
        bc_create_indexes.sql - индексы для оптимизации производительности
        bd_create_materialized_views.sql - Материализованные представления для Feature Store для мгновенных ответов на дашборде
        be_create_maintenance.sql - Регулярное обслуживание базы данных для Timeweb Cloud чтобы БД не деградировала со временем
        bf_test_data.sql - Тестовые данные
        bg_test_data_testing.sql - Дополнительные тестовые SQL запросы к БД после обработки bf_test_data.sql
    
    c_eda/ - Шаг 3: ETL
        data/
            df_features_raw.csv - Сырые данные для EDA
            df_features_clean.csv - Очищенные данные после EDA
        plots/
            01_categories_distribution.png - визуализация bar chart
            02_clients_comparison.png - визуализация bar chart
            03_correlation_heatmap.png - визуализация correlation heatmap
            04_boxplots.png - визуализация выбросов boxplots
        c_run_pipeline.py - Главный скрипт EDA, запуск 5 шагов: ca_load_data, cb_explore_data, cc_quality_check, cd_visualize и ce_clean_data
        ca_load_data.py - Шаг 1: Загрузка из БД PostgreSQL и сохранение в df_features_raw.csv
        cb_explore_data.py - Шаг 2: Первичный анализ
        cc_quality_check.py - Шаг 3: Проверка качества (IQR, Z-score)
        cd_visualize.py - Шаг 4: Визуализация
        ce_clean_data.py - Шаг 5: Очистка (логарифмирование + encoding) и сохранение в df_features_clean.csv
    
    d_ml_model/ - Шаг 4: ML модель
        plots/
            01_feature_correlation_with_churn.png - визуализация корреляции признаков с целевой переменной
        __init__.py - (пустой, для импортов)
        d_run_pipeline.py - Запуск пайплайна предобработки da_pretrain_data_prep.py
        da_pretrain_data_prep.py - Шаги 1-7 (общие для всех моделей): 1. Загрузка очищенных данных из df_features_clean.csv. 2. Автоматический перевод bool в int (0/1). 3. Определение целевой переменной churn. 4. Анализ корреляции признаков с целевой переменной и сохранение в 01_feature_correlation_with_churn.png. 5. Подготовка признаков (разделение на X и y). 6. Разделение на train/test. 7. Масштабирование признаков (StandardScaler).
        db_class_data_preprocessor.py - Класс DataPreprocessor для обучения моделей в dc_logistic_regression, dd_random_forest и de_gradient_boosting с опциональным кешированием в prepared_data.joblib
        dc_logistic_regression.py - обучение Logistic Regression (НЕ ГОТОВО)
        dd_random_forest.py - обучение Random Forest (НЕ ГОТОВО)
        de_gradient_boosting.py - обучение Gradient Boosting (НЕ ГОТОВО)
        df_compare_models.py - сравнение трех моделей (НЕ ГОТОВО)
        cache/ - Опционально
            prepared_data.joblib - кеширование предобработанных данных для моделей
        models/
            logistic_regression_model.joblib - модель + scaler (со сжатием) (НЕ ГОТОВО)
            logistic_regression_metrics.txt - метрики (НЕ ГОТОВО)
            random_forest_model.joblib - модель (НЕ ГОТОВО)
            random_forest_metrics.txt - метрики (НЕ ГОТОВО)
            gradient_boosting_model.joblib - модель (НЕ ГОТОВО)
            gradient_boosting_metrics.txt - метрики (НЕ ГОТОВО)
        predictions/ (НЕ ГОТОВО)
            logistic_regression_predictions.csv (НЕ ГОТОВО)
            random_forest_predictions.csv (НЕ ГОТОВО)
            gradient_boosting_predictions.csv (НЕ ГОТОВО)
    
    05_dashboard/ - Шаг 5: Дашборд (НЕ ГОТОВО)
        metabase_queries.sql - Запросы для Metabase (НЕ ГОТОВО)
        
    requirements.txt - Библиотеки Python
    .env - Секретные настройки (пароли)
    .env.example - Шаблон для Git (без паролей)
    .gitignore - Игнорировать секреты
    README.md - Инструкция для команды
    SECURITY.md - Инструкция по безопасности