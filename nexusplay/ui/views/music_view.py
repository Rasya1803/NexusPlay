"""NexusPlay — MusicView.

Tampilan daftar seluruh lagu di library dalam bentuk tabel modern.
Kolom:
1. # (Nomor trek)
2. Judul Lagu
3. Artis
4. Album
5. Durasi

Klik dua kali (double click) memancarkan sinyal `media_activated(media_dict)`
sehingga langsung diputar oleh pemutar.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from nexusplay.ui.widgets.player_bar import format_ms


class MusicView(QWidget):
    """View daftar lagu musik."""

    media_activated = Signal(dict)
    add_folder_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tracks: list[dict] = []

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(16)

        # ── Header View ────────────────────────────────────────
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self.title_label = QLabel("Musik")
        self.title_label.setStyleSheet("color: #E8EAF0; font-size: 24px; font-weight: bold;")
        self.subtitle_label = QLabel("0 lagu")
        self.subtitle_label.setStyleSheet("color: #8B93A7; font-size: 13px;")
        title_col.addWidget(self.title_label)
        title_col.addWidget(self.subtitle_label)

        header_layout.addLayout(title_col)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # ── Stack Konten (Tabel vs Empty State) ─────────────────
        self.stack = QStackedWidget()

        # 1. Halaman Tabel Lagu
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["#", "Judul", "Artis", "Album", "Durasi"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Kolom ukuran proporsional
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 48)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 76)

        # Style tabel modern
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #0B0D12;
                alternate-background-color: #11141B;
                color: #E8EAF0;
                border: none;
                outline: none;
            }
            QTableWidget::item {
                padding: 10px 8px;
                border-bottom: 1px solid #1A1F2C;
            }
            QTableWidget::item:selected {
                background-color: #1D2230;
                color: #FFFFFF;
                border-left: 2px solid #7C5CFF;
            }
            QHeaderView::section {
                background-color: #0B0D12;
                color: #8B93A7;
                font-size: 12px;
                font-weight: 600;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #262C3B;
            }
        """)

        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self.stack.addWidget(self.table)

        # 2. Halaman Empty State
        empty_widget = QWidget()
        empty_layout = QVBoxLayout(empty_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(12)

        icon_label = QLabel("🎵")
        icon_label.setStyleSheet("font-size: 48px; background: transparent;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_title = QLabel("Belum ada lagu di library")
        empty_title.setStyleSheet("color: #E8EAF0; font-size: 18px; font-weight: bold;")
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_desc = QLabel("Tambahkan folder musik Anda untuk memindai lagu secara otomatis.")
        empty_desc.setStyleSheet("color: #8B93A7; font-size: 13px; margin-bottom: 8px;")
        empty_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)

        add_btn = QPushButton("＋ Tambah Folder Musik")
        add_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #7C5CFF, stop:1 #22D3EE);
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #9074FF, stop:1 #3EE0F8);
            }
        """)
        add_btn.clicked.connect(self.add_folder_requested)

        empty_layout.addStretch()
        empty_layout.addWidget(icon_label)
        empty_layout.addWidget(empty_title)
        empty_layout.addWidget(empty_desc)
        empty_layout.addWidget(add_btn, 0, Qt.AlignmentFlag.AlignCenter)
        empty_layout.addStretch()

        self.stack.addWidget(empty_widget)
        layout.addWidget(self.stack, 1)

    def set_tracks(self, tracks: list[dict]) -> None:
        """Isi tabel dengan data track dari repository."""
        self._tracks = tracks
        count = len(tracks)
        self.subtitle_label.setText(f"{count} lagu")

        if count == 0:
            self.stack.setCurrentIndex(1)  # Empty state
            return

        self.stack.setCurrentIndex(0)      # Tabel
        self.table.setRowCount(count)

        for row, t in enumerate(tracks):
            track_num = str(t.get("track_no") or (row + 1))
            title = t.get("title") or "Tanpa Judul"
            artist = t.get("artist") or "Artis tidak diketahui"
            album = t.get("album") or "Album tidak diketahui"
            duration = format_ms(t.get("duration_ms") or 0)

            item_num = QTableWidgetItem(track_num)
            item_num.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_num.setForeground(Qt.GlobalColor.darkGray)

            item_title = QTableWidgetItem(title)
            item_title.setToolTip(t.get("path", ""))

            item_artist = QTableWidgetItem(artist)
            item_artist.setForeground(Qt.GlobalColor.lightGray)

            item_album = QTableWidgetItem(album)
            item_album.setForeground(Qt.GlobalColor.darkGray)

            item_dur = QTableWidgetItem(duration)
            item_dur.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_dur.setForeground(Qt.GlobalColor.darkGray)

            self.table.setItem(row, 0, item_num)
            self.table.setItem(row, 1, item_title)
            self.table.setItem(row, 2, item_artist)
            self.table.setItem(row, 3, item_album)
            self.table.setItem(row, 4, item_dur)
            self.table.setRowHeight(row, 38)

    def _on_cell_double_clicked(self, row: int, _col: int) -> None:
        if 0 <= row < len(self._tracks):
            self.media_activated.emit(self._tracks[row])
