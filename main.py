import schedule
import time
from typing import Callable
import logging
import sys

# Базовая проверка
print("=== Тестовый запуск ===")
sys.stdout.flush()  # Принудительный вывод

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('call_analytics.log', encoding='utf-8')
    ]
)

try:
    from call_analytics.config.api_keys import GEMINI_API_KEYS
    # Импортируем класс job'а
    from call_analytics.schedulers.jobs import AnalyticsJob
    print("Импорты успешны")
    sys.stdout.flush()
except Exception as e:
    print(f"Ошибка импорта: {e}")
    sys.stdout.flush()
    raise

def create_job() -> AnalyticsJob:
    """Создает экземпляр job'а с настройками."""
    logging.info("Создание job'а")
    return AnalyticsJob(api_keys=GEMINI_API_KEYS)

def schedule_job(time_str: str, job_func: Callable):
    """Планирует выполнение задачи на определенное время."""
    logging.info(f"Планирование задачи на {time_str}")
    schedule.every().day.at(time_str).do(job_func)

def run_schedule():
    """Запускает задачи по расписанию."""
    job = create_job()
    # Первичный запуск анализа звонков: в 06:30 и 10:10
    schedule_job("06:30", job.run_call_analysis)
    schedule_job("10:10", job.run_call_analysis)
    # Повторный запуск (сводная аналитика): в 07:30
    schedule_job("07:30", job.run_summary_analysis)
    
    logging.info("Сервис запущен по расписанию.")
    while True:
        schedule.run_pending()
        time.sleep(1)

def main():
    """Основная функция приложения."""
    logging.info("Запуск приложения")
    try:
        run_schedule()
    except Exception as e:
        logging.error(f"Ошибка при запуске: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
