# ml_create_delivery_package.py
"""
ml_create_delivery_package.py
Скрипт для автоматической сборки пакета для прода (Delivery Package)
"""

import shutil
import mlflow
import mlflow.sklearn
from pathlib import Path

def create_delivery_package():
    """Создает папку f_delivery со всеми необходимыми файлами"""
    
    delivery_dir = Path("f_delivery")
    delivery_dir.mkdir(exist_ok=True)
    
    print("- Начало сборки f_delivery-пакета\n")
    
    # Копируем ml_config.py
    shutil.copy("ml_config.py", delivery_dir / "ml_config.py")
    print(" - Скопирован ml_config.py")
    
    # Копируем и адаптируем класс предобработки
    create_adapted_preprocessor(delivery_dir)
    print(" - Скопирован класс предобработки")
    
    # Копируем и адаптируем оркестратор инференса
    create_adapted_inference_pipeline(delivery_dir)
    print(" - Скопирован оркестратор инференса")
    
    # Экспортируем лучшую модель и scaler из MLflow
    export_model_and_scaler(delivery_dir / "churn_model")
    print(" - Экспортированы модель и scaler из MLflow")
    
    # Создаем минимальный requirements.txt для прода
    with open(delivery_dir / "requirements.txt", "w", encoding="utf-8") as f:
        f.write("""pandas>=2.1.4
numpy>=1.26.3
scikit-learn>=1.4.0
joblib>=1.3.2
sqlalchemy>=2.0.25
psycopg2-binary>=2.9.9
python-dotenv>=1.0.0
""")
    print(" - Создан requirements.txt")
    
    # Создаем .env.example для заказчика
    create_env_example(delivery_dir)
    print(" - Создан .env.example")
    
    # Создаем README для прода
    create_readme(delivery_dir)
    print(" - Создан README.md")
    
    # Создаем .gitignore для папки f_delivery
    create_gitignore(delivery_dir)
    print(" - Создан .gitignore")
    
    print(f"\n- Delivery пакет успешно создан в папке: {delivery_dir.absolute()}")
    print("Теперь эту папку можно передать на прод (архивом или через Git).")
    
def create_adapted_preprocessor(delivery_dir):
    """Создает упрощенную версию preprocess_inference.py для папки f_delivery"""
    code = '''"""
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
'''
    with open(delivery_dir / "fa_preprocess_inference.py", "w", encoding="utf-8") as f:
        f.write(code)
    
