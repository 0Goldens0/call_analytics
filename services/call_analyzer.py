import os
import json
import google.generativeai as genai
from typing import List
import shutil

from call_analytics.core.models import SingleCallAnalysis
from call_analytics.core.file_utils import get_audio_duration, ensure_folders
from call_analytics.core.gemini_client import GeminiClient
from call_analytics.config.settings import GEMINI_FLASH_MODEL

class CallAnalyzer:
    def __init__(self, api_key: str, script_text: str, ideal_call_text: str, 
                 sample_recommendations_text: str, system_prompt: str, main_prompt: str):
        self.client = GeminiClient(api_key)
        self.script_text = script_text
        self.ideal_call_text = ideal_call_text
        self.sample_recommendations_text = sample_recommendations_text
        self.system_prompt = system_prompt
        self.main_prompt = main_prompt
        
    def process_single_call(self, manager_folder: str, filename: str) -> bool:
        """Обрабатывает один звонок."""
        processed_folder, analytics_folder, _ = ensure_folders(manager_folder)
        
        filepath = os.path.join(manager_folder, filename)
        duration_sec = get_audio_duration(filepath)

        # Извлекаем имя контрагента
        no_ext = os.path.splitext(filename)[0]
        splitted = no_ext.split('_')
        contragent_name = splitted[1].strip() if len(splitted) >= 2 else ""

        json_filename = no_ext + ".json"
        json_output = os.path.join(analytics_folder, json_filename)

        # Обработка коротких звонков
        if duration_sec < 30:
            short_json = {
                "call_title": filename,
                "compliance_score": 0.0,
                "transcription": [],
                "detailed_analysis": "",
                "recommendations": "",
                "contragent": contragent_name
            }
            with open(json_output, 'w', encoding='utf-8') as f:
                json.dump(short_json, f, ensure_ascii=False, indent=4)
            shutil.move(filepath, os.path.join(processed_folder, filename))
            return True

        # Загрузка в Gemini
        uploaded = self.client.upload_file(filepath)
        if not uploaded:
            return False

        # Перемещаем в processed
        try:
            shutil.move(filepath, os.path.join(processed_folder, filename))
        except Exception as e:
            print(f"[{manager_folder}] Не удалось переместить {filename}: {e}")

        # Формируем промпты
        context_prompt = (
            f"{self.system_prompt}\n\n"
            f"{self.main_prompt}\n\n"
            f"Сценарий продаж:\n{self.script_text}\n\n"
            f"Идеальный звонок:\n{self.ideal_call_text}\n\n"
            f"Пример рекомендаций:\n{self.sample_recommendations_text}\n\n"
            "Аудиофайл звонка:"
        )

        # Конфигурация генерации
        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=SingleCallAnalysis,
            temperature=0.1,
        )

        # Запрос к модели
        try:
            response = self.client.generate_content(
                inputs=[context_prompt, uploaded],
                model_name=GEMINI_FLASH_MODEL,
                generation_config=generation_config
            )
            
            parsed = json.loads(response)
            parsed["call_title"] = filename
            parsed["contragent"] = contragent_name
            
            with open(json_output, 'w', encoding='utf-8') as f:
                json.dump(parsed, f, ensure_ascii=False, indent=4)
            return True
            
        except Exception as e:
            print(f"[{manager_folder}] Ошибка при обработке {filename}: {e}")
            return False