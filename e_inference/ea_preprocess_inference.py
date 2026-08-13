# e_inference/ea_preprocess_inference.py
"""
e_inference/preprocess_inference.py
Класс для предобработки данных перед инференсом (предсказанием).

Этот класс инкапсулирует всю логику превращения "сырых" данных из БД 
в формат, который ожидает обученная ML-модель.

Что делает:
1. Фильтрация "холодных" пользователей (days_since_last_order < 900)
2. Исключение служебных колонок и days_since_last_order
3. Перевод bool в int
4. Логарифмирование (log1p)
5. One-Hot Encoding для reviews_reading_behavior
6. Удаление model_version (если есть)
7. Winsorization (1%-99% перцентили)
8. Приведение к ожидаемым признакам
9. StandardScaler (из scaler.joblib)
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import joblib
import warnings
warnings.filterwarnings('ignore')

# Настройка путей
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Импортируем ML-константы
from ml_config import (
    MAX_DAYS_SINCE_ORDER,
    LOG_COLUMNS,
    COLS_TO_DROP
)

# Пути к артефактам
MODELS_DIR = project_root / "d_ml_model" / "models"
SCALER_PATH = MODELS_DIR / "scaler.joblib"

class InferencePreprocessor:
    """
    Класс для подготовки сырых данных к инференсу.
    При инициализации загружает сохраненный Scaler и запоминает ожидаемые признаки.
    """
    
    def __init__(self, scaler_path: str = SCALER_PATH):
        """Загружает артефакты (Scaler) при создании экземпляра"""
        if not Path(scaler_path).exists():
            raise FileNotFoundError(f"Scaler не найден по пути: {scaler_path}. Сначала обучите модель.")
        
        self.scaler = joblib.load(scaler_path)
        self.expected_features = list(self.scaler.feature_names_in_)
        print(f"- InferencePreprocessor инициализирован. Ожидается {len(self.expected_features)} признаков.")


    def transform(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """
        Предобработка сырых данных из БД для инференса.
        Повторяет ВСЕ шаги из db_class_data_preprocessor.py и ce_clean_data.py

        Args:
            df_raw: Сырой DataFrame из БД (ml_features)

        Returns:
            pd.DataFrame: Обработанные данные с 26 признаками, готовые к передаче в model.predict() данные
        """

        print("Предобработка данных для инференса")
        df = df_raw.copy()

        # Шаг 1: Фильтрация "холодных" пользователей
        print("\n Шаг 1: Фильтрация 'холодных' пользователей")
        df = df[df['days_since_last_order'] < MAX_DAYS_SINCE_ORDER].copy()
        print(f"   - Осталось клиентов после фильтрации: {len(df)}")
    
        # Шаг 2: Исключение служебных колонок и days_since_last_order
        print("\n Шаг 2: Исключение служебных колонок и days_since_last_order")
        cols_to_drop = [col for col in COLS_TO_DROP if col in df.columns]
        df = df.drop(columns=cols_to_drop)
        print(f"   - Исключено колонок: {len(cols_to_drop)}")

        # Шаг 3: Перевод bool в int (если есть)
        print("\n Шаг 3: Перевод bool в int (0/1)")
        bool_cols = df.select_dtypes(include=['bool']).columns

        if len(bool_cols) > 0:
            print(f"- Найдено колонок с типом bool: {len(bool_cols)}")
            for col in bool_cols:
                print(f"   - {col}")
            df[bool_cols] = df[bool_cols].astype(int)
            print(f"   - Все bool колонки переведены в int (0/1)")
        
        # Шаг 4: Логарифмирование (только для существующих колонок)
        print("\n Шаг 4: Логарифмирование (только для существующих колонок)")
        for col in LOG_COLUMNS:
            if col in df.columns:
                df[col] = np.log1p(df[col])
        print(f"   - Применено логарифмирование для: {[c for c in LOG_COLUMNS if c in df.columns]}")

        # Шаг 5: One-Hot Encoding для reviews_reading_behavior
        print("\n Шаг 5: One-Hot Encoding для reviews_reading_behavior")
        if 'reviews_reading_behavior' in df.columns:
            dummies = pd.get_dummies(df['reviews_reading_behavior'], prefix='behavior')
            df = pd.concat([df, dummies], axis=1)
            df = df.drop(columns=['reviews_reading_behavior'])
            print(f"   - Создано бинарных колонок: {list(dummies.columns)}")
        
        # Шаг 6: Удаление model_version (если есть)
        print("\n Шаг 6: Удаление model_version")
        if 'model_version' in df.columns:
            df = df.drop(columns=['model_version'])
            print("   - Удалена колонка 'model_version' (нулевая дисперсия)")
        
        # Шаг 7: Winsorization (те же перцентили, что при обучении: 1% и 99%)
        print("\n Шаг 7: Winsorization выбросов (ограничение экстремальных значений)")
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            lower_bound = df[col].quantile(0.01)
            upper_bound = df[col].quantile(0.99)
            df[col] = df[col].clip(lower=lower_bound, upper=upper_bound)
        print(f"   - Winsorization применен (1%-99% перцентили)")

        # Шаг 8. Приведение к ожидаемым признакам (Alignment)
        # Добавляем отсутствующие колонки с нулями
        missing_features = set(self.expected_features) - set(df.columns)
        extra_features = set(df.columns) - set(self.expected_features)
        
        if missing_features:
            print(f"   -  Отсутствуют колонки: {missing_features}")
            for col in missing_features:
                df[col] = 0
        
        if extra_features:
            print(f"   -  Лишние колонки: {extra_features}")
            df = df.drop(columns=list(extra_features))
                
        # Удаляем лишние колонки и приводим к правильному порядку
        df = df[self.expected_features]
    
        # Шаг 9: StandardScaler (из joblib)
        print("\n Шаг 9: StandardScaler (из joblib)")

        # Масштабируем
        df_scaled = pd.DataFrame(
            self.scaler.transform(df),
            columns=self.expected_features,
            index=df.index
        )

        print(f"   - Предобработка завершена. Готово {len(df_scaled)} записей с {len(self.expected_features)} признаками")

        return df_scaled
    
if __name__ == "__main__":
    print("- Тест предобработки")
    print("Загрузите данные из БД и вызовите:")
    print("  preprocessor = InferencePreprocessor()")
    print("  df_processed = preprocessor.transform(df_raw)")


