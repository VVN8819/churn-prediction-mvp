# d_ml_model/di_hypothesis_test.py
"""
d_ml_model/di_hypothesis_test.py
Класс для статистического тестирования гипотез о признаках

Что делает:
- Тестирует гипотезы о различиях между группами признаков
- Использует t-test, Cohen's d и другие статистические методы
- Каждая гипотеза — отдельный метод, который можно пропустить

Использование:
    from d_ml_model.di_hypothesis_test import HypothesisTester
    
    tester = HypothesisTester(skip_hypotheses=['hypothesis_2'])
    tester.run_all(df)
"""

import numpy as np
import pandas as pd
from scipy import stats
from pathlib import Path

# Импортируем классификацию признаков из конфига
from d_ml_model.dh_model_config import (
    TRANSACTIONAL_FEATURES,
    BEHAVIORAL_FEATURES,
    HYPOTHESIS_TEST_ALPHA
)

class HypothesisTester:
    """
    Класс для тестирования статистических гипотез о признаках
    
    Атрибуты:
        skip_hypotheses: список гипотез для пропуска (например, ['hypothesis_2'])
        alpha: уровень значимости для статистических тестов
        plots_dir: директория для сохранения графиков
    """
    
    def __init__(self, skip_hypotheses=None, alpha=HYPOTHESIS_TEST_ALPHA):
        """
        Инициализация тестировщика гипотез
        
        Args:
            skip_hypotheses: список гипотез для пропуска
            alpha: уровень значимости (по умолчанию из конфига)
        """
        self.skip_hypotheses = skip_hypotheses or []
        self.alpha = alpha
        
        # Пути
        self.current_dir = Path(__file__).parent
        self.plots_dir = self.current_dir / "plots"
        
    def run_all(self, df):
        """
        Запускает все гипотезы (кроме пропущенных)
        
        Args:
            df: DataFrame с признаками и целевой переменной is_churned
        """
        print("\nТестирование Гипотез о признаках")
        
        # Считаем корреляции один раз для всех гипотез
        correlations = self._calculate_correlations(df)
        
        # Гипотеза 1: Транзакционные vs поведенческие признаки
        if 'hypothesis_1' not in self.skip_hypotheses:
            self.test_hypothesis_1(correlations)
        else:
            print("\n -  Гипотеза 1 пропущена (--skip-hypothesis-1)")
        
        print("\nТестирование Гипотез ЗАВЕРШЕНО")
        
    def _calculate_correlations(self, df):
        """
        Рассчитывает корреляцию Пирсона каждого признака с is_churned
        
        Args:
            df: DataFrame с признаками и целевой переменной
            
        Returns:
            Series с корреляциями, отсортированный по абсолютному значению
        """
        # Выбираем только числовые колонки
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        exclude_cols = [
            'profile_id', 'snapshot_date', 'computed_at',
            'churn_probability', 'risk_level', 'is_churned', 'model_v1.0'
        ]
        feature_cols = [col for col in numeric_cols if col not in exclude_cols]
        
        correlations = df[feature_cols].corrwith(df['is_churned']).dropna()
        correlations_sorted = correlations.reindex(correlations.abs().sort_values(ascending=False).index)
        
        return correlations_sorted
        
    def test_hypothesis_1(self, correlations):
        """
        Гипотеза 1: Транзакционные признаки лучше предсказывают отток, 
        чем поведенческие
        
        H0: Средние абсолютные корреляции равны
        H1: Средние абсолютные корреляции различаются
        
        Метод: Welch's t-test + Cohen's d
        """
        print("\nГипотеза 1: Транзакционные vs поведенческие признаки")
        print("H0: Средние корреляции равны")
        print("H1: Средние корреляции различаются")
        print()
        
        # Классификация признаков (из конфига)
        transactional_features = TRANSACTIONAL_FEATURES
        behavioral_features = BEHAVIORAL_FEATURES
        
        # Фильтруем только существующие признаки в данных
        trans_features = [f for f in transactional_features if f in correlations.index]
        behav_features = [f for f in behavioral_features if f in correlations.index]
        
        print(f"\nТранзакционные признаки ({len(trans_features)}):")
        for feat in trans_features:
            corr = correlations[feat]
            print(f"  - {feat}: {corr:.4f}")
        
        print(f"\nПоведенческие признаки ({len(behav_features)}):")
        for feat in behav_features:
            corr = correlations[feat]
            print(f"  - {feat}: {corr:.4f}")
        
        # Рассчитываем среднюю абсолютную корреляцию
        trans_abs_corr = correlations[trans_features].abs()
        behav_abs_corr = correlations[behav_features].abs()
        
        trans_mean = trans_abs_corr.mean()
        behav_mean = behav_abs_corr.mean()
        
        print("\nРезультаты сравнения:")
        print(f"Средняя абсолютная корреляция (транзакционные): {trans_mean:.4f}")
        print(f"Средняя абсолютная корреляция (поведенческие):  {behav_mean:.4f}")
        
        if behav_mean > trans_mean:
            diff = behav_mean - trans_mean
            pct_improvement = (diff / trans_mean) * 100
            print(f"\nПоведенческие признаки лучше на: {diff:.4f} ({pct_improvement:.1f}%)")
        else:
            diff = trans_mean - behav_mean
            pct_improvement = (diff / behav_mean) * 100
            print(f"\nТранзакционные признаки лучше на: {diff:.4f} ({pct_improvement:.1f}%)")
        
        # T-TEST для проверки значимости
        print("\nСтатистический тест (t-test):")
        
        t_statistic, p_value = stats.ttest_ind(
            behav_abs_corr,  # behavioral features
            trans_abs_corr,  # transactional features
            equal_var=False  # Welch's t-test (не предполагаем равные дисперсии)
        )
        
        print(f"t-статистика: {t_statistic:.4f}")
        print(f"p-value: {p_value:.6f}")
        print(f"Уровень значимости (alpha): {self.alpha}")
        
        if p_value < self.alpha:
            print(f"\n Результат: Статистически значимое различие (p < {self.alpha})")
            print("  H0 отвергается - средние корреляции РАЗЛИЧАЮТСЯ")
            
            if behav_mean > trans_mean:
                print(f"  - Поведенческие признаки действительно лучше предсказывают отток")
            else:
                print(f"  - Транзакционные признаки лучше предсказывают отток")
        else:
            print(f"\n Результат: Различия НЕ статистически значимы (p >= {self.alpha})")
            print("  H0 НЕ отвергается - средние корреляции НЕ различаются")
            print("  - Нет доказательств, что один тип признаков лучше другого")

        # Эффект размера (Cohen's d)
        pooled_std = np.sqrt((trans_abs_corr.std()**2 + behav_abs_corr.std()**2) / 2)
        cohens_d = (behav_mean - trans_mean) / pooled_std
        
        print(f"\nРазмер эффекта (Cohen's d): {cohens_d:.4f}")
        if abs(cohens_d) < 0.2:
            print("  Интерпретация: Очень маленький эффект")
        elif abs(cohens_d) < 0.5:
            print("  Интерпретация: Маленький эффект")
        elif abs(cohens_d) < 0.8:
            print("  Интерпретация: Средний эффект")
        else:
            print("  Интерпретация: Большой эффект")
        
        