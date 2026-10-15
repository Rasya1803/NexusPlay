"""NexusPlay — Sidebar widget.

Panel navigasi utama di sisi kiri jendela.
Menyediakan tombol navigasi untuk:
- ♪ Musik (semua lagu)
- 💿 Album
- 👤 Artis
- 🎬 Video
- 📁 Kelola Folder

Memancarkan sinyal `page_changed(page_id: str)` saat item diklik.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class NavButton(QPushButton):
    """Tombol item navigasi sidebar dengan status aktif/terpilih."""

    def __init__(self, icon_str: str, text: str, page_id: str, parent: QWidget | None = None) -> None:
        super().__init__(f"  {icon_str}   {text}", parent)
        self.page_id = page_id
        self.setCheckable(True)
        self.setFixedHeight(42)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #8B93A7;
                border: none;
                border-radius: 8px;
                text-align: left;
                padding-left: 14px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #1D2230;
                color: #E8EAF0;
            }
            QPushButton:checked {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(124, 92, 255, 0.25), stop:1 transparent);
                color: #FFFFFF;
                font-weight: 600;
                border-left: 3px solid #7C5CFF;
            }
        """)


class Sidebar(QWidget):
    """Sidebar navigasi kiri NexusPlay."""

    page_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(210)
        self.setObjectName("Sidebar")
        self.setStyleSheet("""
            QWidget#Sidebar {
                background-color: #151922;
                border-right: 1px solid #262C3B;
            }
        """)

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 20, 14, 16)
        layout.setSpacing(6)

        # ── Logo & Nama Aplikasi ───────────────────────────────
        logo_layout = QHBoxLayout()
        logo_layout.setContentsMargins(6, 0, 0, 16)
        logo_layout.setSpacing(8)

        logo_badge = QLabel("▶")
        logo_badge.setFixedSize(28, 28)
        logo_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_badge.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #7C5CFF, stop:1 #22D3EE);
            color: #FFFFFF;
            border-radius: 6px;
            font-size: 13px;
            font-weight: bold;
        """)

        title_label = QLabel("NexusPlay")
        title_label.setStyleSheet("color: #FFFFFF; font-size: 17px; font-weight: bold; letter-spacing: 0.5px;")

        logo_layout.addWidget(logo_badge)
        logo_layout.addWidget(title_label)
        logo_layout.addStretch()
        layout.addLayout(logo_layout)

        # ── Label Grup Navigasi ────────────────────────────────
        section_label = QLabel("LIBRARY")
        section_label.setStyleSheet("color: #555E70; font-size: 11px; font-weight: 700; padding: 4px 8px;")
        layout.addWidget(section_label)

        # ── Grup Tombol Navigasi ───────────────────────────────
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        self.nav_music = NavButton("♪", "Musik", "music")
        self.nav_albums = NavButton("💿", "Album", "albums")
        self.nav_artists = NavButton("👤", "Artis", "artists")
        self.nav_videos = NavButton("🎬", "Video", "videos")
        self.nav_folders = NavButton("📁", "Folder Library", "folders")

        nav_buttons = [
            self.nav_music,
            self.nav_albums,
            self.nav_artists,
            self.nav_videos,
            self.nav_folders,
        ]

        for btn in nav_buttons:
            self.button_group.addButton(btn)
            layout.addWidget(btn)
            btn.clicked.connect(lambda checked, b=btn: self._on_btn_clicked(b))

        # Default pilihan aktif: Musik
        self.nav_music.setChecked(True)

        layout.addStretch()

        # Garis pemisah bawah
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #262C3B; max-height: 1px;")
        layout.addWidget(line)

        # Info kecil versi/offline di bawah
        footer_label = QLabel("v0.1 · Offline")
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_label.setStyleSheet("color: #555E70; font-size: 11px; padding-top: 8px;")
        layout.addWidget(footer_label)

    def _on_btn_clicked(self, btn: NavButton) -> None:
        self.page_changed.emit(btn.page_id)

    def select_page(self, page_id: str) -> None:
        """Pilih tombol tertentu secara programatik."""
        for btn in self.button_group.buttons():
            if isinstance(btn, NavButton) and btn.page_id == page_id:
                btn.setChecked(True)
                self.page_changed.emit(page_id)
                break
