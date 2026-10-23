"""NexusPlay — Jendela utama aplikasi.

Kelas `MainWindow` (QMainWindow) merangkai seluruh antarmuka aplikasi:
- Sidebar navigasi di kiri (Musik, Album, Artis, Video, Playlist, Folder Library)
- Area konten utama di tengah (QStackedWidget berisi masing-masing View)
- Panel antrean kanan yang dapat dibuka/tutup (QueuePanel)
- Layar pemutar video tertanam (VideoWidget) yang otomatis aktif saat video diputar
- Bar pemutar bawah (PlayerBar) yang selalu terlihat
- Integrasi antrean pemutaran (PlayQueue), pemindai library latar belakang (QThread), dan database SQLite

Aturan arsitektur (PRD 7.3):
- UI tidak memanggil SQL atau mpv secara langsung.
- Semua interaksi lewat objek Player, PlayQueue, LibraryScanner, dan fungsi repositories.py.
"""

from pathlib import Path
from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QCursor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from nexusplay.core.player import Player
from nexusplay.core.queue import PlayQueue
from nexusplay.db import repositories as repo
from nexusplay.db.connection import open_database
from nexusplay.library.scanner import LibraryScanner, ScanResult
from nexusplay.ui.views import AlbumView, ArtistView, FoldersView, MusicView, PlaylistView, VideoView
from nexusplay.ui.widgets import PlayerBar, QueuePanel, Sidebar, VideoWidget

CONTROLS_HIDE_MS = 3000   # Durasi auto-hide bar pemutar saat fullscreen video (PRD 8.1)


