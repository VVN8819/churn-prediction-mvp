# d_ml_model/db_class_data_preprocessor.py
"""
d_ml_model/db_class_data_preprocessor.py
Класс для подготовки данных для ML моделей.

Что делает:
- Инкапсулирует все шаги подготовки данных в одном классе
- Защита от утечки целевой переменной (исключение days_since_last_order)
- Фильтрация "холодных" пользователей (никогда не заказывали)
- Перевод bool → int
- Анализ корреляции признаков с 'is_churned' (target)
- Подготовка признаков (разделение на X и y)
- Разделение на train/test
- Winsorization выбросов + StandardScaler
- Опциональное кэширование через joblib
- Может быть переиспользован во всех скриптах обучения моделей
- Анализирует корреляцию признаков с is_churned
- Средняя абсолютная корреляция, t-test

Использование:
    from d_ml_model.db_class_data_preprocessor import DataPreprocessor
    
    # Без кэша (всегда актуальные данные)
    preprocessor = DataPreprocessor()
    data = preprocessor.prepare()
    
    # С кэшем (быстрее при повторных запусках)
    preprocessor = DataPreprocessor(use_cache=True)
    data = preprocessor.prepare()
    
    # Принудительно пересоздать кэш
    preprocessor = DataPreprocessor(use_cache=True, force_cache=True)
    data = preprocessor.prepare()
    
    # Получение данных
    X_train = data['X_train_scaled']
    y_train = data['y_train']
    feature_names = data['feature_names']
"""

import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from scipy import stats

# Импортируем ML-константы
from ml_config import (
    MAX_DAYS_SINCE_ORDER,
    SERVICE_COLS,
    EXCLUDE_FROM_FEATURES
)

# Импортируем классификацию признаков
from d_ml_model.dh_model_config import (
    TRANSACTIONAL_FEATURES,
    BEHAVIORAL_FEATURES,
    HYPOTHESIS_TEST_ALPHA
)

