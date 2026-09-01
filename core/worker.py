# core/worker.py

from PyQt6.QtCore import QThread
from core.signals import signals


class WorkerThread(QThread):
    def __init__(self, task, *args, **kwargs):
        super().__init__()
        self.task = task
        self.args = args
        self.kwargs = kwargs
        # Определяем тип задачи по имени функции
        task_name = getattr(task, '__name__', '')
        self.is_llm_task = 'send_message' in task_name
        self.is_montage_task = 'cut_by_timelines' in task_name

    def run(self):
        try:
            result = self.task(*self.args, **self.kwargs)

            if self.is_llm_task:
                signals.llm_response.emit(result)
            elif self.is_montage_task:
                signals.montage_finished.emit(result)
            else:
                signals.transcription_finished.emit(result)

        except Exception as e:
            if self.is_llm_task:
                signals.llm_error.emit(str(e))
            elif self.is_montage_task:
                signals.montage_error.emit(str(e))
            else:
                signals.transcription_error.emit(str(e))