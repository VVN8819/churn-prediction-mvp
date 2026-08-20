"""
fa_preprocess_inference.py (Delivery Version)
Класс для предобработки данных перед инференсом.
Адаптирован для автономной работы в папке f_delivery
"""
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from ml_config import MAX_DAYS_SINCE_ORDER, LOG_COLUMNS, COLS_TO_DROP

# Путь к scaler теперь относительный (в той же папке)
SCALER_PATH = Path(__file__).parent / "churn_model" / "scaler.joblib"

class InferencePreprocessor:
    def __init__(self, scaler_path: str = SCALER_PATH):
        if not Path(scaler_path).exists():
            raise FileNotFoundError(f"Scaler не найден: {scaler_path}")
        
        self.scaler = joblib.load(scaler_path)
        self.expected_features = list(self.scaler.feature_names_in_)
        
    def transform(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        df = df_raw.copy()

        # 1. Фильтрация
        df = df[df['days_since_last_order'] < MAX_DAYS_SINCE_ORDER].copy()
    
        # 2. Исключение колонок
        cols_to_drop = [col for col in COLS_TO_DROP if col in df.columns]
        df = df.drop(columns=cols_to_drop)

        # 3. Bool в Int
        bool_cols = df.select_dtypes(include=['bool']).columns
        if len(bool_cols) > 0:
            df[bool_cols] = df[bool_cols].astype(int)
        
        # 4. Логарифмирование
        for col in LOG_COLUMNS:
            if col in df.columns:
                df[col] = np.log1p(df[col])
        
        # 5. One-Hot Encoding
        if 'reviews_reading_behavior' in df.columns:
            dummies = pd.get_dummies(df['reviews_reading_behavior'], prefix='behavior')
            df = pd.concat([df, dummies], axis=1)
            df = df.drop(columns=['reviews_reading_behavior'])
        
        # 6. Удаление model_version
        if 'model_version' in df.columns:
            df = df.drop(columns=['model_version'])
        
        # 7. Winsorization (1%-99%)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            lower_bound = df[col].quantile(0.01)
            upper_bound = df[col].quantile(0.99)
            df[col] = df[col].clip(lower=lower_bound, upper=upper_bound)

        # 8. Alignment (приведение к ожидаемым признакам)
        missing_features = set(self.expected_features) - set(df.columns)
        extra_features = set(df.columns) - set(self.expected_features)
        
        for col in missing_features:
            df[col] = 0
        if extra_features:
            df = df.drop(columns=list(extra_features))
                
        df = df[self.expected_features]
    
        # 9. StandardScaler
        df_scaled = pd.DataFrame(
            self.scaler.transform(df),
            columns=self.expected_features,
            index=df.index
        )

        return df_scaled
