# c_eda/ca_load_data.py
"""
01_load_data.py
Загрузка данных из PostgreSQL в pandas DataFrame
"""

# ====== подключения к Timeweb Cloud PostgreSQL с SSL ===========
import sys
import pandas as pd
from pathlib import Path

# Добавляем корень проекта в path для импорта config
