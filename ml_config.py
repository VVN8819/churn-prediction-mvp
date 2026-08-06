# ml_config.py
"""
ml_config.py
Константы для ML-пайплайна
Передается вместе с:
- e_inference/ea_preprocess_inference.py - класс InferencePreprocessor
- models/gridsearch_cv_model.joblib - обученная модель
- models/scaler.joblib - масштабировщик
- requirements.txt - зависимости

Этот файл содержит только параметры предобработки данных,
не содержит секретов (пароли, хосты БД и т.д.)
"""

# Порог фильтрации "холодных" пользователей
MAX_DAYS_SINCE_ORDER = 900

# Колонки для логарифмирования (применяется log1p)
LOG_COLUMNS = [
    'days_since_last_order',
    'avg_cart_value_30d',
    'avg_copy_reaction_seconds',
    'personal_views_count_30d'
]

# Колонки, которые нужно исключить из признаков
COLS_TO_DROP = [
    'profile_id',
    'snapshot_date',
    'computed_at',
    'churn_probability',
    'risk_level',
    'is_churned',
    'model_v1.0',
    'days_since_last_order'  # Защита от утечки целевой переменной
]

# Служебные колонки (не используются для обучения)
SERVICE_COLS = [
    'profile_id',
    'snapshot_date',
    'computed_at',
    'churn_probability',
    'risk_level',
    'is_churned',
    'model_v1.0'
]

# Колонки, которые НЕ должны быть в X (защита от утечки)
EXCLUDE_FROM_FEATURES = ['days_since_last_order']

# Пороги для определения уровня риска оттока
RISK_THRESHOLDS = {
    'CRITICAL': 0.70,    # >= 70% вероятность оттока
    'HIGH': 0.50,    # 50-70% вероятность оттока
    'MEDIUM': 0.30   # 30-50% вероятность оттока
}

# Версия модели
MODEL_VERSION = 'v1.0_gs_cv'


