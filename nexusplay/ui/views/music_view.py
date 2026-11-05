"""NexusPlay — MusicView (Minimal Dark).

Tampilan daftar seluruh lagu di library dalam bentuk tabel minimalis tanpa zebra:
1. # (Nomor trek)
2. Favorit (ikon hati Lucide)
3. JUDUL
4. ARTIS
5. ALBUM
6. DURASI
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from nexusplay.ui.theme import COLORS, icon, icon_pixmap, set_button_icon
from nexusplay.ui.widgets.player_bar import format_ms


class MusicView(QWidget):
    """View daftar lagu musik."""

    play_tracks_requested = Signal(list, int)     # (tracks, start_index)
    play_next_requested = Signal(dict)            # (track)
    append_queue_requested = Signal(dict)         # (track)
    add_to_playlist_requested = Signal(int, dict) # (playlist_id, track)
    new_playlist_with_track = Signal(dict)        # (track)
    favorite_toggle_requested = Signal(int)       # (media_id)
    add_folder_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tracks: list[dict] = []
        self._playlists: list[dict] = []

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
        self.title_label.setProperty("role", "title")
        self.subtitle_label = QLabel("0 lagu")
        self.subtitle_label.setProperty("role", "muted")
        title_col.addWidget(self.title_label)
        title_col.addWidget(self.subtitle_label)

        header_layout.addLayout(title_col)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # ── Stack Konten (Tabel vs Empty State) ─────────────────
        self.stack = QStackedWidget()

        # 1. Halaman Tabel Lagu
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["#", "", "JUDUL", "ARTIS", "ALBUM", "DURASI"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(False)
        self.table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 44)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 38)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 76)

        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.cellClicked.connect(self._on_cell_clicked)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self.stack.addWidget(self.table)

        # 2. Halaman Empty State
        empty_widget = QWidget()
        empty_layout = QVBoxLayout(empty_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(12)

        icon_label = QLabel()
        icon_label.setPixmap(icon_pixmap("music", COLORS["text-muted"], 40))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_title = QLabel("Belum ada lagu di library")
        empty_title.setProperty("role", "heading")
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_desc = QLabel("Tambahkan folder musik Anda untuk memindai lagu secara otomatis.")
        empty_desc.setProperty("role", "muted")
        empty_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)

        add_btn = QPushButton("Tambah Folder Musik")
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

    def set_tracks(self, tracks: list[dict]) -> None:
        """Isi tabel dengan data track dari repository."""
        self._tracks = tracks
        count = len(tracks)
        self.subtitle_label.setText(f"{count} lagu")

        if count == 0:
            self.stack.setCurrentIndex(1)
            return

        self.stack.setCurrentIndex(0)
        self.table.setRowCount(count)

        muted_color = QColor(COLORS["text-muted"])
        text_color = QColor(COLORS["text"])

        for row, t in enumerate(tracks):
            track_num = str(t.get("track_no") or (row + 1))
            is_fav = bool(t.get("is_favorite"))
            title = t.get("title") or "Tanpa Judul"
            artist = t.get("artist") or "Artis tidak diketahui"
            album = t.get("album") or "Album tidak diketahui"
            duration = format_ms(t.get("duration_ms") or 0)

            item_num = QTableWidgetItem(track_num)
            item_num.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_num.setForeground(muted_color)

            item_fav = QTableWidgetItem("")
            item_fav.setIcon(
                icon(
                    "heart",
                    COLORS["text"] if is_fav else COLORS["text-disabled"],
                    15,
                    filled=is_fav,
                )
            )
            item_fav.setToolTip(
                "Klik untuk hapus dari Favorit" if is_fav else "Klik untuk tandai Favorit"
            )

            item_title = QTableWidgetItem(title)
            item_title.setForeground(text_color)
            item_title.setToolTip(t.get("path", ""))

            item_artist = QTableWidgetItem(artist)
            item_artist.setForeground(muted_color)

            item_album = QTableWidgetItem(album)
            item_album.setForeground(muted_color)

            item_dur = QTableWidgetItem(duration)
            item_dur.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_dur.setForeground(muted_color)

            self.table.setItem(row, 0, item_num)
            self.table.setItem(row, 1, item_fav)
            self.table.setItem(row, 2, item_title)
            self.table.setItem(row, 3, item_artist)
            self.table.setItem(row, 4, item_album)
            self.table.setItem(row, 5, item_dur)
            self.table.setRowHeight(row, 40)

    def set_playlists(self, playlists: list[dict]) -> None:
        """Simpan daftar playlist aktif untuk pilihan menu klik kanan."""
        self._playlists = playlists

    def _on_cell_clicked(self, row: int, col: int) -> None:
        """Klik tunggal pada kolom hati (kolom 1) mengubah status favorit."""
        if col == 1 and 0 <= row < len(self._tracks):
            media_id = self._tracks[row].get("id")
            if media_id is not None:
                self.favorite_toggle_requested.emit(int(media_id))

    def _on_cell_double_clicked(self, row: int, col: int) -> None:
        if col == 1:
            return
        if 0 <= row < len(self._tracks):
            self.play_tracks_requested.emit(self._tracks, row)

    def _show_context_menu(self, pos) -> None:
        row = self.table.rowAt(pos.y())
        if row < 0 or row >= len(self._tracks):
            return

        track = self._tracks[row]
        is_fav = bool(track.get("is_favorite"))
        menu = QMenu(self.window())

        action_play = menu.addAction(
            icon("play", COLORS["text"], 15, filled=True), "Putar Lagu Ini"
        )
        action_play_next = menu.addAction(
            icon("list-start", COLORS["text"], 15), "Putar Berikutnya"
        )
        action_append = menu.addAction(
            icon("list-end", COLORS["text"], 15), "Tambah ke Antrean"
        )
        action_fav = menu.addAction(
            icon("heart", COLORS["text"], 15, filled=not is_fav),
            "Hapus dari Favorit" if is_fav else "Tandai Favorit",
        )

        menu.addSeparator()
        playlist_submenu = menu.addMenu(
            icon("list-music", COLORS["text"], 15), "Tambahkan ke Playlist"
        )

        if self._playlists:
            for pl in self._playlists:
                action_pl = playlist_submenu.addAction(
                    icon("list-music", COLORS["text-muted"], 14), pl["name"]
                )
                action_pl.setData(pl["id"])
            playlist_submenu.addSeparator()

        action_new_pl = playlist_submenu.addAction(
            icon("plus", COLORS["text"], 15), "Buat Playlist Baru…"
        )

        selected = menu.exec(self.table.mapToGlobal(pos))
        if selected == action_play:
            self.play_tracks_requested.emit(self._tracks, row)
        elif selected == action_play_next:
            self.play_next_requested.emit(track)
        elif selected == action_append:
            self.append_queue_requested.emit(track)
        elif selected == action_fav and track.get("id") is not None:
            self.favorite_toggle_requested.emit(int(track["id"]))
        elif selected == action_new_pl:
            self.new_playlist_with_track.emit(track)
        elif selected and selected.data() is not None:
            pl_id = selected.data()
            self.add_to_playlist_requested.emit(pl_id, track)
