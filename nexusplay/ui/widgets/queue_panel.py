"""NexusPlay — QueuePanel widget (Minimal Dark).

Panel sisi kanan untuk menampilkan dan mengatur antrean pemutaran
menggunakan token warna netral dan ikon SVG Lucide.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from nexusplay.core.queue import PlayQueue
from nexusplay.ui.theme import COLORS, icon_pixmap, set_button_icon
from nexusplay.ui.widgets.player_bar import format_ms


class QueuePanel(QWidget):
    """Panel antrean sisi kanan (320 px)."""

    close_requested = Signal()

    def __init__(self, queue: PlayQueue, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.queue = queue
        self.setFixedWidth(320)
        self.setObjectName("QueuePanel")

        self._build_ui()
        self._connect_signals()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ── Header Panel ───────────────────────────────────────
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("Antrean")
        title_label.setProperty("role", "heading")

        self.clear_btn = QPushButton("Bersihkan")
        self.clear_btn.setProperty("variant", "ghost")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.clicked.connect(self.queue.clear)

        self.close_btn = QPushButton()
        self.close_btn.setProperty("variant", "icon")
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        set_button_icon(self.close_btn, "x", COLORS["text-muted"], 16)
        self.close_btn.clicked.connect(self.close_requested)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.clear_btn)
        header_layout.addWidget(self.close_btn)
        layout.addLayout(header_layout)

        # ── Bagian: Sedang Diputar ─────────────────────────────
        now_section_lbl = QLabel("SEDANG DIPUTAR")
        now_section_lbl.setProperty("role", "caption")
        layout.addWidget(now_section_lbl)

        self.now_playing_card = QFrame()
        self.now_playing_card.setObjectName("NowPlayingQueueCard")
        now_card_layout = QHBoxLayout(self.now_playing_card)
        now_card_layout.setContentsMargins(12, 10, 12, 10)
        now_card_layout.setSpacing(10)

        self.now_icon = QLabel()
        self.now_icon.setFixedSize(20, 20)
        self.now_icon.setPixmap(icon_pixmap("audio-lines", COLORS["accent"], 18))

        now_info = QVBoxLayout()
        now_info.setSpacing(2)
        self.now_title = QLabel("Tidak ada yang diputar")
        self.now_title.setProperty("role", "body-strong")
        self.now_artist = QLabel("—")
        self.now_artist.setProperty("role", "muted")
        now_info.addWidget(self.now_title)
        now_info.addWidget(self.now_artist)

        now_card_layout.addWidget(self.now_icon)
        now_card_layout.addLayout(now_info, 1)
        layout.addWidget(self.now_playing_card)

        # Garis pemisah tipis
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFixedHeight(1)
        line.setStyleSheet(f"background-color: {COLORS['border']}; border: none;")
        layout.addWidget(line)

        # ── Bagian: Berikutnya ─────────────────────────────────
        next_section_layout = QHBoxLayout()
        next_section_lbl = QLabel("BERIKUTNYA")
        next_section_lbl.setProperty("role", "caption")
        self.queue_count_lbl = QLabel("0 lagu")
        self.queue_count_lbl.setProperty("role", "caption")

        next_section_layout.addWidget(next_section_lbl)
        next_section_layout.addStretch()
        next_section_layout.addWidget(self.queue_count_lbl)
        layout.addLayout(next_section_layout)

        self.queue_list = QListWidget()
        self.queue_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.queue_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.queue_list, 1)

    def _connect_signals(self) -> None:
        self.queue.queue_updated.connect(self.refresh)
        self.queue.track_changed.connect(self._on_track_changed)

    def _on_track_changed(self, track: dict) -> None:
        self.now_title.setText(track.get("title") or "Tanpa Judul")
        self.now_artist.setText(track.get("artist") or "Artis tidak diketahui")
        self.refresh()

    def refresh(self) -> None:
        """Perbarui daftar antrean dari data PlayQueue."""
        curr = self.queue.current_track
        if curr:
            self.now_title.setText(curr.get("title") or "Tanpa Judul")
            self.now_artist.setText(curr.get("artist") or "Artis tidak diketahui")
        else:
            self.now_title.setText("Tidak ada yang diputar")
            self.now_artist.setText("—")

        self.queue_list.clear()
        upcoming = self.queue.upcoming_tracks()
        self.queue_count_lbl.setText(f"{len(upcoming)} lagu")

        curr_idx = self.queue.current_index
        for offset, t in enumerate(upcoming):
            title = t.get("title") or "Tanpa Judul"
            artist = t.get("artist") or "Artis tidak diketahui"
            dur = format_ms(t.get("duration_ms") or 0)

            item = QListWidgetItem(f"{title}\n{artist} · {dur}")
            real_index = curr_idx + 1 + offset
            item.setData(Qt.ItemDataRole.UserRole, real_index)
            self.queue_list.addItem(item)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        real_index = item.data(Qt.ItemDataRole.UserRole)
        if real_index is not None:
            self.queue.jump_to(real_index)
