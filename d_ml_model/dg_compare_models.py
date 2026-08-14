# d_ml_model/dg_compare_models.py
"""
d_ml_model/dg_compare_models.py
Финальное сравнение всех обученных моделей:
- Logistic Regression (baseline)
- Random Forest
- Gradient Boosting
- GridSearchCV (оптимизированная Logistic Regression)

Собирает метрики из текстовых файлов, строит матрицу принятия решения и сравнительные графики.
Статистический анализ (Bootstrap CI, Z-test, Гипотеза 2).
"""

import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import re
import numpy as np
from scipy import stats as scipy_stats

# Настройка путей
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

CURRENT_DIR = Path(__file__).parent
MODELS_DIR = CURRENT_DIR / "models"
PLOTS_DIR = CURRENT_DIR / "plots"

# Импортируем веса из конфига
from d_ml_model.dh_model_config import (
    MODEL_SELECTION_WEIGHTS,
    INFERENCE_TIME_REQUIREMENT_MS,
    CONFIDENCE_LEVEL,
    BOOTSTRAP_ITERATIONS,
    CI_METHOD,
    HYPOTHESIS_2_IMPROVEMENT_THRESHOLD,
    TEST_POSITIVE_SAMPLES
)

# Создаем папку для графиков, если её нет
PLOTS_DIR.mkdir(exist_ok=True)

def parse_metrics_file(filepath):
    """Парсит текстовый файл с метриками модели"""
    metrics = {}
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Извлекаем метрики с помощью регулярных выражений
    patterns = {
        'accuracy': r'Accuracy:\s*([\d.]+)',
        'precision': r'Precision:\s*([\d.]+)',
        'recall': r'Recall:\s*([\d.]+)',
        'f1_score': r'F1-Score:\s*([\d.]+)',
        'roc_auc': r'ROC-AUC:\s*([\d.]+)',
        'total_inference_time': r'Общее время инференса:\s*([\d.]+)\s*ms',
        'avg_inference_time': r'Среднее время инференса на гостя:\s*([\d.]+)\s*ms',
        'requirement_met': r'Требования ко времени инференса.*?:(.*?)\n'
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, content)
        if match:
            value = match.group(1).strip()
            if key in ['total_inference_time', 'avg_inference_time']:
                metrics[key] = float(value)
            elif key == 'requirement_met':
                metrics[key] = 'Хорошо' if 'выполнено' in value.lower() else 'Плохо'
            else:
                metrics[key] = float(value)
                
    return metrics

def calculate_interpretability_score(model_name):
    """
    Возвращает оценку интерпретируемости (0-1)
    """
    if 'Logistic' in model_name or 'GridSearchCV' in model_name:
        return 1.0  # Полная интерпретируемость
    elif 'Random Forest' in model_name:
        return 0.6  # Средняя (важность признаков)
    elif 'Gradient' in model_name:
        return 0.4  # Низкая (ансамбль деревьев)
    return 0.5

def calculate_weighted_scores(df_metrics):
    """
    Рассчитывает взвешенные баллы для каждой модели
    Используем АБСОЛЮТНЫЕ значения метрик (без нормализации)
    """
    df_scores = df_metrics.copy()
    
    # Прямой расчет взвешенных баллов (метрики уже в диапазоне 0-1)
    df_scores['recall_score'] = df_scores['recall'] * MODEL_SELECTION_WEIGHTS['recall']
    df_scores['roc_auc_score'] = df_scores['roc_auc'] * MODEL_SELECTION_WEIGHTS['roc_auc']
    df_scores['f1_score_weighted'] = df_scores['f1_score'] * MODEL_SELECTION_WEIGHTS['f1_score']
    df_scores['precision_score'] = df_scores['precision'] * MODEL_SELECTION_WEIGHTS['precision']
    
    # Для скорости: инвертируем (чем меньше время, тем больше баллов)
    # Нормализуем относительно требования (100 мс)
    max_time = INFERENCE_TIME_REQUIREMENT_MS  # 100 мс
    df_scores['speed_score'] = (1 - df_scores['avg_inference_time'] / max_time) * MODEL_SELECTION_WEIGHTS['speed_score']
    
    # Интерпретируемость (категориальная оценка)
    df_scores['interpretability_norm'] = df_scores['model'].apply(
        calculate_interpretability_score
    )
    df_scores['interpretability_score'] = df_scores['interpretability_norm'] * MODEL_SELECTION_WEIGHTS['interpretability']
    
    # Итоговый балл
    df_scores['total_score'] = (
        df_scores['recall_score'] +
        df_scores['roc_auc_score'] +
        df_scores['f1_score_weighted'] +
        df_scores['speed_score'] +
        df_scores['precision_score'] +
        df_scores['interpretability_score']
    )
    
    return df_scores

