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
- CDP Elasticsearch - собирает события от сайта и приложения по JS трекеру (17 событий выбрал: page-view, profile-traits-update, identification, product-details-page-view, cart-changes, checkout-started, cart-delete, sign-in, profile-update, promotion-viewed, promotion-clicked,promotion-close, message-status, message-opened, rating, personal-view, copy-promocode).
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
        cache/
            prepared_data.joblib - файл для ускорения обучение каждой модели, кеширование предобработанных данных для моделей
        plots/
            01_feature_correlation_with_churn.png - визуализация корреляции признаков с целевой переменной
        __init__.py - (пустой, для импортов)
        d_run_pipeline_class.py - Запуск пайплайна предобработки через class db_class_data_preprocessor.py
        d_run_pipeline.py - Запуск пайплайна предобработки da_pretrain_data_prep.py
        da_pretrain_data_prep.py - Шаги 1-7 (общие для всех моделей): 1. Загрузка очищенных данных из df_features_clean.csv. 2. Автоматический перевод bool в int (0/1). 3. Определение целевой переменной churn. 4. Анализ корреляции признаков с целевой переменной и сохранение в 01_feature_correlation_with_churn.png. 5. Подготовка признаков (разделение на X и y). 6. Разделение на train/test. 7. Масштабирование признаков (StandardScaler).
        db_class_data_preprocessor.py - Класс DataPreprocessor для обучения моделей в dc_logistic_regression, dd_random_forest и de_gradient_boosting с опциональным кешированием в prepared_data.joblib
        dc_logistic_regression.py - обучение Logistic Regression
        dd_random_forest.py - обучение Random Forest
        de_gradient_boosting.py - обучение Gradient Boosting
        de_gridsearch_cv.py - Поиск и cross-validation по лучшим параметрам, обучение Logistic Regression
        df_compare_models.py - сравнение трех моделей (НЕ ГОТОВО)
        models/
            logistic_regression_model.joblib - модель + scaler (со сжатием)
            logistic_regression_metrics.txt - метрики
            random_forest_model.joblib - модель (НЕ ГОТОВО)
            random_forest_metrics.txt - метрики (НЕ ГОТОВО)
            gradient_boosting_model.joblib - модель (НЕ ГОТОВО)
            gradient_boosting_metrics.txt - метрики (НЕ ГОТОВО)
        predictions/ (НЕ ГОТОВО)
            logistic_regression_predictions.csv
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

# Признаки для моделей:

1. days_since_last_order: Дней с последнего заказа
2. cart_abandonment_rate_30d: % отказов на /checkout
3. checkout_completion_rate: Конверсия оформления заказа (/order)
4. checkout_frustration_index: (удаления на /checkout + низкие рейтинги) / начатые оформления
5. personal_offer_conversion_rate: Конверсия персонального предложения (увидел personal-view и скопировал copy-promocode)
6. promo_ignore_rate_14d: % игнорирования баннерных акций
7. session_engagement_score: Вовлечённость сессии
8. message_open_rate_30d: % открытых сообщений
9. cart_browse_abandon_rate_30d: % отказов в каталоге/на главной
10. personal_views_count_30d: Количество просмотров персонального предложения
11. push_channel_available: Доступен ли push-канал
12. phone_changed_90d: Менялся ли телефон за 90 дней (исключаем identification на /checkout это валидация, не изменение)
13. avg_rating_90d: Средняя оценка за 90 дней
14. coupon_dependency_ratio: Доля заказов с купоном за 90 дней
15. avg_cart_value_30d: Средняя сумма корзины за 30 дней
16. profile_completeness_score: Заполненность профиля (телефон 0.4 + имя 0.3 + день рождения 0.3)
17. delta_page_views_14d: Дельта просмотров (последние 14 дней vs предыдущие 14)
18. has_unpublished_review: Есть ли негативный отзыв за 90 дней
19. cart_to_checkout_ratio: Соотношение суммы корзины к сумме чекаута
20. avg_copy_reaction_seconds: Среднее время реакции на копирование промокода
21. reviews_reading_behavior: Поведенческий паттерн чтения отзывов
22. promo_interest_rate: Комбинированный интерес к акциям
23. checkout_value_trend: Линейный тренд суммы заказа за 30 дней
24. auth_on_checkout_flag: Флаг неавторизованного посещения чекаута
25. Целевая переменная is_churned - Если клиент делал заказы (days < 900) и не заказывал 60+ дней - churn = 1