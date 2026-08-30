# Dockerfile для Churn Prediction System

# Базовый образ: Python 3.12 slim (минимальный размер)
FROM python:3.12-slim

# Метаданные
LABEL maintainer="vitalii8819@yandex.ru"
LABEL description="Churn Prediction Inference Service"
LABEL version="1.0"

# Переменные окружения (значения по умолчанию)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Рабочая директория внутри контейнера
WORKDIR /app

# Копируем только f_delivery/ (не весь проект!)
COPY f_delivery/ ./

# Устанавливаем зависимости
# Сначала requirements.txt для кэширования слоя
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Создаем директорию для предсказаний
RUN mkdir -p predictions

# Создаем non-root пользователя для безопасности
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Healthcheck — проверка работоспособности контейнера
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import psycopg2; psycopg2.connect(host='$DB_HOST', dbname='$DB_NAME', user='$DB_USER', password='$DB_PASSWORD')" || exit 1

# Точка входа по умолчанию
ENTRYPOINT ["python"]

# Команда по умолчанию (можно переопределить в docker-compose)
CMD ["fb_inference_pipeline.py"]


