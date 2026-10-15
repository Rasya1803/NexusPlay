"""NexusPlay — ArtistView.

Tampilan daftar artis di library.
Menampilkan nama artis, jumlah album, dan total lagu.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class ArtistView(QWidget):
    """View daftar artis."""

    artist_selected = Signal(int)  # emits artist_id

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._artists: list[dict] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(16)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self.title_label = QLabel("Artis")
        self.title_label.setStyleSheet("color: #E8EAF0; font-size: 24px; font-weight: bold;")
        self.subtitle_label = QLabel("0 artis")
        self.subtitle_label.setStyleSheet("color: #8B93A7; font-size: 13px;")
        title_col.addWidget(self.title_label)
        title_col.addWidget(self.subtitle_label)
        layout.addLayout(title_col)

        self.stack = QStackedWidget()

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Artis", "Jumlah Album", "Total Lagu"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 140)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 120)

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
        self.table.cellDoubleClicked.connect(self._on_row_double_clicked)
        self.stack.addWidget(self.table)

        empty = QWidget()
        el = QVBoxLayout(empty)
        el.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.setSpacing(8)
        lbl_icon = QLabel("👤")
        lbl_icon.setStyleSheet("font-size: 48px; background: transparent;")
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_text = QLabel("Belum ada artis")
        lbl_text.setStyleSheet("color: #8B93A7; font-size: 15px;")
        lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.addWidget(lbl_icon)
        el.addWidget(lbl_text)
        self.stack.addWidget(empty)

        layout.addWidget(self.stack, 1)

    def set_artists(self, artists: list[dict]) -> None:
        self._artists = artists
        count = len(artists)
        self.subtitle_label.setText(f"{count} artis")

        if count == 0:
            self.stack.setCurrentIndex(1)
            return

        self.stack.setCurrentIndex(0)
        self.table.setRowCount(count)

        for row, ar in enumerate(artists):
            name = ar.get("name") or "Artis tidak diketahui"
            albums = f"{ar.get('album_count', 0)} album"
            tracks = f"{ar.get('track_count', 0)} lagu"

            item_name = QTableWidgetItem(f"👤  {name}")
            item_albums = QTableWidgetItem(albums)
            item_albums.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_albums.setForeground(Qt.GlobalColor.darkGray)
            item_tracks = QTableWidgetItem(tracks)
            item_tracks.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_tracks.setForeground(Qt.GlobalColor.darkGray)

            self.table.setItem(row, 0, item_name)
            self.table.setItem(row, 1, item_albums)
            self.table.setItem(row, 2, item_tracks)
            self.table.setRowHeight(row, 40)

    def _on_row_double_clicked(self, row: int, _col: int) -> None:
        if 0 <= row < len(self._artists):
            artist_id = self._artists[row].get("id")
            if artist_id:
                self.artist_selected.emit(artist_id)
