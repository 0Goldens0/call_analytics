import os

# Корневая директория теперь D:\BeelineRecords
PROJECT_ROOT_DIR = r"D:\BeelineRecords"

# Пути к файлам относительно корневой директории
SCRIPT_PATH = os.path.join(PROJECT_ROOT_DIR, "script.docx")
IDEAL_CALL_PATH = os.path.join(PROJECT_ROOT_DIR, "perfect_call.docx")
SAMPLE_RECOMMENDATIONS_PATH = os.path.join(PROJECT_ROOT_DIR, "recomendations.docx")

# Папка для данных звонков (теперь корневая директория и есть папка с данными)
ROOT_DATA_DIR = PROJECT_ROOT_DIR  # Данные хранятся прямо в корневой папке D:\BeelineRecords

# Настройки параллелизма
MAX_WORKERS_FOR_MANAGERS = 3
MAX_WORKERS_FOR_CALLS = 10
MAX_ROUNDS = 6

# Расписание
CALL_ANALYSIS_TIME = "06:30"
SUMMARY_ANALYSIS_TIME = "07:30"
ADDITIONAL_ANALYSIS_TIME = "10:10"

# Настройки Gemini
GEMINI_MODEL_NAME = "gemini-1.5-pro"
GEMINI_FLASH_MODEL = "gemini-1.5-flash"