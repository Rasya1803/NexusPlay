"""NexusPlay — PlayerBar widget.

Bar kontrol pemutar yang selalu ada di bagian bawah jendela.
Menampilkan:
- Info media yang sedang diputar (cover/thumbnail, judul, artis)
- Kontrol pemutaran (sebelumnya, play/pause, berikutnya)
- Slider pencari posisi (seek slider) + indikator waktu (0:00 / 3:45)
- Kontrol volume (slider + tombol mute)
- Tombol fullscreen

Komponen ini hanya berkomunikasi lewat sinyal dan memanggil metode Player,
tidak menyentuh backend mpv secara langsung (PRD 7.3).
"""

from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from nexusplay.core.player import Player
from nexusplay.core.queue import PlayQueue


def format_ms(ms: int) -> str:
    """Format milidetik ke mm:ss atau hh:mm:ss."""
    if ms < 0:
        ms = 0
    total_seconds = int(ms / 1000)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


class PlayerBar(QWidget):
    """Bar pemutar bawah yang modern."""

    # Sinyal keluar ke MainWindow
    fullscreen_requested = Signal()
    queue_toggle_requested = Signal()
    next_requested = Signal()
    prev_requested = Signal()

    def __init__(
        self,
        player: Player,
        queue: PlayQueue | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.player = player
        self.queue = queue
        self._seeking = False

        self.setFixedHeight(84)
        self.setObjectName("PlayerBar")
        self.setStyleSheet("""
            QWidget#PlayerBar {
                background-color: #151922;
                border-top: 1px solid #262C3B;
            }
        """)

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(16)

        # ── 1. Kiri: Info Track (Cover + Judul + Artis) ─────────
        self.info_widget = QWidget()
        info_layout = QHBoxLayout(self.info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(12)

        # Cover thumbnail (48x48)
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(52, 52)
        self.cover_label.setStyleSheet("""
            background-color: #1D2230;
            border-radius: 8px;
            border: 1px solid #262C3B;
        """)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._set_default_cover()

        # Teks Judul & Artis
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.title_label = QLabel("Belum ada media")
        self.title_label.setStyleSheet("color: #E8EAF0; font-size: 14px; font-weight: 600;")
        self.title_label.setMaximumWidth(260)

        self.artist_label = QLabel("Pilih lagu atau video untuk memutar")
        self.artist_label.setStyleSheet("color: #8B93A7; font-size: 12px;")
        self.artist_label.setMaximumWidth(260)

        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.artist_label)

        info_layout.addWidget(self.cover_label)
        info_layout.addLayout(text_layout)
        layout.addWidget(self.info_widget, 0)

        # ── 2. Tengah: Kontrol & Seek Bar ────────────────────────
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(4)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Baris tombol kontrol
        buttons_row = QHBoxLayout()
        buttons_row.setContentsMargins(0, 0, 0, 0)
        buttons_row.setSpacing(10)
        buttons_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.shuffle_button = QPushButton("🔀")
        self.shuffle_button.setFixedSize(32, 32)
        self.shuffle_button.setToolTip("Acak (S)")
        self.shuffle_button.setStyleSheet(self._button_style(round_shape=True))

        self.prev_button = QPushButton("⏮")
        self.prev_button.setFixedSize(36, 36)
        self.prev_button.setToolTip("Sebelumnya (P)")
        self.prev_button.setStyleSheet(self._button_style(round_shape=True))

        self.play_button = QPushButton("▶")
        self.play_button.setFixedSize(42, 42)
        self.play_button.setToolTip("Putar / Jeda (Spasi)")
        self.play_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #7C5CFF, stop:1 #22D3EE);
                color: #FFFFFF;
                border: none;
                border-radius: 21px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #9074FF, stop:1 #3EE0F8);
            }
            QPushButton:pressed {
                background: #6040E0;
            }
        """)

        self.next_button = QPushButton("⏭")
        self.next_button.setFixedSize(36, 36)
        self.next_button.setToolTip("Berikutnya (N)")
        self.next_button.setStyleSheet(self._button_style(round_shape=True))

        self.repeat_button = QPushButton("🔁")
        self.repeat_button.setFixedSize(32, 32)
        self.repeat_button.setToolTip("Ulang: Mati (R)")
        self.repeat_button.setStyleSheet(self._button_style(round_shape=True))

        buttons_row.addWidget(self.shuffle_button)
        buttons_row.addWidget(self.prev_button)
        buttons_row.addWidget(self.play_button)
        buttons_row.addWidget(self.next_button)
        buttons_row.addWidget(self.repeat_button)

        # Baris slider posisi + waktu
        seek_row = QHBoxLayout()
        seek_row.setContentsMargins(0, 0, 0, 0)
        seek_row.setSpacing(8)

        self.time_current = QLabel("0:00")
        self.time_current.setStyleSheet("color: #8B93A7; font-size: 11px; min-width: 36px;")
        self.time_current.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.setFixedHeight(18)
        self.seek_slider.setStyleSheet(self._slider_style("#7C5CFF"))

        self.time_total = QLabel("0:00")
        self.time_total.setStyleSheet("color: #8B93A7; font-size: 11px; min-width: 36px;")

        seek_row.addWidget(self.time_current)
        seek_row.addWidget(self.seek_slider, 1)
        seek_row.addWidget(self.time_total)

        center_layout.addLayout(buttons_row)
        center_layout.addLayout(seek_row)
        layout.addWidget(center_widget, 1)

        # ── 3. Kanan: Volume & Fullscreen ────────────────────────
        right_widget = QWidget()
        right_layout = QHBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.mute_button = QPushButton("🔊")
        self.mute_button.setFixedSize(34, 34)
        self.mute_button.setToolTip("Bisu (M)")
        self.mute_button.setStyleSheet(self._button_style(round_shape=True))

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(self.player.volume)
        self.volume_slider.setFixedWidth(90)
        self.volume_slider.setFixedHeight(18)
        self.volume_slider.setStyleSheet(self._slider_style("#22D3EE"))

        self.queue_button = QPushButton("☰")
        self.queue_button.setFixedSize(34, 34)
        self.queue_button.setToolTip("Antrean (Ctrl+Q)")
        self.queue_button.setStyleSheet(self._button_style(round_shape=True))

        self.fullscreen_button = QPushButton("⛶")
        self.fullscreen_button.setFixedSize(34, 34)
        self.fullscreen_button.setToolTip("Layar Penuh (F)")
        self.fullscreen_button.setStyleSheet(self._button_style(round_shape=True))

        right_layout.addWidget(self.mute_button)
        right_layout.addWidget(self.volume_slider)
        right_layout.addWidget(self.queue_button)
        right_layout.addWidget(self.fullscreen_button)
        layout.addWidget(right_widget, 0)

    def _button_style(self, round_shape: bool = False) -> str:
        radius = "17px" if round_shape else "8px"
        return f"""
            QPushButton {{
                background-color: #1D2230;
                color: #E8EAF0;
                border: 1px solid #262C3B;
                border-radius: {radius};
                font-size: 13px;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: #7C5CFF;
                border-color: #7C5CFF;
                color: #FFFFFF;
            }}
            QPushButton:pressed {{
                background-color: #151922;
            }}
        """

    def _slider_style(self, accent_color: str) -> str:
        return f"""
            QSlider::groove:horizontal {{
                height: 4px;
                background: #262C3B;
                border-radius: 2px;
            }}
            QSlider::sub-page:horizontal {{
                background: {accent_color};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: #FFFFFF;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {accent_color};
            }}
        """

    def _set_default_cover(self) -> None:
        self.cover_label.setText("🎵")
        self.cover_label.setStyleSheet("""
            background-color: #1D2230;
            border-radius: 8px;
            border: 1px solid #262C3B;
            font-size: 20px;
        """)

    def set_media_info(self, title: str, artist: str = "", cover_path: str | None = None) -> None:
        """Perbarui informasi track yang tampil di bar."""
        self.title_label.setText(title or "Tanpa Judul")
        self.artist_label.setText(artist or "Artis tidak diketahui")

        if cover_path and Path(cover_path).exists():
            pixmap = QPixmap(cover_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    52, 52,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.cover_label.setPixmap(scaled)
                return
        self._set_default_cover()

    # ── Koneksi Sinyal ─────────────────────────────────────────

    def _connect_signals(self) -> None:
        # Tombol
        self.play_button.clicked.connect(self.player.toggle_pause)
        self.mute_button.clicked.connect(self.player.toggle_mute)
        self.fullscreen_button.clicked.connect(self.fullscreen_requested)
        self.queue_button.clicked.connect(self.queue_toggle_requested)

        # Slider pengguna
        self.volume_slider.valueChanged.connect(self.player.set_volume)
        self.seek_slider.sliderPressed.connect(self._on_seek_pressed)
        self.seek_slider.sliderMoved.connect(self._on_seek_moved)
        self.seek_slider.sliderReleased.connect(self._on_seek_released)

        # Player -> Bar
        self.player.state_changed.connect(self._on_state_changed)
        self.player.position_changed.connect(self._on_position_changed)
        self.player.duration_changed.connect(self._on_duration_changed)
        self.player.volume_changed.connect(self._on_volume_changed)
        self.player.mute_changed.connect(self._on_mute_changed)
        self.player.media_loaded.connect(self._on_media_loaded)

        if self.queue:
            self.set_queue(self.queue)
        else:
            self.prev_button.clicked.connect(self.prev_requested)
            self.next_button.clicked.connect(self.next_requested)

    def set_queue(self, queue: PlayQueue) -> None:
        """Hubungkan PlayQueue ke tombol kontrol antrean, shuffle, dan repeat."""
        self.queue = queue
        self.prev_button.clicked.connect(self.queue.prev)
        self.next_button.clicked.connect(self.queue.next)
        self.shuffle_button.clicked.connect(self.queue.toggle_shuffle)
        self.repeat_button.clicked.connect(self.queue.cycle_repeat_mode)

        self.queue.shuffle_changed.connect(self._on_shuffle_changed)
        self.queue.repeat_changed.connect(self._on_repeat_changed)

        self._on_shuffle_changed(self.queue.shuffle)
        self._on_repeat_changed(self.queue.repeat_mode)

    # ── Handler Sinyal ─────────────────────────────────────────

    def _on_shuffle_changed(self, enabled: bool) -> None:
        if enabled:
            self.shuffle_button.setStyleSheet("""
                QPushButton {
                    background-color: #7C5CFF;
                    color: #FFFFFF;
                    border: 1px solid #7C5CFF;
                    border-radius: 16px;
                    font-size: 13px;
                }
            """)
            self.shuffle_button.setToolTip("Acak: Aktif (S)")
        else:
            self.shuffle_button.setStyleSheet(self._button_style(round_shape=True))
            self.shuffle_button.setToolTip("Acak: Mati (S)")

    def _on_repeat_changed(self, mode: str) -> None:
        if mode == "all":
            self.repeat_button.setText("🔁")
            self.repeat_button.setStyleSheet("""
                QPushButton {
                    background-color: #7C5CFF;
                    color: #FFFFFF;
                    border: 1px solid #7C5CFF;
                    border-radius: 16px;
                    font-size: 13px;
                }
            """)
            self.repeat_button.setToolTip("Ulang: Semua Lagu (R)")
        elif mode == "one":
            self.repeat_button.setText("🔂")
            self.repeat_button.setStyleSheet("""
                QPushButton {
                    background-color: #7C5CFF;
                    color: #FFFFFF;
                    border: 1px solid #7C5CFF;
                    border-radius: 16px;
                    font-size: 13px;
                }
            """)
            self.repeat_button.setToolTip("Ulang: Satu Lagu Ini (R)")
        else:
            self.repeat_button.setText("🔁")
            self.repeat_button.setStyleSheet(self._button_style(round_shape=True))
            self.repeat_button.setToolTip("Ulang: Mati (R)")

    def _on_state_changed(self, state: str) -> None:
        self.play_button.setText("⏸" if state == "playing" else "▶")

    def _on_media_loaded(self, path: str) -> None:
        if not self.title_label.text() or self.title_label.text() == "Belum ada media":
            self.title_label.setText(Path(path).name)

    def _on_duration_changed(self, duration_ms: int) -> None:
        self.seek_slider.setRange(0, duration_ms)
        self.time_total.setText(format_ms(duration_ms))

    def _on_position_changed(self, position_ms: int) -> None:
        if self._seeking:
            return
        self.seek_slider.setValue(position_ms)
        self.time_current.setText(format_ms(position_ms))

    def _on_seek_pressed(self) -> None:
        self._seeking = True

    def _on_seek_moved(self, value: int) -> None:
        self.time_current.setText(format_ms(value))

    def _on_seek_released(self) -> None:
        self.player.seek(self.seek_slider.value())
        self._seeking = False

    def _on_volume_changed(self, volume: int) -> None:
        self.volume_slider.blockSignals(True)
        self.volume_slider.setValue(volume)
        self.volume_slider.blockSignals(False)

    def _on_mute_changed(self, is_muted: bool) -> None:
        self.mute_button.setText("🔇" if is_muted else "🔊")
