import os
import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from config import Config

if __name__ == "__main__":

    if getattr(sys, 'frozen', False):
        # Для Hydra
        os.environ['HYDRA_MAIN_MODULE'] = 'gigaam'
        # Добавляем путь к папке GigaAM
        sys.path.insert(0, os.path.join(sys._MEIPASS, 'GigaAM'))

    Config.init_dirs()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())