"""NexusPlay — FoldersView (Minimal Dark).

Tampilan pengelolaan folder library:
- Daftar folder yang sedang dipantau
- Tambah folder baru
- Hapus folder dari library
- Pindai ulang (rescan)
- Indikator progres pemindaian
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from nexusplay.ui.theme import COLORS, icon, set_button_icon


class FoldersView(QWidget):
    """View pengelolaan folder library dan pemindaian."""

    add_folder_requested = Signal()
    remove_folder_requested = Signal(str)
    rescan_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(16)

        # Header
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self.title_label = QLabel("Folder Library")
        self.title_label.setProperty("role", "title")
        self.subtitle_label = QLabel(
            "Kelola direktori musik dan video yang diindeks oleh NexusPlay"
        )
        self.subtitle_label.setProperty("role", "muted")
        title_col.addWidget(self.title_label)
        title_col.addWidget(self.subtitle_label)
        layout.addLayout(title_col)

        # Baris aksi folder & pemindaian
        actions_row = QHBoxLayout()
        actions_row.setSpacing(10)

        self.add_btn = QPushButton("Tambah Folder")
        self.add_btn.setProperty("variant", "primary")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        set_button_icon(self.add_btn, "folder-plus", COLORS["on-accent"], 16)
        self.add_btn.clicked.connect(self.add_folder_requested)

        self.rescan_btn = QPushButton("Pindai Ulang")
        self.rescan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        set_button_icon(self.rescan_btn, "refresh-cw", COLORS["text"], 15)
        self.rescan_btn.clicked.connect(self.rescan_requested)

        self.remove_btn = QPushButton("Hapus Folder")
        self.remove_btn.setProperty("variant", "danger")
        self.remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        set_button_icon(self.remove_btn, "trash-2", COLORS["text-muted"], 15)
        self.remove_btn.clicked.connect(self._on_remove_clicked)

        actions_row.addWidget(self.add_btn)
        actions_row.addWidget(self.rescan_btn)
        actions_row.addWidget(self.remove_btn)
        actions_row.addStretch()
        layout.addLayout(actions_row)

        # Status pemindaian & progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setProperty("role", "muted")
        layout.addWidget(self.status_label)

        # Daftar Folder di dalam Kartu permukaan
        list_card = QFrame()
        list_card.setObjectName("StatCard")
        list_card_layout = QVBoxLayout(list_card)
        list_card_layout.setContentsMargins(8, 8, 8, 8)

        self.folder_list = QListWidget()
        list_card_layout.addWidget(self.folder_list)
        layout.addWidget(list_card, 1)

    def set_folders(self, folders: list[str]) -> None:
        """Tampilkan daftar folder dengan ikon Lucide."""
        self.folder_list.clear()
        folder_icon = icon("folder", COLORS["text-muted"], 16)
        for f in folders:
            item = QListWidgetItem(f)
            item.setIcon(folder_icon)
            item.setData(Qt.ItemDataRole.UserRole, f)
            self.folder_list.addItem(item)

    def set_scan_state(
        self,
        is_scanning: bool,
        message: str = "",
        progress: int = 0,
        total: int = 0,
    ) -> None:
        """Update tampilan saat sedang atau selesai memindai."""
        self.add_btn.setEnabled(not is_scanning)
        self.rescan_btn.setEnabled(not is_scanning)
        self.remove_btn.setEnabled(not is_scanning)

        if is_scanning:
            self.progress_bar.show()
            if total > 0:
                self.progress_bar.setRange(0, total)
                self.progress_bar.setValue(progress)
            else:
                self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.hide()

        self.status_label.setText(message)

    def _on_remove_clicked(self) -> None:
        curr = self.folder_list.currentItem()
        if not curr:
            QMessageBox.information(
                self.window(),
                "Pilih Folder",
                "Pilih folder yang ingin dihapus dari daftar terlebih dahulu.",
            )
            return
        folder_path = curr.data(Qt.ItemDataRole.UserRole)
        confirm = QMessageBox.question(
            self.window(),
            "Konfirmasi Hapus Folder",
            (
                f"Hapus folder ini dari library NexusPlay?\n\n{folder_path}\n\n"
                "(Catatan: File fisik di komputer Anda TIDAK akan terhapus)."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.remove_folder_requested.emit(folder_path)
