"""NexusPlay — Jendela Mini-Player (FR-61).

Jendela kecil yang selalu berada di atas jendela lain (always-on-top)
dengan kontrol putar/jeda, sebelum/berikut, seek bar, info trek,
dan tombol untuk kembali ke jendela utama.
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
from nexusplay.ui.theme import COLORS, extract_accent_color
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

        self.setWindowTitle("NexusPlay — Mini Player")
        self.setFixedSize(380, 150)

        self._setup_ui()
        self._apply_styles(self._accent_color)
        self._connect_signals()

    def _setup_ui(self) -> None:
        c = COLORS
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(8)

        # ── Baris 1: Sampul + Judul/Artis + Tombol Kembali ─────
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self.cover_thumb = QLabel("🎵")
        self.cover_thumb.setFixedSize(44, 44)
        self.cover_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_thumb.setStyleSheet(f"""
            background-color: {c["surface-2"]};
            border: 1px solid {c["border"]};
            border-radius: 8px;
            font-size: 20px;
        """)
        top_row.addWidget(self.cover_thumb)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)

        self.title_label = QLabel("Tidak ada media")
        self.title_label.setStyleSheet(
            f"font-size: 13px; font-weight: 600; color: {c['text']};"
        )
        self.title_label.setMaximumWidth(235)
        info_col.addWidget(self.title_label)

        self.artist_label = QLabel("Pilih lagu atau video")
        self.artist_label.setStyleSheet(
            f"font-size: 11px; color: {c['text-muted']};"
        )
        self.artist_label.setMaximumWidth(235)
        info_col.addWidget(self.artist_label)

        top_row.addLayout(info_col, stretch=1)

        self.btn_restore = QPushButton("🗖")
        self.btn_restore.setFixedSize(32, 32)
        self.btn_restore.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_restore.setToolTip("Kembali ke Jendela Utama")
        top_row.addWidget(self.btn_restore)

        root.addLayout(top_row)

        # ── Baris 2: Waktu + Seek Slider ───────────────────────
        seek_row = QHBoxLayout()
        seek_row.setSpacing(8)

        self.time_current = QLabel("0:00")
        self.time_current.setStyleSheet(
            f"font-size: 11px; color: {c['text-muted']}; min-width: 32px;"
        )
        seek_row.addWidget(self.time_current)

        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.setValue(0)
        self.seek_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        seek_row.addWidget(self.seek_slider, stretch=1)

        self.time_total = QLabel("0:00")
        self.time_total.setStyleSheet(
            f"font-size: 11px; color: {c['text-muted']}; min-width: 32px;"
        )
        self.time_total.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        seek_row.addWidget(self.time_total)

        root.addLayout(seek_row)

        # ── Baris 3: Tombol Kontrol Putar ──────────────────────
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(12)
        ctrl_row.addStretch()

        self.btn_prev = QPushButton("⏮")
        self.btn_prev.setFixedSize(32, 32)
        self.btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev.setToolTip("Sebelumnya")
        ctrl_row.addWidget(self.btn_prev)

        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedSize(38, 38)
        self.btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_play.setToolTip("Putar / Jeda")
        ctrl_row.addWidget(self.btn_play)

        self.btn_next = QPushButton("⏭")
        self.btn_next.setFixedSize(32, 32)
        self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next.setToolTip("Berikutnya")
        ctrl_row.addWidget(self.btn_next)

        ctrl_row.addStretch()
        root.addLayout(ctrl_row)

    def _apply_styles(self, accent: str) -> None:
        self._accent_color = accent
        c = COLORS
        self.setStyleSheet(f"""
            MiniPlayer {{
                background-color: {c["surface"]};
            }}
        """)

        small_btn_qss = f"""
            QPushButton {{
                background-color: {c["surface-2"]};
                color: {c["text"]};
                border: 1px solid {c["border"]};
                border-radius: 16px;
                font-size: 13px;
                padding: 0;
            }}
            QPushButton:hover {{
                background-color: {accent};
                border-color: {accent};
            }}
        """
        self.btn_prev.setStyleSheet(small_btn_qss)
        self.btn_next.setStyleSheet(small_btn_qss)
        self.btn_restore.setStyleSheet(small_btn_qss)

        self.btn_play.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                color: {c["text"]};
                border: none;
                border-radius: 19px;
                font-size: 15px;
                padding: 0;
            }}
            QPushButton:hover {{
                background-color: {c["accent-2"]};
                color: {c["bg"]};
            }}
        """)

        self.seek_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {c["surface-2"]};
                height: 5px;
                border-radius: 2px;
            }}
            QSlider::sub-page:horizontal {{
                background: {accent};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {c["text"]};
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
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
        if state == "playing":
            self.btn_play.setText("⏸")
        else:
            self.btn_play.setText("▶")

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
            self.cover_thumb.setPixmap(QPixmap())
            self.cover_thumb.setText("🎬" if kind == "video" else "🎵")

    def closeEvent(self, event: QCloseEvent) -> None:
        """Saat jendela mini-player ditutup, kembalikan jendela utama."""
        self.restore_requested.emit()
        super().closeEvent(event)

