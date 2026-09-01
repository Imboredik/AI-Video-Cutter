# core/signals.py

from PyQt6.QtCore import QObject, pyqtSignal


class Signals(QObject):
    """Централизованные сигналы для связи между UI и бекендом."""

    # Сигналы для транскрибации
    transcription_progress = pyqtSignal(int)  # 0-100
    transcription_status = pyqtSignal(str)  # статус
    transcription_log = pyqtSignal(str)  # лог в чат
    transcription_finished = pyqtSignal(object)  # результат
    transcription_error = pyqtSignal(str)  # ошибка

    # Сигналы для LLM
    # llm_response = pyqtSignal(str)  # ответ от LLM
    llm_error = pyqtSignal(str)  # ошибка LLM
    llm_progress = pyqtSignal(int)        # 👈 ДОБАВИТЬ
    llm_status = pyqtSignal(str)          # 👈 ДОБАВИТЬ
    llm_response = pyqtSignal(object)

    # Сигналы для монтажа
    montage_progress = pyqtSignal(int)
    montage_status = pyqtSignal(str)
    montage_finished = pyqtSignal(object)  # путь к готовому видео
    montage_error = pyqtSignal(str)
    montage_log = pyqtSignal(str)

    # Общие
    video_added = pyqtSignal(str)  # путь к видео
    video_processed = pyqtSignal(str)  # путь к видео (готово)


signals = Signals()