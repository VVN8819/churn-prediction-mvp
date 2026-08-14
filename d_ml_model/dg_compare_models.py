# d_ml_model/dg_compare_models.py
"""
d_ml_model/dg_compare_models.py
Финальное сравнение всех обученных моделей:
- Logistic Regression (baseline)
- Random Forest
- Gradient Boosting
- GridSearchCV (оптимизированная Logistic Regression)

Собирает метрики из текстовых файлов, строит матрицу принятия решения и сравнительные графики.
"""

import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import re
import numpy as np

# Настройка путей
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

CURRENT_DIR = Path(__file__).parent
MODELS_DIR = CURRENT_DIR / "models"
PLOTS_DIR = CURRENT_DIR / "plots"

# Импортируем веса из конфига
from d_ml_model.dh_model_config import (
    MODEL_SELECTION_WEIGHTS,
    INFERENCE_TIME_REQUIREMENT_MS
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
        
    print("\n Сравнение моделей ML ЗАВЕРШЕНО")

if __name__ == "__main__":
    compare_models()
    
    
    
    