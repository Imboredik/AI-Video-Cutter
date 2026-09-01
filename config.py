# config.py

import os
import sys
from dotenv import load_dotenv

load_dotenv()

class Config:
    # LLM
    QWEN_API_KEY = os.getenv("QWEN_API_KEY")
    QWEN_API_URL = os.getenv("QWEN_API_URL")
    QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen/qwen3.5-flash")

    # Проект
    LOG_DIR = os.getenv("LOG_DIR", "logs")
    TEMP_DIR = os.getenv("TEMP_DIR", "temp")
    PROJECTS_DIR = os.getenv("PROJECTS_DIR", "projects")

    @classmethod
    def init_dirs(cls):
        os.makedirs(cls.LOG_DIR, exist_ok=True)
        os.makedirs(cls.TEMP_DIR, exist_ok=True)
        os.makedirs(cls.PROJECTS_DIR, exist_ok=True)
        os.makedirs(os.path.join(cls.LOG_DIR, "llm"), exist_ok=True)


def get_ffmpeg_path():
    """Возвращает путь к ffmpeg.exe рядом с программой."""
    if getattr(sys, 'frozen', False):
        # Запущено как .exe
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    # Ищем ffmpeg.exe в папке ffmpeg/bin/
    ffmpeg_path = os.path.join(base_dir, 'ffmpeg', 'bin', 'ffmpeg.exe')

    if os.path.exists(ffmpeg_path):
        return ffmpeg_path
    return 'ffmpeg'  # fallback на системный