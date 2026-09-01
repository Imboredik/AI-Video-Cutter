# core/project_manager.py

import os
import json
from datetime import datetime
from config import Config


class ProjectManager:
    def __init__(self):
        self.projects = {}
        self.current_project = None
        self.load_all_projects()

    def _get_project_dir(self, video_path):
        """Возвращает папку для проекта."""
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        return os.path.join(Config.PROJECTS_DIR, video_name)

    def _get_history_path(self, video_path):
        """Возвращает путь к файлу истории."""
        return os.path.join(self._get_project_dir(video_path), "history.json")

    def _get_transcription_path(self, video_path):
        """Возвращает путь к файлу транскрипции."""
        return os.path.join(self._get_project_dir(video_path), "transcription.json")

    def add_project(self, video_path):
        """Добавляет новый проект."""
        project_dir = self._get_project_dir(video_path)
        os.makedirs(project_dir, exist_ok=True)

        project_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        project_data = {
            'id': project_id,
            'video_path': video_path,
            'video_name': os.path.basename(video_path),
            'transcription': None,
            'chat_history': [],
            'timelines': [],
            'status': 'processing',
            'created_at': datetime.now().isoformat()
        }

        self.projects[video_path] = project_data
        self.current_project = video_path

        # Сохраняем проект
        self._save_project(video_path)
        return project_data

    def _save_project(self, video_path):
        """Сохраняет проект в JSON."""
        if video_path not in self.projects:
            return

        project = self.projects[video_path]
        project_dir = self._get_project_dir(video_path)

        # Сохраняем транскрипцию отдельно
        if project.get('transcription'):
            trans_path = self._get_transcription_path(video_path)
            with open(trans_path, 'w', encoding='utf-8') as f:
                json.dump(project['transcription'], f, ensure_ascii=False, indent=2)

        # Сохраняем историю чата отдельно
        if project.get('chat_history'):
            history_path = self._get_history_path(video_path)
            with open(history_path, 'w', encoding='utf-8') as f:
                json.dump(project['chat_history'], f, ensure_ascii=False, indent=2)

        # Сохраняем весь проект
        project_file = os.path.join(project_dir, "project.json")
        project_copy = project.copy()
        # Убираем большие данные из основного файла
        project_copy.pop('transcription', None)
        project_copy.pop('chat_history', None)

        with open(project_file, 'w', encoding='utf-8') as f:
            json.dump(project_copy, f, ensure_ascii=False, indent=2)

    def load_all_projects(self):
        """Загружает все сохранённые проекты."""
        if not os.path.exists(Config.PROJECTS_DIR):
            os.makedirs(Config.PROJECTS_DIR, exist_ok=True)
            return

        for project_name in os.listdir(Config.PROJECTS_DIR):
            project_dir = os.path.join(Config.PROJECTS_DIR, project_name)
            if not os.path.isdir(project_dir):
                continue

            project_file = os.path.join(project_dir, "project.json")
            if not os.path.exists(project_file):
                continue

            try:
                with open(project_file, 'r', encoding='utf-8') as f:
                    project = json.load(f)

                video_path = project.get('video_path')
                if not video_path or not os.path.exists(video_path):
                    continue

                # Загружаем транскрипцию
                trans_path = self._get_transcription_path(video_path)
                if os.path.exists(trans_path):
                    with open(trans_path, 'r', encoding='utf-8') as f:
                        project['transcription'] = json.load(f)

                # Загружаем историю чата
                history_path = self._get_history_path(video_path)
                if os.path.exists(history_path):
                    with open(history_path, 'r', encoding='utf-8') as f:
                        project['chat_history'] = json.load(f)
                else:
                    project['chat_history'] = []

                project['status'] = 'done'
                self.projects[video_path] = project

            except Exception as e:
                print(f"Ошибка загрузки проекта {project_name}: {e}")

    def get_project(self, video_path):
        """Возвращает проект по пути к видео."""
        return self.projects.get(video_path)

    def get_current_project(self):
        """Возвращает текущий проект."""
        if self.current_project:
            return self.projects.get(self.current_project)
        return None

    def set_transcription(self, video_path, transcription_data):
        """Сохраняет транскрипцию для проекта."""
        if video_path in self.projects:
            self.projects[video_path]['transcription'] = transcription_data
            self.projects[video_path]['status'] = 'done'
            self._save_project(video_path)

    def add_chat_message(self, video_path, role, content):
        """Добавляет сообщение в историю чата проекта."""
        if video_path in self.projects:
            self.projects[video_path]['chat_history'].append({
                'role': role,
                'content': content,
                'timestamp': datetime.now().isoformat()
            })
            self._save_project(video_path)

    def add_timelines(self, video_path, timelines):
        """Добавляет таймкоды от LLM."""
        if video_path in self.projects:
            if 'timelines' not in self.projects[video_path]:
                self.projects[video_path]['timelines'] = []
            self.projects[video_path]['timelines'].extend(timelines)
            self._save_project(video_path)

    def get_all_projects(self):
        """Возвращает список всех проектов."""
        return list(self.projects.values())

    def get_all_video_paths(self):
        """Возвращает список путей ко всем видео."""
        return list(self.projects.keys())