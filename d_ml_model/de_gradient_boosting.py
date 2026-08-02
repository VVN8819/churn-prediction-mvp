# d_ml_model/de_gradient_boosting.py
"""
d_ml_model/de_gradient_boosting.py
Обучение, оценка и сохранение модели Gradient Boosting для предсказания оттока.
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
from sklearn.ensemble import GradientBoostingClassifier
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
    
    print("\n Обучение Gradient Boosting")
    
    # 1. Загружаем подготовленные данные из кэша
    print("\n Загрузка данных из кэша")
    preprocessor = DataPreprocessor(use_cache=True, skip_correlation=True)
    data = preprocessor.prepare()
    
    X_train = data['X_train_scaled']
    X_test = data['X_test_scaled']
    y_train = data['y_train']
    y_test = data['y_test']
    feature_names = data['feature_names']
    
    # 2. Инициализация и обучение модели
    print("\n Обучение модели Gradient Boosting")
    model_gb = GradientBoostingClassifier(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=5,
        random_state=42
    )
    model_gb.fit(X_train, y_train)
    
    # Замер времени инференса
    print("\n Замер времени инференса")
    inference_start = time.perf_counter()
    
    # 3. Предсказания
    y_pred = model_gb.predict(X_test)
    y_pred_proba = model_gb.predict_proba(X_test)[:, 1]
    
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
    
    # 4. Расчет метрик
    print("\n Метрики модели (X_test):")
    print(f"- Accuracy:  {accuracy_score(y_test, y_pred):.4f}")
    print(f"- Precision: {precision_score(y_test, y_pred):.4f}  (Доля верно предсказанных ушедших среди всех предсказанных как ушедшие)")
    print(f"- Recall:    {recall_score(y_test, y_pred):.4f}  (Доля найденных ушедших среди всех реально ушедших)")
    print(f"- F1-Score:  {f1_score(y_test, y_pred):.4f}")
    print(f"- ROC-AUC:   {roc_auc_score(y_test, y_pred_proba):.4f}")
    
    print("\n Classification Report:")
    print(classification_report(y_test, y_pred, target_names=['Активные (0)', 'Ушедшие (1)']))
    
    # 5. Визуализация Confusion Matrix
    cm = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Oranges', cbar=False,
                xticklabels=['Активные (0)', 'Ушедшие (1)'],
                yticklabels=['Активные (0)', 'Ушедшие (1)'])
    plt.title('Confusion Matrix - Gradient Boosting', fontsize=14, fontweight='bold')
    plt.xlabel('Predicted Label')
    plt.ylabel('True Label')
    plt.tight_layout()
    
    cm_path = PLOTS_DIR / "06_confusion_matrix_gb.png"
    plt.savefig(cm_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print("\nConfusion Matrix Random Forest:")
    print(cm)
    print(f"\nTN={cm[0,0]} (верно: 'Останется'), FP={cm[0,1]} (ошибка: сказал 'Уйдет', но остался)")
    print(f"FN={cm[1,0]} (ошибка: сказал 'Останется', но ушел), TP={cm[1,1]} (верно: 'Уйдет')")    
    print(f"\n Confusion Matrix сохранен: {cm_path}")
    
    # 6. Анализ важности признаков (feature_importances_)
    print("\n Важность признаков (Gradient Boosting)")
    
    importances = model_gb.feature_importances_
    feature_importance = pd.DataFrame({
        'feature': feature_names,
        'importance': importances
    }).sort_values('importance', ascending=False)
    
    print("\nТоп-10 самых важных признаков:")
    for i, row in feature_importance.head(10).iterrows():
        print(f"{row['feature']:35s} {row['importance']:.4f}")
    
    # Визуализация топ-15 признаков
    plt.figure(figsize=(12, 8))
    top_n = 15
    top_features = feature_importance.head(top_n)
    
    plt.barh(range(len(top_features)), top_features['importance'], 
             color='#FF9800', edgecolor='black')
    plt.yticks(range(len(top_features)), top_features['feature'])
    plt.xlabel('Importance Score', fontsize=12)
    plt.ylabel('Feature', fontsize=12)
    plt.title(f'Top {top_n} Feature Importance (Gradient Boosting)', 
              fontsize=14, fontweight='bold')
    plt.gca().invert_yaxis()
    plt.grid(axis='x', linestyle=':', alpha=0.7)
    plt.tight_layout()
    
    fi_path = PLOTS_DIR / "07_feature_importance_gb.png"
    plt.savefig(fi_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n График важности признаков сохранен: {fi_path}")
    
    # 7. Сохранение артефактов модели
    print("\n Сохранение артефактов модели Gradient Boosting")
    
    # Сохраняем модель
    model_path = MODELS_DIR / "gradient_boosting_model.joblib"
    joblib.dump(model_gb, model_path, compress=3)
    print(f"- Модель сохранена: {model_path}")
    
    # Сохраняем важность признаков в CSV
    fi_csv_path = MODELS_DIR / "gb_feature_importance.csv"
    feature_importance.to_csv(fi_csv_path, index=False)
    print(f"- Важность признаков сохранена: {fi_csv_path}")
    
    # Сохраняем метрики в текстовый файл
    metrics_path = MODELS_DIR / "gradient_boosting_metrics.txt"
    with open(metrics_path, 'w', encoding='utf-8') as f:
        f.write("Gradient Boosting Model Metrics\n")
        f.write(f"Accuracy:  {accuracy_score(y_test, y_pred):.4f}\n")
        f.write(f"Precision: {precision_score(y_test, y_pred):.4f}\n")
        f.write(f"Recall:    {recall_score(y_test, y_pred):.4f}\n")
        f.write(f"F1-Score:  {f1_score(y_test, y_pred):.4f}\n")
        f.write(f"ROC-AUC:   {roc_auc_score(y_test, y_pred_proba):.4f}\n")
        f.write("\nВремя инференса:\n")
        f.write(f"Общее время инференса: {total_inference_time_ms:.2f} ms\n")
        f.write(f"Среднее время инференса на гостя: {avg_inference_time_per_client_ms:.4f} ms\n")
        f.write(f"Требования ко времени инференса (< 100ms): {'Требование выполнено!' if inference_requirement_met else 'Требование НЕ выполнено!'}\n")
    print(f"- Метрики сохранены: {metrics_path}")
    
    print("\n Обучение Gradient Boosting завершено УСПЕШНО!")

if __name__ == "__main__":
    train_and_evaluate()
    
    
    