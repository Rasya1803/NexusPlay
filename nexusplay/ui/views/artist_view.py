"""NexusPlay — ArtistView (Minimal Dark).

Tampilan daftar artis di library dengan ikon SVG Lucide dan tabel minimalis.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from nexusplay.ui.theme import COLORS, icon, icon_pixmap


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
        self.title_label.setProperty("role", "title")
        self.subtitle_label = QLabel("0 artis")
        self.subtitle_label.setProperty("role", "muted")
        title_col.addWidget(self.title_label)
        title_col.addWidget(self.subtitle_label)
        layout.addLayout(title_col)

        self.stack = QStackedWidget()

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ARTIS", "JUMLAH ALBUM", "TOTAL LAGU"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(False)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 140)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 120)

        self.table.cellDoubleClicked.connect(self._on_row_double_clicked)
        self.stack.addWidget(self.table)

        empty = QWidget()
        el = QVBoxLayout(empty)
        el.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.setSpacing(10)
        lbl_icon = QLabel()
        lbl_icon.setPixmap(icon_pixmap("user-round", COLORS["text-muted"], 40))
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_text = QLabel("Belum ada artis")
        lbl_text.setProperty("role", "muted")
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

        artist_icon = icon("user-round", COLORS["text-muted"], 16)
        muted_color = QColor(COLORS["text-muted"])
        text_color = QColor(COLORS["text"])

        for row, ar in enumerate(artists):
            name = ar.get("name") or "Artis tidak diketahui"
            albums = f"{ar.get('album_count', 0)} album"
            tracks = f"{ar.get('track_count', 0)} lagu"

            item_name = QTableWidgetItem(name)
            item_name.setIcon(artist_icon)
            item_name.setForeground(text_color)

            item_albums = QTableWidgetItem(albums)
            item_albums.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_albums.setForeground(muted_color)

            item_tracks = QTableWidgetItem(tracks)
            item_tracks.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_tracks.setForeground(muted_color)

            self.table.setItem(row, 0, item_name)
            self.table.setItem(row, 1, item_albums)
            self.table.setItem(row, 2, item_tracks)
            self.table.setRowHeight(row, 40)

    def _on_row_double_clicked(self, row: int, _col: int) -> None:
        if 0 <= row < len(self._artists):
            artist_id = self._artists[row].get("id")
            if artist_id:
                self.artist_selected.emit(artist_id)
