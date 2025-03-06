import os
import json
import re
import google.generativeai as genai
from typing import List
from typing_extensions import TypedDict

from call_analytics.core.file_utils import load_json_files, ensure_folders
from call_analytics.config.settings import GEMINI_MODEL_NAME

# Определяем схему ответа для сводной аналитики
class CallsList(TypedDict):
    call_name: str
    score: float
    text: str

class SingleManagerSummary(TypedDict):
    manager_name: str
    all_score: List[CallsList]
    date: str
    total_calls: int
    summary: str

class SummaryAnalyzer:
    def __init__(self, api_key: str, system_prompt: str, main_prompt: str, response_schema):
        self.api_key = api_key
        self.system_prompt = system_prompt
        self.main_prompt = main_prompt
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(GEMINI_MODEL_NAME)  # Используем pro-модель для summary
        self.response_schema = response_schema  # Используем переданную схему ответа

    def process_manager_summary(self, manager_folder: str, date_str: str) -> bool:
        """
        Обрабатывает сводную аналитику для одного менеджера.
        Загружает JSON файлы из папки Analitics, отправляет запрос в Gemini
        и сохраняет summary в папку sum.
        """
        print(f"    [SummaryAnalyzer.process_manager_summary] Обработка сводки для папки: {manager_folder}")
        analytics_folder = os.path.join(manager_folder, "Analitics")
        sum_folder = os.path.join(manager_folder, "sum")
        ensure_folders(manager_folder)

        json_files = load_json_files(analytics_folder)
        if not json_files:
            print(f"    [SummaryAnalyzer.process_manager_summary] Нет JSON файлов в папке {analytics_folder}. Пропускаем.")
            return False

        try:
            response_text = self._upload_jsons_to_model(manager_folder, date_str, json_files)
        except Exception as e:
            print(f"    [SummaryAnalyzer.process_manager_summary] Ошибка при обращении к модели: {e}")
            return False

        try:
            summary_parsed = self._parse_summary_response(response_text)
        except json.JSONDecodeError as e:
            print(f"    [SummaryAnalyzer.process_manager_summary] Модель вернула невалидный JSON:\n{response_text}")
            return False

        output_fname = f"summary_{date_str}.json"
        out_path = os.path.join(sum_folder, output_fname)
        try:
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(summary_parsed, f, ensure_ascii=False, indent=4)
            print(f"    [SummaryAnalyzer.process_manager_summary] Итоговое summary сохранено: {out_path}")
            return True
        except Exception as e:
            print(f"    [SummaryAnalyzer.process_manager_summary] Ошибка при сохранении summary: {e}")
            return False

    def _upload_jsons_to_model(self, manager_name: str, date_str: str, list_of_json: List[dict]) -> str:
        """
        Отправляет список JSON объектов (аналитика отдельных звонков) в модель Gemini как единый пакет.
        """
        print(f"      [SummaryAnalyzer._upload_jsons_to_model] Отправка JSONs в модель для менеджера: {manager_name}")
        calls_str = json.dumps(list_of_json, ensure_ascii=False)
        main_prompt_with_calls = (
            f"{self.main_prompt}\n\n"
            f"Список JSON звонков:\n{calls_str}\n\n"
            f"Задача: составить общий итог работы менеджера {manager_name} за {date_str}."
        )

        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=self.response_schema,
            temperature=0.1,
        )
        inputs = [self.system_prompt, main_prompt_with_calls]
        response = self.model.generate_content(inputs)
        return response.text

    def _parse_summary_response(self, response_text: str) -> dict:
        """
        Парсит ответ от модели Gemini, который должен быть в формате JSON.
        Если стандартный json.loads() не срабатывает, пытается извлечь корректный JSON с помощью регулярного выражения.
        """
        print(f"      [SummaryAnalyzer._parse_summary_response] Парсинг JSON ответа модели.")
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            # Попытка извлечь JSON между первой фигурной скобкой и последней
            match = re.search(r'(\{.*\})', response_text, re.DOTALL)
            if match:
                json_str = match.group(1)
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as e2:
                    print(f"      [SummaryAnalyzer._parse_summary_response] Ошибка при парсинге извлечённого JSON: {e2}")
                    raise e2
            else:
                raise e
