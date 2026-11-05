"""NexusPlay — PlaylistView (Minimal Dark).

Tampilan pengelolaan dan pemutaran playlist:
- Kolom kiri: Daftar playlist yang tersimpan di SQLite, tombol buat playlist baru,
  menu klik kanan (Ubah Nama, Pin/Unpin, Hapus).
- Kolom kanan: Isi playlist yang dipilih (tabel lagu dengan tombol "Putar Semua"),
  menu klik kanan untuk menghapus lagu dari playlist.
"""

import sqlite3

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from nexusplay.db import repositories as repo
from nexusplay.ui.theme import COLORS, icon, icon_pixmap, set_button_icon
from nexusplay.ui.widgets.player_bar import format_ms


class PlaylistView(QWidget):
    """View pengelolaan playlist."""

    play_tracks_requested = Signal(list, int)  # (tracks, start_index)

    def __init__(self, db: sqlite3.Connection, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = db
        self._current_playlist_id: int | None = None
        self._current_tracks: list[dict] = []

        self._build_ui()
        self.reload_playlists()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(16)

        # ── Header View ────────────────────────────────────────
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self.title_label = QLabel("Playlist")
        self.title_label.setProperty("role", "title")
        self.subtitle_label = QLabel("Koleksi musik pilihan Anda")
        self.subtitle_label.setProperty("role", "muted")
        title_col.addWidget(self.title_label)
        title_col.addWidget(self.subtitle_label)

        self.new_playlist_btn = QPushButton("Buat Playlist")
        self.new_playlist_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        set_button_icon(self.new_playlist_btn, "plus", COLORS["text"], 15)
        self.new_playlist_btn.clicked.connect(self._create_new_playlist)

        header_layout.addLayout(title_col)
        header_layout.addStretch()
        header_layout.addWidget(self.new_playlist_btn)
        root.addLayout(header_layout)

        # ── Splitter: Kiri (Daftar Playlist) | Kanan (Isi Playlist) ──
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {COLORS["border"]};
                width: 1px;
            }}
        """)

        # Panel Kiri: Daftar Playlist
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 16, 0)
        left_layout.setSpacing(8)

        left_lbl = QLabel("DAFTAR PLAYLIST")
        left_lbl.setProperty("role", "caption")
        left_layout.addWidget(left_lbl)

        list_card = QFrame()
        list_card.setObjectName("StatCard")
        list_card_layout = QVBoxLayout(list_card)
        list_card_layout.setContentsMargins(6, 6, 6, 6)

        self.playlist_list = QListWidget()
        self.playlist_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.playlist_list.customContextMenuRequested.connect(self._show_playlist_context_menu)
        self.playlist_list.currentItemChanged.connect(self._on_playlist_selected)
        list_card_layout.addWidget(self.playlist_list)

        left_layout.addWidget(list_card, 1)
        self.splitter.addWidget(left_widget)

        # Panel Kanan: Stack (Detail Playlist vs Empty State)
        self.right_stack = QStackedWidget()

        # Page 0: Detail Playlist Terpilih
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        detail_layout.setContentsMargins(16, 0, 0, 0)
        detail_layout.setSpacing(12)

        detail_header = QHBoxLayout()
        detail_header.setContentsMargins(0, 0, 0, 0)

        info_box = QVBoxLayout()
        info_box.setSpacing(2)
        self.pl_title_label = QLabel("Nama Playlist")
        self.pl_title_label.setProperty("role", "title")
        self.pl_stats_label = QLabel("0 lagu · 0:00 total durasi")
        self.pl_stats_label.setProperty("role", "muted")
        info_box.addWidget(self.pl_title_label)
        info_box.addWidget(self.pl_stats_label)

        self.play_all_btn = QPushButton("Putar Semua")
        self.play_all_btn.setProperty("variant", "primary")
        self.play_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        set_button_icon(self.play_all_btn, "play", COLORS["on-accent"], 15, filled=True)
        self.play_all_btn.clicked.connect(self._play_all_tracks)

        detail_header.addLayout(info_box)
        detail_header.addStretch()
        detail_header.addWidget(self.play_all_btn)
        detail_layout.addLayout(detail_header)

        # Tabel Lagu di Playlist
        self.tracks_table = QTableWidget()
        self.tracks_table.setColumnCount(5)
        self.tracks_table.setHorizontalHeaderLabels(["#", "JUDUL", "ARTIS", "ALBUM", "DURASI"])
        self.tracks_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tracks_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tracks_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tracks_table.setShowGrid(False)
        self.tracks_table.verticalHeader().setVisible(False)
        self.tracks_table.setAlternatingRowColors(False)
        self.tracks_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tracks_table.customContextMenuRequested.connect(self._show_track_context_menu)
        self.tracks_table.cellDoubleClicked.connect(self._on_track_double_clicked)

        header = self.tracks_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.tracks_table.setColumnWidth(0, 48)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.tracks_table.setColumnWidth(4, 76)

        detail_layout.addWidget(self.tracks_table)
        self.right_stack.addWidget(detail_widget)

        # Page 1: Empty State
        empty_widget = QWidget()
        el = QVBoxLayout(empty_widget)
        el.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.setSpacing(10)

        lbl_icon = QLabel()
        lbl_icon.setPixmap(icon_pixmap("list-music", COLORS["text-muted"], 40))
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_title = QLabel("Pilih atau Buat Playlist")
        lbl_title.setProperty("role", "heading")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_desc = QLabel(
            "Pilih playlist di sisi kiri atau buat playlist baru untuk mulai mengatur musik Anda."
        )
        lbl_desc.setProperty("role", "muted")
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)

        el.addWidget(lbl_icon)
        el.addWidget(lbl_title)
        el.addWidget(lbl_desc)
        self.right_stack.addWidget(empty_widget)

        self.splitter.addWidget(self.right_stack)
        self.splitter.setSizes([240, 620])
        root.addWidget(self.splitter, 1)

    # ── Logika Playlist ────────────────────────────────────────

    def reload_playlists(self) -> None:
        """Muat ulang daftar playlist dari SQLite."""
        self.playlist_list.clear()
        playlists = repo.list_playlists(self.db)

        if not playlists:
            self.right_stack.setCurrentIndex(1)
            return

        pin_icon = icon("pin", COLORS["accent"], 15)
        list_icon = icon("list-music", COLORS["text-muted"], 15)

        for pl in playlists:
            item = QListWidgetItem(f"{pl['name']}\n{pl['track_count']} lagu")
            item.setIcon(pin_icon if pl["is_pinned"] else list_icon)
            item.setData(Qt.ItemDataRole.UserRole, pl["id"])
            self.playlist_list.addItem(item)

        if self._current_playlist_id is None and self.playlist_list.count() > 0:
            self.playlist_list.setCurrentRow(0)
        else:
            self._select_playlist_by_id(self._current_playlist_id)

    def _select_playlist_by_id(self, playlist_id: int | None) -> None:
        if playlist_id is None:
            return
        for i in range(self.playlist_list.count()):
            item = self.playlist_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == playlist_id:
                self.playlist_list.setCurrentRow(i)
                return

    def _on_playlist_selected(self, current: QListWidgetItem, _previous) -> None:
        if not current:
            self.right_stack.setCurrentIndex(1)
            return

        self._current_playlist_id = current.data(Qt.ItemDataRole.UserRole)
        pl_info = repo.get_playlist(self.db, self._current_playlist_id)
        if not pl_info:
            return

        self.right_stack.setCurrentIndex(0)
        self.pl_title_label.setText(pl_info["name"])

        items = repo.get_playlist_items(self.db, self._current_playlist_id)
        self._current_tracks = [dict(r) for r in items]

        count = len(self._current_tracks)
        total_ms = sum(t.get("duration_ms") or 0 for t in self._current_tracks)
        self.pl_stats_label.setText(f"{count} lagu · {format_ms(total_ms)} total durasi")

        muted_color = QColor(COLORS["text-muted"])
        text_color = QColor(COLORS["text"])

        self.tracks_table.setRowCount(count)
        for row, t in enumerate(self._current_tracks):
            pos_str = str(row + 1)
            title = t.get("title") or "Tanpa Judul"
            artist = t.get("artist") or "Artis tidak diketahui"
            album = t.get("album") or "Album tidak diketahui"
            dur = format_ms(t.get("duration_ms") or 0)

            item_pos = QTableWidgetItem(pos_str)
            item_pos.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_pos.setForeground(muted_color)

            item_title = QTableWidgetItem(title)
            item_title.setForeground(text_color)

            item_artist = QTableWidgetItem(artist)
            item_artist.setForeground(muted_color)

            item_album = QTableWidgetItem(album)
            item_album.setForeground(muted_color)

            item_dur = QTableWidgetItem(dur)
            item_dur.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_dur.setForeground(muted_color)

            self.tracks_table.setItem(row, 0, item_pos)
            self.tracks_table.setItem(row, 1, item_title)
            self.tracks_table.setItem(row, 2, item_artist)
            self.tracks_table.setItem(row, 3, item_album)
            self.tracks_table.setItem(row, 4, item_dur)
            self.tracks_table.setRowHeight(row, 40)

    def _create_new_playlist(self) -> None:
        name, ok = QInputDialog.getText(self.window(), "Playlist Baru", "Nama playlist:")
        if ok and name.strip():
            new_id = repo.create_playlist(self.db, name.strip())
            self._current_playlist_id = new_id
            self.reload_playlists()

    def _play_all_tracks(self) -> None:
        if self._current_tracks:
            self.play_tracks_requested.emit(self._current_tracks, 0)

    def _on_track_double_clicked(self, row: int, _col: int) -> None:
        if 0 <= row < len(self._current_tracks):
            self.play_tracks_requested.emit(self._current_tracks, row)

    # ── Context Menu (Klik Kanan) ──────────────────────────────

    def _show_playlist_context_menu(self, pos) -> None:
        item = self.playlist_list.itemAt(pos)
        if not item:
            return

        pl_id = item.data(Qt.ItemDataRole.UserRole)
        pl_info = repo.get_playlist(self.db, pl_id)
        if not pl_info:
            return

        menu = QMenu(self.window())

        pin_text = "Lepas Pin" if pl_info["is_pinned"] else "Sematkan di Atas (Pin)"
        pin_icon_name = "pin-off" if pl_info["is_pinned"] else "pin"
        action_pin = menu.addAction(icon(pin_icon_name, COLORS["text"], 15), pin_text)
        action_rename = menu.addAction(icon("pencil", COLORS["text"], 15), "Ubah Nama…")
        menu.addSeparator()
        action_delete = menu.addAction(icon("trash-2", COLORS["danger"], 15), "Hapus Playlist")

        selected = menu.exec(self.playlist_list.mapToGlobal(pos))
        if selected == action_pin:
            repo.toggle_playlist_pin(self.db, pl_id)
            self.reload_playlists()
        elif selected == action_rename:
            new_name, ok = QInputDialog.getText(
                self.window(), "Ubah Nama", "Nama baru:", text=pl_info["name"]
            )
            if ok and new_name.strip():
                repo.rename_playlist(self.db, pl_id, new_name.strip())
                self.reload_playlists()
        elif selected == action_delete:
            confirm = QMessageBox.question(
                self.window(),
                "Hapus Playlist",
                f"Yakin ingin menghapus playlist \"{pl_info['name']}\"?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if confirm == QMessageBox.StandardButton.Yes:
                repo.delete_playlist(self.db, pl_id)
                self._current_playlist_id = None
                self.reload_playlists()

    def _show_track_context_menu(self, pos) -> None:
        row = self.tracks_table.rowAt(pos.y())
        if row < 0 or row >= len(self._current_tracks):
            return

        menu = QMenu(self.window())
        action_play = menu.addAction(
            icon("play", COLORS["text"], 15, filled=True), "Putar Lagu Ini"
        )
        action_remove = menu.addAction(
            icon("trash-2", COLORS["danger"], 15), "Hapus dari Playlist Ini"
        )

        selected = menu.exec(self.tracks_table.mapToGlobal(pos))
        if selected == action_play:
            self.play_tracks_requested.emit(self._current_tracks, row)
        elif selected == action_remove:
            if self._current_playlist_id:
                repo.remove_from_playlist(self.db, self._current_playlist_id, row)
                self.reload_playlists()
