# churn-prediction-mvp

## Содержание

- [Введение](#введение)
- [ML проект для SaaS платформы доставки еды](#ml-проект-для-saas-платформы-доставки-еды)
- [Быстрый старт](#быстрый-старт)
- [Архитектура проекта](#архитектура-проекта)
- [Ключевые классы и конфигурация](#ключевые-классы-и-конфигурация)
- [ML Pipeline](#ml-pipeline)
  - [Обучение 4 моделей](#обучение-4-моделей)
  - [GridSearchCV оптимизация](#gridsearchcv-оптимизация)
- [Inference Pipeline](#inference-pipeline)
  - [Шаг 1: Предобработка](#шаг-1-предобработка)
  - [Шаг 2: Предсказание и экспорт](#шаг-2-предсказание-и-экспорт)
- [Ключевые визуализации](#ключевые-визуализации)
  - [Сравнение моделей](#сравнение-моделей)
  - [Важность признаков GridSearchCV](#важность-признаков-gridsearchcv)
  - [GridSearchCV результаты](#gridsearchcv-результаты)
  - [Корреляция признаков с оттоком](#корреляция-признаков-с-оттоком)
- [Структура проекта](#структура-проекта)
- [24 признака](#24-признака)
  - [Транзакционные](#транзакционные)
  - [Отказы и фрустрация](#отказы-и-фрустрация)
  - [Персональные предложения](#персональные-предложения)
  - [Маркетинг](#маркетинг)
  - [Поведенческие](#поведенческие)
  - [Целевая переменная](#целевая-переменная)
- [Безопасность](#безопасность)
- [Контакты](#контакты)

## Введение
**Аттестационный проект:**

Демонстрирует комплексное владение навыками архитектора ИИ через создание законченного ML-проекта, включающего все этапы: от сбора требований и проектирования архитектуры данных до разработки, тестирования и развертывания модели машинного обучения.

**Задача:** Прогнозирование оттока клиентов (Customer Churn Prediction)

**Описание:** Построить систему, которая предсказывает вероятность того, что клиент перестанет совершать покупки в течение следующих 2 месяцев.

**Датасет:**

Датасет состоит из данных действующего проекта SaaS-платформы доставки еды, предоставляющая услуги более 700 рестораторам по всей России и зарубежом.
Исходный датасет содержит персональные данные гостей одного из рестораторов, в связи с чем сырые данные могут быть предоставлены только в форме заранее рассчитанных 24 признаков + 1 target (`df_features_raw.csv`) без явного указания персональных данных.

**Бизнес-требования:**
- Precision не менее 0.70 (важно не беспокоить лояльных клиентов)
- Recall не менее 0.65 (важно выявить большинство потенциальных оттоков)
- Модель должна объяснять свои предсказания (интерпретируемость)
- Время инференса: < 100ms на одного клиента

## ML проект для SaaS платформы доставки еды

**Цель анализа:** Предсказание вероятности оттока клиентов (Classification)

**На выходе результат:**
- `churn_probability` — вероятность ухода клиента (0.0 - 1.0)
- `risk_level` — уровень риска (`CRITICAL`/`HIGH`/`MEDIUM`/`LOW`)
- CSV-файлы для маркетинговых команд

**Использование результата:** Проактивная оценка, триггерные push-уведомления и рассылки в мессенджеры для реактивации клиента

**Объект работы:** Сложное поведение гостей на сайте и в приложении

**Технологии:** Python 3.12, PostgreSQL, Elasticsearch, scikit-learn, Pandas

## Быстрый старт

**1. Установка зависимостей**
```bash
pip install -r requirements.txt
```

**2. Настройка подключения к БД**
```bash
cp .env.example .env
```
*Заполните `.env` своими настройками*

**3. Запуск полного пайплайна (от сбора данных до предсказания)**
```bash
python a_data_collection/a_run_pipeline.py            # Шаг 1: Сбор данных из CDP и помещение в БД

\i b_database/bd_create_materialized_views.sql        # Шаг 2: Пересчет 24 признаков в таблице 'mv_ml_features'

\i b_database/be_create_maintenance.sql               # Шаг 3: Перенос данных из 'mv_ml_features' в таблицу 'ml_features'

python c_eda/c_run_pipeline.py                        # Шаг 4: Загрузка сырых данных, EDA, очистка и сохранение CSV

python d_ml_model/d_run_pipeline_class.py --use-cache # Шаг 5: Создание кэша для моделей

python d_ml_model/dc_logistic_regression.py           # Шаг 6: Обучение Logistic Regression

python d_ml_model/dd_random_forest.py                 # Шаг 7: Обучение Random Forest

python d_ml_model/de_gradient_boosting.py             # Шаг 8: Обучение Gradient Boosting

python d_ml_model/df_gridsearch_cv.py                 # Шаг 9: Обучение через cross-validation Logistic Regression

python d_ml_model/dg_compare_models.py                # Шаг 10: Сравнение моделей

python e_inference/e_run_pipeline.py                  # Шаг 11: Предсказание оттока
```

## Архитектура проекта
```bash
┌─────────────────┐     ┌──────────────┐     ┌─────────────
│  CDP (Elastic)  │────▶│  PostgreSQL  │────▶│  EDA/ML     │
│  17 событий     │     │  raw_events  │     │  Training   │
└─────────────────┘     └──────────────┘     ─────────────┘
                               │                      │
                               ▼                      ▼
                        ┌──────────────┐     ┌─────────────┐
                        │  ml_features │◀────│  Inference  │
                        │  24 признака │     │  Predict    │
                        └──────────────┘     └─────────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │  CSV Export  │
                        │  Marketing   │
                        └──────────────┘
```
**Поток данных:**
1. **Сбор** (`a_data_collection`): JS Tracker - CDP Elasticsearch - `events_queue` - `raw_events` + `profiles`
2. **Feature Engineering** (`b_database`): SQL-агрегация 24 признаков - `ml_features`
3. **EDA** (`c_eda`): Загрузка в `df_features_raw.csv` - Анализ качества, визуализация, очистка - `df_features_clean.csv`
4. **ML Training** (`d_ml_model`): 3 модели + GridSearchCV - лучшая модель (`.joblib`)
5. **Inference** (`e_inference`): Предобработка - предсказание - запись в БД + CSV

## Ключевые классы и конфигурация
1. **AppConfig** (`a_data_collection/ac_config.py`)

Единый центр конфигурации для всего проекта. Хранит настройки БД, Elasticsearch и константы ETL.
```python
from a_data_collection.ac_config import PG_CONFIG, ES_CONFIG, BATCH_SIZE

# Пример использования
engine = create_engine(f"postgresql://{PG_CONFIG['user']}:{PG_CONFIG['password']}@...")
```

2. **ml_config.py**

Константы ML-пайплайна (передаются заказчику вместе с моделью):
- `MAX_DAYS_SINCE_ORDER = 900` - порог фильтрации "холодных" пользователей
- `LOG_COLUMNS` - признаки для логарифмирования
- `RISK_THRESHOLDS` - пороги для CRITICAL/HIGH/MEDIUM/LOW
- `BATCH_SIZE_INFERENCE = 1000` - размер батча при обновлении БД

3. **DataPreprocessor** (`d_ml_model/db_class_data_preprocessor.py`)

Класс для подготовки данных к обучению:
- Защита от утечки целевой переменной (исключает `days_since_last_order`)
- Winsorization выбросов (1%-99% перцентили)
- StandardScaler для нормализации
- Кэширование через `joblib`

```python
from d_ml_model.db_class_data_preprocessor import DataPreprocessor

preprocessor = DataPreprocessor(use_cache=True)
data = preprocessor.prepare()
X_train, y_train = data['X_train_scaled'], data['y_train']
```
4. **InferencePreprocessor** (`e_inference/ea_preprocess_inference.py`)

Класс для предобработки сырых данных перед инференсом. Повторяет все шаги обучения:
```python
from e_inference.ea_preprocess_inference import InferencePreprocessor

preprocessor = InferencePreprocessor()
df_processed = preprocessor.transform(df_raw)  # Сырые данные → 26 признаков
probabilities = model.predict_proba(df_processed)[:, 1]
```
## ML Pipeline
### Обучение 4 моделей
Проект сравнивает 4 алгоритма для выбора лучшего:

```markdown
| Модель | ROC-AUC | Recall | F1-Score | Время инференса |
|--------|---------|--------|----------|----------|
| Logistic Regression | 0.8466 | 90.18% | 0.8252 | **0.002 мс** |
| **Random Forest** | **0.8556** | 96.18% | **0.8587** | 0.061 мс |
| Gradient Boosting | 0.8478 | 95.91% | 0.8552 | 0.007 мс |
| **GridSearchCV (LogReg)** | 0.8488 | **97.14%** | 0.8391 | 0.003 |
```

### GridSearchCV оптимизация
Автоматический подбор гиперпараметров для Logistic Regression:
- `C`: [0.01, 0.1, 1.0, 10.0, 100.0]
- `penalty`: ['l1', 'l2']
- `class_weight`: [None, 'balanced']
**Лучшие параметры:** `C=0.01, penalty=l1, class_weight=None` (сильная регуляризация)
**Ключевые метрики для бизнеса**
- **Recall 97.14%** — ловим почти всех уходящих клиентов (GridSearchCV)
- **Скорость <0.01 мс** — в 10,000 раз быстрее требования (100 мс)
- **Интерпретируемость** — можно объяснить бизнесу через коэффициенты модели

## Inference Pipeline
### Шаг 1: Предобработка
Класс `InferencePreprocessor` применяет 9 шагов трансформации:
1. Фильтрация "холодных" пользователей (days < 900)
2. Исключение служебных колонок
3. Перевод bool → int
4. Логарифмирование (log1p)
5. One-Hot Encoding (reviews_reading_behavior → 4 бинарных признака)
6. Winsorization (1%-99%)
7. StandardScaler

### Шаг 2: Предсказание и экспорт
- Загрузка модели `gridsearch_cv_model.joblib`
- Предсказание вероятности оттока
- Определение уровня риска (`CRITICAL`/`HIGH`/`MEDIUM`/`LOW`)
- Запись в БД (`ml_features`)
- Экспорт в 4 CSV-файла для маркетинговых команд
**Пример вывода**
```bash
 ШАГ 2: Предсказание оттока и обновление БД
  - Модель загружена: gridsearch_cv_model.joblib
  - Сделано 6893 предсказаний

 Статистика по уровням риска:
  - CRITICAL: 4082 клиентов (59.2%)
  - HIGH: 731 клиентов (10.6%)
  - MEDIUM: 152 клиентов (2.2%)
  - LOW: 1928 клиентов (28.0%)

 Обновление таблицы ml_features в базе данных...
  - Батч 1: обновлено 1,000 / 6,893 записей (14.5%)
  - Батч 7: обновлено 6,893 / 6,893 записей (100.0%)
  - Успешно обновлено 6893 записей
```

## Ключевые визуализации
### Сравнение моделей

*Сравнение ROC-AUC, Recall, F1-Score и скорости инференса для 4 моделей*

### Важность признаков GridSearchCV

*Топ-15 признаков, влияющих на отток. `checkout_completion_rate (-1.53)` — самый важный*

### GridSearchCV результаты

*Зависимость Recall от параметра C для L1 и L2 регуляризаций. Лучший результат при C=0.01*

### Корреляция признаков с оттоком

*Какие признаки повышают/снижают риск оттока*

## Структура проекта
```bash
churn-prediction-mvp/
── a_data_collection/      # Шаг 1: Сбор данных из CDP
│   ├── a_run_pipeline.py   # Оркестратор
│   ├── aa_fetch_from_cdp.py
│   ├── ab_process_queue.py
│   ├── ac_config.py        # AppConfig (единый конфиг)
│   └── ad_test_pg_connection.py
│
── b_database/             # Шаг 2: SQL-агрегация признаков
│   ├── ba_create_tables.sql
│   ├── bb_create_partitions.sql
│   ├── bc_create_indexes.sql
│   ├── bd_create_materialized_views.sql  # 24 признака + target
│   ├── be_create_maintenance.sql # Перенос в таблицу ml_features
│   ├── bf_test_data.sql
│   └── bg_test_data_testing.sql
│
├── c_eda/                  # Шаг 3: EDA и очистка
│   ├── data/    # данные до/после EDA и очистка CSV
│   ├── c_run_pipeline.py
│   ├── ca_load_data.py
│   ├── cb_explore_data.py
│   ├── cc_quality_check.py
│   ├── cd_visualize.py
│   └── ce_clean_data.py    # Логарифмирование + One-Hot, сохранение в CSV
│
├── d_ml_model/             # Шаг 4: Обучение моделей
│   ├── d_run_pipeline_class.py
│   ├── db_class_data_preprocessor.py  # DataPreprocessor
│   ├── dc_logistic_regression.py
│   ├── dd_random_forest.py
│   ├── de_gradient_boosting.py
│   ├── df_gridsearch_cv.py
│   └── dg_compare_models.py  # Сравнение 4 моделей
│
├── e_inference/            # Шаг 5: Предсказание
│   ├── e_run_pipeline.py
│   ├── ea_preprocess_inference.py  # InferencePreprocessor
│   ├── eb_predict_churn.py
│   └── predictions/        # CSV для маркетинга
│
├── ml_config.py            # ML-константы (для заказчика)
├── requirements.txt
└── .env.example
```

## 24 признака
### Транзакционные
- `days_since_last_order` — дней с последнего заказа
- `avg_cart_value_30d` — средняя сумма корзины
- `cart_to_checkout_ratio` — соотношение корзины к чекауту
- `checkout_value_trend` — тренд суммы заказа
### Отказы и фрустрация
- `cart_abandonment_rate_30d` — % отказов на /checkout
- `checkout_completion_rate` — конверсия оформления
- `checkout_frustration_index` — индекс фрустрации
- `cart_browse_abandon_rate_30d` — % отказов в каталоге
- `auth_on_checkout_flag` — неавторизованный чекаут
### Персональные предложения
- `personal_offer_conversion_rate` — конверсия персонального оффера
- `personal_views_count_30d` — кол-во просмотров персонального оффера
- `avg_copy_reaction_seconds` — время реакции на промокод
### Маркетинг
- `promo_ignore_rate_14d` — % игнорирования акций
- `promo_interest_rate` — интерес к акциям
- `message_open_rate_30d` — % открытых сообщений
- `push_channel_available` — доступен ли push
- `coupon_dependency_ratio` — доля заказов с купоном
- `phone_changed_90d` — менялся ли телефон
### Поведенческие
- `session_engagement_score` — вовлеченность сессии
- `delta_page_views_14d` — дельта просмотров
- `profile_completeness_score` — заполненность профиля
- `avg_rating_90d` — средняя оценка
- `has_unpublished_review` — негативный отзыв
- `reviews_reading_behavior` — паттерн чтения отзывов
### Целевая переменная
- `is_churned` — клиент не заказывал 60+ дней

## Безопасность
- `.env` файл содержит пароли и не коммитится в Git
- `ac_config.py` не передается заказчику (содержит секреты)
- `ml_config.py` безопасен для передачи (только ML-константы)
- SSL-сертификаты для подключения к БД

## Контакты
По вопросам: [vitalii8819@gmail.com]

**Версия:** v1.0
**Последнее обновление:** Август 2026