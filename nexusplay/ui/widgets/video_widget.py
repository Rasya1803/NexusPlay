"""NexusPlay — Widget layar video.

`VideoWidget` hanyalah "kanvas" hitam. mpv menggambar video langsung
ke jendela native milik widget ini, lewat nomor jendela (`winId`).

Widget ini TIDAK memanggil mpv. Ia hanya:
- menyediakan nomor jendela untuk diberikan ke `Player`,
- memberi kabar lewat sinyal saat diklik ganda atau mouse bergerak.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QWidget


class VideoWidget(QWidget):
    """Area tempat mpv menggambar video."""

    double_clicked = Signal()   # untuk masuk/keluar fullscreen
    mouse_moved = Signal()      # untuk memunculkan kontrol saat fullscreen

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # WA_NativeWindow: minta Qt membuat jendela OS sungguhan untuk
        # widget ini. Tanpa ini, widget tidak punya winId sendiri dan
        # mpv tidak bisa menggambar di dalamnya.
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)

        # Qt tidak perlu menggambar latar; mpv yang menggambar.
        self.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors)

        # Latar hitam saat belum ada video
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#000000"))
        self.setPalette(palette)
        self.setAutoFillBackground(True)
        self.setStyleSheet("background-color: #000000;")

        # Supaya mouseMoveEvent terpanggil walau tombol mouse tidak ditekan
        self.setMouseTracking(True)
        self.setMinimumHeight(240)

    def window_id(self) -> int:
        """Nomor jendela native, untuk diberikan ke mpv sebagai `wid`."""
        return int(self.winId())

    # ── Event Qt ───────────────────────────────────────────────

    def mouseDoubleClickEvent(self, event) -> None:
        self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event) -> None:
        self.mouse_moved.emit()
        super().mouseMoveEvent(event)
