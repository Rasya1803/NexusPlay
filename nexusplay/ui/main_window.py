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
    QLineEdit,
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
from nexusplay.ui.mini_player import MiniPlayer
from nexusplay.ui.theme import extract_accent_color
from nexusplay.ui.views import (
    AlbumView,
    ArtistView,
    FavoritesView,
    FoldersView,
    MusicView,
    NowPlayingView,
    PlaylistView,
    StatsView,
    VideoView,
)
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
        self._current_media: dict | None = None
        self._current_listen_ms = 0
        self._current_play_recorded = False

        # ── Database & Komponen Utama ──────────────────────────
        self.db = open_database()
        self.scanner = LibraryScanner(self)
        self.queue = PlayQueue(self)

        # Layar video (mpv butuh window_id native saat inisialisasi)
        self.video_widget = VideoWidget()
        self.player = Player(wid=self.video_widget.window_id(), parent=self)
        self.mini_player = MiniPlayer(self.player)

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

        # 2. Kolom Tengah: Bar Pencarian Atas + Content Stack
        center_column = QWidget()
        center_col_layout = QVBoxLayout(center_column)
        center_col_layout.setContentsMargins(0, 0, 0, 0)
        center_col_layout.setSpacing(0)

        # Bar Pencarian Cepat FTS5 (PRD 8.1 & FR-26)
        self.top_search_bar = QWidget()
        self.top_search_bar.setObjectName("TopSearchBar")
        self.top_search_bar.setStyleSheet("""
            QWidget#TopSearchBar {
                background-color: #0B0D12;
                border-bottom: 1px solid #1D2230;
            }
        """)
        search_layout = QHBoxLayout(self.top_search_bar)
        search_layout.setContentsMargins(24, 12, 24, 10)
        search_layout.setSpacing(10)

        search_icon = QLabel("🔍")
        search_icon.setStyleSheet("color: #8B93A7; font-size: 14px; background: transparent;")

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Cari lagu, artis, album, video… (Ctrl+F)")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setFixedHeight(36)
        self.search_input.setMaximumWidth(460)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #151922;
                color: #E8EAF0;
                border: 1px solid #262C3B;
                border-radius: 18px;
                padding: 0 16px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #7C5CFF;
                background-color: #1D2230;
            }
        """)

        search_layout.addWidget(search_icon)
        search_layout.addWidget(self.search_input, 1)
        search_layout.addStretch()

        center_col_layout.addWidget(self.top_search_bar)

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

        # Index 7: Now Playing View (Layar Sedang Diputar — FR-60)
        self.now_playing_view = NowPlayingView(self)
        self.content_stack.addWidget(self.now_playing_view)

        # Index 8: Favorites View (Layar Favorit ♥ — FR-25, FR-27)
        self.favorites_view = FavoritesView(self)
        self.content_stack.addWidget(self.favorites_view)

        # Index 9: Stats View (Layar Statistik & Riwayat — FR-29, FR-30)
        self.stats_view = StatsView(self)
        self.content_stack.addWidget(self.stats_view)

        center_col_layout.addWidget(self.content_stack, 1)
        body_layout.addWidget(center_column, 1)

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
        QShortcut(QKeySequence("Ctrl+F"), self, self._focus_search)

        # Timer debounce pencarian cepat FTS5 (FR-26)
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(80)
        self._search_timer.timeout.connect(self._perform_search)

        # Timer pelacak waktu dengar tiap 1 detik (FR-29, FR-30, Bagian 10)
        self._listen_timer = QTimer(self)
        self._listen_timer.setInterval(1000)
        self._listen_timer.timeout.connect(self._on_listen_tick)
        self._listen_timer.start()

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

        # Timer simpan posisi resume video/audio panjang setiap 5 detik (FR-28)
        self._resume_timer = QTimer(self)
        self._resume_timer.setInterval(5000)
        self._resume_timer.timeout.connect(self._save_current_resume_position)
        self._resume_timer.start()

    # ── Koneksi Sinyal ─────────────────────────────────────────

    def _connect_signals(self) -> None:
        # Navigasi Sidebar & Pencarian FTS5
        self.sidebar.page_changed.connect(self._on_page_changed)
        self.search_input.textChanged.connect(lambda _text: self._search_timer.start())

        # Aksi Pemutaran Musik & Playlist -> Masuk ke Antrean (M5)
        self.music_view.play_tracks_requested.connect(self._on_play_tracks)
        self.music_view.play_next_requested.connect(self.queue.play_next)
        self.music_view.append_queue_requested.connect(self.queue.append)
        self.music_view.add_to_playlist_requested.connect(self._add_track_to_playlist)
        self.music_view.new_playlist_with_track.connect(self._create_playlist_with_track)
        self.music_view.favorite_toggle_requested.connect(self._on_toggle_favorite)
        self.music_view.add_folder_requested.connect(self._go_to_folders_page)

        # Halaman Favorit (FR-25, FR-27)
        self.favorites_view.play_tracks_requested.connect(self._on_play_tracks)
        self.favorites_view.play_next_requested.connect(self.queue.play_next)
        self.favorites_view.append_queue_requested.connect(self.queue.append)
        self.favorites_view.add_to_playlist_requested.connect(self._add_track_to_playlist)
        self.favorites_view.new_playlist_with_track.connect(self._create_playlist_with_track)
        self.favorites_view.favorite_toggle_requested.connect(self._on_toggle_favorite)

        # Halaman Statistik & Riwayat (FR-29, FR-30)
        self.stats_view.play_media_requested.connect(self._on_play_single_media)

        self.playlist_view.play_tracks_requested.connect(self._on_play_tracks)

        # Antrean (Queue) -> Pemutar Lagu & Otomatis Lanjut (Auto-Advance)
        self.queue.track_changed.connect(self._on_queue_track_changed)
        self.player.track_finished.connect(self._on_track_finished)

        # Panel Antrean, Layar Sedang Diputar (FR-60), Mini-Player (FR-61), & Favorit
        self.player_bar.queue_toggle_requested.connect(self._toggle_queue_panel)
        self.player_bar.now_playing_requested.connect(self._toggle_now_playing_view)
        self.player_bar.mini_player_requested.connect(self._enter_mini_player)
        self.player_bar.favorite_toggled.connect(self._on_toggle_current_favorite)
        self.now_playing_view.back_requested.connect(self._exit_now_playing_view)
        self.mini_player.prev_requested.connect(self.queue.prev)
        self.mini_player.next_requested.connect(self.queue.next)
        self.mini_player.restore_requested.connect(self._exit_mini_player)
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
        query = self.search_input.text().strip() if hasattr(self, "search_input") else ""

        # 1. Musik, Video, & Favorit (mendukung filter pencarian FTS5)
        audios = [dict(r) for r in repo.search_media(self.db, query, kind="audio")]
        self.music_view.set_tracks(audios)

        videos = [dict(r) for r in repo.search_media(self.db, query, kind="video")]
        self.video_view.set_videos(videos)

        favs = [dict(r) for r in repo.search_media(self.db, query, favorite_only=True)]
        self.favorites_view.set_tracks(favs)

        # 2. Album
        albums = [dict(r) for r in repo.list_albums(self.db)]
        self.album_view.set_albums(albums)

        # 3. Artis
        artists = [dict(r) for r in repo.list_artists(self.db)]
        self.artist_view.set_artists(artists)

        # 4. Playlist
        playlists = [dict(r) for r in repo.list_playlists(self.db)]
        self.music_view.set_playlists(playlists)
        self.favorites_view.set_playlists(playlists)
        self.playlist_view.reload_playlists()

        # 5. Folder
        folders = repo.list_library_folders(self.db)
        self.folders_view.set_folders(folders)

        # 6. Statistik & Riwayat (FR-29, FR-30)
        self._refresh_stats_view()

    def _refresh_stats_view(self) -> None:
        """Perbarui data di halaman Statistik & Riwayat."""
        summary = repo.get_listening_summary(self.db, days=28)
        top_tracks = [dict(r) for r in repo.list_top_tracks(self.db, days=28, limit=10)]
        top_artists = [dict(r) for r in repo.list_top_artists(self.db, days=28, limit=10)]
        recent_history = [dict(r) for r in repo.list_recent_history(self.db, limit=30)]
        self.stats_view.set_stats_data(summary, top_tracks, top_artists, recent_history)

    # ── Pencarian Cepat FTS5 & Favorit (M7) ────────────────────

    def _focus_search(self) -> None:
        """Fokuskan kursor ke kotak pencarian atas (Ctrl+F)."""
        if not self.top_search_bar.isVisible():
            self.top_search_bar.show()
        self.search_input.setFocus()
        self.search_input.selectAll()

    def _perform_search(self) -> None:
        """Jalankan pencarian cepat FTS5 saat pengguna mengetik."""
        query = self.search_input.text().strip()
        audios = [dict(r) for r in repo.search_media(self.db, query, kind="audio")]
        videos = [dict(r) for r in repo.search_media(self.db, query, kind="video")]
        favs = [dict(r) for r in repo.search_media(self.db, query, favorite_only=True)]

        self.music_view.set_tracks(audios)
        self.video_view.set_videos(videos)
        self.favorites_view.set_tracks(favs)

        # Bila pengguna mengetik di halaman selain Musik/Video/Favorit, alihkan ke Musik
        if query and self._last_active_page not in ("music", "videos", "favorites"):
            self.sidebar.select_page("music")

    def _on_toggle_favorite(self, media_id: int) -> None:
        """Nyalakan/matikan status favorit untuk media_id tertentu."""
        is_fav = repo.toggle_favorite(self.db, media_id)
        if self._current_media and self._current_media.get("id") == media_id:
            self._current_media["is_favorite"] = 1 if is_fav else 0
            self.player_bar.set_favorite_state(is_fav)
        self._load_library_data()

    def _on_toggle_current_favorite(self) -> None:
        """Nyalakan/matikan status favorit untuk media yang sedang diputar di PlayerBar."""
        if not self._current_media or self._current_media.get("id") is None:
            return
        self._on_toggle_favorite(int(self._current_media["id"]))

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
            "favorites": 8,
            "stats": 9,
        }
        if page_id == "stats":
            self._refresh_stats_view()
        idx = page_map.get(page_id, 0)
        self.content_stack.setCurrentIndex(idx)

    def _go_to_folders_page(self) -> None:
        self.sidebar.select_page("folders")

    def _exit_video_view(self) -> None:
        """Kembali dari layar video ke daftar video atau halaman sebelumnya."""
        self._save_current_resume_position()
        videos = [dict(r) for r in repo.list_media(self.db, kind="video", sort_by="title")]
        self.video_view.set_videos(videos)
        self.sidebar.select_page(self._last_active_page or "videos")

    def _toggle_now_playing_view(self) -> None:
        """Buka atau tutup layar Sedang Diputar (FR-60)."""
        if self.content_stack.currentIndex() == 7:
            self._exit_now_playing_view()
        elif self._current_media and self._current_media.get("kind") == "video":
            self.content_stack.setCurrentIndex(6)
        else:
            self.content_stack.setCurrentIndex(7)

    def _exit_now_playing_view(self) -> None:
        """Kembali dari layar Sedang Diputar ke halaman aktif terakhir."""
        self._on_page_changed(self._last_active_page or "music")

    def _enter_mini_player(self) -> None:
        """Tampilkan jendela Mini-Player selalu-di-atas (FR-61)."""
        self.mini_player.show()
        self.mini_player.raise_()
        self.mini_player.activateWindow()
        self.hide()

    def _exit_mini_player(self) -> None:
        """Kembali dari Mini-Player ke jendela utama."""
        if self.mini_player.isVisible():
            self.mini_player.blockSignals(True)
            self.mini_player.hide()
            self.mini_player.blockSignals(False)
        self.show()
        self.raise_()
        self.activateWindow()

    def _toggle_queue_panel(self) -> None:
        """Tampilkan atau sembunyikan panel antrean sisi kanan."""
        if self.queue_panel.isVisible():
            self.queue_panel.hide()
        else:
            self.queue_panel.refresh()
            self.queue_panel.show()

    # ── Slot Pemutaran Media & Antrean ─────────────────────────

    def _on_listen_tick(self) -> None:
        """Dipanggil tiap 1 detik: tambah durasi dengar & catat riwayat bila memenuhi syarat."""
        if self.player.state != "playing" or not self._current_media:
            return
        media_id = self._current_media.get("id")
        if media_id is None:
            return

        self._current_listen_ms += 1000
        dur_ms = self.player.duration_ms or int(self._current_media.get("duration_ms") or 0)
        if not self._current_play_recorded and repo.should_count_play(self._current_listen_ms, dur_ms):
            repo.record_play(self.db, int(media_id), self._current_listen_ms)
            self._current_play_recorded = True
            if self.content_stack.currentIndex() == 9:
                self._refresh_stats_view()

    def _finalize_current_listen(self) -> None:
        """Pastikan riwayat tercatat bila trek diganti/selesai setelah memenuhi syarat."""
        if not self._current_media or self._current_media.get("id") is None:
            return
        media_id = int(self._current_media["id"])
        dur_ms = self.player.duration_ms or int(self._current_media.get("duration_ms") or 0)
        if not self._current_play_recorded and repo.should_count_play(self._current_listen_ms, dur_ms):
            repo.record_play(self.db, media_id, self._current_listen_ms)
            self._current_play_recorded = True
        self._current_listen_ms = 0
        self._current_play_recorded = False

    def _on_play_single_media(self, media: dict) -> None:
        """Putar satu item media dari halaman Statistik/Riwayat."""
        if media.get("kind") == "video":
            self._play_video_track(media)
        else:
            self._on_play_tracks([media], 0)

    def _save_current_resume_position(self) -> None:
        """Simpan posisi putar saat ini ke SQLite untuk video / audio panjang (FR-28)."""
        if not self._current_media:
            return
        media_id = self._current_media.get("id")
        if media_id is None:
            return
        dur_ms = self.player.duration_ms or int(self._current_media.get("duration_ms") or 0)
        pos_ms = self.player.position_ms
        is_video = self._current_media.get("kind") == "video"
        is_long_audio = dur_ms >= 600_000  # >= 10 menit
        if (is_video or is_long_audio) and dur_ms > 0 and pos_ms > 0:
            repo.update_resume_position(self.db, int(media_id), pos_ms, dur_ms)

    def _on_track_finished(self) -> None:
        """Saat trek selesai diputar, catat riwayat, reset resume ke 0, lalu lanjut antrean."""
        self._finalize_current_listen()
        if self._current_media and self._current_media.get("id") is not None:
            dur_ms = self.player.duration_ms or int(self._current_media.get("duration_ms") or 0)
            repo.update_resume_position(self.db, int(self._current_media["id"]), 0, dur_ms)
            if self._current_media.get("kind") == "video":
                videos = [dict(r) for r in repo.list_media(self.db, kind="video", sort_by="title")]
                self.video_view.set_videos(videos)
        self.queue.next()

    def _on_play_tracks(self, tracks: list[dict], start_index: int) -> None:
        """Pengguna mengaktifkan daftar lagu (dari MusicView, FavoritesView, atau PlaylistView)."""
        self.queue.set_tracks(tracks, start_index)

    def _on_queue_track_changed(self, track: dict) -> None:
        """Lagu dalam antrean berubah (dipicu next/prev atau klik lagu)."""
        self._finalize_current_listen()
        self._save_current_resume_position()

        if track.get("kind") == "video":
            self._play_video_track(track)
            return

        path = track.get("path")
        if not path or not Path(path).exists():
            QMessageBox.warning(self, "File tidak ditemukan", f"File audio tidak ditemukan di disk:\n{path}")
            return

        # Ambil data terbaru dari DB bila ada (untuk resume_ms audio panjang & is_favorite)
        start_ms = 0
        if track.get("id") is not None:
            fresh = repo.get_media(self.db, int(track["id"]))
            if fresh is not None:
                track = dict(fresh)
                if int(track.get("duration_ms") or 0) >= 600_000:
                    start_ms = int(track.get("resume_ms") or 0)

        self._current_media = track
        self._current_listen_ms = 0
        self._current_play_recorded = False
        cover_path = track.get("cover_path")
        accent = extract_accent_color(cover_path)

        self.player.play(path, start_ms=start_ms)
        self.player_bar.set_media_info(
            title=track.get("title", ""),
            artist=track.get("artist", ""),
            cover_path=cover_path,
            accent_color=accent,
        )
        self.player_bar.set_favorite_state(bool(track.get("is_favorite")))
        self.now_playing_view.set_track(track, accent_color=accent)
        self.mini_player.set_track_info(
            title=track.get("title", ""),
            artist=track.get("artist", ""),
            kind=track.get("kind", "audio"),
            cover_path=cover_path,
            accent_color=accent,
        )

    def _play_video_track(self, video: dict) -> None:
        """Putar video yang dipilih, lanjutkan dari resume_ms (FR-28), dan beralih ke layar video."""
        self._finalize_current_listen()
        self._save_current_resume_position()

        path = video.get("path")
        if not path or not Path(path).exists():
            QMessageBox.warning(self, "File tidak ditemukan", f"File video tidak ditemukan di disk:\n{path}")
            return

        start_ms = int(video.get("resume_ms") or 0)
        if video.get("id") is not None:
            fresh = repo.get_media(self.db, int(video["id"]))
            if fresh is not None:
                video = dict(fresh)
                start_ms = int(video.get("resume_ms") or 0)

        self._current_media = video
        self._current_listen_ms = 0
        self._current_play_recorded = False
        cover_path = video.get("cover_path")
        accent = extract_accent_color(cover_path)
        title = video.get("title") or Path(path).stem

        self.player.play(path, start_ms=start_ms)
        self.player_bar.set_media_info(
            title=title,
            artist="Video",
            cover_path=cover_path,
            accent_color=accent,
        )
        self.player_bar.set_favorite_state(bool(video.get("is_favorite")))
        self.now_playing_view.set_track(video, accent_color=accent)
        self.mini_player.set_track_info(
            title=title,
            artist="Video",
            kind="video",
            cover_path=cover_path,
            accent_color=accent,
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
            self.top_search_bar.hide()
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
        self.top_search_bar.show()
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
        self._listen_timer.stop()
        self._resume_timer.stop()
        self._finalize_current_listen()
        self._save_current_resume_position()
        self.mini_player.blockSignals(True)
        self.mini_player.close()
        self.scanner.stop(wait=True)
        self.player.cleanup()
        self.db.close()
        super().closeEvent(event)
