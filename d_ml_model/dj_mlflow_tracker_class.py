# d_ml_model/dj_mlflow_tracker_class.py
"""
d_ml_model/dh_mlflow_tracker_class.py
Класс для трекинга экспериментов через MLflow
"""

import mlflow
import mlflow.sklearn
from pathlib import Path
from typing import Dict, Optional, Any

class MLflowTracker:
    """
    Класс для управления MLflow экспериментами
    
    Использование:
        tracker = MLflowTracker(experiment_name="churn_prediction")
        
        with tracker.start_run("logistic_regression"):
            tracker.log_params({"C": 0.1, "penalty": "l2"})
            tracker.log_metrics({"recall": 0.95, "roc_auc": 0.85})
            tracker.log_model(model, "model")
            tracker.log_artifact("confusion_matrix.png")
    """
    
    def __init__(
        self,
        tracking_uri: str = "sqlite:///mlflow.db",
        experiment_name: str = "churn_prediction"
    ):
        """
        Инициализация трекера
        
        Args:
            tracking_uri: URI для хранения метаданных MLflow
            experiment_name: Название эксперимента
        """
        self.tracking_uri = tracking_uri
        self.experiment_name = experiment_name
        
        # Настраиваем MLflow
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)
        
        print(f"- MLflowTracker инициализирован")
        print(f"   Tracking URI: {tracking_uri}")
        print(f"   Experiment: {experiment_name}")
        
    def start_run(self, run_name: str, nested: bool = False):
        """
        Контекстный менеджер для запуска эксперимента
        
        Args:
            run_name: Название запуска (обычно название модели)
            nested: Вложенный запуск (для подэкспериментов)
        
        Yields:
            mlflow.active_run()
        
        Пример:
            with tracker.start_run("logistic_regression"):
                tracker.log_metrics({"recall": 0.95})
        """
        return mlflow.start_run(run_name=run_name, nested=nested)
    
    def log_params(self, params: Dict[str, Any]):
        """
        Логирует гиперпараметры модели
        
        Args:
            params: Словарь с параметрами
        """
        mlflow.log_params(params)
        print(f"   - Записаны параметры: {list(params.keys())}")
        
    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None):
        """
        Логирует метрики модели
        
        Args:
            metrics: Словарь с метриками
            step: Шаг (для обучения по эпохам)
        """
        mlflow.log_metrics(metrics, step=step)
        print(f"   - Записаны метрики: {list(metrics.keys())}")
        
    def log_model(
        self,
        model,
        artifact_path: str = "model",
        registered_model_name: Optional[str] = None
    ):
        """
        Логирует sklearn модель
        
        Args:
            model: Обученная sklearn модель
            artifact_path: Путь в артефактах
            registered_model_name: Имя для Model Registry
        """
        mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path=artifact_path,
            registered_model_name=registered_model_name
        )
        print(f"   - Записана модель: {artifact_path}")
        
    def log_artifact(self, local_path: str, artifact_path: Optional[str] = None):
        """
        Логирует файл (график, CSV, и т.д.)
        
        Args:
            local_path: Путь к файлу на диске
            artifact_path: Путь в артефактах (опционально)
        """
        if Path(local_path).exists():
            mlflow.log_artifact(local_path, artifact_path)
            print(f"   - Записан артефакт: {local_path}")
        else:
            print(f"   - Файл не найден: {local_path}")
            
    def log_artifacts(self, local_dir: str, artifact_path: Optional[str] = None):
        """
        Логирует всю папку с файлами
        
        Args:
            local_dir: Путь к папке
            artifact_path: Путь в артефактах
        """
        if Path(local_dir).exists():
            mlflow.log_artifacts(local_dir, artifact_path)
            print(f"   - Записана папка: {local_dir}")
            
    def end_run(self):
        """Завершает активный запуск"""
        mlflow.end_run()
        
    def get_run_id(self) -> Optional[str]:
        """Возвращает ID текущего запуска"""
        active_run = mlflow.active_run()
        return active_run.info.run_id if active_run else None
    
# Singleton экземпляр для удобства
_tracker_instance: Optional[MLflowTracker] = None

def get_tracker(
    tracking_uri: str = "sqlite:///mlflow.db",
    experiment_name: str = "churn_prediction"
) -> MLflowTracker:
    """
    Возвращает singleton экземпляр трекера
    
    Args:
        tracking_uri: URI для MLflow
        experiment_name: Название эксперимента
    
    Returns:
        MLflowTracker instance
    """
    global _tracker_instance
    
    if _tracker_instance is None:
        _tracker_instance = MLflowTracker(tracking_uri, experiment_name)
        
    return _tracker_instance
            

            
            
        
        
        
        