def print_decision_matrix(df_scores):
    """
    Выводит матрицу принятия решения с весами и баллами
    """
    print("\nМатрица принятия решения")
    
    # Заголовок таблицы
    header = f"{'Модель':<20} "
    metrics_header = ""
    weights_header = ""
    
    for metric, weight in MODEL_SELECTION_WEIGHTS.items():
        col_name = metric.replace('_score', '').replace('_', ' ').title()
        metrics_header += f"{col_name:>12} "
        weights_header += f"({weight*100:>3.0f}%) {'':6} "
    
    header += metrics_header + f"{'Итого':>10}"
    print(header)
    print(" " * 20 + " " + weights_header)
    
    # Строки с данными (показываем абсолютные значения метрик 0-1)
    for idx, row in df_scores.iterrows():
        line = f"{row['model']:<20} "
        line += f"{row['recall']:>11.4f} "
        line += f"{row['roc_auc']:>11.4f} "
        line += f"{row['f1_score']:>11.4f} "
        line += f"{row['speed_score']/MODEL_SELECTION_WEIGHTS['speed_score']:>11.4f} "
        line += f"{row['precision']:>11.4f} "
        line += f"{row['interpretability_norm']:>11.1f} "
        line += f"{row['total_score']:>10.4f}"
        print(line)
    
    print("\nРасчет итогового балла:")
    print("  Total = (Recall × 40%) + (ROC-AUC × 25%) + (F1 × 15%) + (Speed × 10%) + (Precision × 5%) + (Interpret. × 5%)")
    print("\nПримечание:")
    print("  - Все метрики используют абсолютные значения (0-1)")
    print("  - Для скорости: Score = (1 - время/100мс) × 10%")

def get_quality_description(roc_auc):
    """Возвращает текстовое описание качества модели по ROC-AUC"""
    if roc_auc >= 0.90:
        return "отличная разделяющая способность"
    elif roc_auc >= 0.80:
        return "высокая разделяющая способность"
    elif roc_auc >= 0.70:
        return "хорошая разделяющая способность"
    elif roc_auc >= 0.60:
        return "удовлетворительная разделяющая способность"
    else:
        return "низкая разделяющая способность"
    
def get_interpretability_description(model_name):
    """Возвращает описание интерпретируемости модели"""
    if 'Logistic' in model_name or 'GridSearchCV' in model_name:
        return "Полная интерпретируемость (можно объяснить бизнесу через коэффициенты)"
    elif 'Random Forest' in model_name:
        return "Средняя интерпретируемость (важность признаков, но без направления влияния)"
    elif 'Gradient' in model_name:
        return "Низкая интерпретируемость (ансамбль деревьев)"
    return "Интерпретируемость неизвестна"

