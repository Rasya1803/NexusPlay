"""NexusPlay — AlbumView (Minimal Dark).

Tampilan daftar album di library dengan ikon SVG Lucide dan tabel minimalis.
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


class AlbumView(QWidget):
    """View daftar album."""

    album_selected = Signal(int)  # emits album_id

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._albums: list[dict] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(16)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self.title_label = QLabel("Album")
        self.title_label.setProperty("role", "title")
        self.subtitle_label = QLabel("0 album")
        self.subtitle_label.setProperty("role", "muted")
        title_col.addWidget(self.title_label)
        title_col.addWidget(self.subtitle_label)
        layout.addLayout(title_col)

        self.stack = QStackedWidget()

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ALBUM", "ARTIS", "TAHUN", "JUMLAH LAGU"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(False)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 80)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 110)

        self.table.cellDoubleClicked.connect(self._on_row_double_clicked)
        self.stack.addWidget(self.table)

        empty = QWidget()
        el = QVBoxLayout(empty)
        el.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.setSpacing(10)
        lbl_icon = QLabel()
        lbl_icon.setPixmap(icon_pixmap("disc-3", COLORS["text-muted"], 40))
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_text = QLabel("Belum ada album")
        lbl_text.setProperty("role", "muted")
        lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.addWidget(lbl_icon)
        el.addWidget(lbl_text)
        self.stack.addWidget(empty)

        layout.addWidget(self.stack, 1)

    def set_albums(self, albums: list[dict]) -> None:
        self._albums = albums
        count = len(albums)
        self.subtitle_label.setText(f"{count} album")

        if count == 0:
            self.stack.setCurrentIndex(1)
            return

        self.stack.setCurrentIndex(0)
        self.table.setRowCount(count)

        disc_icon = icon("disc-3", COLORS["text-muted"], 16)
        muted_color = QColor(COLORS["text-muted"])
        text_color = QColor(COLORS["text"])

        for row, al in enumerate(albums):
            title = al.get("title") or "Tanpa Judul"
            artist = al.get("artist") or "Artis tidak diketahui"
            year = str(al.get("year")) if al.get("year") else "—"
            tracks = f"{al.get('track_count', 0)} lagu"

            item_title = QTableWidgetItem(title)
            item_title.setIcon(disc_icon)
            item_title.setForeground(text_color)

            item_artist = QTableWidgetItem(artist)
            item_artist.setForeground(muted_color)

            item_year = QTableWidgetItem(year)
            item_year.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_year.setForeground(muted_color)

            item_tracks = QTableWidgetItem(tracks)
            item_tracks.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_tracks.setForeground(muted_color)

            self.table.setItem(row, 0, item_title)
            self.table.setItem(row, 1, item_artist)
            self.table.setItem(row, 2, item_year)
            self.table.setItem(row, 3, item_tracks)
            self.table.setRowHeight(row, 40)

    def _on_row_double_clicked(self, row: int, _col: int) -> None:
        if 0 <= row < len(self._albums):
            album_id = self._albums[row].get("id")
            if album_id:
                self.album_selected.emit(album_id)
