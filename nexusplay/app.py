"""NexusPlay — Inisialisasi aplikasi Qt.

Modul ini berisi fungsi `run()` yang:
1. Membuat QApplication.
2. Memasang stylesheet tema gelap dari `theme.py`.
3. Membuat dan menampilkan MainWindow.
4. Menjalankan event loop Qt.

Dipisahkan dari `main.py` supaya logika aplikasi ada di dalam
package `nexusplay/`, sedangkan `main.py` hanya titik masuk.
"""

import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from nexusplay.ui.theme import dark_stylesheet
from nexusplay.ui.main_window import MainWindow


def run() -> None:
    """Jalankan aplikasi NexusPlay."""

    # 1. Buat QApplication (wajib ada sebelum widget apa pun)
    app = QApplication(sys.argv)

    # Set font dasar aplikasi
    app.setFont(QFont("Segoe UI", 10))

    # 2. Terapkan tema gelap ke seluruh aplikasi
    app.setStyleSheet(dark_stylesheet())

    # 3. Buat dan tampilkan jendela utama
    window = MainWindow()
    window.show()

    # 4. Jalankan event loop — aplikasi berjalan di sini
    #    sampai jendela ditutup
    sys.exit(app.exec())