# Функции статистического анализа
def bootstrap_recall_ci(recall, n_positive, confidence=CONFIDENCE_LEVEL, 
                        n_iterations=BOOTSTRAP_ITERATIONS):
    """
    Рассчитывает Bootstrap доверительный интервал для Recall
    
    Метод: симуляция биномиального распределения
    На каждой итерации генерируем количество "успехов" (правильно предсказанных
    ушедших клиентов) из биномиального распределения и считаем долю.
    
    Args:
        recall: значение Recall (0-1)
        n_positive: количество положительных примеров в тесте
        confidence: уровень доверия (0.95 = 95%)
        n_iterations: количество bootstrap-итераций
    
    Returns:
        (lower, upper) - границы доверительного интервала
    """
    bootstrap_recalls = []
    
    for _ in range(n_iterations):
        # Симуляция: сколько из n_positive клиентов модель правильно определит
        successes = np.random.binomial(n_positive, recall)
        bootstrap_recalls.append(successes / n_positive)
    
    alpha = 1 - confidence
    lower = np.percentile(bootstrap_recalls, 100 * alpha / 2)
    upper = np.percentile(bootstrap_recalls, 100 * (1 - alpha / 2))
    
    return lower, upper

def compare_two_recalls_ztest(recall_1, recall_2, n_positive):
    """
    Z-test для сравнения двух Recall (двух пропорций)
    
    Проверяет, статистически значимо ли отличаются два Recall,
    рассчитанных на одной и той же тестовой выборке.
    
    Args:
        recall_1: Recall первой модели (baseline)
        recall_2: Recall второй модели (optimized)
        n_positive: количество положительных примеров в тесте
    
    Returns:
        dict с z_statistic, p_value, significant
    """
    # Стандартные ошибки для каждой пропорции
    se1 = np.sqrt(recall_1 * (1 - recall_1) / n_positive)
    se2 = np.sqrt(recall_2 * (1 - recall_2) / n_positive)
    
    # Объединённая стандартная ошибка разности
    se_diff = np.sqrt(se1**2 + se2**2)
    
    if se_diff == 0:
        return {'z_statistic': 0.0, 'p_value': 1.0, 'significant': False}
    
    # Z-статистика
    z = (recall_2 - recall_1) / se_diff
    
    # Двусторонний p-value
    p_value = 2 * (1 - scipy_stats.norm.cdf(abs(z)))
    
    return {
        'z_statistic': z,
        'p_value': p_value,
        'significant': p_value < 0.05
    }
    
def calculate_improvement_percentage(recall_new, recall_baseline):
    """
    Рассчитывает процент улучшения Recall
    
    Args:
        recall_new: Recall новой (оптимизированной) модели
        recall_baseline: Recall baseline модели
    
    Returns:
        float: процент улучшения
    """
    if recall_baseline == 0:
        return 0.0
    return ((recall_new - recall_baseline) / recall_baseline) * 100