class MainWindow(QMainWindow):
    """Jendela utama NexusPlay."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("NexusPlay")
        self.resize(1200, 800)
        self.setMinimumSize(950, 580)

        self._was_maximized = False
        self._last_active_page = "music"

        # ── Database & Komponen Utama ──────────────────────────
        self.db = open_database()
        self.scanner = LibraryScanner(self)
        self.queue = PlayQueue(self)

        # Layar video (mpv butuh window_id native saat inisialisasi)
        self.video_widget = VideoWidget()
        self.player = Player(wid=self.video_widget.window_id(), parent=self)

        self._build_ui()
        self._build_fullscreen_helpers()
        self._connect_signals()
        self._load_library_data()

    # ── Membangun Tata Letak ───────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Bagian Atas: Sidebar + Content Stack + Queue Panel ──
        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # 1. Sidebar kiri
        self.sidebar = Sidebar(self)
        body_layout.addWidget(self.sidebar)

        # 2. Content stack tengah
        self.content_stack = QStackedWidget(self)

        # Index 0: Musik View
        self.music_view = MusicView(self)
        self.content_stack.addWidget(self.music_view)

        # Index 1: Album View
        self.album_view = AlbumView(self)
        self.content_stack.addWidget(self.album_view)

        # Index 2: Artis View
        self.artist_view = ArtistView(self)
        self.content_stack.addWidget(self.artist_view)

        # Index 3: Video View
        self.video_view = VideoView(self)
        self.content_stack.addWidget(self.video_view)

        # Index 4: Playlist View
        self.playlist_view = PlaylistView(self.db, self)
        self.content_stack.addWidget(self.playlist_view)

        # Index 5: Folder Library View
        self.folders_view = FoldersView(self)
        self.content_stack.addWidget(self.folders_view)

        # Index 6: Video Player View (Layar Video Tertanam)
        self.video_container = QWidget()
        video_layout = QVBoxLayout(self.video_container)
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_layout.setSpacing(0)

        # Bar atas video (Kembali ke library)
        self.video_top_bar = QWidget()
        self.video_top_bar.setStyleSheet("background-color: #0B0D12; border-bottom: 1px solid #1D2230;")
        top_bar_layout = QHBoxLayout(self.video_top_bar)
        top_bar_layout.setContentsMargins(16, 8, 16, 8)

        self.back_to_library_btn = QPushButton("← Kembali ke Daftar Video")
        self.back_to_library_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8B93A7;
                border: none;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                color: #FFFFFF;
            }
        """)
        self.back_to_library_btn.clicked.connect(self._exit_video_view)

        top_bar_layout.addWidget(self.back_to_library_btn)
        top_bar_layout.addStretch()

        video_layout.addWidget(self.video_top_bar)
        video_layout.addWidget(self.video_widget, 1)

        self.content_stack.addWidget(self.video_container)
        body_layout.addWidget(self.content_stack, 1)

        # 3. Panel antrean kanan (QueuePanel)
        self.queue_panel = QueuePanel(self.queue, self)
        self.queue_panel.hide()
        body_layout.addWidget(self.queue_panel)

        root.addLayout(body_layout, 1)

        # ── Bagian Bawah: Bar Pemutar ──────────────────────────
        self.player_bar = PlayerBar(self.player, self.queue, self)
        root.addWidget(self.player_bar)

    # ── Fullscreen & Kontrol Otomatis ──────────────────────────

    def _build_fullscreen_helpers(self) -> None:
        # Pintasan Keyboard (PRD bagian 9)
        QShortcut(QKeySequence(Qt.Key.Key_F), self, self.toggle_fullscreen)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self.exit_fullscreen)
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, self.player.toggle_pause)
        QShortcut(QKeySequence("Ctrl+Q"), self, self._toggle_queue_panel)
        QShortcut(QKeySequence(Qt.Key.Key_S), self, self.queue.toggle_shuffle)
        QShortcut(QKeySequence(Qt.Key.Key_R), self, self.queue.cycle_repeat_mode)
        QShortcut(QKeySequence(Qt.Key.Key_N), self, self.queue.next)
        QShortcut(QKeySequence(Qt.Key.Key_P), self, self.queue.prev)

        # Timer auto-hide player bar di mode fullscreen
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(CONTROLS_HIDE_MS)
        self._hide_timer.timeout.connect(self._hide_fullscreen_controls)

        # Timer deteksi gerakan mouse
        self._last_cursor_pos = QPoint()
        self._cursor_timer = QTimer(self)
        self._cursor_timer.setInterval(200)
        self._cursor_timer.timeout.connect(self._check_cursor_moved)

    # ── Koneksi Sinyal ─────────────────────────────────────────

    def _connect_signals(self) -> None:
        # Navigasi Sidebar -> Ganti Halaman
        self.sidebar.page_changed.connect(self._on_page_changed)

        # Aksi Pemutaran Musik & Playlist -> Masuk ke Antrean (M5)
        self.music_view.play_tracks_requested.connect(self._on_play_tracks)
        self.music_view.play_next_requested.connect(self.queue.play_next)
        self.music_view.append_queue_requested.connect(self.queue.append)
        self.music_view.add_to_playlist_requested.connect(self._add_track_to_playlist)
        self.music_view.new_playlist_with_track.connect(self._create_playlist_with_track)
        self.music_view.add_folder_requested.connect(self._go_to_folders_page)

        self.playlist_view.play_tracks_requested.connect(self._on_play_tracks)

        # Antrean (Queue) -> Pemutar Lagu & Otomatis Lanjut (Auto-Advance)
        self.queue.track_changed.connect(self._on_queue_track_changed)
        self.player.track_finished.connect(self.queue.next)

        # Panel Antrean
        self.player_bar.queue_toggle_requested.connect(self._toggle_queue_panel)
        self.queue_panel.close_requested.connect(self.queue_panel.hide)

        # Video
        self.video_view.media_activated.connect(self._play_video_track)
        self.video_view.add_folder_requested.connect(self._go_to_folders_page)

        # Folders View -> Library Actions
        self.folders_view.add_folder_requested.connect(self._add_folder)
        self.folders_view.remove_folder_requested.connect(self._remove_folder)
        self.folders_view.rescan_requested.connect(self._rescan_library)

        # Scanner -> Folders View & Main Window
        self.scanner.progress.connect(self._on_scan_progress)
        self.scanner.finished.connect(self._on_scan_finished)
        self.scanner.failed.connect(self._on_scan_failed)

        # Video & PlayerBar -> Fullscreen
        self.video_widget.double_clicked.connect(self.toggle_fullscreen)
        self.video_widget.mouse_moved.connect(self._on_user_activity)
        self.player_bar.fullscreen_requested.connect(self.toggle_fullscreen)

    # ── Pembacaan Data dari Database (PRD 7.3) ─────────────────

    def _load_library_data(self) -> None:
        """Muat seluruh data library dari SQLite ke dalam masing-masing view."""
        # 1. Musik
        audios = [dict(r) for r in repo.list_media(self.db, kind="audio", sort_by="title")]
        self.music_view.set_tracks(audios)

        # 2. Video
        videos = [dict(r) for r in repo.list_media(self.db, kind="video", sort_by="title")]
        self.video_view.set_videos(videos)

        # 3. Album
        albums = [dict(r) for r in repo.list_albums(self.db)]
        self.album_view.set_albums(albums)

        # 4. Artis
        artists = [dict(r) for r in repo.list_artists(self.db)]
        self.artist_view.set_artists(artists)

        # 5. Playlist
        playlists = [dict(r) for r in repo.list_playlists(self.db)]
        self.music_view.set_playlists(playlists)
        self.playlist_view.reload_playlists()

        # 6. Folder
        folders = repo.list_library_folders(self.db)
        self.folders_view.set_folders(folders)

    # ── Slot Navigasi ──────────────────────────────────────────

    def _on_page_changed(self, page_id: str) -> None:
        self._last_active_page = page_id
        page_map = {
            "music": 0,
            "albums": 1,
            "artists": 2,
            "videos": 3,
            "playlists": 4,
            "folders": 5,
        }
        idx = page_map.get(page_id, 0)
        self.content_stack.setCurrentIndex(idx)

    def _go_to_folders_page(self) -> None:
        self.sidebar.select_page("folders")

    def _exit_video_view(self) -> None:
        """Kembali dari layar video ke daftar video atau halaman sebelumnya."""
        self.sidebar.select_page(self._last_active_page or "videos")

    def _toggle_queue_panel(self) -> None:
        """Tampilkan atau sembunyikan panel antrean sisi kanan."""
        if self.queue_panel.isVisible():
            self.queue_panel.hide()
        else:
            self.queue_panel.refresh()
            self.queue_panel.show()

    # ── Slot Pemutaran Media & Antrean ─────────────────────────

    def _on_play_tracks(self, tracks: list[dict], start_index: int) -> None:
        """Pengguna mengaktifkan daftar lagu (dari MusicView atau PlaylistView)."""
        self.queue.set_tracks(tracks, start_index)

    def _on_queue_track_changed(self, track: dict) -> None:
        """Lagu dalam antrean berubah (dipicu next/prev atau klik lagu)."""
        path = track.get("path")
        if not path or not Path(path).exists():
            QMessageBox.warning(self, "File tidak ditemukan", f"File audio tidak ditemukan di disk:\n{path}")
            return

        self.player.play(path)
        self.player_bar.set_media_info(
            title=track.get("title", ""),
            artist=track.get("artist", ""),
            cover_path=track.get("cover_path"),
        )

    def _play_video_track(self, video: dict) -> None:
        """Putar video yang dipilih dan beralih ke layar video."""
        path = video.get("path")
        if not path or not Path(path).exists():
            QMessageBox.warning(self, "File tidak ditemukan", f"File video tidak ditemukan di disk:\n{path}")
            return

        self.player.play(path)
        self.player_bar.set_media_info(
            title=video.get("title", ""),
            artist="Video",
            cover_path=None,
        )
        # Beralih ke layar pemutar video (index 6)
        self.content_stack.setCurrentIndex(6)

    # ── Slot Playlist Management ───────────────────────────────

    def _add_track_to_playlist(self, playlist_id: int, track: dict) -> None:
        media_id = track.get("id")
        if media_id is not None:
            repo.add_media_to_playlist(self.db, playlist_id, media_id)
            self._load_library_data()

    def _create_playlist_with_track(self, track: dict) -> None:
        media_id = track.get("id")
        name, ok = QInputDialog.getText(self, "Playlist Baru", "Nama playlist:")
        if ok and name.strip() and media_id is not None:
            pl_id = repo.create_playlist(self.db, name.strip())
            repo.add_media_to_playlist(self.db, pl_id, media_id)
            self._load_library_data()

    # ── Slot Pengelolaan Library & Scanner ─────────────────────

    def _add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Pilih folder musik/video")
        if not folder:
            return
        folder_norm = repo.add_library_folder(self.db, folder)
        self.folders_view.set_folders(repo.list_library_folders(self.db))
        self._start_scan([folder_norm])

    def _remove_folder(self, folder_path: str) -> None:
        removed_count = repo.remove_library_folder(self.db, folder_path)
        self._load_library_data()
        self.folders_view.set_scan_state(
            False,
            f"Folder dihapus dari library ({removed_count} media dibersihkan)."
        )

    def _rescan_library(self) -> None:
        folders = repo.list_library_folders(self.db)
        if not folders:
            QMessageBox.information(self, "Library Kosong", "Tambahkan folder terlebih dahulu.")
            return
        self._start_scan(None)

    def _start_scan(self, folders: list[str] | None) -> None:
        if not self.scanner.start(folders):
            return
        self.folders_view.set_scan_state(True, "Mencari file media…", 0, 0)

    def _on_scan_progress(self, done: int, total: int, folder: str) -> None:
        folder_name = Path(folder).name
        self.folders_view.set_scan_state(
            True,
            f"Memindai {folder_name}… ({done}/{total} file)",
            done,
            total,
        )

    def _on_scan_finished(self, result: ScanResult) -> None:
        msg = f"Selesai: +{result.added} baru, {result.updated} diperbarui, {result.removed} dihapus."
        if result.errors:
            msg += f" (⚠ {len(result.errors)} file dilewati)"
        self.folders_view.set_scan_state(False, msg)
        self._load_library_data()

    def _on_scan_failed(self, message: str) -> None:
        self.folders_view.set_scan_state(False, f"Pemindaian gagal: {message}")
        QMessageBox.warning(self, "Pemindaian Gagal", message)

    # ── Logika Fullscreen ──────────────────────────────────────

    def toggle_fullscreen(self) -> None:
        """Beralih antara mode normal dan fullscreen."""
        if self.isFullScreen():
            self.exit_fullscreen()
        else:
            self._was_maximized = self.isMaximized()
            self.sidebar.hide()
            self.video_top_bar.hide()
            self.queue_panel.hide()
            self.showFullScreen()
            self._last_cursor_pos = QCursor.pos()
            self._cursor_timer.start()
            self._hide_timer.start()

    def exit_fullscreen(self) -> None:
        """Keluar dari fullscreen kembali ke mode jendela normal."""
        if not self.isFullScreen():
            # Bila ditekan Esc di layar video non-fullscreen, kembali ke library
            if self.content_stack.currentIndex() == 6:
                self._exit_video_view()
            return

        self._cursor_timer.stop()
        self._hide_timer.stop()
        self.video_widget.unsetCursor()
        self.sidebar.show()
        self.video_top_bar.show()
        self.player_bar.show()

        if self._was_maximized:
            self.showMaximized()
        else:
            self.showNormal()

    def _on_user_activity(self) -> None:
        if not self.isFullScreen():
            return
        self.player_bar.show()
        self.video_widget.unsetCursor()
        self._hide_timer.start()

    def _check_cursor_moved(self) -> None:
        if not self.isFullScreen():
            return
        current = QCursor.pos()
        if current != self._last_cursor_pos:
            self._last_cursor_pos = current
            self._on_user_activity()

    def _hide_fullscreen_controls(self) -> None:
        if not self.isFullScreen():
            return
        self.player_bar.hide()
        self.video_widget.setCursor(Qt.CursorShape.BlankCursor)

    # ── Saat Jendela Ditutup ───────────────────────────────────

    def closeEvent(self, event) -> None:
        self.scanner.stop(wait=True)
        self.player.cleanup()
        self.db.close()
        super().closeEvent(event)
