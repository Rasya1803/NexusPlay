"""NexusPlay — QueuePanel widget.

Panel sisi kanan untuk menampilkan dan mengatur antrean pemutaran:
- Lagu yang sedang aktif ("Sedang Diputar")
- Daftar lagu berikutnya dalam antrean ("Berikutnya")
- Tombol bersihkan antrean (Clear)
- Hapus lagu dari antrean
- Klik dua kali lagu di antrean untuk langsung memutarnya
- Tombol tutup panel (✕)
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
from nexusplay.ui.widgets.player_bar import format_ms


class QueuePanel(QWidget):
    """Panel antrean yang dapat disembunyikan/ditampilkan."""

    close_requested = Signal()

    def __init__(self, queue: PlayQueue, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.queue = queue

        self.setFixedWidth(280)
        self.setObjectName("QueuePanel")
        self.setStyleSheet("""
            QWidget#QueuePanel {
                background-color: #151922;
                border-left: 1px solid #262C3B;
            }
        """)

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
        title_label.setStyleSheet("color: #E8EAF0; font-size: 16px; font-weight: bold;")

        self.clear_btn = QPushButton("Bersihkan")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8B93A7;
                border: none;
                font-size: 12px;
                padding: 4px 6px;
            }
            QPushButton:hover {
                color: #FF5C7A;
            }
        """)
        self.clear_btn.clicked.connect(self.queue.clear)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8B93A7;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                color: #FFFFFF;
            }
        """)
        self.close_btn.clicked.connect(self.close_requested)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.clear_btn)
        header_layout.addWidget(self.close_btn)
        layout.addLayout(header_layout)

        # ── Bagian: Sedang Diputar ─────────────────────────────
        now_section_lbl = QLabel("SEDANG DIPUTAR")
        now_section_lbl.setStyleSheet("color: #555E70; font-size: 11px; font-weight: 700; padding-top: 4px;")
        layout.addWidget(now_section_lbl)

        self.now_playing_card = QWidget()
        self.now_playing_card.setStyleSheet("""
            background-color: #1D2230;
            border-radius: 8px;
            border: 1px solid #262C3B;
        """)
        now_card_layout = QHBoxLayout(self.now_playing_card)
        now_card_layout.setContentsMargins(10, 8, 10, 8)
        now_card_layout.setSpacing(10)

        self.now_icon = QLabel("🎵")
        self.now_icon.setStyleSheet("font-size: 18px; background: transparent;")

        now_info = QVBoxLayout()
        now_info.setSpacing(2)
        self.now_title = QLabel("Tidak ada yang diputar")
        self.now_title.setStyleSheet("color: #E8EAF0; font-size: 13px; font-weight: 600; background: transparent;")
        self.now_artist = QLabel("—")
        self.now_artist.setStyleSheet("color: #8B93A7; font-size: 11px; background: transparent;")
        now_info.addWidget(self.now_title)
        now_info.addWidget(self.now_artist)

        now_card_layout.addWidget(self.now_icon)
        now_card_layout.addLayout(now_info, 1)
        layout.addWidget(self.now_playing_card)

        # Garis pemisah
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #262C3B; max-height: 1px;")
        layout.addWidget(line)

        # ── Bagian: Berikutnya ─────────────────────────────────
        next_section_layout = QHBoxLayout()
        next_section_lbl = QLabel("BERIKUTNYA")
        next_section_lbl.setStyleSheet("color: #555E70; font-size: 11px; font-weight: 700;")
        self.queue_count_lbl = QLabel("0 lagu")
        self.queue_count_lbl.setStyleSheet("color: #555E70; font-size: 11px;")

        next_section_layout.addWidget(next_section_lbl)
        next_section_layout.addStretch()
        next_section_layout.addWidget(self.queue_count_lbl)
        layout.addLayout(next_section_layout)

        # Daftar antrean berikutnya
        self.queue_list = QListWidget()
        self.queue_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.queue_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                color: #E8EAF0;
            }
            QListWidget::item {
                background-color: transparent;
                border-radius: 6px;
                padding: 6px 8px;
                margin-bottom: 2px;
            }
            QListWidget::item:hover {
                background-color: #1D2230;
            }
            QListWidget::item:selected {
                background-color: #262C3B;
                color: #FFFFFF;
                border-left: 2px solid #7C5CFF;
            }
        """)
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
            # Simpan indeks riil di play order: curr_idx + 1 + offset
            real_index = curr_idx + 1 + offset
            item.setData(Qt.ItemDataRole.UserRole, real_index)
            self.queue_list.addItem(item)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        real_index = item.data(Qt.ItemDataRole.UserRole)
        if real_index is not None:
            self.queue.jump_to(real_index)
