"""NexusPlay — Inisialisasi aplikasi Qt.

Modul ini berisi fungsi `run()` yang:
1. Membuat QApplication.
2. Memuat font Inter dari `nexusplay/resources/fonts/`.
3. Memasang stylesheet global Minimal Dark dari `theme.py`.
4. Membuat dan menampilkan MainWindow.
5. Menjalankan event loop Qt.
"""

import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from nexusplay.ui.main_window import MainWindow
from nexusplay.ui.theme import dark_stylesheet, load_app_fonts


def run() -> None:
    """Jalankan aplikasi NexusPlay."""
    app = QApplication(sys.argv)

    family = load_app_fonts()
    base_font = QFont(family, 10)
    app.setFont(base_font)

    app.setStyleSheet(dark_stylesheet())

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
