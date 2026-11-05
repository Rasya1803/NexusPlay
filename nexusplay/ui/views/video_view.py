"""NexusPlay — VideoView (Minimal Dark).

Tampilan daftar seluruh file video di library dalam bentuk tabel minimalis.
Kolom:
1. # (Nomor)
2. JUDUL VIDEO
3. RESOLUSI
4. UKURAN
5. DURASI
"""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
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

from nexusplay.ui.theme import COLORS, icon_pixmap, set_button_icon
from nexusplay.ui.widgets.player_bar import format_ms


def format_bytes(bytes_num: int) -> str:
    """Format bytes ke KB, MB, atau GB."""
    if not bytes_num or bytes_num <= 0:
        return "—"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_num < 1024:
            return f"{bytes_num:.1f} {unit}"
        bytes_num /= 1024
    return f"{bytes_num:.1f} PB"


class VideoView(QWidget):
    """View daftar video."""

    media_activated = Signal(dict)
    add_folder_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._videos: list[dict] = []

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
        self.title_label = QLabel("Video")
        self.title_label.setProperty("role", "title")
        self.subtitle_label = QLabel("0 video")
        self.subtitle_label.setProperty("role", "muted")
        title_col.addWidget(self.title_label)
        title_col.addWidget(self.subtitle_label)

        header_layout.addLayout(title_col)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # ── Stack Konten (Tabel vs Empty State) ─────────────────
        self.stack = QStackedWidget()

        # 1. Halaman Tabel Video
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["#", "JUDUL VIDEO", "RESOLUSI", "UKURAN", "DURASI"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(False)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 48)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 110)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 100)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 150)

        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self.stack.addWidget(self.table)

        # 2. Halaman Empty State
        empty_widget = QWidget()
        empty_layout = QVBoxLayout(empty_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(12)

        icon_label = QLabel()
        icon_label.setPixmap(icon_pixmap("film", COLORS["text-muted"], 40))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_title = QLabel("Belum ada video di library")
        empty_title.setProperty("role", "heading")
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_desc = QLabel("Tambahkan folder film, series, atau video Anda untuk mulai menonton.")
        empty_desc.setProperty("role", "muted")
        empty_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)

        add_btn = QPushButton("Tambah Folder Video")
        add_btn.setProperty("variant", "primary")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        set_button_icon(add_btn, "folder-plus", COLORS["on-accent"], 16)
        add_btn.clicked.connect(self.add_folder_requested)

        empty_layout.addStretch()
        empty_layout.addWidget(icon_label)
        empty_layout.addWidget(empty_title)
        empty_layout.addWidget(empty_desc)
        empty_layout.addWidget(add_btn, 0, Qt.AlignmentFlag.AlignCenter)
        empty_layout.addStretch()

        self.stack.addWidget(empty_widget)
        layout.addWidget(self.stack, 1)

    def set_videos(self, videos: list[dict]) -> None:
        """Isi tabel dengan data video dari repository."""
        self._videos = videos
        count = len(videos)
        self.subtitle_label.setText(f"{count} video")

        if count == 0:
            self.stack.setCurrentIndex(1)
            return

        self.stack.setCurrentIndex(0)
        self.table.setRowCount(count)

        muted_color = QColor(COLORS["text-muted"])
        text_color = QColor(COLORS["text"])
        accent_color = QColor(COLORS["accent"])

        for row, v in enumerate(videos):
            num = str(row + 1)
            title = v.get("title") or Path(v.get("path", "")).stem
            width = v.get("width")
            height = v.get("height")
            res_str = f"{width}x{height}" if width and height else "—"
            size_str = format_bytes(v.get("file_size") or 0)
            duration = format_ms(v.get("duration_ms") or 0)
            resume_ms = int(v.get("resume_ms") or 0)

            item_num = QTableWidgetItem(num)
            item_num.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_num.setForeground(muted_color)

            item_title = QTableWidgetItem(title)
            item_title.setForeground(text_color)
            item_title.setToolTip(v.get("path", ""))

            item_res = QTableWidgetItem(res_str)
            item_res.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_res.setForeground(muted_color)

            item_size = QTableWidgetItem(size_str)
            item_size.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_size.setForeground(muted_color)

            if resume_ms > 0:
                dur_text = f"{format_ms(resume_ms)} / {duration}"
                item_dur = QTableWidgetItem(dur_text)
                item_dur.setForeground(accent_color)
                item_dur.setToolTip(f"Lanjutkan dari {format_ms(resume_ms)}")
            else:
                item_dur = QTableWidgetItem(duration)
                item_dur.setForeground(muted_color)
            item_dur.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            self.table.setItem(row, 0, item_num)
            self.table.setItem(row, 1, item_title)
            self.table.setItem(row, 2, item_res)
            self.table.setItem(row, 3, item_size)
            self.table.setItem(row, 4, item_dur)
            self.table.setRowHeight(row, 40)

    def _on_cell_double_clicked(self, row: int, _col: int) -> None:
        if 0 <= row < len(self._videos):
            self.media_activated.emit(self._videos[row])
