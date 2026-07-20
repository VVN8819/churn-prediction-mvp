#c_eda/cd_visualize.py
"""
cd_visualize.py
Визуализация данных EDA

Что делает:
1. Строит bar chart для категорий (reviews_reading_behavior)
2. Сравнивает ключевые метрики по клиентам
3. Строит heatmap корреляций между признаками
4. Строит boxplots для поиска выбросов
5. Сохраняет все графики в папку plots/
"""

import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Импортируем функцию загрузки из CSV
from c_eda.ca_load_data import load_from_csv

# Настройка стиля графиков
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)

# =========== Создаёт папку для графиков ========
def create_plots_folder():
    """Создаёт папку plots/ если её нет"""
    plots_dir = Path(__file__).parent / "plots"
    plots_dir.mkdir(exist_ok=True)
    return plots_dir

# ========= Bar chart для категорий =========
def plot_categories_distribution(df, plots_dir):
    """
    Строит bar chart для категориальных признаков
    
    Показывает сколько профилей относится к каждой категории
    """
    print("\nПостроение bar chart для категорий")
    
    # Проверяем, есть ли is_churned, иначе берем 2 графика, если нет - 1
    has_churn = 'is_churned' in df.columns
    fig, axes = plt.subplots(1, 2 if has_churn else 1, figsize=(14 if has_churn else 7, 5))
    if not has_churn:
        axes = [axes]
    
    # 1. reviews_reading_behavior
    behavior_counts = df['reviews_reading_behavior'].value_counts()
    colors = sns.color_palette("husl", len(behavior_counts))
    
    axes[0].bar(behavior_counts.index, behavior_counts.values, color=colors, edgecolor='black')
    axes[0].set_title('Reviews Reading Behavior', fontsize=14, fontweight='bold')
    axes[0].set_xlabel('Category')
    axes[0].set_ylabel('Count')
    axes[0].tick_params(axis='x', rotation=30)
    
    # Добавляем значения на столбцы
    for i, (cat, count) in enumerate(behavior_counts.items()):
        axes[0].text(i, count + 0.05, str(count), ha='center', fontweight='bold')
        
    # 2. is_churned
    if has_churn:
        churn_counts = df['is_churned'].value_counts()
        churn_labels = ['Активен (False)', 'Ушел (True)']
        colors_churn = ['#4CAF50', '#F44336']
        
        axes[1].bar(churn_labels, churn_counts.values, color=colors_churn, edgecolor='black')
        axes[1].set_title('Распределение оттока (is_churned)', fontsize=14, fontweight='bold')
        axes[1].set_ylabel('Количество клиентов')
        
        for i, count in enumerate(churn_counts.values):
            axes[1].text(i, count + 0.05, str(count), ha='center', fontweight='bold')
        
    plt.tight_layout()
    filepath = plots_dir / "01_categories_distribution.png"
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Сохранено: {filepath.name}")

# ========= Сравнение клиентов по ключевым метрикам =========
def plot_clients_comparison(df, plots_dir):
    """Сравнивает средние ключевые метрики между ушедшими и активными клиентами"""
    print("\nПостроение сравнения метрик по группам оттока")
    
    if 'is_churned' not in df.columns:
        print("   Пропуск: нет колонки is_churned")
        return

    key_metrics = [
        'checkout_frustration_index',
        'session_engagement_score',
        'personal_offer_conversion_rate',
        'avg_cart_value_30d'
    ]
    
    # Группируем по is_churned и считаем среднее
    df_grouped = df.groupby('is_churned')[key_metrics].mean().reset_index()
    df_grouped['group_name'] = df_grouped['is_churned'].map({False: 'Активные', True: 'Ушедшие'})
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()
    
    for i, metric in enumerate(key_metrics):
        ax = axes[i]
        
        bars = ax.bar(
            df_grouped['group_name'],
            df_grouped[metric],
            color=['#4CAF50', '#F44336'],
            edgecolor='black'
        )
        
        ax.set_title(metric.replace('_', ' ').title(), fontsize=12, fontweight='bold')
        ax.set_ylabel('Среднее значение')
        
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width()/2., 
                height + 0.02 * ax.get_ylim()[1],
                f'{height:.2f}',
                ha='center', va='bottom', fontsize=10, fontweight='bold'
            )
    
    plt.suptitle('Сравнение средних метрик: Активные vs Ушедшие', fontsize=16, fontweight='bold', y=1.02)    
    plt.tight_layout()
    filepath = plots_dir / "02_clients_comparison.png"
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Сохранено: {filepath.name}")

