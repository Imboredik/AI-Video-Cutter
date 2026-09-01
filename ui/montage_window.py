# ui/montage_window.py

import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem,
    QCheckBox, QProgressBar, QFileDialog, QMessageBox,
    QGroupBox, QLineEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction

from core.video_cutter import VideoCutter
from core.signals import signals
from core.worker import WorkerThread


class MontageWindow(QMainWindow):
    """Окно для выбора фрагментов и монтажа."""

    def __init__(self, parent, video_path, timelines, transcription_words=None):
        super().__init__(parent)
        self.parent = parent
        self.video_path = video_path
        self.timelines = timelines
        self.transcription_words = transcription_words

        self.setWindowTitle("✂️ Монтаж видео")
        self.setGeometry(200, 200, 800, 600)
        self.setMinimumSize(700, 500)

        self.video_cutter = VideoCutter(use_gpu=True)
        self.current_worker = None
        self.montage_results = []

        self.setup_ui()
        self.populate_timelines()
        self.connect_signals()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(15)

        title = QLabel("📋 Выберите фрагменты для монтажа")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        info = QLabel(f"Видео: {os.path.basename(self.video_path)}")
        info.setStyleSheet("color: #aaaaaa;")
        layout.addWidget(info)

        self.list_label = QLabel("Фрагменты:")
        layout.addWidget(self.list_label)

        self.timeline_list = QListWidget()
        self.timeline_list.setMinimumHeight(200)
        layout.addWidget(self.timeline_list)

        btn_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("✅ Выбрать все")
        self.select_all_btn.clicked.connect(self.select_all)
        btn_layout.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton("❌ Снять все")
        self.deselect_all_btn.clicked.connect(self.deselect_all)
        btn_layout.addWidget(self.deselect_all_btn)

        btn_layout.addStretch()

        self.separate_check = QCheckBox("📁 Отдельные видео")
        self.separate_check.setToolTip("Создать отдельное видео для каждого фрагмента")
        btn_layout.addWidget(self.separate_check)

        layout.addLayout(btn_layout)

        save_group = QGroupBox("Сохранение")
        save_layout = QHBoxLayout(save_group)

        save_layout.addWidget(QLabel("Сохранить как:"))
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("Выберите место сохранения...")
        self.output_path.setReadOnly(True)
        save_layout.addWidget(self.output_path)

        self.browse_btn = QPushButton("📁 Обзор")
        self.browse_btn.clicked.connect(self.browse_output)
        save_layout.addWidget(self.browse_btn)

        layout.addWidget(save_group)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Готов к монтажу")
        self.status_label.setStyleSheet("color: #aaaaaa;")
        layout.addWidget(self.status_label)

        btn_layout2 = QHBoxLayout()
        self.montage_btn = QPushButton("✂️ Смонтировать")
        self.montage_btn.setMinimumHeight(50)
        self.montage_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #34ce57;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #999999;
            }
        """)
        self.montage_btn.clicked.connect(self.start_montage)
        btn_layout2.addWidget(self.montage_btn)

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.close)
        btn_layout2.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout2)

        self.update_montage_button_state()

    def populate_timelines(self):
        self.timeline_list.clear()

        if not self.timelines:
            self.timeline_list.addItem("Нет фрагментов для монтажа")
            return

        for i, tl in enumerate(self.timelines):
            start = self._format_time(tl['start'])
            end = self._format_time(tl['end'])
            desc = tl.get('description', f'Фрагмент {i+1}')
            duration = tl['end'] - tl['start']

            item = QListWidgetItem(f"[{start} - {end}]  {desc}  ({duration:.1f} сек)")
            item.setData(Qt.ItemDataRole.UserRole, i)
            item.setCheckState(Qt.CheckState.Checked)
            self.timeline_list.addItem(item)

    def _format_time(self, seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def select_all(self):
        for i in range(self.timeline_list.count()):
            self.timeline_list.item(i).setCheckState(Qt.CheckState.Checked)

    def deselect_all(self):
        for i in range(self.timeline_list.count()):
            self.timeline_list.item(i).setCheckState(Qt.CheckState.Unchecked)

    def browse_output(self):
        default_name = os.path.splitext(os.path.basename(self.video_path))[0]
        default_name += "_montage.mp4"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить видео как",
            default_name,
            "MP4 видео (*.mp4)"
        )
        if file_path:
            if not file_path.lower().endswith('.mp4'):
                file_path += '.mp4'
            self.output_path.setText(file_path)
            self.update_montage_button_state()

    def update_montage_button_state(self):
        has_selected = False
        for i in range(self.timeline_list.count()):
            item = self.timeline_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                has_selected = True
                break

        self.montage_btn.setEnabled(has_selected and bool(self.output_path.text()))

    def connect_signals(self):
        self.timeline_list.itemChanged.connect(self.update_montage_button_state)

        signals.montage_progress.connect(self.progress_bar.setValue)
        signals.montage_status.connect(self.status_label.setText)
        signals.montage_log.connect(self.log_message)
        signals.montage_finished.connect(self.on_montage_finished)
        signals.montage_error.connect(self.on_montage_error)

    def start_montage(self):
        selected = []
        for i in range(self.timeline_list.count()):
            item = self.timeline_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                idx = item.data(Qt.ItemDataRole.UserRole)
                selected.append(self.timelines[idx])

        if not selected:
            QMessageBox.warning(self, "Предупреждение", "Выберите хотя бы один фрагмент")
            return

        output_path = self.output_path.text()
        if not output_path:
            QMessageBox.warning(self, "Предупреждение", "Укажите место сохранения")
            return

        separate = self.separate_check.isChecked()

        self.set_controls_enabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Подготовка к монтажу...")

        self.current_worker = WorkerThread(
            task=self.video_cutter.cut_by_timelines,
            video_path=self.video_path,
            timelines=selected,
            output_path=output_path,
            separate=separate
        )
        self.current_worker.start()

    def set_controls_enabled(self, enabled):
        self.montage_btn.setEnabled(enabled)
        self.browse_btn.setEnabled(enabled)
        self.select_all_btn.setEnabled(enabled)
        self.deselect_all_btn.setEnabled(enabled)
        self.separate_check.setEnabled(enabled)
        self.timeline_list.setEnabled(enabled)

    def log_message(self, message):
        print(f"[МОНТАЖ] {message}")

    def on_montage_finished(self, results):
        self.set_controls_enabled(True)
        self.montage_results = results

        msg = f"✅ Готово! Создано {len(results)} видео."
        self.status_label.setText(msg)
        QMessageBox.information(self, "Готово", msg)

        self.montage_btn.setEnabled(False)
        self.montage_btn.setText("✅ Готово")

    def on_montage_error(self, error_msg):
        self.set_controls_enabled(True)
        self.status_label.setText(f"❌ Ошибка: {error_msg}")
        QMessageBox.critical(self, "Ошибка", error_msg)

    def closeEvent(self, event):
        if self.current_worker and self.current_worker.isRunning():
            self.video_cutter.stop()
            self.current_worker.wait()
        event.accept()