def print_statistical_analysis(df_metrics):
    """
    Выводит полный статистический анализ сравнения моделей:
    - Bootstrap доверительные интервалы для Recall каждой модели
    - Z-test сравнения GridSearchCV vs baseline (Logistic Regression)
    - Процент улучшения
    - Проверка порога 5% из Гипотезы 2
    """
    print("\nСтатистический анализ сравнения моделей")
    
    # Базовая модель для сравнения
    baseline_name = 'Logistic Regression'
    optimized_name = 'GridSearchCV'
    
    baseline_row = df_metrics[df_metrics['model'] == baseline_name].iloc[0]
    optimized_row = df_metrics[df_metrics['model'] == optimized_name].iloc[0]
    
    baseline_recall = baseline_row['recall']
    optimized_recall = optimized_row['recall']
    
    # Количество положительных примеров в тесте
    n_positive = TEST_POSITIVE_SAMPLES
    
    print(f"\n- Сравнение: {optimized_name} vs {baseline_name}")
    print(f"   Количество положительных примеров в тесте: {n_positive}")
    print(f"   Уровень доверия: {CONFIDENCE_LEVEL*100:.0f}%")
    print(f"   Метод CI: {CI_METHOD}")
    print(f"   Bootstrap итераций: {BOOTSTRAP_ITERATIONS}")
    print()
    
    # Блок 1: Доверительные интервалы для Recall каждой модели
    print("\n - Доверительные интервалы для Recall (Bootstrap):")
    
    for _, row in df_metrics.iterrows():
        if CI_METHOD == 'bootstrap':
            ci_lower, ci_upper = bootstrap_recall_ci(
                row['recall'], n_positive, CONFIDENCE_LEVEL, BOOTSTRAP_ITERATIONS
            )
        else:
            # Нормальное приближение (fallback)
            z = scipy_stats.norm.ppf(1 - (1 - CONFIDENCE_LEVEL) / 2)
            se = np.sqrt(row['recall'] * (1 - row['recall']) / n_positive)
            ci_lower = max(0, row['recall'] - z * se)
            ci_upper = min(1, row['recall'] + z * se)
        
        ci_width = ci_upper - ci_lower
        
        # Подсветка лучшей модели
        marker = " ПОБЕДА!" if row['model'] == optimized_name else ""
        
        print(f"   {row['model']:<25} Recall={row['recall']:.4f}  "
              f"95% CI=[{ci_lower:.4f}, {ci_upper:.4f}]  "
              f"(ширина: ±{ci_width/2:.4f}){marker}")
    
    # Блок 2: Z-test сравнения GridSearchCV vs baseline
    print(f"\n - Z-test: {optimized_name} vs {baseline_name}")
    
    test_result = compare_two_recalls_ztest(baseline_recall, optimized_recall, n_positive)
    
    print(f"   Recall {baseline_name}: {baseline_recall:.4f}")
    print(f"   Recall {optimized_name}: {optimized_recall:.4f}")
    print(f"   Абсолютное улучшение:   {optimized_recall - baseline_recall:+.4f}")
    
    improvement_pct = calculate_improvement_percentage(optimized_recall, baseline_recall)
    print(f"   Относительное улучшение: {improvement_pct:+.2f}%")
    print()
    print(f"   Z-статистика: {test_result['z_statistic']:.4f}")
    print(f"   P-value:      {test_result['p_value']:.6f}")
    
    if test_result['p_value'] < 0.001:
        print(f"   - РЕЗУЛЬТАТ: Статистически значимое улучшение (p < 0.001)")
    elif test_result['p_value'] < 0.01:
        print(f"   - РЕЗУЛЬТАТ: Статистически значимое улучшение (p < 0.01)")
    elif test_result['p_value'] < 0.05:
        print(f"   - РЕЗУЛЬТАТ: Статистически значимое улучшение (p < 0.05)")
    else:
        print(f"   - РЕЗУЛЬТАТ: Улучшение НЕ статистически значимо (p >= 0.05)")
    
    # Блок 3: Проверка Гипотезы 2 (порог 5%)
    print(f"\n - Проверка Гипотезы 2:")
    print(f"   H0: GridSearchCV не улучшает Recall на ≥ {HYPOTHESIS_2_IMPROVEMENT_THRESHOLD*100:.0f}% "
          f"по сравнению с {baseline_name}")
    print(f"   H1: GridSearchCV улучшает Recall на ≥ {HYPOTHESIS_2_IMPROVEMENT_THRESHOLD*100:.0f}% "
          f"по сравнению с {baseline_name}")
    print()
    
    threshold_met = improvement_pct >= HYPOTHESIS_2_IMPROVEMENT_THRESHOLD * 100
    statistically_significant = test_result['p_value'] < 0.05
    
    print(f"   Порог улучшения ({HYPOTHESIS_2_IMPROVEMENT_THRESHOLD*100:.0f}%): "
          f"{' - ДОСТИГНУТ' if threshold_met else ' - НЕ ДОСТИГНУТ'} "
          f"(факт: {improvement_pct:+.2f}%)")
    print(f"   Статистическая значимость: "
          f"{' - ЕСТЬ' if statistically_significant else ' - НЕТ'} "
          f"(p = {test_result['p_value']:.6f})")
    print()
    
    # Итоговый вывод по Гипотезе 2
    if threshold_met and statistically_significant:
        print("   - ВЫВОД: Гипотеза 2 ПОДТВЕРЖДЕНА")
        print("      GridSearchCV значимо улучшает Recall на ≥ 5% по сравнению с baseline")
    elif statistically_significant and not threshold_met:
        print("   -  ВЫВОД: Гипотеза 2 ЧАСТИЧНО ПОДТВЕРЖДЕНА")
        print("      Улучшение статистически значимо, но не достигает порога 5%")
        print(f"      Фактическое улучшение: {improvement_pct:+.2f}%")
        print(f"      Не хватает до порога: {HYPOTHESIS_2_IMPROVEMENT_THRESHOLD*100 - improvement_pct:.2f}%")
    elif threshold_met and not statistically_significant:
        print("   -  ВЫВОД: Гипотеза 2 ЧАСТИЧНО ПОДТВЕРЖДЕНА")
        print("      Порог 5% достигнут, но улучшение НЕ статистически значимо")
        print("      Возможно, требуется больше данных для подтверждения")
    else:
        print("   - ВЫВОД: Гипотеза 2 НЕ ПОДТВЕРЖДЕНА")
        print("      Улучшение не достигает порога 5% и не является статистически значимым")
    
    # Блок 4: Практическая интерпретация для бизнеса
    print(f"\n - Практическая интерпретация для бизнеса:")
    
    # Сколько дополнительных клиентов "поймали" благодаря GridSearchCV
    additional_caught = int((optimized_recall - baseline_recall) * n_positive)
    missed_by_baseline = int((1 - baseline_recall) * n_positive)
    missed_by_optimized = int((1 - optimized_recall) * n_positive)
    
    print(f"   Из {n_positive} ушедших клиентов в тестовой выборке:")
    print(f"   - {baseline_name} находит: {int(baseline_recall * n_positive)} клиентов "
          f"(пропускает {missed_by_baseline})")
    print(f"   - {optimized_name} находит: {int(optimized_recall * n_positive)} клиентов "
          f"(пропускает {missed_by_optimized})")
    print(f"   - Дополнительно поймано: {additional_caught} клиентов")
    print()
    print(f"   Если средний чек клиента = 991.69:")
    print(f"   - Потерянная выручка при {baseline_name}: {missed_by_baseline * 991.69:,.2f}₽")
    print(f"   - Потерянная выручка при {optimized_name}: {missed_by_optimized * 991.69:,.2f}₽")
    print(f"   - Сохранённая выручка: {(missed_by_baseline - missed_by_optimized) * 991.69:,.2f}₽")
    
    return {
        'baseline_recall': baseline_recall,
        'optimized_recall': optimized_recall,
        'improvement_pct': improvement_pct,
        'p_value': test_result['p_value'],
        'threshold_met': threshold_met,
        'statistically_significant': statistically_significant,
        'additional_caught': additional_caught,
    }   
    