# ============ Heatmap корреляций ==========
def plot_correlation_heatmap(df, plots_dir):
    """
    Строит heatmap корреляций между числовыми признаками
    
    Показывает какие признаки связаны друг с другом
    """
    print("\nПостроение heatmap корреляций")
    
    # Выбираем числовые признаки (без служебных)
    service_cols = ['profile_id', 'snapshot_date', 'computed_at', 
                    'churn_probability', 'risk_level']
    numerical_cols = df.select_dtypes(include=['number']).columns.tolist()
    feature_cols = [c for c in numerical_cols if c not in service_cols]
    
    # Считаем корреляцию
    corr_matrix = df[feature_cols].corr()
    
    # Создаём heatmap
    plt.figure(figsize=(16, 14))
    
    # Маска для верхней треугольной части (чтобы не дублировать)
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
    
    sns.heatmap(
        corr_matrix,
        mask=mask,
        annot=True,
        fmt='.2f',
        cmap='coolwarm',
        center=0,
        square=True,
        linewidths=1,
        cbar_kws={"shrink": 0.8},
        annot_kws={"size": 8}
    )
    
    plt.title('Heatmap корреляций', fontsize=16, fontweight='bold', pad=20)
    plt.xticks(rotation=45, ha='right', fontsize=9)
    plt.yticks(rotation=0, fontsize=9)
    
    filepath = plots_dir / "03_correlation_heatmap.png"
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Сохранено: {filepath.name}")
    
    # Показываем сильные корреляции (|r| > 0.7)
    print("\nСильные корреляции (|r| > 0.7):")
    strong_corr = []
    for i in range(len(corr_matrix.columns)):
        for j in range(i):
            corr_val = corr_matrix.iloc[i, j]
            if abs(corr_val) > 0.7:
                strong_corr.append({
                    'признак_1': corr_matrix.columns[i],
                    'признак_2': corr_matrix.columns[j],
                    'корреляция': round(corr_val, 3)
                })
    
    if len(strong_corr) > 0:
        for item in strong_corr:
            print(f" - {item['признак_1']} <-> {item['признак_2']}: {item['корреляция']}")
    else:
        print("Сильных корреляций не найдено")

# ============ Boxplots для поиска выбросов ==========
def plot_boxplots(df, plots_dir):
    """
    Строит boxplots для ключевых признаков
    
    Наглядно показывает выбросы
    """
    print("\nПостроение boxplots")
    
    # Выбираем ключевые признаки для boxplots
    key_features = [
        'days_since_last_order',
        'cart_abandonment_rate_30d',
        'checkout_frustration_index',
        'avg_cart_value_30d',
        'avg_rating_90d',
        'session_engagement_score'
    ]
    
    # Создаём подграфики
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    axes = axes.flatten()
    
    for i, feature in enumerate(key_features):
        ax = axes[i]
        
        # Строим boxplot
        bp = ax.boxplot(
            df[feature], 
            vert=True,
            patch_artist=True,
            boxprops=dict(facecolor='lightblue', color='black'),
            medianprops=dict(color='red', linewidth=2),
            whiskerprops=dict(color='black'),
            capprops=dict(color='black'),
            flierprops=dict(marker='o', color='red', markersize=8)
        )
        
        ax.set_title(feature.replace('_', ' ').title(), fontsize=11, fontweight='bold')
        ax.set_ylabel('Value')
        ax.set_xticks([])  # Убираем метки по X
        
        # Добавляем значения (min, Q1, median, Q3, max)
        stats_text = (
            f"Max: {df[feature].max():.2f}\n"
            f"Q3:  {df[feature].quantile(0.75):.2f}\n"
            f"Med: {df[feature].median():.2f}\n"
            f"Q1:  {df[feature].quantile(0.25):.2f}\n"
            f"Min: {df[feature].min():.2f}" 
        )
        ax.text(
            1.15, 0.5, stats_text,
            transform=ax.transAxes,
            fontsize=8,
            verticalalignment='center',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        )
        
    plt.suptitle('Boxplots для поиска выбросов', fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    filepath = plots_dir / "04_boxplots.png"
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Сохранено: {filepath.name}")
    

# ============ Главная функция шага 4 ==========
def visualize_data():
    """Главная функция: запускает все визуализации"""
    
    print("\n4. Визуализация данных")
    
    try:
        # Загружаем данные из CSV (быстрее, чем из БД)
        print(f'Загрузка данных из CSV')
        df = load_from_csv("df_features_raw.csv")
        
        # Создаём папку для графиков
        plots_dir = create_plots_folder()
        print(f"Папка для графиков: {plots_dir}")
        
        # Строим все графики
        plot_categories_distribution(df, plots_dir)
        plot_clients_comparison(df, plots_dir)
        plot_correlation_heatmap(df, plots_dir)
        plot_boxplots(df, plots_dir)
        
        print(f'\nВизуализация данных. Успешно!')
        print(f'Графики сохранены в: {plots_dir}')
        
        return df
        
    except Exception as e:
        print(f"\nОшибка: {e}")
        print("\nПодробности:")
        import traceback
        traceback.print_exc()
        
        return None

if __name__ == "__main__":
    visualize_data()
    
    
    
    