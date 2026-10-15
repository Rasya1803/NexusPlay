"""NexusPlay — FoldersView.

Tampilan pengelolaan folder library:
- Daftar folder yang sedang dipantau
- Tambah folder baru
- Hapus folder dari library
- Pindai ulang (rescan)
- Indikator progres pemindaian
"""

from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
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
        self.title_label.setStyleSheet("color: #E8EAF0; font-size: 24px; font-weight: bold;")
        self.subtitle_label = QLabel("Kelola direktori musik dan video yang diindeks oleh NexusPlay")
        self.subtitle_label.setStyleSheet("color: #8B93A7; font-size: 13px;")
        title_col.addWidget(self.title_label)
        title_col.addWidget(self.subtitle_label)
        layout.addLayout(title_col)

        # Baris aksi folder & pemindaian
        actions_row = QHBoxLayout()
        actions_row.setSpacing(10)

        self.add_btn = QPushButton("＋ Tambah Folder")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #7C5CFF, stop:1 #22D3EE);
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #9074FF, stop:1 #3EE0F8);
            }
        """)
        self.add_btn.clicked.connect(self.add_folder_requested)

        self.rescan_btn = QPushButton("↻ Pindai Ulang")
        self.rescan_btn.setStyleSheet("""
            QPushButton {
                background-color: #1D2230;
                color: #E8EAF0;
                border: 1px solid #262C3B;
                border-radius: 8px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #262C3B;
            }
        """)
        self.rescan_btn.clicked.connect(self.rescan_requested)

        self.remove_btn = QPushButton("🗑 Hapus Folder")
        self.remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #1D2230;
                color: #FF5C7A;
                border: 1px solid #262C3B;
                border-radius: 8px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #2E1A22;
                border-color: #FF5C7A;
            }
        """)
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
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1D2230;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7C5CFF, stop:1 #22D3EE);
                border-radius: 3px;
            }
        """)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #8B93A7; font-size: 13px;")
        layout.addWidget(self.status_label)

        # Daftar Folder
        self.folder_list = QListWidget()
        self.folder_list.setStyleSheet("""
            QListWidget {
                background-color: #151922;
                border: 1px solid #262C3B;
                border-radius: 10px;
                padding: 8px;
                color: #E8EAF0;
            }
            QListWidget::item {
                padding: 10px 12px;
                border-radius: 6px;
                margin-bottom: 4px;
            }
            QListWidget::item:hover {
                background-color: #1D2230;
            }
            QListWidget::item:selected {
                background-color: #262C3B;
                color: #FFFFFF;
                border-left: 3px solid #7C5CFF;
            }
        """)
        layout.addWidget(self.folder_list, 1)

    def set_folders(self, folders: list[str]) -> None:
        """Tampilkan daftar folder."""
        self.folder_list.clear()
        for f in folders:
            item = QListWidgetItem(f"📁   {f}")
            item.setData(Qt.ItemDataRole.UserRole, f)
            self.folder_list.addItem(item)

    def set_scan_state(self, is_scanning: bool, message: str = "", progress: int = 0, total: int = 0) -> None:
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
            QMessageBox.information(self, "Pilih Folder", "Pilih folder yang ingin dihapus dari daftar terlebih dahulu.")
            return
        folder_path = curr.data(Qt.ItemDataRole.UserRole)
        confirm = QMessageBox.question(
            self,
            "Konfirmasi Hapus Folder",
            f"Hapus folder ini dari library NexusPlay?\n\n{folder_path}\n\n(Catatan: File fisik di komputer Anda TIDAK akan terhapus).",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.remove_folder_requested.emit(folder_path)
