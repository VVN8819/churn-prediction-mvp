# - Churn Prediction Model - Delivery Package

Этот пакет содержит обученную ML-модель для прогнозирования оттока клиентов и все необходимые скрипты для её запуска.

## - Структура пакета
```bash
f_delivery/
├── sql/ # SQL-скрипты для БД
├── fc_bootstrap_database.py # Инициализация БД
├── fd_sync_cdp_data.py # Первичная загрузка из CDP
├── fe_refresh_features.py # Обновление признаков
├── fa_preprocess_inference.py # ML-препроцессор
├── fb_inference_pipeline.py # ML-инференс
├── ml_config.py # ML-константы
├── churn_model/ # Модель + scaler
├── predictions/ # сюда будут сохраняться CSV-файлы с результатами.
├── requirements.txt # Зависимости
├── .env.example # Шаблон переменных
├── README.md # Документация
└── .gitignore # Git исключения
```
## Что включено

### Фаза 1: Инициализация инфраструктуры
- **SQL-скрипты** (`sql/`) — создание таблиц, партиций, индексов, материализованных представлений
- **fc_bootstrap_database.py** — автоматическая инициализация БД
- **fd_sync_cdp_data.py** — первичная загрузка данных из CDP Elasticsearch
- **fe_refresh_features.py** — расчет 24 признаков и обновление Feature Store

### Фаза 2: ML-инференс
- **fa_preprocess_inference.py** — предобработка данных (9 шагов трансформации)
- **fb_inference_pipeline.py** — оркестратор инференса (загрузка - предобработка - предсказание - сохранение)
- **churn_model/** — обученная модель
- **ml_config.py** — ML-константы и пороги

## Инструкция по запуску

### 1. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 2. Настройка переменных окружения для подключения к БД
```bash
cp f_delivery/.env.example .env
```
*Заполните `.env` своими настройками*

### 3. Фаза 1: Инициализация БД
```bash
python fc_bootstrap_database.py
```
*Создаст все таблицы, индексы и материализованные представления.

### 4. Фаза 1: Первичная загрузка данных из CDP
```bash
python fd_sync_cdp_data.py
```
* Загрузит исторические события из Elasticsearch в PostgreSQL.

### 5. Фаза 1: Расчет признаков
```bash
python fe_refresh_features.py
```
* Рассчитает 24 признака для всех активных пользователей и сохранит в `ml_features`.

### 6. Фаза 2: Запуск инференса
```bash
python fb_inference_pipeline.py
```
* Загрузит данные из `ml_features`, сделает предсказания, сохранит CSV и обновит БД.

### Результаты
Предсказания сохраняются в папку `predictions/`:
```bash
churn_critical_YYYYMM.csv — клиенты с риском оттока ≥70%
churn_high_YYYYMM.csv — риск 50-70%
churn_medium_YYYYMM.csv — риск 30-50%
churn_low_YYYYMM.csv — риск <30%
```
Каждый CSV содержит: `profile_id`, `churn_probability`, `risk_level`

### Ежедневное обслуживание
Для ежедневного обновления признаков или предсказаний:
```bash
# 1. Загрузить новые события из CDP (опционально, если есть новые данные)
python fd_sync_cdp_data.py

# 2. Обновить признаки
python fe_refresh_features.py

# 3. Сделать предсказания
python fb_inference_pipeline.py
```

### Безопасность
- Файл `.env` с паролями никогда не коммитится в Git
- Модель использует только агрегированные признаки, персональные данные не обрабатываются
- Все SQL-запросы используют параметризованные запросы (защита от SQL-инъекций)

### Поддержка
При возникновении проблем:
1. Проверьте подключение к БД: `psql -h $DB_HOST -U $DB_USER -d $DB_NAME`
2. Проверьте подключение к ES: `curl $ES_HOST`
3. Проверьте логи в таблице `events_processing_log`
