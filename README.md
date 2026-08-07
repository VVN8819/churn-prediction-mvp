# churn-prediction-mvp

**Аттестационный проект:**

Демонстрирует комплексное владение навыками архитектора ИИ через создание законченного ML-проекта, включающего все этапы: от сбора требований и проектирования архитектуры данных до разработки, тестирования и развертывания модели машинного обучения.

**Задача:** Прогнозирование оттока клиентов (Customer Churn Prediction)

**Описание:** Построить систему, которая предсказывает вероятность того, что клиент перестанет совершать покупки в течение следующих 3 месяцев.

**Датасет:**

Датасет состоит из данных действующего проекта SaaS-платформы доставки еды, предоставляющая услуги более 700 рестораторам по всей России и зарубежом.
Исходный датасет содержит персональные данные гостей одного из рестораторов, в связи с чем сырые данные могут быть предоставлены только в форме заранее рассчитанных 24 признаков + 1 target (`df_features_raw.csv`) без явного указания персональных данных.

**Бизнес-требования:**
- Precision не менее 0.70 (важно не беспокоить лояльных клиентов)
- Recall не менее 0.65 (важно выявить большинство потенциальных оттоков)
- Модель должна объяснять свои предсказания (интерпретируемость)
- Время инференса: < 100ms на одного клиента

**ML-проект для SaaS-платформы доставки еды**

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

```bash
from d_ml_model.db_class_data_preprocessor import DataPreprocessor

preprocessor = DataPreprocessor(use_cache=True)
data = preprocessor.prepare()
X_train, y_train = data['X_train_scaled'], data['y_train']
```
4. **InferencePreprocessor** (`e_inference/ea_preprocess_inference.py`)

Класс для предобработки сырых данных перед инференсом. Повторяет все шаги обучения:
```bash
from e_inference.ea_preprocess_inference import InferencePreprocessor

preprocessor = InferencePreprocessor()
df_processed = preprocessor.transform(df_raw)  # Сырые данные → 26 признаков
probabilities = model.predict_proba(df_processed)[:, 1]
```