def compare_models():
    """Главная функция сравнения моделей"""
    
    print("\nФинальное сравнение моделей ML для прогнозирования оттока")
    
    # 1. Загружаем метрики всех моделей
    models_data = {
        'Logistic Regression': MODELS_DIR / 'logistic_regression_metrics.txt',
        'Random Forest': MODELS_DIR / 'random_forest_metrics.txt',
        'Gradient Boosting': MODELS_DIR / 'gradient_boosting_metrics.txt',
        'GridSearchCV': MODELS_DIR / 'gridsearch_cv_metrics.txt'
    }
    
    all_metrics = []
    
    for model_name, filepath in models_data.items():
        if filepath.exists():
            metrics = parse_metrics_file(filepath)
            metrics['model'] = model_name
            all_metrics.append(metrics)
            print(f"- Загружены метрики: {model_name}")
        else:
            print(f"-  Файл не найден: {filepath}")

    # Создаем DataFrame
    df_metrics = pd.DataFrame(all_metrics)
    
    # 2. Рассчитываем взвешенные баллы
    df_scores = calculate_weighted_scores(df_metrics)
    
    # 3. Выводим матрицу принятия решения
    print_decision_matrix(df_scores)
    
    # 4. Вывод сводной таблицы
    print("\n - Сводная таблица метрик")
    
    display_cols = ['model', 'accuracy', 'precision', 'recall', 'f1_score',
                    'roc_auc', 'avg_inference_time', 'requirement_met']
    
    df_display = df_metrics[display_cols].copy()
    df_display.columns = ['Модель', 'Accuracy', 'Precision', 'Recall', 
                          'F1-Score', 'ROC-AUC', 'Время среднее (мс)', 'Требование <100мс']
    
    # Форматируем числа
    for col in ['Accuracy', 'Precision', 'Recall', 'F1-Score', 'ROC-AUC']:
        df_display[col] = df_display[col].apply(lambda x: f"{x:.4f}")
        
    df_display['Время среднее (мс)'] = df_display['Время среднее (мс)'].apply(lambda x: f"{x:.4f}")
    
    print('\n', df_display.to_string(index=False))
    
    # 5. Визуализация: Сравнение ключевых метрик
    plt.figure(figsize=(16, 12))
    
    # График 1: ROC-AUC
    plt.subplot(2, 2, 1)
    colors = ['#3498db', '#2ecc71', '#e74c3c', '#f39c12']
    bar = plt.bar(range(len(df_metrics)), df_metrics['roc_auc'],
                  color=colors, edgecolor='black', alpha=0.7)
    plt.xticks(range(len(df_metrics)), df_metrics['model'], rotation=15, ha='right')
    plt.ylabel('ROC-AUC', fontsize=12, fontweight='bold')
    plt.title('Сравнение ROC-AUC', fontsize=14, fontweight='bold')
    plt.ylim(0.75, 0.90)
    plt.grid(axis='y', linestyle=':', alpha=0.7)
    
    # Добавляем значения на столбцы
    for i, v in enumerate(df_metrics['roc_auc']):
        plt.text(i, v + 0.005, f"{v:.3f}", ha='center', fontsize=10, fontweight='bold')
    
    # График 2: Recall
    plt.subplot(2, 2, 2)
    bars = plt.bar(range(len(df_metrics)), df_metrics['recall'], 
                   color=colors, edgecolor='black', alpha=0.7)
    plt.xticks(range(len(df_metrics)), df_metrics['model'], rotation=15, ha='right')
    plt.ylabel('Recall', fontsize=12, fontweight='bold')
    plt.title('Сравнение Recall (доля найденных ушедших)', fontsize=14, fontweight='bold')
    plt.ylim(0.90, 1.00)
    plt.grid(axis='y', linestyle=':', alpha=0.7)
    
    for i, v in enumerate(df_metrics['recall']):
        plt.text(i, v + 0.002, f"{v:.3f}", ha='center', fontsize=10, fontweight='bold')
    
    # График 3: F1-Score
    plt.subplot(2, 2, 3)
    bars = plt.bar(range(len(df_metrics)), df_metrics['f1_score'], 
                   color=colors, edgecolor='black', alpha=0.7)
    plt.xticks(range(len(df_metrics)), df_metrics['model'], rotation=15, ha='right')
    plt.ylabel('F1-Score', fontsize=12, fontweight='bold')
    plt.title('Сравнение F1-Score (баланс Precision/Recall)', fontsize=14, fontweight='bold')
    plt.ylim(0.75, 0.90)
    plt.grid(axis='y', linestyle=':', alpha=0.7)
    
    for i, v in enumerate(df_metrics['f1_score']):
        plt.text(i, v + 0.005, f"{v:.3f}", ha='center', fontsize=10, fontweight='bold')
    
    # График 4: Время инференса (логарифмическая шкала)
    plt.subplot(2, 2, 4)
    bars = plt.bar(range(len(df_metrics)), df_metrics['avg_inference_time'], 
                   color=colors, edgecolor='black', alpha=0.7)
    plt.xticks(range(len(df_metrics)), df_metrics['model'], rotation=15, ha='right')
    plt.ylabel('Время инференса (мс)', fontsize=12, fontweight='bold')
    plt.title('Сравнение скорости инференса', fontsize=14, fontweight='bold')
    plt.yscale('log')
    plt.grid(axis='y', linestyle=':', alpha=0.7)
    
    # Линия требования 100 мс
    plt.axhline(y=INFERENCE_TIME_REQUIREMENT_MS, color='red', linestyle='--',
                linewidth=2, label=f'Требование: {INFERENCE_TIME_REQUIREMENT_MS} мс')
    plt.legend()
    
    for i, v in enumerate(df_metrics['avg_inference_time']):
        plt.text(i, v * 1.5, f"{v:.4f}", ha='center', fontsize=9, fontweight='bold')
        
    plt.tight_layout()
    comparison_plot_path = PLOTS_DIR / "11_models_comparison.png"
    plt.savefig(comparison_plot_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"\n- Сравнительный график сохранен: {comparison_plot_path}")
    
    # 6. Определение лучшей модели по итоговому баллу
    print("\nЛучшая модели по итоговому баллу")
    
    best_model = df_scores.loc[df_scores['total_score'].idxmax()]
    
    print(f"\n- Лучшая модели: {best_model['model']}")
    print(f"   Итоговый балл: {best_model['total_score']:.4f}")
    print(f"\n   Детализация вклада в итоговый балл:")
    print(f"   - Recall (40%):          {best_model['recall_score']:.4f}")
    print(f"   - ROC-AUC (25%):         {best_model['roc_auc_score']:.4f}")
    print(f"   - F1-Score (15%):        {best_model['f1_score_weighted']:.4f}")
    print(f"   - Speed (10%):           {best_model['speed_score']:.4f}")
    print(f"   - Precision (5%):        {best_model['precision_score']:.4f}")
    print(f"   - Interpretability (5%): {best_model['interpretability_score']:.4f}")
    
    print(f"\n   Фактические метрики:")
    print(f"   - Recall: {best_model['recall']:.4f} ({best_model['recall']*100:.2f}%)")
    print(f"   - ROC-AUC: {best_model['roc_auc']:.4f}")
    print(f"   - F1-Score: {best_model['f1_score']:.4f}")
    print(f"   - Precision: {best_model['precision']:.4f}")
    print(f"   - Скорость: {best_model['avg_inference_time']:.4f} мс")
    
    # Показываем топ-2 модели
    top_2 = df_scores.nlargest(2, 'total_score')
    if len(top_2) > 1:
        second_best = top_2.iloc[1]
        score_diff = (best_model['total_score'] - second_best['total_score']) * 100
        print(f"\n   Отрыв от 2-го места ({second_best['model']}): +{score_diff:.2f} баллов")
    
    # 7. Дополнительные рекомендации
    print("\n - Рекомендации для продакшена -")

    # Лучшая по ROC-AUC
    best_roc_auc = df_metrics.loc[df_metrics['roc_auc'].idxmax()]
    print(f"\n - Лучшая по ROC-AUC: {best_roc_auc['model']}")
    print(f"   ROC-AUC: {best_roc_auc['roc_auc']:.4f}")
    
    # Лучшая по Recall
    best_recall = df_metrics.loc[df_metrics['recall'].idxmax()]
    print(f"\n - Лучшая по Recall: {best_recall['model']}")
    print(f"   Recall: {best_recall['recall']:.4f}")
    
    # Лучшая по F1-Score
    best_f1 = df_metrics.loc[df_metrics['f1_score'].idxmax()]
    print(f"\n -  Лучшая по F1-Score: {best_f1['model']}")
    print(f"   F1-Score: {best_f1['f1_score']:.4f}")
    
    # Самая быстрая
    fastest = df_metrics.loc[df_metrics['avg_inference_time'].idxmin()]
    print(f"\n - Самая быстрая: {fastest['model']}")
    print(f"   Время: {fastest['avg_inference_time']:.4f} мс")

    # Итоговая рекомендация
    print("\n - Итоговая рекомендация -")
    
    # Для задачи оттока важен Recall (не пропустить уходящих клиентов)
    # Но также важна скорость для real-time инференса

    # Вычисляем динамические значения
    best_recall_roc_auc = best_recall['roc_auc']
    best_recall_speed = best_recall['avg_inference_time']
    speed_ratio = int(INFERENCE_TIME_REQUIREMENT_MS / best_recall_speed)
    quality_desc = get_quality_description(best_recall_roc_auc)
    interpretability_desc = get_interpretability_description(best_recall['model'])
    
    recall_percent = best_recall['recall'] * 100
    
    print("\nДля MVP SaaS-платформы доставки еды рекомендуется избегать ошибок в ложном утверждении, что гость останется, но и не пропустить уходящих. Для этой цели лучше всего подойдет модель:")
    print(f"\n {best_recall['model']}")
    print("\nПреимущества:")
    print("  - Лучший баланс качества и интерпретируемости")
    print(f"  - Recall: {best_recall['recall']:.4f} (ловим {recall_percent}% уходящих гостей)")
    print(f"  - ROC-AUC: {best_recall_roc_auc:.4f} ({quality_desc})")
    print(f"  - Скорость: ~{best_recall_speed:.4f} мс (в {speed_ratio:,} раз быстрее требования < {INFERENCE_TIME_REQUIREMENT_MS} мс)")
    print(f"  - {interpretability_desc}")
    print("  - Простота поддержки и деплоя")
    
    # Альтернатива
    best_roc_auc_speed = best_roc_auc['avg_inference_time']
    best_roc_auc_speed_ratio = int(INFERENCE_TIME_REQUIREMENT_MS / best_roc_auc_speed)
    best_roc_auc_quality = get_quality_description(best_roc_auc['roc_auc'])
    best_roc_auc_interpretability = get_interpretability_description(best_roc_auc['model'])
    
    print("\nАльтернатива для максимальной точности (ROC-AUC):")
    print(f" {best_roc_auc['model']}")
    print(f"  - Лучший ROC-AUC: {best_roc_auc['roc_auc']:.4f} ({best_roc_auc_quality})")
    print(f"  - Recall: {best_roc_auc['recall']:.4f}")
    print(f"  - Скорость: {best_roc_auc_speed:.4f} мс (в {best_roc_auc_speed_ratio:,} раз быстрее требования)")
    print(f"  - {best_roc_auc_interpretability}")
    
    # Если лучшая по ROC-AUC и лучшая по Recall - разные модели
    if best_recall['model'] != best_roc_auc['model']:
        print(f"\n  Примечание: лучшая по ROC-AUC ({best_roc_auc['model']}) и лучшая по Recall")
        print(f"   ({best_recall['model']}) - разные модели. Выбор зависит от приоритета бизнеса:")
        print(f"   - Если важнее НЕ ПРОПУСТИТЬ уходящего, то {best_recall['model']}")
        print(f"   - Если важнее ОБЩАЯ ТОЧНОСТЬ, то {best_roc_auc['model']}")
    
    # Блок 8 - Статистический анализ
    print("\nСтатистическая валидация")
    
    stats_results = print_statistical_analysis(df_metrics)
       
    print("\n Сравнение моделей ML ЗАВЕРШЕНО")

if __name__ == "__main__":
    compare_models()
    
    
    
    