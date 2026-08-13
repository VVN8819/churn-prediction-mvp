# d_ml_model/dh_model_weights.py
"""
Конфигурация весов для сравнения моделей
Можно менять без изменения кода сравнения
"""

# Веса метрик
MODEL_SELECTION_WEIGHTS = {
    'recall': 0.40,           # не пропустить уходящих
    'roc_auc': 0.25,          # общая разделяющая способность
    'f1_score': 0.15,         # баланс precision/recall
    'speed_score': 0.10,      # скорость инференса
    'precision': 0.05,        # избегать ложных срабатываний
    'interpretability': 0.05  # возможность объяснить бизнесу
}

# Порог требования к скорости (мс)
INFERENCE_TIME_REQUIREMENT_MS = 100

# Нормализация: чем выше метрика, тем лучше
HIGHER_IS_BETTER = {
    'recall': True,
    'roc_auc': True,
    'f1_score': True,
    'speed_score': False, # Для скорости: чем меньше, тем лучше
    'precision': True,
    'interpretability': True
}