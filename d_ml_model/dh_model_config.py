# d_ml_model/dh_model_config.py
"""
- Конфигурация весов для сравнения моделей
- Классификация признаков для тестирования гипотез
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

# Классификация признаков для тестирования гипотез
# Транзакционные признаки (связаны с покупками и чеками)
TRANSACTIONAL_FEATURES = [
    'days_since_last_order',
    'avg_cart_value_30d',
    'cart_to_checkout_ratio',
    'checkout_value_trend',
    'coupon_dependency_ratio'
]

# Поведенческие признаки (связаны с активностью и вовлеченностью)
BEHAVIORAL_FEATURES = [
    'cart_abandonment_rate_30d',
    'checkout_completion_rate',
    'checkout_frustration_index',
    'cart_browse_abandon_rate_30d',
    'auth_on_checkout_flag',
    'promo_ignore_rate_14d',
    'session_engagement_score',
    'message_open_rate_30d',
    'push_channel_available',
    'phone_changed_90d',
    'avg_rating_90d',
    'profile_completeness_score',
    'delta_page_views_14d',
    'has_unpublished_review',
    'personal_offer_conversion_rate',
    'personal_views_count_30d',
    'avg_copy_reaction_seconds',
    'promo_interest_rate'
]

# Уровень значимости для статистических тестов (t-test)
HYPOTHESIS_TEST_ALPHA = 0.05


