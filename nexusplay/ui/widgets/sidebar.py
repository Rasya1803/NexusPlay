"""NexusPlay — Sidebar widget (Minimal Dark).

Panel navigasi utama di sisi kiri jendela menggunakan ikon SVG Lucide
dan indikator garis aksen 2 px di kiri tanpa gradien dekoratif.
"""

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from nexusplay.ui.theme import COLORS, icon, make_font


class NavButton(QPushButton):
    """Tombol item navigasi sidebar dengan ikon SVG Lucide."""

    def __init__(
        self,
        icon_name: str,
        text: str,
        page_id: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(f"  {text}", parent)
        self.icon_name = icon_name
        self.page_id = page_id
        self.setObjectName("NavButton")
        self.setCheckable(True)
        self.setFixedHeight(36)
        self.setIconSize(QSize(18, 18))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_icon(False)
        self.toggled.connect(self._update_icon)

    def _update_icon(self, checked: bool) -> None:
        color = COLORS["text"] if checked else COLORS["text-muted"]
        self.setIcon(icon(self.icon_name, color=color, size=18))


class Sidebar(QWidget):
    """Sidebar navigasi kiri NexusPlay."""

    page_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(220)
        self.setObjectName("Sidebar")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(4)

        # ── Wordmark Aplikasi (Minimal Swiss — Tanpa Badge Gradien) ──
        logo_layout = QHBoxLayout()
        logo_layout.setContentsMargins(8, 0, 8, 16)
        logo_layout.setSpacing(8)

        title_label = QLabel("NexusPlay")
        title_label.setFont(make_font(15, title_label.font().Weight.DemiBold, -0.3))
        logo_layout.addWidget(title_label)
        logo_layout.addStretch()
        layout.addLayout(logo_layout)

        # ── Label Seksi ────────────────────────────────────────
        section_label = QLabel("LIBRARY")
        section_label.setProperty("role", "caption")
        section_label.setContentsMargins(8, 4, 8, 4)
        layout.addWidget(section_label)

        # ── Grup Tombol Navigasi ───────────────────────────────
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        self.nav_music = NavButton("music", "Musik", "music")
        self.nav_albums = NavButton("disc-3", "Album", "albums")
        self.nav_artists = NavButton("user-round", "Artis", "artists")
        self.nav_videos = NavButton("film", "Video", "videos")
        self.nav_favorites = NavButton("heart", "Favorit", "favorites")
        self.nav_playlists = NavButton("list-music", "Playlist", "playlists")
        self.nav_stats = NavButton("chart-column", "Statistik", "stats")
        self.nav_folders = NavButton("folder", "Folder Library", "folders")

        nav_buttons = [
            self.nav_music,
            self.nav_albums,
            self.nav_artists,
            self.nav_videos,
            self.nav_favorites,
            self.nav_playlists,
            self.nav_stats,
            self.nav_folders,
        ]

        for btn in nav_buttons:
            self.button_group.addButton(btn)
            layout.addWidget(btn)
            btn.clicked.connect(lambda _checked, b=btn: self._on_btn_clicked(b))

        self.nav_music.setChecked(True)
        layout.addStretch()

        # Garis pemisah tipis
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFixedHeight(1)
        line.setStyleSheet(f"background-color: {COLORS['border']}; border: none;")
        layout.addWidget(line)

        footer_label = QLabel("v1.0 · Offline")
        footer_label.setProperty("role", "caption")
        footer_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        footer_label.setContentsMargins(8, 8, 8, 0)
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