class DataPreprocessor:
    """
    Класс для подготовки данных для ML
    
    Атрибуты:
        clean_csv: путь к очищенному CSV файлу
        cache_file: путь к файлу кэша
        use_cache: использовать ли кэш
        force_cache: принудительно пересоздать кэш
        skip_correlation: пропустить ли анализ корреляции
    """
    
    def __init__(
        self,
        use_cache=False,
        force_cache=False,
        skip_correlation=False,
        random_state=42,
        test_size=0.2
    ):
        """
        Инициализация препроцессора
        
        Args:
            use_cache: использовать ли кэш (по умолчанию False)
            force_cache: принудительно пересоздать кэш (по умолчанию False)
            skip_correlation: пропустить ли анализ корреляции (по умолчанию False)
            random_state: случайное число для воспроизводимости
            test_size: доля тестовой выборки
        """
        # Пути
        self.current_dir = Path(__file__).parent
        self.project_root = self.current_dir.parent
        self.data_dir = self.project_root / "c_eda" / "data"
        self.clean_csv = self.data_dir / "df_features_clean.csv"
        
        self.cache_dir = self.current_dir / "cache"
        self.cache_file = self.cache_dir / "prepared_data.joblib"
        self.plots_dir = self.current_dir / "plots"
        
        # Параметры
        self.use_cache = use_cache
        self.force_cache = force_cache
        self.skip_correlation = skip_correlation
        self.random_state = random_state
        self.test_size = test_size
    
    def prepare(self):
        """
        Главный метод: подготавливает данные
        
        Returns:
            dict с ключами:
                - X_train_scaled: DataFrame с масштабированными признаками train
                - X_test_scaled: DataFrame с масштабированными признаками test
                - y_train: Series с целевой переменной train
                - y_test: Series с целевой переменной test
                - scaler: объект StandardScaler (для инференса)
                - feature_names: список названий признаков
        """
        print("\nПодготовка данных для ML")
        
        # Проверяем, нужно ли использовать кэш
        if self.use_cache and self.cache_file.exists() and not self.force_cache:
            return self._load_from_cache()
        
        # Если кэш не используется или не найден — готовим данные
        if self.force_cache and self.cache_file.exists():
            print(f"\n Принудительное пересоздание кэша")
            self.cache_file.unlink()
        
        # Выполняем все шаги подготовки
        data = self._prepare_fresh()
        
        # Сохраняем в кэш, если нужно
        if self.use_cache:
            self._save_to_cache(data)
        
        return data
    
    def _load_from_cache(self):
        """Загружает данные из кэша"""
        print(f"\n Кэш найден: {self.cache_file}")
        print("- Загрузка данных из кэша")
        
        data = joblib.load(self.cache_file)
        
        print(f"- X_train_scaled: {data['X_train_scaled'].shape[0]:,} строк × {data['X_train_scaled'].shape[1]} столбцов")
        print(f"- X_test_scaled:  {data['X_test_scaled'].shape[0]:,} строк × {data['X_test_scaled'].shape[1]} столбцов")
        print(f"- y_train: {data['y_train'].shape[0]:,} значений")
        print(f"- y_test:  {data['y_test'].shape[0]:,} значений")
        print(f"- Признаков: {len(data['feature_names'])}")
        
        print("\n Кэш загружен УСПЕШНО!")
        
        return data
    
    def _save_to_cache(self, data):
        """Сохраняет данные в кэш"""
        print(f"\n- Сохранение в кэш")
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Добавляем метаданные
        data['skip_correlation'] = self.skip_correlation
        
        joblib.dump(data, self.cache_file, compress=3)
        
        file_size_mb = self.cache_file.stat().st_size / (1024 * 1024)
        print(f" Кэш сохранён УСПЕШНО: {self.cache_file}")
        print(f"   Размер: {file_size_mb:.2f} MB")
    
    def _prepare_fresh(self):
        """Готовит данные с нуля (все шаги)"""
        
        # ========== Шаг 1: Загрузка данных ==========
        print("\n Шаг 1: Загрузка данных")
        print(f"- Файл: {self.clean_csv}")
        
        if not self.clean_csv.exists():
            raise FileNotFoundError(
                f"- ОШИБКА: Файл не найден по пути: {self.clean_csv}\n"
                f"- Подсказка: Сначала запустите EDA пайплайн:\n"
                f"- python c_eda/c_run_pipeline.py --skip-visualize"
            )
        
        print("- Чтение CSV файла")
        df = pd.read_csv(self.clean_csv)
        print(f" Успешно загружено!")
        print(f" - Размер данных: {df.shape[0]:,} строк на {df.shape[1]} столбцов")
        print(f" - Первые 3 колонки: {list(df.columns[:3])}")
        
        # ========== Шаг 2: Фильтрация "холодных" пользователей ==========
        print("\n Шаг 2: Фильтрация 'холодных' пользователей")
        initial_count = len(df)
        df = df[df['days_since_last_order'] < MAX_DAYS_SINCE_ORDER].copy()
        
        print(f"   - Было строк: {initial_count:,}")
        print(f"   - Осталось строк: {len(df):,}")
        print(f"   - Удалено (никогда не заказывали): {initial_count - len(df):,}")
        
        # ========== Шаг 3: Перевод bool → int ==========
        print("\n Шаг 3: Перевод bool в int (0/1)")
        bool_cols = df.select_dtypes(include=['bool']).columns
        
        if len(bool_cols) > 0:
            print(f"- Найдено колонок с типом bool: {len(bool_cols)}")
            for col in bool_cols:
                print(f"   - {col}")
            df[bool_cols] = df[bool_cols].astype(int)
            print(f"- Все bool колонки переведены в int (0/1)")
        
        # ========== Шаг 4: Анализ корреляции ==========
        if not self.skip_correlation:
            print("\n Шаг 4: Анализ корреляции признаков с 'is_churned'")
            self._analyze_correlation(df)
        else:
            print("\n Шаг 4: Пропущен (--skip-correlation)")
        
        # ========== Шаг 5: Подготовка признаков (разделение на X и y) ==========
        print("\n Шаг 5: Подготовка признаков (разделение на X и y)")
        
        # Исключаем служебные колонки и признаки с утечкой
        all_exclude_cols = [
            col for col in (SERVICE_COLS + EXCLUDE_FROM_FEATURES) 
            if col in df.columns
        ]
        
        print(f"- Убираем из X:")
        for col in all_exclude_cols:
            print(f"   - {col}")
        
        X = df.drop(columns=all_exclude_cols)
        y = df['is_churned']  # Используем готовую целевую переменную из БД
        
        print(f"\n- Результат:")
        print(f"   - X: {X.shape[0]:,} строк × {X.shape[1]} столбцов")
        print(f"   - y: {y.shape[0]:,} значений")
        print(f"\n- Первые 5 признаков (X):")
        print(f" {list(X.columns[:5])}")
        print(f"\n- Типы данных в X:")
        print(f"   {X.dtypes.value_counts().to_dict()}")
        print(f"\n- Пропуски в X: {X.isnull().sum().sum()}")
        print(f"- Пропуски в y: {y.isnull().sum()}")
        
        # ========== Шаг 6: Разделение на train/test ==========
        print("\n Шаг 6: Разделение на train/test")
        
        print(f"\nРаспределение классов в полном датасете:")
        print(y.value_counts(normalize=True))
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=self.test_size,
            random_state=self.random_state,
            stratify=y
        )
        
        print(f"\nРаспределение классов в train:")
        print(y_train.value_counts(normalize=True))
        
        print(f"\nРаспределение классов в test:")
        print(y_test.value_counts(normalize=True))
        
        print(f"   - Train: {X_train.shape[0]:,} примеров")
        print(f"   - Test:  {X_test.shape[0]:,} примеров")
        
        train_churn_rate = y_train.mean() * 100
        test_churn_rate = y_test.mean() * 100
        print(f"\n- Проверка баланса классов:")
        print(f"   - Train churn rate: {train_churn_rate:.2f}%")
        print(f"   - Test churn rate:  {test_churn_rate:.2f}%")
        print(f"   - Разница: {abs(train_churn_rate - test_churn_rate):.2f}%")
        
        if abs(train_churn_rate - test_churn_rate) < 1.0:
            print(f"  Баланс сохранён (разница < 1%)")
        else:
            print(f"  Баланс немного нарушен (разница > 1%)")
        
        # ========== Шаг 7: Winsorization выбросов ==========
        print("\n Шаг 7: Winsorization выбросов (ограничение экстремальных значений)")
        X_train_w = X_train.copy()
        X_test_w = X_test.copy()
        
        for col in X_train.columns:
            lower_bound = X_train[col].quantile(0.01)
            upper_bound = X_train[col].quantile(0.99)
            X_train_w[col] = X_train[col].clip(lower=lower_bound, upper=upper_bound)
            X_test_w[col] = X_test[col].clip(lower=lower_bound, upper=upper_bound)
        
        X_train = X_train_w
        X_test = X_test_w
        
        print(f" - Ограничено на уровне 1% - 99% перцентилей")
        
        # ========== Шаг 8: Масштабирование ==========
        print("\n Шаг 8: Масштабирование признаков (StandardScaler)")
        scaler = StandardScaler()
        
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        X_train_scaled = pd.DataFrame(X_train_scaled, columns=X_train.columns, index=X_train.index)
        X_test_scaled = pd.DataFrame(X_test_scaled, columns=X_test.columns, index=X_test.index)
        
        print(f"\n- Train (до масштабирования):")
        print(f"   - Среднее: {X_train.mean().mean():.4f}")
        print(f"   - Стандартное отклонение: {X_train.std().mean():.4f}")
        print(f"   - Мин: {X_train.min().min():.4f}")
        print(f"   - Макс: {X_train.max().max():.4f}")
        
        print(f"\n- Train (после масштабирования):")
        print(f"   - Среднее: {X_train_scaled.mean().mean():.4f} (должно быть ≈ 0)")
        print(f"   - Стандартное отклонение: {X_train_scaled.std().mean():.4f} (должно быть ≈ 1)")
        print(f"   - Мин: {X_train_scaled.min().min():.4f}")
        print(f"   - Макс: {X_train_scaled.max().max():.4f}")
        
        print(f"\n- Test (после масштабирования):")
        print(f"   - Среднее: {X_test_scaled.mean().mean():.4f}")
        print(f"   - Стандартное отклонение: {X_test_scaled.std().mean():.4f}")
        
        print(f"\n- Размер данных:")
        print(f"   - X_train_scaled: {X_train_scaled.shape[0]:,} строк × {X_train_scaled.shape[1]} столбцов")
        print(f"   - X_test_scaled: {X_test_scaled.shape[0]:,} строк × {X_test_scaled.shape[1]} столбцов")
        
        print(f"\n- Scaler сохранён")
        
        print("\nПодготовка данных для ML ЗАВЕРШЕНА!")
        
        return {
            'X_train_scaled': X_train_scaled,
            'X_test_scaled': X_test_scaled,
            'y_train': y_train,
            'y_test': y_test,
            'scaler': scaler,
            'feature_names': list(X.columns)
        }
    
    def _analyze_correlation(self, df):
        """Анализирует корреляцию признаков с is_churned"""
        
        # Выбираем только числовые колонки
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        exclude_cols = [
            'profile_id', 'snapshot_date', 'computed_at',
            'churn_probability', 'risk_level', 'is_churned', 'model_v1.0'
        ]
        feature_cols = [col for col in numeric_cols if col not in exclude_cols]
        
        correlations = df[feature_cols].corrwith(df['is_churned']).dropna()
        correlations_sorted = correlations.reindex(correlations.abs().sort_values(ascending=False).index)
        
        # Тестирование Гипотезы 1
        print("\nТестирование Гипотезы 1")
        print("Транзакционные признаки имеют более высокую корреляцию с is_churned")
        
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
        
        # H0: Средние корреляции равны (нет различий)
        # H1: Средние корреляции различаются
        
        t_statistic, p_value = stats.ttest_ind(
            behav_abs_corr,  # behavioral features
            trans_abs_corr,  # transactional features
            equal_var=False  # Welch's t-test (не предполагаем равные дисперсии)
        )
        
        print(f"t-статистика: {t_statistic:.4f}")
        print(f"p-value: {p_value:.6f}")
        
        alpha = HYPOTHESIS_TEST_ALPHA  # Уровень значимости из конфига
        
        if p_value < alpha:
            print(f"\n Результат: Статистически значимое различие (p < {alpha})")
            print("  H0 отвергается - средние корреляции РАЗЛИЧАЮТСЯ")
            
            if behav_mean > trans_mean:
                print(f"  - Поведенческие признаки действительно лучше предсказывают отток")
            else:
                print(f"  - Транзакционные признаки лучше предсказывают отток")
        else:
            print(f"\n Результат: Различия НЕ статистически значимы (p >= {alpha})")
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
        
        # Топ-5 положительных
        positive_corr = correlations[correlations > 0].sort_values(ascending=False)
        print("\n- Топ-5 признаков, повышающих риск оттока:")
        for feature, corr in positive_corr.head(5).items():
            print(f"   - {feature}: {corr:.4f}")
        
        # Топ-5 отрицательных
        negative_corr = correlations[correlations < 0].sort_values(ascending=True)
        print("\n- Топ-5 признаков, снижающих риск оттока:")
        for feature, corr in negative_corr.head(5).items():
            print(f"   - {feature}: {corr:.4f}")
        
        # Корреляция каждого признака с is_churned
        print("\nКорреляция каждого признака с is_churned")

        for feature, corr in correlations.items():
            abs_corr = abs(corr)
            if abs_corr >= 0.7:
                strength = "Сильная"
            elif abs_corr >= 0.3:
                strength = "Умеренная"
            elif abs_corr >= 0.1:
                strength = "Слабая"
            else:
                strength = "Очень слабая/нет связи"

            direction = "положительная" if corr > 0 else "отрицательная"

            print(f"\n{feature}:")
            print(f"- Корреляция: {corr:.4f}")
            print(f"- Сила: {strength}")
            print(f"- Направление: {direction}")
        
        # Визуализация
        self.plots_dir.mkdir(parents=True, exist_ok=True)
        
        correlations_plot = correlations.sort_values(ascending=True)
        plt.figure(figsize=(12, max(8, len(correlations_plot) * 0.35)))
        
        colors = ['#ff9999' if v < 0 else '#99ff99' for v in correlations_plot.values]
        
        sns.barplot(
            x=correlations_plot.values,
            y=correlations_plot.index,
            hue=correlations_plot.index,
            palette=colors,
            legend=False
        )
        
        plt.title('Корреляция признаков с оттоком (is_churned)', fontsize=14, fontweight='bold', pad=15)
        plt.xlabel('Коэффициент корреляции Пирсона', fontsize=12)
        plt.ylabel('Признак', fontsize=12)
        plt.xlim(-1, 1)
        plt.axvline(0, color='black', linestyle='--', linewidth=1.5)
        plt.grid(axis='x', linestyle=':', alpha=0.7)
        plt.tight_layout()
        
        filepath = self.plots_dir / "01_feature_correlation_with_churn.png"
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"\n- График сохранён: {filepath}")
        
        return correlations_sorted
    
    
    