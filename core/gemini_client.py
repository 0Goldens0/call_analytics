import google.generativeai as genai
from typing import Any, Optional

class GeminiClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        genai.configure(api_key=api_key)
        
    def upload_file(self, file_path: str) -> Optional[Any]:
        """Загружает файл в Gemini."""
        try:
            return genai.upload_file(file_path)
        except Exception as e:
            print(f"Ошибка при загрузке файла {file_path} в Gemini: {e}")
            return None
            
    def generate_content(self, 
                        inputs: Any,
                        model_name: str,
                        generation_config: Optional[genai.GenerationConfig] = None) -> str:
        """Генерирует контент с помощью модели Gemini."""
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(inputs, generation_config=generation_config)
        return response.text