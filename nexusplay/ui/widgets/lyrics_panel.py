"""NexusPlay — LyricsPanel widget (M8 — FR-62, Minimal Dark).

Panel sisi kanan (320 px) untuk menampilkan lirik tersinkron (`.lrc`):
- Menyorot baris aktif sesuai waktu putar (`position_ms`) secara real-time.
- Menggulir otomatis (auto-scroll) agar baris aktif selalu berada di tengah panel.
- Klik pada baris lirik mana pun akan melompatkan lagu (seek) ke waktu baris tersebut.
- Menyediakan tombol untuk memuat file `.lrc` eksternal secara manual bila belum ada.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from nexusplay.library.lyrics import LyricLine, active_line_index
from nexusplay.ui.theme import COLORS, icon_pixmap, make_font, set_button_icon


class LyricsPanel(QWidget):
    """Panel lirik tersinkron yang dapat dibuka/sembunyikan (Ctrl+L)."""

    close_requested = Signal()
    seek_requested = Signal(int)      # time_ms saat baris lirik diklik
    load_lrc_requested = Signal()     # pengguna klik tombol muat file .lrc manual

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._lines: list[LyricLine] = []
        self._active_index: int = -1
        self._accent_color: str = COLORS["accent"]

        self.setFixedWidth(320)
        self.setObjectName("LyricsPanel")

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ── Header Panel ───────────────────────────────────────
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("Lirik")
        title_label.setProperty("role", "heading")

        self.open_lrc_btn = QPushButton("Muat .lrc")
        self.open_lrc_btn.setProperty("variant", "ghost")
        self.open_lrc_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_lrc_btn.setToolTip("Pilih file .lrc dari komputer")
        self.open_lrc_btn.clicked.connect(self.load_lrc_requested)

        self.close_btn = QPushButton()
        self.close_btn.setProperty("variant", "icon")
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        set_button_icon(self.close_btn, "x", COLORS["text-muted"], 16)
        self.close_btn.clicked.connect(self.close_requested)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.open_lrc_btn)
        header_layout.addWidget(self.close_btn)
        layout.addLayout(header_layout)

        # ── Stack: Daftar Lirik vs Empty State ─────────────────
        self.stack = QStackedWidget()

        # 1. Daftar Baris Lirik
        self.list_widget = QListWidget()
        self.list_widget.setWordWrap(True)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.list_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.stack.addWidget(self.list_widget)

        # 2. Empty State (Saat belum ada file .lrc)
        empty_widget = QWidget()
        empty_layout = QVBoxLayout(empty_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(10)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(icon_pixmap("mic-vocal", COLORS["text-muted"], 36))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.empty_title = QLabel("Belum ada lirik tersinkron")
        self.empty_title.setProperty("role", "heading")
        self.empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_desc = QLabel(
            "Letakkan file .lrc dengan nama yang sama\n"
            "di sebelah file lagu, atau muat manual:"
        )
        empty_desc.setProperty("role", "muted")
        empty_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)

        load_btn = QPushButton("Pilih File .lrc…")
        load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        set_button_icon(load_btn, "file-text", COLORS["text"], 15)
        load_btn.clicked.connect(self.load_lrc_requested)

        empty_layout.addStretch()
        empty_layout.addWidget(icon_lbl)
        empty_layout.addWidget(self.empty_title)
        empty_layout.addWidget(empty_desc)
        empty_layout.addWidget(load_btn, 0, Qt.AlignmentFlag.AlignCenter)
        empty_layout.addStretch()

        self.stack.addWidget(empty_widget)
        layout.addWidget(self.stack, 1)

    def set_accent_color(self, accent_color: str) -> None:
        """Perbarui warna aksen aktif sesuai sampul lagu."""
        self._accent_color = accent_color or COLORS["accent"]
        if 0 <= self._active_index < self.list_widget.count():
            self._apply_item_style(self._active_index, is_active=True)

    def set_lyrics(self, lines: list[LyricLine]) -> None:
        """Isi panel dengan daftar baris lirik baru."""
        self._lines = list(lines)
        self._active_index = -1
        self.list_widget.clear()

        if not self._lines:
            self.stack.setCurrentIndex(1)
            return

        self.stack.setCurrentIndex(0)
        for idx, line in enumerate(self._lines):
            display_text = line.text if line.text else "· · ·"
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, line.time_ms)
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.list_widget.addItem(item)
            self._apply_item_style(idx, is_active=False)

    def update_position(self, position_ms: int) -> None:
        """Sorot baris lirik yang sesuai dengan waktu `position_ms` saat ini."""
        if not self._lines:
            return

        new_idx = active_line_index(self._lines, position_ms)
        if new_idx == self._active_index:
            return

        if 0 <= self._active_index < self.list_widget.count():
            self._apply_item_style(self._active_index, is_active=False)

        self._active_index = new_idx

        if 0 <= self._active_index < self.list_widget.count():
            self._apply_item_style(self._active_index, is_active=True)
            active_item = self.list_widget.item(self._active_index)
            if active_item is not None:
                self.list_widget.scrollToItem(
                    active_item,
                    QAbstractItemView.ScrollHint.PositionAtCenter,
                )

    def _apply_item_style(self, index: int, is_active: bool) -> None:
        item = self.list_widget.item(index)
        if item is None:
            return

        if is_active:
            item.setFont(make_font(16, QFont.Weight.DemiBold))
            item.setForeground(QColor(COLORS["text"]))
            item.setBackground(QColor(COLORS["surface-2"]))
        else:
            item.setFont(make_font(14, QFont.Weight.Normal))
            item.setForeground(QColor(COLORS["text-muted"]))
            item.setBackground(QColor(0, 0, 0, 0))

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        time_ms = item.data(Qt.ItemDataRole.UserRole)
        if time_ms is not None:
            self.seek_requested.emit(int(time_ms))
