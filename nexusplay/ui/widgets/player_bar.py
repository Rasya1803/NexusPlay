"""NexusPlay — PlayerBar widget (Minimal Dark).

Bar kontrol pemutar bawah dengan ikon SVG Lucide, satu aksen untuk tombol
Play dan progres seek, serta tanpa gradien dekoratif.
"""

from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QPixmap
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
from nexusplay.ui.theme import (
    COLORS,
    extract_accent_color,
    icon_pixmap,
    refresh_style,
    set_button_icon,
)


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
    """Bar pemutar bawah bergaya Minimal Dark."""

    fullscreen_requested = Signal()
    queue_toggle_requested = Signal()
    lyrics_toggle_requested = Signal()
    now_playing_requested = Signal()
    mini_player_requested = Signal()
    favorite_toggled = Signal()
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
        self._is_playing = False
        self._is_favorite = False
        self._accent_color = COLORS["accent"]

        self.setFixedHeight(80)
        self.setObjectName("PlayerBar")

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(16)

        # ── 1. Kiri: Info Track (Cover + Judul + Artis) + Hati ──
        self.info_widget = QWidget()
        self.info_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        self.info_widget.setToolTip("Klik untuk membuka layar Sedang Diputar")
        self.info_widget.installEventFilter(self)
        info_layout = QHBoxLayout(self.info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(12)

        self.cover_label = QLabel()
        self.cover_label.setObjectName("CoverThumb")
        self.cover_label.setFixedSize(48, 48)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._set_default_cover()

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.title_label = QLabel("Belum ada media")
        self.title_label.setProperty("role", "body-strong")
        self.title_label.setMaximumWidth(240)

        self.artist_label = QLabel("Pilih lagu atau video")
        self.artist_label.setProperty("role", "muted")
        self.artist_label.setMaximumWidth(240)

        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.artist_label)

        info_layout.addWidget(self.cover_label)
        info_layout.addLayout(text_layout)
        layout.addWidget(self.info_widget, 0)

        self.favorite_button = self._make_icon_btn("heart", "Tandai Favorit")
        self.set_favorite_state(False)
        layout.addWidget(self.favorite_button, 0)

        # ── 2. Tengah: Kontrol Transport & Seek Bar ─────────────
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(4)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        buttons_row = QHBoxLayout()
        buttons_row.setContentsMargins(0, 0, 0, 0)
        buttons_row.setSpacing(8)
        buttons_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.shuffle_button = self._make_icon_btn("shuffle", "Acak (S)")
        self.prev_button = self._make_icon_btn("skip-back", "Sebelumnya (P)")

        self.play_button = QPushButton()
        self.play_button.setProperty("variant", "play")
        self.play_button.setFixedSize(40, 40)
        self.play_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_button.setToolTip("Putar / Jeda (Spasi)")
        set_button_icon(self.play_button, "play", COLORS["on-accent"], 18, filled=True)

        self.next_button = self._make_icon_btn("skip-forward", "Berikutnya (N)")
        self.repeat_button = self._make_icon_btn("repeat", "Ulang: Mati (R)")

        buttons_row.addWidget(self.shuffle_button)
        buttons_row.addWidget(self.prev_button)
        buttons_row.addWidget(self.play_button)
        buttons_row.addWidget(self.next_button)
        buttons_row.addWidget(self.repeat_button)

        seek_row = QHBoxLayout()
        seek_row.setContentsMargins(0, 0, 0, 0)
        seek_row.setSpacing(10)

        self.time_current = QLabel("0:00")
        self.time_current.setProperty("role", "time")
        self.time_current.setMinimumWidth(38)
        self.time_current.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setObjectName("SeekSlider")
        self.seek_slider.setRange(0, 0)
        self.seek_slider.setFixedHeight(16)
        self.seek_slider.setCursor(Qt.CursorShape.PointingHandCursor)

        self.time_total = QLabel("0:00")
        self.time_total.setProperty("role", "time")
        self.time_total.setMinimumWidth(38)

        seek_row.addWidget(self.time_current)
        seek_row.addWidget(self.seek_slider, 1)
        seek_row.addWidget(self.time_total)

        center_layout.addLayout(buttons_row)
        center_layout.addLayout(seek_row)
        layout.addWidget(center_widget, 1)

        # ── 3. Kanan: Volume, Lirik, Antrean, Mini, Fullscreen ──
        right_widget = QWidget()
        right_layout = QHBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.mute_button = self._make_icon_btn("volume-2", "Bisu (M)")

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setObjectName("VolumeSlider")
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(self.player.volume)
        self.volume_slider.setFixedWidth(84)
        self.volume_slider.setFixedHeight(16)
        self.volume_slider.setCursor(Qt.CursorShape.PointingHandCursor)

        self.lyrics_button = self._make_icon_btn("mic-vocal", "Lirik Tersinkron (Ctrl+L)")
        self.queue_button = self._make_icon_btn("list-music", "Antrean (Ctrl+Q)")
        self.mini_player_button = self._make_icon_btn("picture-in-picture-2", "Mini-Player (FR-61)")
        self.fullscreen_button = self._make_icon_btn("maximize-2", "Layar Penuh (F)")

        right_layout.addWidget(self.mute_button)
        right_layout.addWidget(self.volume_slider)
        right_layout.addWidget(self.lyrics_button)
        right_layout.addWidget(self.queue_button)
        right_layout.addWidget(self.mini_player_button)
        right_layout.addWidget(self.fullscreen_button)
        layout.addWidget(right_widget, 0)

    def _make_icon_btn(self, icon_name: str, tooltip: str) -> QPushButton:
        btn = QPushButton()
        btn.setProperty("variant", "icon")
        btn.setFixedSize(32, 32)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip(tooltip)
        set_button_icon(btn, icon_name, COLORS["text-muted"], 17)
        return btn

    def _set_default_cover(self) -> None:
        self.cover_label.setText("")
        self.cover_label.setPixmap(icon_pixmap("music", COLORS["text-muted"], 20))

    def set_accent_color(self, accent_color: str) -> None:
        """Perbarui warna aksen tunggal pada tombol Play dan progres seek."""
        self._accent_color = accent_color or COLORS["accent"]
        self.play_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._accent_color};
                border: none;
                border-radius: 20px;
                padding: 0px;
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
            QSlider::handle:horizontal:hover {{
                background: {self._accent_color};
            }}
        """)
        if self.queue:
            self._on_shuffle_changed(self.queue.shuffle)
            self._on_repeat_changed(self.queue.repeat_mode)

    def set_media_info(
        self,
        title: str,
        artist: str = "",
        cover_path: str | None = None,
        accent_color: str | None = None,
    ) -> None:
        """Perbarui info lagu yang tampil di bar serta warna aksen sampul."""
        self.title_label.setText(title or "Tanpa Judul")
        self.artist_label.setText(artist or "Artis tidak diketahui")

        resolved_accent = accent_color or extract_accent_color(cover_path)
        self.set_accent_color(resolved_accent)

        if cover_path and Path(cover_path).exists():
            pixmap = QPixmap(cover_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    48, 48,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.cover_label.setPixmap(scaled)
                return
        self._set_default_cover()

    def set_favorite_state(self, is_favorite: bool) -> None:
        """Perbarui ikon hati favorit (kosong = text-muted, terisi = text)."""
        self._is_favorite = is_favorite
        if is_favorite:
            self.favorite_button.setToolTip("Hapus dari Favorit")
            set_button_icon(self.favorite_button, "heart", COLORS["text"], 17, filled=True)
        else:
            self.favorite_button.setToolTip("Tandai Favorit")
            set_button_icon(self.favorite_button, "heart", COLORS["text-muted"], 17, filled=False)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.info_widget and event.type() == QEvent.Type.MouseButtonRelease:
            self.now_playing_requested.emit()
            return True
        return super().eventFilter(watched, event)

    # ── Koneksi Sinyal ─────────────────────────────────────────

    def _connect_signals(self) -> None:
        self.play_button.clicked.connect(self.player.toggle_pause)
        self.mute_button.clicked.connect(self.player.toggle_mute)
        self.fullscreen_button.clicked.connect(self.fullscreen_requested)
        self.lyrics_button.clicked.connect(self.lyrics_toggle_requested)
        self.queue_button.clicked.connect(self.queue_toggle_requested)
        self.mini_player_button.clicked.connect(self.mini_player_requested)
        self.favorite_button.clicked.connect(self.favorite_toggled)

        self.volume_slider.valueChanged.connect(self.player.set_volume)
        self.seek_slider.sliderPressed.connect(self._on_seek_pressed)
        self.seek_slider.sliderMoved.connect(self._on_seek_moved)
        self.seek_slider.sliderReleased.connect(self._on_seek_released)

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
        self.shuffle_button.setProperty("active", "true" if enabled else "false")
        color = self._accent_color if enabled else COLORS["text-muted"]
        set_button_icon(self.shuffle_button, "shuffle", color, 17)
        self.shuffle_button.setToolTip("Acak: Aktif (S)" if enabled else "Acak: Mati (S)")
        refresh_style(self.shuffle_button)

    def _on_repeat_changed(self, mode: str) -> None:
        if mode == "all":
            self.repeat_button.setProperty("active", "true")
            set_button_icon(self.repeat_button, "repeat", self._accent_color, 17)
            self.repeat_button.setToolTip("Ulang: Semua Lagu (R)")
        elif mode == "one":
            self.repeat_button.setProperty("active", "true")
            set_button_icon(self.repeat_button, "repeat-1", self._accent_color, 17)
            self.repeat_button.setToolTip("Ulang: Satu Lagu Ini (R)")
        else:
            self.repeat_button.setProperty("active", "false")
            set_button_icon(self.repeat_button, "repeat", COLORS["text-muted"], 17)
            self.repeat_button.setToolTip("Ulang: Mati (R)")
        refresh_style(self.repeat_button)

    def _on_state_changed(self, state: str) -> None:
        self._is_playing = state == "playing"
        icon_name = "pause" if self._is_playing else "play"
        set_button_icon(self.play_button, icon_name, COLORS["on-accent"], 18, filled=True)

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
        icon_name = "volume-x" if is_muted else "volume-2"
        set_button_icon(self.mute_button, icon_name, COLORS["text-muted"], 17)
