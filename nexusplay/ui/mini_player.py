"""NexusPlay — Jendela Mini-Player (FR-61, Minimal Dark).

Jendela ringkas yang selalu berada di atas jendela lain (always-on-top)
dengan kontrol putar/jeda, sebelum/berikut, seek bar, info trek,
dan tombol untuk kembali ke jendela utama menggunakan ikon SVG Lucide.
"""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from nexusplay.core.player import Player
from nexusplay.ui.theme import (
    COLORS,
    extract_accent_color,
    icon_pixmap,
    set_button_icon,
)
from nexusplay.ui.widgets.player_bar import format_ms


class MiniPlayer(QWidget):
    """Jendela mini-player selalu-di-atas (FR-61)."""

    prev_requested = Signal()
    next_requested = Signal()
    restore_requested = Signal()

    def __init__(self, player: Player, parent: QWidget | None = None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint,
        )
        self.player = player
        self._is_seeking = False
        self._accent_color = COLORS["accent"]

        self.setObjectName("MiniPlayerRoot")
        self.setWindowTitle("NexusPlay — Mini Player")
        self.setFixedSize(360, 144)

        self._setup_ui()
        self._apply_styles(self._accent_color)
        self._connect_signals()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(8)

        # ── Baris 1: Sampul + Judul/Artis + Tombol Kembali ─────
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self.cover_thumb = QLabel()
        self.cover_thumb.setObjectName("CoverThumb")
        self.cover_thumb.setFixedSize(44, 44)
        self.cover_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._set_default_thumb("audio")
        top_row.addWidget(self.cover_thumb)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)

        self.title_label = QLabel("Tidak ada media")
        self.title_label.setProperty("role", "body-strong")
        self.title_label.setMaximumWidth(220)
        info_col.addWidget(self.title_label)

        self.artist_label = QLabel("Pilih lagu atau video")
        self.artist_label.setProperty("role", "muted")
        self.artist_label.setMaximumWidth(220)
        info_col.addWidget(self.artist_label)

        top_row.addLayout(info_col, stretch=1)

        self.btn_restore = QPushButton()
        self.btn_restore.setProperty("variant", "icon")
        self.btn_restore.setFixedSize(30, 30)
        self.btn_restore.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_restore.setToolTip("Kembali ke Jendela Utama")
        set_button_icon(self.btn_restore, "maximize-2", COLORS["text-muted"], 16)
        top_row.addWidget(self.btn_restore)

        root.addLayout(top_row)

        # ── Baris 2: Waktu + Seek Slider ───────────────────────
        seek_row = QHBoxLayout()
        seek_row.setSpacing(8)

        self.time_current = QLabel("0:00")
        self.time_current.setProperty("role", "time")
        self.time_current.setMinimumWidth(34)
        seek_row.addWidget(self.time_current)

        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setObjectName("SeekSlider")
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.setValue(0)
        self.seek_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        seek_row.addWidget(self.seek_slider, stretch=1)

        self.time_total = QLabel("0:00")
        self.time_total.setProperty("role", "time")
        self.time_total.setMinimumWidth(34)
        self.time_total.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        seek_row.addWidget(self.time_total)

        root.addLayout(seek_row)

        # ── Baris 3: Tombol Kontrol Putar ──────────────────────
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(10)
        ctrl_row.addStretch()

        self.btn_prev = QPushButton()
        self.btn_prev.setProperty("variant", "icon")
        self.btn_prev.setFixedSize(32, 32)
        self.btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev.setToolTip("Sebelumnya")
        set_button_icon(self.btn_prev, "skip-back", COLORS["text-muted"], 16)
        ctrl_row.addWidget(self.btn_prev)

        self.btn_play = QPushButton()
        self.btn_play.setProperty("variant", "play")
        self.btn_play.setFixedSize(36, 36)
        self.btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_play.setToolTip("Putar / Jeda")
        set_button_icon(self.btn_play, "play", COLORS["on-accent"], 16, filled=True)
        ctrl_row.addWidget(self.btn_play)

        self.btn_next = QPushButton()
        self.btn_next.setProperty("variant", "icon")
        self.btn_next.setFixedSize(32, 32)
        self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next.setToolTip("Berikutnya")
        set_button_icon(self.btn_next, "skip-forward", COLORS["text-muted"], 16)
        ctrl_row.addWidget(self.btn_next)

        ctrl_row.addStretch()
        root.addLayout(ctrl_row)

    def _set_default_thumb(self, kind: str = "audio") -> None:
        icon_name = "film" if kind == "video" else "music"
        self.cover_thumb.setText("")
        self.cover_thumb.setPixmap(icon_pixmap(icon_name, COLORS["text-muted"], 18))

    def _apply_styles(self, accent: str) -> None:
        self._accent_color = accent or COLORS["accent"]
        self.btn_play.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._accent_color};
                border: none;
                border-radius: 18px;
                padding: 0;
            }}
            QPushButton:hover {{
                background-color: {COLORS["text"]};
            }}
        """)
        self.seek_slider.setStyleSheet(f"""
            QSlider::sub-page:horizontal {{
                background: {self._accent_color};
                border-radius: 2px;
            }}
        """)

    def _connect_signals(self) -> None:
        self.btn_play.clicked.connect(self.player.toggle_pause)
        self.btn_prev.clicked.connect(self.prev_requested.emit)
        self.btn_next.clicked.connect(self.next_requested.emit)
        self.btn_restore.clicked.connect(self.restore_requested.emit)

        self.seek_slider.sliderPressed.connect(self._on_seek_start)
        self.seek_slider.sliderReleased.connect(self._on_seek_end)

        self.player.position_changed.connect(self._on_position_changed)
        self.player.duration_changed.connect(self._on_duration_changed)
        self.player.state_changed.connect(self._on_state_changed)

    def _on_seek_start(self) -> None:
        self._is_seeking = True

    def _on_seek_end(self) -> None:
        self._is_seeking = False
        self.player.seek(self.seek_slider.value())

    def _on_position_changed(self, pos_ms: int) -> None:
        if not self._is_seeking:
            self.seek_slider.setValue(pos_ms)
        self.time_current.setText(format_ms(pos_ms))

    def _on_duration_changed(self, dur_ms: int) -> None:
        self.seek_slider.setRange(0, max(1, dur_ms))
        self.time_total.setText(format_ms(dur_ms))

    def _on_state_changed(self, state: str) -> None:
        icon_name = "pause" if state == "playing" else "play"
        set_button_icon(self.btn_play, icon_name, COLORS["on-accent"], 16, filled=True)

    # ── API Publik ─────────────────────────────────────────────

    def set_track_info(
        self,
        title: str,
        artist: str = "",
        kind: str = "audio",
        cover_path: str | None = None,
        accent_color: str | None = None,
    ) -> None:
        """Perbarui info trek dan warna aksen di mini-player."""
        self.title_label.setText(title or "Tidak ada media")
        self.artist_label.setText(artist or "Artis Tidak Diketahui")

        resolved_accent = accent_color or extract_accent_color(cover_path)
        self._apply_styles(resolved_accent)

        loaded = False
        if cover_path and Path(str(cover_path)).is_file():
            pix = QPixmap(str(cover_path))
            if not pix.isNull():
                scaled = pix.scaled(
                    44,
                    44,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.cover_thumb.setText("")
                self.cover_thumb.setPixmap(scaled)
                loaded = True

        if not loaded:
            self._set_default_thumb(kind)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Saat jendela mini-player ditutup, kembalikan jendela utama."""
        self.restore_requested.emit()
        super().closeEvent(event)
