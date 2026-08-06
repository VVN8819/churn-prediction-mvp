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
        a_run_pipeline.py - Главный файл запуска CDP pipeline
        aa_fetch_from_cdp.py - Получение событий из CDP и вставка в events_queue PostgreSQL
        ab_process_queue.py - Обработка событий из events_queue
        ac_config.py - Единый центр конфигурации для всего проекта 'class AppConfig'
        ad_test_pg_connection.py - Проверочное подключение к базе PostgreSQL на Timeweb Cloud
        ae_test_es_connection.py - Проверочное подключение к CDP Elasticsearch
    
    b_database/ - Шаг 2: База данных: формирование и оптимизация
        ba_create_tables.sql - Создание таблиц
        bb_create_partitions.sql - Партиционирование raw_events по месяцам для производительности
        bc_create_indexes.sql - индексы для оптимизации производительности
        bd_create_materialized_views.sql - MV для Feature Store для мгновенных ответов на дашборде
        be_create_maintenance.sql - Обслуживание БД для Timeweb Cloud чтобы не деградировала
        bf_test_data.sql - Тестовые данные
        bg_test_data_testing.sql - Тестовые SQL запросы к БД после обработки bf_test_data.sql
    
    c_eda/ - Шаг 3: ETL
        data/
            df_features_raw.csv - Сырые данные для EDA
            df_features_clean.csv - Очищенные данные после EDA
        plots/
            01_categories_distribution.png - визуализация bar chart
            02_clients_comparison.png - визуализация bar chart
            03_correlation_heatmap.png - визуализация correlation heatmap
            04_boxplots.png - визуализация выбросов boxplots
        c_run_pipeline.py - Главный файл запуска всего EDA пайплайна
        ca_load_data.py - Загрузка данных из PostgreSQL в CSV файл
        cb_explore_data.py - Первичный анализ данных (EDA)
        cc_quality_check.py - Проверка качества (IQR, Z-score)
        cd_visualize.py - Визуализация
        ce_clean_data.py - Очистка и подготовка данных для ML-модели
    
    d_ml_model/ - Шаг 4: ML модель: обучение и выбор лучшей
        cache/
            prepared_data.joblib - кеширование предобработанных данных для обучения моделей
        models/
            gb_feature_importance.csv - важность признаков
            gradient_boosting_metrics.txt - метрики после обучения
            gradient_boosting_model.joblib - обученная модель
            gridsearch_cv_feature_importance.csv - важность признаков
            gridsearch_cv_metrics.txt - метрики после обучения
            gridsearch_cv_model.joblib - обученная модель
            logistic_regression_metrics.txt - метрики после обучения
            logistic_regression_model.joblib - обученная модель
            logreg_feature_importance.csv - важность признаков
            random_forest_metrics.txt - метрики после обучения
            random_forest_model.joblib - обученная модель
            rf_feature_importance.csv - важность признаков
            scaler.joblib - scaler для инференса на новых данных
        plots/
            01_feature_correlation_with_churn.png - визуализация корреляции признаков с target
            02_confusion_matrix_logreg.png - визуализация confusion matrix Logistic Regression
            03_feature_importance_logreg.png - визуализация важности признаков Logistic Regression
            04_confusion_matrix_rf.png - визуализация confusion matrix Random Forest
            05_feature_importance_rf.png - визуализация важности признаков Random Forest
            06_confusion_matrix_gb.png - визуализация confusion matrix Gradient Boosting
            07_feature_importance_gb.png - визуализация важности признаков Gradient Boosting
            08_confusion_matrix_gridsearch_cv.png - визуализация confusion matrix GridSearchCV
            09_feature_importance_gridsearch_cv.png - визуализация важности признаков GridSearchCV
            10_gridsearch_cv_results.png - визуализация зависимости Recall от параметра C
            11_models_comparison.png - визуализация сравнения ключевых метрик всех моделей
        __init__.py - (пустой, для импортов)
        d_run_pipeline_class.py - Запуск ML-пайплайна черех class DataPreprocessor
        db_class_data_preprocessor.py - Класс для подготовки данных для ML моделей
        dc_logistic_regression.py - обучение Logistic Regression
        dd_random_forest.py - обучение Random Forest
        de_gradient_boosting.py - обучение Gradient Boosting
        de_gridsearch_cv.py - Поиск и cross-validation по параметрам, обучение Logistic Regression
        df_compare_models.py - сравнение четырех моделей
    
    e_inference/ - Шаг 5: Inference (предсказанием)
        e_run_pipeline.py - Оркестратор инференс-пайплайна
        ea_preprocess_inference.py - Класс для предобработки данных перед инференсом
        eb_predict_churn.py - предсказание оттока и запись результатов в БД
        
    
    05_dashboard/ - Шаг 5: Дашборд (НЕ ГОТОВО)
        metabase_queries.sql - Запросы для Metabase (НЕ ГОТОВО)
    
    .env - Секретные настройки (пароли)
    .env.example - Шаблон для Git (без паролей)
    .gitignore - Игнорировать секреты
    LICENSE - Лицензия
    ml_config.py - Константы для ML-пайплайна
    README.md - Инструкция для команды
    requirements.txt - Библиотеки Python
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