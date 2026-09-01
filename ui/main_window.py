# ui/main_window.py

import os
import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QLineEdit,
    QListWidget, QListWidgetItem, QSplitter,
    QFrame, QProgressBar, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QPixmap, QDragEnterEvent, QDropEvent

from core.signals import signals
from core.worker import WorkerThread
from core.project_manager import ProjectManager
from core.video_processor import VideoProcessor
from core.transcriber import GigaAMTranscriber
from core.llm_client import LLMClient
from config import Config


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video AI Cutter")
        self.setGeometry(100, 100, 1400, 800)

        # Инициализация
        self.project_manager = ProjectManager()
        self.current_worker = None
        self.current_video_path = None
        self.llm_client = None
        self.current_transcription = None
        self.current_video_name = None
        self.llm_worker = None

        # Включаем Drag & Drop
        self.setAcceptDrops(True)

        self.setup_styles()
        self.create_menu()
        self.create_ui()
        self.connect_signals()

        # Загружаем сохранённые проекты
        self.load_saved_projects()

    def setup_styles(self):
        """Настройка стилей."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QSplitter::handle {
                background-color: #2d2d2d;
            }
            QListWidget {
                background-color: #2d2d2d;
                border: none;
                padding: 5px;
                color: #ffffff;
            }
            QListWidget::item {
                padding: 10px;
                border-radius: 8px;
            }
            QListWidget::item:selected {
                background-color: #3d3d3d;
            }
            QListWidget::item:hover {
                background-color: #353535;
            }
            QPushButton {
                background-color: #0078d7;
                color: #ffffff;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1088e7;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #999999;
            }
            QTextEdit {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                padding: 10px;
                color: #ffffff;
            }
            QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                padding: 8px 12px;
                color: #ffffff;
            }
            QLineEdit:focus {
                border: 1px solid #0078d7;
            }
            QProgressBar {
                border: none;
                background-color: #2d2d2d;
                border-radius: 4px;
                height: 9px;
            }
            QProgressBar::chunk {
                background-color: #0078d7;
                border-radius: 4px;
            }
            QFrame#dropArea {
                border: 2px dashed #3d3d3d;
                border-radius: 12px;
                background-color: #252525;
            }
            QFrame#dropArea:hover {
                border: 2px dashed #0078d7;
                background-color: #2a2a2a;
            }
            QListWidget#videoList {
                background-color: #252525;
                border: 1px solid #2d2d2d;
                border-radius: 8px;
            }
            QLabel#videoTitle {
                font-size: 18px;
                font-weight: bold;
                color: #ffffff;
                padding: 5px 0;
            }
            QLabel#chatTitle {
                font-size: 18px;
                font-weight: bold;
                color: #ffffff;
                padding: 5px 0;
            }
            QLabel#infoTitle {
                font-size: 18px;
                font-weight: bold;
                color: #ffffff;
                padding: 5px 0;
            }
        """)

    def create_menu(self):
        """Создаёт верхнее меню."""
        menubar = self.menuBar()

        # Файл
        file_menu = menubar.addMenu("Файл")
        open_action = QAction("Открыть видео", self)
        open_action.triggered.connect(self.open_video_dialog)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Настройки
        settings_menu = menubar.addMenu("Настройки")
        settings_action = QAction("Настройки", self)
        settings_action.triggered.connect(self.show_settings)
        settings_menu.addAction(settings_action)

        # Помощь
        help_menu = menubar.addMenu("Помощь")
        about_action = QAction("О программе", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_ui(self):
        """Создаёт основной интерфейс."""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.create_left_panel()
        self.create_center_panel()
        self.create_right_panel()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.left_panel)
        splitter.addWidget(self.center_panel)
        splitter.addWidget(self.right_panel)
        splitter.setSizes([280, 700, 300])
        self.main_layout.addWidget(splitter)

    def create_left_panel(self):
        """Левая панель: список видео."""
        self.left_panel = QWidget()
        self.left_panel.setFixedWidth(300)
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(10)

        title = QLabel("📹 Видео")
        title.setObjectName("videoTitle")
        left_layout.addWidget(title)

        self.video_list = QListWidget()
        self.video_list.setObjectName("videoList")
        self.video_list.setMinimumHeight(200)
        self.video_list.itemClicked.connect(self.on_video_selected)
        left_layout.addWidget(self.video_list)

        add_btn = QPushButton("➕ Добавить видео")
        add_btn.setFixedHeight(40)
        add_btn.clicked.connect(self.open_video_dialog)
        left_layout.addWidget(add_btn)

        hint = QLabel("Перетащите видео сюда или нажмите кнопку")
        hint.setStyleSheet("color: #888888; font-size: 11px;")
        hint.setWordWrap(True)
        left_layout.addWidget(hint)

        left_layout.addStretch()

    def create_center_panel(self):
        """Центральная панель: чат."""
        self.center_panel = QWidget()
        center_layout = QVBoxLayout(self.center_panel)
        center_layout.setContentsMargins(10, 10, 10, 10)
        center_layout.setSpacing(10)

        title = QLabel("💬 Чат с ИИ")
        title.setObjectName("chatTitle")
        center_layout.addWidget(title)

        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setPlaceholderText("Здесь будет история чата...")
        center_layout.addWidget(self.chat_history, 1)

        input_layout = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Напишите запрос...")
        self.chat_input.returnPressed.connect(self.send_message)
        self.chat_input.setEnabled(False)
        input_layout.addWidget(self.chat_input)

        self.send_btn = QPushButton("➤")
        self.send_btn.setFixedWidth(50)
        self.send_btn.setFixedHeight(40)
        self.send_btn.clicked.connect(self.send_message)
        self.send_btn.setEnabled(False)
        input_layout.addWidget(self.send_btn)
        center_layout.addLayout(input_layout)

        self.montage_btn = QPushButton("✂️ Смонтировать")
        self.montage_btn.setEnabled(False)
        self.montage_btn.setFixedHeight(50)
        self.montage_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                font-size: 16px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #34ce57;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #999999;
            }
        """)
        self.montage_btn.clicked.connect(self.open_montage_window)
        center_layout.addWidget(self.montage_btn)

    def create_right_panel(self):
        """Правая панель: информация."""
        self.right_panel = QWidget()
        self.right_panel.setFixedWidth(280)
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(10)

        title = QLabel("📊 Информация")
        title.setObjectName("infoTitle")
        right_layout.addWidget(title)

        info_frame = QFrame()
        info_frame.setObjectName("dropArea")
        info_layout = QVBoxLayout(info_frame)

        self.preview_label = QLabel("🎬 Превью")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("font-size: 14px; color: #888888; padding: 20px;")
        self.preview_label.setMinimumHeight(150)
        info_layout.addWidget(self.preview_label)

        self.video_info = QLabel("Нет загруженного видео")
        self.video_info.setWordWrap(True)
        self.video_info.setStyleSheet("font-size: 12px; color: #aaaaaa; padding: 5px;")
        info_layout.addWidget(self.video_info)

        right_layout.addWidget(info_frame)

        status_label = QLabel("📌 Статус")
        status_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px;")
        right_layout.addWidget(status_label)

        self.status_text = QLabel("Ожидание")
        self.status_text.setStyleSheet("color: #aaaaaa;")
        right_layout.addWidget(self.status_text)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(15)
        right_layout.addWidget(self.progress_bar)

        right_layout.addStretch()

    def connect_signals(self):
        """Подключает сигналы бекенда."""
        signals.transcription_progress.connect(self.update_progress)
        signals.transcription_status.connect(self.set_status)
        signals.transcription_log.connect(self.append_chat_log)
        signals.transcription_finished.connect(self.on_transcription_done)
        signals.transcription_error.connect(self.on_error)

        # Сигналы для LLM
        signals.llm_response.connect(self.on_llm_response)
        signals.llm_error.connect(self.on_llm_error)
        signals.llm_status.connect(self.set_status)
        signals.llm_progress.connect(self.update_progress)

        # Сигналы для монтажа
        signals.montage_progress.connect(self.update_progress)
        signals.montage_status.connect(self.set_status)

    # ---------- ЗАГРУЗКА СОХРАНЁННЫХ ПРОЕКТОВ ----------

    def load_saved_projects(self):
        """Загружает сохранённые проекты в список."""
        projects = self.project_manager.get_all_projects()

        for project in projects:
            video_path = project['video_path']
            if not os.path.exists(video_path):
                continue

            file_name = os.path.basename(video_path)
            item = QListWidgetItem(f"✅ {file_name}")
            item.setData(Qt.ItemDataRole.UserRole, video_path)
            self.video_list.addItem(item)

        if projects:
            # Выбираем первый проект
            first_item = self.video_list.item(0)
            if first_item:
                self.video_list.setCurrentItem(first_item)
                self.on_video_selected(first_item)

    # ---------- РАБОТА С ВИДЕО ----------

    def open_video_dialog(self):
        """Открывает диалог выбора видео."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите видео",
            "",
            "Видео файлы (*.mp4 *.avi *.mkv *.mov *.wmv);;Все файлы (*.*)"
        )
        if file_path:
            self.add_video(file_path)

    def add_video(self, file_path):
        """Добавляет видео в список и запускает транскрибацию."""
        file_name = os.path.basename(file_path)

        # Проверяем, не добавлено ли уже
        for i in range(self.video_list.count()):
            item = self.video_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == file_path:
                QMessageBox.information(self, "Информация", "Это видео уже добавлено")
                return

        # Добавляем в список
        item = QListWidgetItem(f"⏳ {file_name}")
        item.setData(Qt.ItemDataRole.UserRole, file_path)
        self.video_list.addItem(item)

        # Добавляем проект
        self.project_manager.add_project(file_path)

        # Обновляем информацию
        self.current_video_path = file_path
        self.video_info.setText(f"Файл: {file_name}\nСтатус: ⏳ Обработка...\nСлов: -")
        self.set_status("Транскрибация...")
        self.progress_bar.setValue(0)
        self.preview_label.setText("⏳ Обработка...")

        # Запускаем транскрибацию
        self.start_transcription(file_path)

    def start_transcription(self, video_path):
        """Запускает транскрибацию в фоновом потоке."""
        self.current_worker = WorkerThread(
            task=self._transcribe_video,
            video_path=video_path
        )
        self.current_worker.start()

    def _transcribe_video(self, video_path):
        """Фоновая задача: транскрибация."""
        signals.transcription_status.emit("Извлечение аудио...")
        signals.transcription_progress.emit(10)

        audio_path = VideoProcessor.extract_audio(video_path)

        signals.transcription_status.emit("Распознавание речи...")
        signals.transcription_progress.emit(30)

        transcriber = GigaAMTranscriber(model_name="v3_e2e_rnnt")
        words = transcriber.transcribe_segment(audio_path)

        signals.transcription_progress.emit(90)
        signals.transcription_status.emit("Форматирование...")

        if words:
            text = " ".join([w['word'] for w in words])
            signals.transcription_log.emit(f"✅ Распознано {len(words)} слов")
            return {
                'text': text,
                'words': words,
                'video_path': video_path,
                'audio_path': audio_path
            }
        else:
            raise Exception("Не удалось распознать текст в видео")

    def on_transcription_done(self, result):
        """Обработка завершения транскрибации."""
        video_path = result['video_path']
        file_name = os.path.basename(video_path)

        # Обновляем элемент в списке
        for i in range(self.video_list.count()):
            item = self.video_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == video_path:
                item.setText(f"✅ {file_name}")
                break

        # Сохраняем транскрипцию
        self.project_manager.set_transcription(video_path, result)

        # Сохраняем для LLM
        self.current_transcription = result['text']
        self.current_video_name = file_name
        self.current_video_path = video_path

        # Обновляем информацию
        self.video_info.setText(
            f"Файл: {file_name}\n"
            f"Статус: ✅ Готово\n"
            f"Слов: {len(result['words'])}"
        )
        self.set_status("Готово")
        self.progress_bar.setValue(100)

        # Превью
        try:
            thumb_path = VideoProcessor.extract_thumbnail(video_path)
            pixmap = QPixmap(thumb_path)
            if not pixmap.isNull():
                self.preview_label.setPixmap(pixmap.scaled(
                    200, 150, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
                self.preview_label.setText("")
        except Exception as e:
            self.preview_label.setText("🎬 Превью не доступно")

        # Создаём LLM клиент
        try:
            self.llm_client = LLMClient()
        except Exception as e:
            self.chat_history.append(f"❌ **Ошибка инициализации LLM:** {e}")
            self.chat_input.setEnabled(True)
            self.send_btn.setEnabled(True)
            return

        # Отправляем приветственное сообщение
        welcome_msg = self.llm_client.get_initial_message(
            self.current_transcription,
            self.current_video_name
        )
        self.chat_history.append(f"\n🤖 {welcome_msg['content']}")
        self.project_manager.add_chat_message(video_path, "🤖 ИИ", welcome_msg['content'])

        # Активируем чат и монтаж
        self.chat_input.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.montage_btn.setEnabled(True)

    def on_video_selected(self, item):
        """Обработка выбора видео из списка."""
        video_path = item.data(Qt.ItemDataRole.UserRole)
        if not video_path:
            return

        self.current_video_path = video_path

        # Создаём LLM клиент если ещё нет
        if not self.llm_client:
            try:
                self.llm_client = LLMClient()
            except Exception as e:
                self.chat_history.append(f"❌ **Ошибка LLM:** {e}")
                return

        # Загружаем историю чата
        self.load_chat_history(video_path)

        # Обновляем информацию
        project = self.project_manager.get_project(video_path)
        if project:
            status = project.get('status', 'unknown')
            transcription = project.get('transcription')
            if transcription:
                self.video_info.setText(
                    f"Файл: {os.path.basename(video_path)}\n"
                    f"Статус: ✅ Готово\n"
                    f"Слов: {len(transcription.get('words', []))}"
                )
                self.current_transcription = transcription['text']
                self.montage_btn.setEnabled(True)
                self.chat_input.setEnabled(True)
                self.send_btn.setEnabled(True)
            else:
                self.video_info.setText(f"Файл: {os.path.basename(video_path)}\nСтатус: ⏳ Обработка...")

    def load_chat_history(self, video_path):
        """Загружает историю чата для выбранного видео."""
        project = self.project_manager.get_project(video_path)
        if not project:
            return

        # Очищаем чат
        self.chat_history.clear()

        # Загружаем историю
        chat_history = project.get('chat_history', [])
        if chat_history:
            for msg in chat_history:
                role = msg['role']
                content = msg['content']
                self.chat_history.append(f"{role}: {content}")
        else:
            # Если истории нет, показываем приветствие
            if project.get('transcription'):
                try:
                    welcome_msg = self.llm_client.get_initial_message(
                        project['transcription']['text'],
                        project['video_name']
                    )
                    self.chat_history.append(f"🤖 {welcome_msg['content']}")
                except Exception as e:
                    self.chat_history.append(f"❌ **Ошибка загрузки приветствия:** {e}")

        # Восстанавливаем транскрипцию
        if project.get('transcription'):
            self.current_transcription = project['transcription']['text']
            self.montage_btn.setEnabled(True)

    def add_chat_message(self, role, content):
        """Добавляет сообщение в чат и сохраняет в проект."""
        self.chat_history.append(f"\n{role}: {content}")

        if self.current_video_path:
            self.project_manager.add_chat_message(
                self.current_video_path,
                role,
                content
            )

    # ---------- ЧАТ ----------

    def send_message(self):
        """Отправка сообщения в LLM."""
        text = self.chat_input.text().strip()
        if not text:
            return

        if not self.llm_client:
            self.chat_history.append("❌ **Ошибка:** LLM не инициализирован.")
            return

        if not self.current_transcription:
            self.chat_history.append("❌ **Ошибка:** Нет транскрипции для обработки запроса.")
            return

        # Получаем проект
        project = self.project_manager.get_project(self.current_video_path)

        # Получаем слова с таймкодами из транскрипции
        words = []
        if project and project.get('transcription'):
            words = project['transcription'].get('words', [])

        # Сохраняем сообщение пользователя
        self.add_chat_message("👤 Вы", text)
        self.chat_input.clear()
        self.chat_input.setEnabled(False)
        self.send_btn.setEnabled(False)

        # Запускаем LLM
        self.llm_worker = WorkerThread(
            task=self.llm_client.send_message,
            user_message=text,
            transcription_text=self.current_transcription,
            video_name=self.current_video_name or "видео",
            words=words
        )
        self.llm_worker.start()

    def on_llm_response(self, result):
        """Обработка ответа от LLM."""
        self.chat_input.setEnabled(True)
        self.send_btn.setEnabled(True)

        response_text = result['response']
        timelines = result['timelines']

        # Сохраняем ответ ИИ
        self.add_chat_message("🤖 ИИ", response_text)

        if timelines:
            # Сохраняем таймкоды в проект
            if self.current_video_path:
                self.project_manager.add_timelines(self.current_video_path, timelines)

            # Показываем таймкоды
            timeline_text = "\n📌 **Найденные фрагменты:**\n"
            for i, tl in enumerate(timelines, 1):
                start = self._format_time(tl['start'])
                end = self._format_time(tl['end'])
                desc = tl.get('description', 'Фрагмент')
                timeline_text += f"  {i}. [{start} - {end}] — {desc}\n"

            self.chat_history.append(timeline_text)

            self.montage_btn.setEnabled(True)
            self.montage_btn.setText(f"✂️ Смонтировать ({len(timelines)} фрагментов)")

    def on_llm_error(self, error_msg):
        """Обработка ошибки LLM."""
        self.chat_input.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.chat_history.append(f"❌ **Ошибка LLM:** {error_msg}")

    def append_chat_log(self, message):
        """Добавляет лог в чат."""
        self.chat_history.append(f"🔹 {message}")

    # ---------- УТИЛИТЫ ----------

    def set_status(self, text):
        """Устанавливает статус."""
        self.status_text.setText(text)

    def update_progress(self, value):
        """Обновляет прогресс-бар."""
        self.progress_bar.setValue(value)

    def on_error(self, error_msg):
        """Обработка ошибок."""
        self.set_status("❌ Ошибка")
        self.progress_bar.setValue(0)
        self.chat_history.append(f"❌ **Ошибка:** {error_msg}")
        QMessageBox.critical(self, "Ошибка", error_msg)

    def _format_time(self, seconds):
        """Форматирует секунды в ЧЧ:ММ:СС."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    # ---------- ДИАЛОГИ ----------

    def show_settings(self):
        QMessageBox.information(self, "Настройки", "Окно настроек в разработке.")

    def show_about(self):
        QMessageBox.about(
            self,
            "О программе",
            "Video AI Cutter\n\n"
            "Умное приложение для монтажа видео с помощью ИИ.\n"
            "Версия 0.1.0\n\n"
            "Разработано с использованием:\n"
            "• PyQt6\n"
            "• GigaAM (распознавание речи)\n"
            "• Qwen (AI ассистент)"
        )

    def open_montage_window(self):
        """Открывает окно монтажа."""
        if not self.current_video_path:
            QMessageBox.warning(self, "Предупреждение", "Сначала загрузите видео")
            return

        project = self.project_manager.get_project(self.current_video_path)
        if not project:
            QMessageBox.warning(self, "Предупреждение", "Проект не найден")
            return

        timelines = project.get('timelines', [])
        if not timelines:
            QMessageBox.warning(self, "Предупреждение", "Нет таймкодов для монтажа")
            return

        from ui.montage_window import MontageWindow
        self.montage_window = MontageWindow(
            self,
            self.current_video_path,
            timelines,
            project.get('transcription', {}).get('words', [])
        )
        self.montage_window.show()

    # ---------- DROP EVENT ----------

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.mp4', '.avi', '.mkv', '.mov', '.wmv')):
                self.add_video(file_path)