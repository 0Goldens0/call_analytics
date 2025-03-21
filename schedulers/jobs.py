import os
import datetime
import concurrent.futures
import shutil
from typing import List
import logging
from datetime import datetime as dt

from call_analytics.config.settings import (
    ROOT_DATA_DIR, SCRIPT_PATH, IDEAL_CALL_PATH, 
    SAMPLE_RECOMMENDATIONS_PATH, MAX_WORKERS_FOR_MANAGERS,
    MAX_WORKERS_FOR_CALLS, MAX_ROUNDS
)
from call_analytics.core.file_utils import extract_text_from_docx
from call_analytics.services.call_analyzer import CallAnalyzer
from call_analytics.services.summary_analyzer import SummaryAnalyzer, SingleManagerSummary
from call_analytics.config.prompts import (
    CALLS_SYSTEM_PROMPT,
    CALLS_MAIN_PROMPT,
    SUMMARY_SYSTEM_PROMPT,
    SUMMARY_MAIN_PROMPT
)

class AnalyticsJob:
    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys
        
        # Загружаем тексты
        self.script_text = extract_text_from_docx(SCRIPT_PATH)
        self.ideal_call_text = extract_text_from_docx(IDEAL_CALL_PATH)
        self.sample_recommendations_text = extract_text_from_docx(SAMPLE_RECOMMENDATIONS_PATH)
        
        if not (self.script_text and self.ideal_call_text and self.sample_recommendations_text):
            raise ValueError("Не удалось загрузить необходимые docx файлы")
            
        self.system_prompt = (
            "Я отвечу как всемирно известный эксперт по анализу звонков с наградой 'Лучший аналитик года'.\n\n"
            # ... (здесь идет длинный текст промпта из оригинального скрипта)
        )

    def process_calls_for_manager(self, manager_folder: str, api_key: str):
        """Обрабатывает все звонки одного менеджера."""
        print(f"  [process_calls_for_manager] Обработка папки менеджера: {manager_folder}")  # ЛОГ

        analyzer = CallAnalyzer(
            api_key,
            self.script_text,
            self.ideal_call_text,
            self.sample_recommendations_text,
            CALLS_SYSTEM_PROMPT,
            CALLS_MAIN_PROMPT
        )

        audio_files = [
            f for f in os.listdir(manager_folder)
            if os.path.isfile(os.path.join(manager_folder, f))
            and f.lower().endswith(('.wav', '.mp3', '.aiff', '.aac', '.ogg', '.flac'))
        ]
        print(f"  [process_calls_for_manager] Найдено аудиофайлов: {len(audio_files)}")  # ЛОГ

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS_FOR_CALLS) as executor:
            futures = []
            for filename in audio_files:
                print(f"  [process_calls_for_manager] Отправка на обработку: {filename}")  # ЛОГ
                future = executor.submit(analyzer.process_single_call, manager_folder, filename)
                futures.append(future)
            concurrent.futures.wait(futures)

    def process_summary_for_manager(self, manager_folder: str, date_str: str, api_key: str):
        """Обрабатывает сводную аналитику для менеджера."""
        # Здесь можно не создавать лишнюю переменную mgr_folder, оставляем manager_folder
        analyzer = SummaryAnalyzer(
            api_key,
            SUMMARY_SYSTEM_PROMPT,
            SUMMARY_MAIN_PROMPT,
            SingleManagerSummary  # Теперь схема передается извне (см. summary_analyzer.py)
        )
        print(f"  [process_summary_for_manager] Запуск SummaryAnalyzer для папки: {manager_folder}")  # ЛОГ
        return analyzer.process_manager_summary(manager_folder, date_str)

    def run_call_analysis(self):
        """Запускает анализ звонков за последние дни."""
        for offset in range(1, 5):
            target_date = datetime.date.today() - datetime.timedelta(days=offset)
            date_str = target_date.strftime('%d%m%y')
            root_folder = os.path.join(ROOT_DATA_DIR, date_str)

            if not os.path.exists(root_folder):
                print(f"Папка {root_folder} не найдена (прошло {offset} дн). Пропускаем.")
                continue

            print(f"\n=== Обработка папки за {offset} дн назад: {root_folder} ===")

            # Раскладываем аудио-файлы по менеджерам (логика из single_calls_analitics.py)
            files_in_root = os.listdir(root_folder)
            audio_files = [
                f for f in files_in_root
                if os.path.isfile(os.path.join(root_folder, f))
                and f.lower().endswith(('.wav', '.mp3', '.aiff', '.aac', '.ogg', '.flac'))
            ]
            manager_files_map = {}
            for afile in audio_files:
                no_ext = os.path.splitext(afile)[0]
                splitted = no_ext.split('_')
                manager_name = splitted[0].strip() if splitted else "UnknownManager"
                manager_files_map.setdefault(manager_name, []).append(afile)

            for mgr, flist in manager_files_map.items():
                mgr_folder = os.path.join(root_folder, mgr)
                os.makedirs(mgr_folder, exist_ok=True)
                for f in flist:
                    src = os.path.join(root_folder, f)
                    dst = os.path.join(mgr_folder, f)
                    try:
                        shutil.move(src, dst)
                    except Exception as e:
                        print(f"Ошибка переноса {f}: {e}")

            # Получаем папки менеджеров (теперь уже после раскладывания)
            manager_folders = [
                os.path.join(root_folder, d) for d in os.listdir(root_folder)
                if os.path.isdir(os.path.join(root_folder, d))
            ]
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS_FOR_MANAGERS) as executor:
                futures = []
                for i, folder in enumerate(manager_folders):
                    api_key = self.api_keys[i % len(self.api_keys)]
                    future = executor.submit(self.process_calls_for_manager, folder, api_key)
                    futures.append(future)
                concurrent.futures.wait(futures)

    def run_summary_analysis(self):
        """Запускает анализ сводной статистики за последний день."""
        logging.info("=== Запуск run_summary_analysis ===")  # ЛОГ
        
        # Получаем список всех папок с датами и выбираем самую последнюю
        date_folders = [
            d for d in os.listdir(ROOT_DATA_DIR)
            if os.path.isdir(os.path.join(ROOT_DATA_DIR, d)) and d.isdigit() and len(d) == 6
        ]
        if not date_folders:
            logging.info(f"Нет папок с датами в {ROOT_DATA_DIR}. Пропускаем сводную аналитику.")
            return

        # Сортировка по дате: преобразуем строку в дату по формату ddmmyy
        date_folders.sort(key=lambda d: dt.strptime(d, "%d%m%y"), reverse=True)
        logging.info(f"Найдены папки дат (от новых к старым): {date_folders}")
        date_str = date_folders[0]  # Берем самую последнюю дату
        logging.info(f"Выбрана последняя папка с датой для сводной аналитики: {date_str}")
        root_folder = os.path.join(ROOT_DATA_DIR, date_str)
        
        if not os.path.exists(root_folder):
            print(f"Папка {root_folder} не найдена. Пропускаем.")
            return
          
        manager_folders = [
            os.path.join(root_folder, d) for d in os.listdir(root_folder)
            if os.path.isdir(os.path.join(root_folder, d))
        ]
        
        remaining = set(manager_folders)
        round_i = 0
        
        while remaining and round_i < MAX_ROUNDS:
            round_i += 1
            print(f"\n=== Раунд #{round_i}. Осталось менеджеров: {len(remaining)} ===")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS_FOR_MANAGERS) as executor:
                futures = {}
                for folder in remaining:
                    i = manager_folders.index(folder)
                    api_key = self.api_keys[i % len(self.api_keys)]
                    future = executor.submit(
                        self.process_summary_for_manager, 
                        folder, 
                        date_str,
                        api_key
                    )
                    futures[future] = folder
                    
                concurrent.futures.wait(futures.keys())
                
            new_remaining = set()
            for future, folder in futures.items():
                try:
                    if not future.result():
                        new_remaining.add(folder)
                except Exception as e:
                    print(f"[{folder}] Ошибка: {e}")
                    new_remaining.add(folder)
                    
            remaining = new_remaining

# Экспортируем класс
__all__ = ['AnalyticsJob']
