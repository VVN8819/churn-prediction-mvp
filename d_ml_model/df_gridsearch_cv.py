# d_ml_model/df_gridsearch_cv.py
"""
d_ml_model/df_gridsearch_cv.py
Поиск и cross-validation по лучшим параметрам, обучение, оценка и сохранение лучшей модели Logistic Regression для предсказания оттока.
"""

import sys
from pathlib import Path

# Настройка путей
# Добавляем корень проекта в системные пути, чтобы Python мог находить модули
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import time
from pathlib import Path
from sklearn.model_selection import GridSearchCV, cross_val_score
import warnings
warnings.filterwarnings('ignore')
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)

# Импортируем наш класс подготовки данных
from d_ml_model.db_class_data_preprocessor import DataPreprocessor

# Настройка путей
CURRENT_DIR = Path(__file__).parent
MODELS_DIR = CURRENT_DIR / "models"
PLOTS_DIR = CURRENT_DIR / "plots"

# Создаем папки, если их нет
MODELS_DIR.mkdir(exist_ok=True)
PLOTS_DIR.mkdir(exist_ok=True)

def train_and_evaluate():
    
    print("Настройка GridSearchCV:")
            
    # 1. Загружаем подготовленные данные из кэша
    print("\n Загрузка данных из кэша")
    preprocessor = DataPreprocessor(use_cache=True, skip_correlation=True)
    data = preprocessor.prepare()
    
    X_train = data['X_train_scaled']
    X_test = data['X_test_scaled']
    y_train = data['y_train']
    y_test = data['y_test']
    feature_names = data['feature_names']
    
    # 2. определение сетки параметров
    param_grid = {
        'C': [0.001, 0.01, 0.1, 1.0, 10.0, 100.0],
        'penalty': ['l1', 'l2'],
        'class_weight': [None, 'balanced'],
        'solver': ['saga', 'liblinear'] # liblinear для l1, saga для обоих
    }

    print(f"\nПараметры для перебора:")
    print(f"  C: {param_grid['C']}")
    print(f"  penalty: {param_grid['penalty']}")
    print(f"  solver: {param_grid['solver']}")

    print("Запуск GridSearchCV:")
    
    # 3. Инициализация и обучение модели
    base_model = LogisticRegression(class_weight='balanced', max_iter=3000, random_state=42)

    # GridSearchCV с несколькими метриками
    grid_search = GridSearchCV(
        estimator=base_model,
        param_grid=param_grid,
        cv=5, # 5-fold cross-validation
        scoring='recall',
        n_jobs=-1, # использовать все CPU
        verbose=1,
        return_train_score=True
    )
    
    grid_search.fit(X_train, y_train)
    print("Обучение завершено!")
    
    print("\n Результаты:")
    print(f" - Лучшие параметры: {grid_search.best_params_}")
    print(f" - Лучший Recall (CV): {grid_search.best_score_:.4f}")

    # получение лучшей модели
    best_model = grid_search.best_estimator_
    
    # Замер времени инференса
    print("\n Замер времени инференса:")
    inference_start = time.perf_counter()
    
    # 4. Предсказания
    y_test_pred_best = best_model.predict(X_test)
    y_test_proba_best = best_model.predict_proba(X_test)[:, 1]
    
    inference_end = time.perf_counter()
        
    # Расчет времени инференса
    total_inference_time_ms = (inference_end - inference_start) * 1000
    avg_inference_time_per_client_ms = total_inference_time_ms / len(X_test)
    
    print(f"   - Общее время инференса на {len(X_test)} клиентов: {total_inference_time_ms:.2f} ms")
    print(f"   - Среднее время на 1 клиента: {avg_inference_time_per_client_ms:.4f} ms")
    
    # Проверка требования < 100ms
    if avg_inference_time_per_client_ms < 100:
        print(f"   - Требование выполнено: {avg_inference_time_per_client_ms:.4f} ms < 100 ms")
        inference_requirement_met = True
    else:
        print(f"   - Требование НЕ выполнено!: {avg_inference_time_per_client_ms:.4f} ms > 100 ms")
        inference_requirement_met = False
        
    # 5. Расчет метрик
    print("\nМетрики модели (X_test):")
    print(f"- Accuracy:  {accuracy_score(y_test, y_test_pred_best):.4f}")
    print(f"- Precision: {precision_score(y_test, y_test_pred_best):.4f}  (Доля верно предсказанных ушедших среди всех предсказанных как ушедшие)")
    print(f"- Recall:    {recall_score(y_test, y_test_pred_best):.4f}  (Доля найденных ушедших среди всех реально ушедших)")
    print(f"- F1-Score:  {f1_score(y_test, y_test_pred_best):.4f}")
    print(f"- ROC-AUC:   {roc_auc_score(y_test, y_test_proba_best):.4f}")
    
    print("\n Classification Report:")
    print(classification_report(y_test, y_test_pred_best, target_names=['Активные (0)', 'Ушедшие (1)']))
    
    #6. Топ-5 комбинаций и визуализация
    print("\nТОП-5 комбинаций по ROC-AUC")

    results_df = pd.DataFrame(grid_search.cv_results_)
    top_5 = results_df.nlargest(5, 'mean_test_score') # mean_test_score - это Recall

    print("\nТоп-5 комбинаций:")
    for idx, row in top_5.iterrows():
        print(f"C={row['param_C']}, penalty={row['param_penalty']}, class_weight={row['param_class_weight']}")
        print(f"Recall (CV): {row['mean_test_score']:.4f} ± {row['std_test_score']:.4f}")
        print()
        
    print("\nВизуализация результатов GridSearchCV")
    
    # Разделяем по типу регуляризации
    # Группируем по C и penalty, берем лучший class_weight
    l1_results = (results_df[results_df['param_penalty'] == 'l1']
                  .groupby('param_C')
                  .agg({'mean_test_score': 'max', 'std_test_score': 'first'})
                  .reset_index()
                  .sort_values('param_C'))
    
    l2_results = (results_df[results_df['param_penalty'] == 'l2']
                      .groupby('param_C')
                      .agg({'mean_test_score': 'max', 'std_test_score': 'first'})
                      .reset_index()
                      .sort_values('param_C'))
    
    # Преобразуем param_C в float
    l1_results['param_C'] = l1_results['param_C'].astype(float)
    l2_results['param_C'] = l2_results['param_C'].astype(float)
        
    print(f"\nРезультаты для L1 (сгруппировано по C, лучший class_weight):")
    print(l1_results[['param_C', 'mean_test_score', 'std_test_score']].to_string(index=False))

    print(f"\nРезультаты для L2 (сгруппировано по C, лучший class_weight):")
    print(l2_results[['param_C', 'mean_test_score', 'std_test_score']].to_string(index=False))

    # Построение графика
    plt.figure(figsize=(12, 7))

    color_l1 = '#e74c3c'
    color_l2 = '#3498db'

    # L1 регуляризация
    plt.plot(l1_results['param_C'], l1_results['mean_test_score'],
            'o-', color=color_l1, linewidth=2.5, markersize=10,
            label='L1 (Lasso)', zorder=3)
    plt.fill_between(l1_results['param_C'],
                    l1_results['mean_test_score'] - l1_results['std_test_score'],
                    l1_results['mean_test_score'] + l1_results['std_test_score'],
                    alpha=0.2, color=color_l1)

    # L2 регуляризация
    plt.plot(l2_results['param_C'], l2_results['mean_test_score'],
            's-', color=color_l2, linewidth=2.5, markersize=10,
            label='L2 (Ridge)', zorder=3)
    plt.fill_between(l2_results['param_C'],
                    l2_results['mean_test_score'] - l2_results['std_test_score'],
                    l2_results['mean_test_score'] + l2_results['std_test_score'],
                    alpha=0.2, color=color_l2)
    
    # Отмечаем ключевые элементы
    best_C = grid_search.best_params_['C']
    best_penalty = grid_search.best_params_['penalty']
    best_score = grid_search.best_score_

    plt.axvline(best_C, color='green', linestyle='--', linewidth=2,
                label=f'Лучший C={best_C} ({best_penalty.upper()})', alpha=0.7, zorder=2)

    # Горизонтальная линия случайного угадывания
    plt.axhline(0.5, color='gray', linestyle=':', linewidth=1.5,
                label='Случайное угадывание (ROC-AUC=0.5)', alpha=0.7, zorder=1)
    
    # Оформление графика
    plt.xscale('log')  # Логарифмическая шкала для C
    plt.xlabel('Параметр C (обратная сила регуляризации)', fontsize=13, fontweight='bold')
    plt.ylabel('Recall (CV, 5-fold)', fontsize=13, fontweight='bold')
    plt.title('GridSearchCV: Зависимость Recall от параметра C\nСравнение L1 и L2 регуляризаций',
            fontsize=15, fontweight='bold', pad=15)

    # Подписи на точках
    for _, row in l1_results.iterrows():
        plt.annotate(f'{row["mean_test_score"]:.3f}',
                    (row['param_C'], row['mean_test_score']),
                    textcoords="offset points", xytext=(0, 12),
                    ha='center', fontsize=9, color=color_l1, fontweight='bold')

    for _, row in l2_results.iterrows():
        plt.annotate(f'{row["mean_test_score"]:.3f}',
                    (row['param_C'], row['mean_test_score']),
                    textcoords="offset points", xytext=(0, -18),
                    ha='center', fontsize=9, color=color_l2, fontweight='bold')

    # Сетка и легенда
    plt.grid(True, alpha=0.3, which='both')
    plt.grid(True, alpha=0.5, which='minor', linestyle=':')
    plt.legend(loc='lower right', fontsize=10, framealpha=0.95)
    plt.ylim(0.70, 0.99)  # Фокус на интересной области

    # Подписи осей X
    plt.xticks([0.001, 0.01, 0.1, 1.0, 10.0, 100.0],
            ['0.001\n(сильная\nрег.)', '0.01', '0.1', '1.0', '10.0', '100.0\n(слабая\nрег.)'])

    # Добавляем пояснения по регионам
    plt.text(0.015, 0.985, '← Недообучение\n(модель слишком простая)',
            ha='left', va='top', fontsize=10, style='italic', color='#555')
    plt.text(80, 0.985, 'Переобучение →\n(модель слишком сложная)',
            ha='right', va='top', fontsize=10, style='italic', color='#555')

    plt.tight_layout()
    
    gscv_path = PLOTS_DIR / "10_gridsearch_cv_results.png"
    plt.savefig(gscv_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"\n График GridSearchCV сохранен: {gscv_path}")

    # 7. Визуализация Confusion Matrix
    cm_best = confusion_matrix(y_test, y_test_pred_best)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm_best, annot=True, fmt='d', cmap='Blues', cbar=False,
                xticklabels=['Активные (0)', 'Ушедшие (1)'],
                yticklabels=['Активные (0)', 'Ушедшие (1)'])
    plt.title('Confusion Matrix - Logistic Regression', fontsize=14, fontweight='bold')
    plt.xlabel('Predicted Label')
    plt.ylabel('True Label')
    plt.tight_layout()
    
    cm_path = PLOTS_DIR / "08_confusion_matrix_gridsearch_cv.png"
    plt.savefig(cm_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print("\nConfusion Matrix GridSearchCV:")
    print(cm_best)
    print(f"\nTN={cm_best[0,0]} (верно: 'Останется'), FP={cm_best[0,1]} (ошибка: сказал 'Уйдет', но остался)")
    print(f"FN={cm_best[1,0]} (ошибка: сказал 'Останется', но ушел), TP={cm_best[1,1]} (верно: 'Уйдет')")
    print(f"\n Confusion Matrix сохранен: {cm_path}")
    
    # 8. Анализ важности признаков (коэффициенты модели)
    print("\nВажность признаков (коэффициенты GridSearchCV)")
    
    coefficients = best_model.coef_[0]
    feature_importance = pd.DataFrame({
        'feature': feature_names,
        'coefficient': coefficients,
        'abs_coefficient': np.abs(coefficients)
    }).sort_values('abs_coefficient', ascending=False)
    
    print("\nТоп-10 самых важных признаков:")
    for i, row in feature_importance.head(10).iterrows():
        direction = "УВЕЛИЧИВАЕТ риск оттока" if row['coefficient'] > 0 else "СНИЖАЕТ риск оттока"
        print(f"{row['feature']:35s} {row['coefficient']:+.4f}  {direction}")
    
    # Визуализация топ-15 признаков
    plt.figure(figsize=(12, 8))
    top_n = 15
    top_features = feature_importance.head(top_n)
    
    colors = ['#F44336' if c > 0 else '#4CAF50' for c in top_features['coefficient']]
        
    plt.barh(range(len(top_features)), top_features['coefficient'], color=colors, edgecolor='black')
    plt.yticks(range(len(top_features)), top_features['feature'])
    plt.xlabel('Coefficient Value', fontsize=12)
    plt.ylabel('Feature', fontsize=12)
    plt.title(f'Top {top_n} Feature Importance (GridSearchCV)', fontsize=14, fontweight='bold')
    plt.axvline(0, color='black', linestyle='-', linewidth=1)
    plt.grid(axis='x', linestyle=':', alpha=0.7)
    plt.tight_layout()
    
    fi_path = PLOTS_DIR / "09_feature_importance_gridsearch_cv.png"
    plt.savefig(fi_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n График важности признаков сохранен: {fi_path}")
    
    # 9. Сохранение артефактов модели
    print("\nСохранение артефактов модели")
    
    # Сохраняем модель
    model_path = MODELS_DIR / "gridsearch_cv_model.joblib"
    joblib.dump(best_model, model_path, compress=3)
    print(f"- Модель сохранена: {model_path}")
    
    # Сохраняем важность признаков в CSV
    fi_csv_path = MODELS_DIR / "gridsearch_cv_feature_importance.csv"
    feature_importance.to_csv(fi_csv_path, index=False)
    print(f"- Важность признаков сохранена: {fi_csv_path}")
    
    # Сохраняем метрики в текстовый файл
    metrics_path = MODELS_DIR / "gridsearch_cv_metrics.txt"
    with open(metrics_path, 'w', encoding='utf-8') as f:
        f.write("GridSearchCV Model Metrics\n")
        f.write(f"Accuracy:  {accuracy_score(y_test, y_test_pred_best):.4f}\n")
        f.write(f"Precision: {precision_score(y_test, y_test_pred_best):.4f}\n")
        f.write(f"Recall:    {recall_score(y_test, y_test_pred_best):.4f}\n")
        f.write(f"F1-Score:  {f1_score(y_test, y_test_pred_best):.4f}\n")
        f.write(f"ROC-AUC:   {roc_auc_score(y_test, y_test_proba_best):.4f}\n")
        f.write("\nВремя инференса:\n")
        f.write(f"Общее время инференса: {total_inference_time_ms:.2f} ms\n")
        f.write(f"Среднее время инференса на гостя: {avg_inference_time_per_client_ms:.4f} ms\n")
        f.write(f"Требования ко времени инференса (< 100ms): {'Требование выполнено!' if inference_requirement_met else 'Требование НЕ выполнено!'}\n")
    print(f"- Метрики сохранены: {metrics_path}")
    
    print("\nОбучение GridSearchCV завершено УСПЕШНО!")


if __name__ == "__main__":
    train_and_evaluate()

