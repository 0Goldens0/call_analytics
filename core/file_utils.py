import os
import shutil
import docx
from pymediainfo import MediaInfo
import json
from typing import List

def extract_text_from_docx(docx_path: str) -> str:
    """Читаем docx, возвращаем содержимое построчно."""
    try:
        doc = docx.Document(docx_path)
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        print(f"Ошибка при чтении файла {docx_path}: {e}")
        return ""

def get_audio_duration(filepath: str) -> float:
    """Получает длительность аудиофайла в секундах."""
    info = MediaInfo.parse(filepath)
    for track in info.tracks:
        if track.track_type == 'Audio' and track.duration:
            return float(track.duration) / 1000.0
    return 0.0

def ensure_folders(manager_folder: str) -> tuple:
    """Создает необходимые подпапки и возвращает пути к ним."""
    processed_folder = os.path.join(manager_folder, "processed")
    analytics_folder = os.path.join(manager_folder, "Analitics")
    summary_folder = os.path.join(manager_folder, "sum")
    
    os.makedirs(processed_folder, exist_ok=True)
    os.makedirs(analytics_folder, exist_ok=True)
    os.makedirs(summary_folder, exist_ok=True)
    
    return processed_folder, analytics_folder, summary_folder

def load_json_files(json_folder: str) -> List[dict]:
    """
    Считывает все .json файлы из папки `json_folder`.
    Возвращает список словарей (по одному на файл).
    """
    all_data = []
    for fname in os.listdir(json_folder):
        if fname.lower().endswith('.json'):
            fullpath = os.path.join(json_folder, fname)
            if os.path.isfile(fullpath):
                try:
                    with open(fullpath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        all_data.append(data)
                except Exception as e:
                    print(f"Ошибка при чтении JSON файла {fullpath}: {e}")
    return all_data