def create_adapted_inference_pipeline(delivery_dir):
    """Создает упрощенную версию e_run_pipeline.py для папки delivery"""
    code = '''"""
fb_inference_pipeline.py (Delivery Version)
Оркестратор инференс-пайплайна для заказчика.
Запускает полный цикл: Загрузка из БД - Предобработка - Предсказание - Сохранение в CSV/БД.
"""
import sys
import os
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import joblib
from datetime import datetime
from sqlalchemy import create_engine, text

# Локальные импорты вместо проектных
from fa_preprocess_inference import InferencePreprocessor
from ml_config import RISK_THRESHOLDS, MODEL_VERSION, BATCH_SIZE_INFERENCE

# Пути относительно папки delivery
MODEL_DIR = Path(__file__).parent / "churn_model"
MODEL_PATH = MODEL_DIR / "model.skops" # Или model.joblib, model.pkl, в зависимости от экспорта MLflow
OUTPUT_DIR = Path(__file__).parent / "predictions"

def get_db_engine():
    """Создает подключение к БД заказчика через переменные окружения"""
    # Заказчик должен задать свои креды в .env или переменных окружения
    user = os.getenv("DB_USER", "your_db_user")
    password = os.getenv("DB_PASSWORD", "your_db_password")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    database = os.getenv("DB_NAME", "your_db_name")
    
    connection_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    return create_engine(connection_string)
    
def get_risk_level(probability: float) -> str:
    if probability >= RISK_THRESHOLDS['CRITICAL']: return 'CRITICAL'
    elif probability >= RISK_THRESHOLDS['HIGH']: return 'HIGH'
    elif probability >= RISK_THRESHOLDS['MEDIUM']: return 'MEDIUM'
    else: return 'LOW'
    
def run_prediction(df_raw: pd.DataFrame, df_preprocessed: pd.DataFrame):
    print("\\n - Запуск предсказания")
    
    # 1. Загрузка модели
    model = joblib.load(MODEL_PATH)
    
    # 2. Предсказание
    probabilities = model.predict_proba(df_preprocessed)[:, 1]
    risk_levels = [get_risk_level(p) for p in probabilities]
    
    # 3. Формирование результата
    df_results = pd.DataFrame({
        'profile_id': df_raw['profile_id'].values[:len(probabilities)],
        'churn_probability': np.round(probabilities, 4),
        'risk_level': risk_levels
    })
    
    # 4. Экспорт в CSV
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d")
    
    for level in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        df_level = df_results[df_results['risk_level'] == level]
        filepath = OUTPUT_DIR / f"churn_{level.lower()}_{timestamp}.csv"
        df_level.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"   - Сохранено {len(df_level)} записей: {filepath.name}")
        
    # 5. Обновление БД заказчика
    print("\\n - Обновление таблицы ml_features в БД")
    engine = get_db_engine()
    update_query = """
        UPDATE ml_features
        SET churn_probability = :churn_probability,
            risk_level = :risk_level,
            computed_at = NOW(),
            model_version = :model_version
        WHERE profile_id = :profile_id
    """
    
    params_list = [
        {
            'churn_probability': float(row['churn_probability']),
            'risk_level': row['risk_level'],
            'model_version': MODEL_VERSION,
            'profile_id': str(row['profile_id'])
        }
        for _, row in df_results.iterrows()
    ]
    
    with engine.begin() as conn:
        for i in range(0, len(params_list), BATCH_SIZE_INFERENCE):
            batch = params_list[i : i + BATCH_SIZE_INFERENCE]
            conn.execute(text(update_query), batch)
            
    print(f"   - Успешно обновлено {len(params_list)} записей в БД.")
    return True
    
def main():
    parser = argparse.ArgumentParser(description='Инференс пайплайн (Delivery)')
    parser.add_argument('--skip-predict', action='store_true', help='Только предобработка')
    args = parser.parse_args()
    
    print("\\n - Инференс пайплайн: Предсказание оттока клиентов")
    
    try:
        # Шаг 1: Загрузка из БД
        print("\\n - Шаг 1: Загрузка данных из БД")
        engine = get_db_engine()
        query = "SELECT * FROM ml_features WHERE days_since_last_order < 900"
        df_raw = pd.read_sql(query, engine)
        print(f"   Загружено {len(df_raw)} записей")
        
        if len(df_raw) == 0:
            print("   Нет данных для обработки. Завершение.")
            return
            
        # Шаг 2: Предобработка
        print("\\n - Шаг 2: Предобработка данных")
        preprocessor = InferencePreprocessor()
        df_preprocessed = preprocessor.transform(df_raw)
        print(f"   Готово {len(df_preprocessed)} записей с {len(df_preprocessed.columns)} признаками")
        
        # Шаг 3: Предсказание
        if not args.skip_predict:
            run_prediction(df_raw, df_preprocessed)
            
        print("\\n - Инференс пайплайн завершен успешно!")
        
    except Exception as e:
        print(f"\\n - Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
    with open(delivery_dir / "fb_inference_pipeline.py", "w", encoding="utf-8") as f:
        f.write(code)
    
def export_model_and_scaler(output_dir):
    """Экспортирует модель и scaler из MLflow в папку delivery"""
    output_dir.mkdir(exist_ok=True)
    
    # Настраиваем URI на локальную базу MLflow проекта
    mlflow.set_tracking_uri("sqlite:///mlflow.db")
    
    # Загружаем зарегистрированную модель по имени
    # Убедись, что ты зарегистрировал модель в UI как "churn_prediction_best"
    model_uri = "models:/churn_prediction_best/1"
    
    try:
        # Загружаем модель
        model = mlflow.sklearn.load_model(model_uri)
        
        # Сохраняем в формате, понятном заказчику
        mlflow.sklearn.save_model(model, str(output_dir))
        
        # Явно копируем scaler, если он не был включен в pipeline MLflow
        project_scaler_path = Path("d_ml_model/models/scaler.joblib")
        if project_scaler_path.exists():
            shutil.copy(project_scaler_path, output_dir / "scaler.joblib")
    
    except Exception as e:
        print(f"- Не удалось загрузить модель из MLflow: {e}")
        print("- Убедись, что модель зарегистрирована в MLflow UI как 'churn_prediction_best'")
        # Fallback: копируем напрямую из папки проекта
        shutil.copy("d_ml_model/models/gridsearch_cv_model.joblib", output_dir / "model.joblib")
        shutil.copy("d_ml_model/models/scaler.joblib", output_dir / "scaler.joblib")

# Функция создания .env.example
def create_env_example(delivery_dir):
    """Создает файл .env.example с примерами переменных окружения для БД"""
    env_example_content = """
# Конфигурация подключения к базе данных
# Скопируйте этот файл в .env и заполните реальными значениями:
#   cp .env.example .env
#
# ВАЖНО: Никогда не коммитьте файл .env в Git

# Основные параметры подключения PostgreSQL
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database_name

# SSL-настройки (опционально)
# Для продакшена рекомендуется использовать sslmode=require
# Для локальной разработки можно использовать sslmode=disable
DB_SSLMODE=require

# Примеры для разных окружений:
# Локальная разработка (без SSL):
# DB_USER=postgres
# DB_PASSWORD=postgres
# DB_HOST=localhost
# DB_PORT=5432
# DB_NAME=churn_prediction
# DB_SSLMODE=disable

# Продакшен (с SSL):
# DB_USER=app_user
# DB_PASSWORD=secure_password_here
# DB_HOST=db.yourcompany.com
# DB_PORT=5432
# DB_NAME=production_db
# DB_SSLMODE=require
"""
    with open(delivery_dir / ".env.example", "w", encoding="utf-8") as f:
        f.write(env_example_content)

def create_readme(delivery_dir):
    readme_content = """# - Churn Prediction Model - Delivery Package

Этот пакет содержит обученную ML-модель для прогнозирования оттока клиентов и все необходимые скрипты для её запуска.

## - Структура папки
- `ml_config.py` — константы и пороги для ML (безопасно для передачи).
- `fa_preprocess_inference.py` — логика предобработки данных (26 признаков).
- `fb_inference_pipeline.py` — **главный скрипт** для запуска предсказаний.
- `churn_model/` — папка с файлами модели (`model.skope`, `scaler.joblib`, `conda.yaml`).
- `predictions/` — сюда будут сохраняться CSV-файлы с результатами.
- `requirements.txt` — необходимые Python-библиотеки.

## Инструкция по запуску

### 1. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 2. Настройка подключения к БД
```bash
cp .env.example .env
```
*Заполните `.env` своими настройками*

### 3. Запуск полного пайплайна (от сбора данных до предсказания)
```bash
python f_delivery/fb_inference_pipeline.py    # Оркестратор инференс-пайплайна для заказчика. Запускает полный цикл: Загрузка из БД - Предобработка - Предсказание - Сохранение в CSV/БД.
```

"""
    with open(delivery_dir / "README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
        
# Функция создания .gitignore для f_delivery
def create_gitignore(delivery_dir):
    """Создает .gitignore для папки f_delivery, чтобы исключить чувствительные файлы"""
    gitignore_content = """# Чувствительные данные - никогда не коммитить!
.env

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Виртуальное окружение
venv/
ENV/
env/
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Результаты предсказаний (могут содержать бизнес-данные)
predictions/

# OS
.DS_Store
Thumbs.db
"""
    with open(delivery_dir / ".gitignore", "w", encoding="utf-8") as f:
        f.write(gitignore_content)
    
if __name__ == "__main__":
    create_delivery_package()

    
    
    
    