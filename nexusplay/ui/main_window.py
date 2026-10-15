"""NexusPlay — Jendela utama aplikasi.

Kelas `MainWindow` adalah jendela utama (QMainWindow) yang menjadi
wadah semua tampilan: sidebar, area konten, bar pemutar bawah, dll.

Untuk M2, jendela ini berisi:
- layar video (VideoWidget) di atas,
- panel kontrol di bawah: Buka File, Play/Pause, Stop, Fullscreen,
  pilih trek audio/subtitle, muat subtitle, slider posisi & volume,
- fullscreen dengan F / Esc / klik ganda; di mode fullscreen panel
  kontrol bersembunyi setelah 3 detik mouse diam (FR-11).
Untuk M3 ditambah baris library SEMENTARA: Tambah Folder, Pindai Ulang,
progress bar, dan jumlah lagu/video.
Kerangka UI lengkap dibuat di M4.

Aturan arsitektur (PRD 7.3): jendela ini TIDAK memanggil mpv atau SQL
langsung. Semua lewat objek `Player`, `LibraryScanner`, dan fungsi di
`repositories.py`.
"""

from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QCursor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from nexusplay.core.player import Player
from nexusplay.db import repositories as repo
from nexusplay.db.connection import open_database
from nexusplay.library.scanner import LibraryScanner, ScanResult
from nexusplay.ui.widgets.video_widget import VideoWidget

# Format yang didukung (PRD FR-1 dan FR-2)
AUDIO_EXT = "*.mp3 *.flac *.m4a *.aac *.ogg *.opus *.wav"
VIDEO_EXT = "*.mp4 *.mkv *.avi *.webm *.mov"
MEDIA_FILTER = (
    f"Semua media ({AUDIO_EXT} {VIDEO_EXT});;"
    f"Audio ({AUDIO_EXT});;"
    f"Video ({VIDEO_EXT});;"
    "Semua file (*.*)"
)
SUBTITLE_FILTER = "Subtitle (*.srt *.ass);;Semua file (*.*)"

CONTROLS_HIDE_MS = 3000   # kontrol hilang setelah 3 detik diam (PRD 8.1)


def format_ms(ms: int) -> str:
    """Ubah milidetik jadi teks 'm:ss'. Contoh: 83000 -> '1:23'."""
    total_seconds = max(0, ms) // 1000
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes}:{seconds:02d}"


def format_count(n: int) -> str:
    """Angka dengan titik ribuan gaya Indonesia: 1234 -> '1.234'."""
    return f"{n:,}".replace(",", ".")


class MainWindow(QMainWindow):
    """Jendela utama NexusPlay."""

    def __init__(self) -> None:
        super().__init__()

        # ── Properti jendela ────────────────────────────────
        self.setWindowTitle("NexusPlay")
        self.resize(1200, 800)
        self.setMinimumSize(800, 500)

        # True selama pengguna sedang menyeret slider posisi,
        # supaya update dari player tidak "melawan" tarikan mouse.
        self._seeking = False

        # Untuk kembali ke ukuran semula setelah keluar fullscreen
        self._was_maximized = False

        # Layar video harus dibuat DULU, karena nomor jendelanya
        # dibutuhkan saat membuat Player.
        self.video_widget = VideoWidget()

        # ── Mesin pemutar ───────────────────────────────────
        self.player = Player(wid=self.video_widget.window_id(), parent=self)

        # ── Database & pemindai (M3) ──────────────────────
        # Koneksi ini khusus thread UI. Pemindai membuka koneksinya sendiri.
        self.db = open_database()
        self.scanner = LibraryScanner(self)

        self._build_ui()
        self._build_fullscreen_helpers()
        self._connect_signals()
        self._refresh_library_stats()

    # ── Membangun tampilan ─────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Layar video mengambil semua ruang sisa (stretch = 1)
        root.addWidget(self.video_widget, 1)

        # ── Panel kontrol ───────────────────────────────────
        # Dibungkus satu QWidget supaya bisa disembunyikan sekaligus.
        self.controls = QWidget()
        self.controls.setStyleSheet("background-color: #151922;")
        panel = QVBoxLayout(self.controls)
        panel.setContentsMargins(16, 12, 16, 12)
        panel.setSpacing(8)

        # ── Baris library (SEMENTARA, diganti sidebar di M4) ───
        self.add_folder_button = QPushButton("＋ Tambah Folder")
        self.rescan_button = QPushButton("↻ Pindai Ulang")
        self.scan_progress = QProgressBar()
        self.scan_progress.setFixedWidth(220)
        self.scan_progress.setTextVisible(False)
        self.scan_progress.hide()           # hanya tampil saat memindai
        self.library_label = QLabel()
        self.library_label.setStyleSheet("color: #8B93A7;")

        library_row = QHBoxLayout()
        library_row.addWidget(self.add_folder_button)
        library_row.addWidget(self.rescan_button)
        library_row.addWidget(self.scan_progress)
        library_row.addWidget(self.library_label, 1)
        panel.addLayout(library_row)

        # Nama file yang sedang diputar
        self.track_label = QLabel("Belum ada media. Klik \"Buka File\" untuk mulai.")
        self.track_label.setStyleSheet("font-size: 15px; color: #8B93A7;")

        # Baris posisi: 0:00 [=====o-----] 3:45
        self.position_label = QLabel("0:00")
        self.duration_label = QLabel("0:00")
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 0)

        seek_row = QHBoxLayout()
        seek_row.addWidget(self.position_label)
        seek_row.addWidget(self.seek_slider, 1)
        seek_row.addWidget(self.duration_label)

        # Baris tombol
        self.open_button = QPushButton("Buka File")
        self.play_button = QPushButton("Play")
        self.stop_button = QPushButton("Stop")
        self.fullscreen_button = QPushButton("Fullscreen (F)")
        self.subtitle_button = QPushButton("Muat Subtitle…")
        self.play_button.setEnabled(False)
        self.stop_button.setEnabled(False)

        # Pilihan trek
        self.audio_combo = QComboBox()
        self.audio_combo.setMinimumWidth(140)
        self.audio_combo.setEnabled(False)
        self.subtitle_combo = QComboBox()
        self.subtitle_combo.setMinimumWidth(160)
        self.subtitle_combo.setEnabled(False)

        # Volume
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(self.player.volume)
        self.volume_slider.setFixedWidth(120)
        self.volume_label = QLabel(f"Vol {self.player.volume}")

        buttons = QHBoxLayout()
        buttons.addWidget(self.open_button)
        buttons.addWidget(self.play_button)
        buttons.addWidget(self.stop_button)
        buttons.addSpacing(16)
        buttons.addWidget(QLabel("Audio:"))
        buttons.addWidget(self.audio_combo)
        buttons.addWidget(QLabel("Subtitle:"))
        buttons.addWidget(self.subtitle_combo)
        buttons.addWidget(self.subtitle_button)
        buttons.addStretch()
        buttons.addWidget(self.volume_label)
        buttons.addWidget(self.volume_slider)
        buttons.addWidget(self.fullscreen_button)

        panel.addWidget(self.track_label)
        panel.addLayout(seek_row)
        panel.addLayout(buttons)

        root.addWidget(self.controls)

    def _build_fullscreen_helpers(self) -> None:
        # Pintasan F dan Esc. QShortcut tetap bekerja walau fokus
        # keyboard sedang ada di tombol atau slider.
        QShortcut(QKeySequence(Qt.Key.Key_F), self, self.toggle_fullscreen)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self.exit_fullscreen)

        # Timer sekali jalan: setelah 3 detik diam, sembunyikan kontrol.
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(CONTROLS_HIDE_MS)
        self._hide_timer.timeout.connect(self._hide_controls)

        # Timer berulang: cek apakah posisi mouse berubah.
        # Kenapa tidak cukup pakai mouseMoveEvent? Karena mpv membuat
        # jendela sendiri di atas VideoWidget, sehingga event mouse
        # di area video sering "ditelan" mpv dan tidak sampai ke Qt.
        self._last_cursor_pos = QPoint()
        self._cursor_timer = QTimer(self)
        self._cursor_timer.setInterval(200)
        self._cursor_timer.timeout.connect(self._check_cursor_moved)

    # ── Menghubungkan sinyal ke slot ───────────────────────────

    def _connect_signals(self) -> None:
        # UI -> Player (pengguna menekan sesuatu)
        self.open_button.clicked.connect(self._open_file)
        self.play_button.clicked.connect(self.player.toggle_pause)
        self.stop_button.clicked.connect(self.player.stop)
        self.fullscreen_button.clicked.connect(self.toggle_fullscreen)
        self.subtitle_button.clicked.connect(self._open_subtitle)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        self.seek_slider.sliderPressed.connect(self._on_seek_start)
        self.seek_slider.sliderReleased.connect(self._on_seek_end)
        self.audio_combo.currentIndexChanged.connect(self._on_audio_selected)
        self.subtitle_combo.currentIndexChanged.connect(self._on_subtitle_selected)

        # Library (M3)
        self.add_folder_button.clicked.connect(self._add_folder)
        self.rescan_button.clicked.connect(self._rescan_library)
        self.scanner.progress.connect(self._on_scan_progress)
        self.scanner.finished.connect(self._on_scan_finished)
        self.scanner.failed.connect(self._on_scan_failed)

        # VideoWidget -> jendela
        self.video_widget.double_clicked.connect(self.toggle_fullscreen)
        self.video_widget.mouse_moved.connect(self._on_user_activity)

        # Player -> UI (player memberi kabar)
        self.player.position_changed.connect(self._on_position_changed)
        self.player.duration_changed.connect(self._on_duration_changed)
        self.player.state_changed.connect(self._on_state_changed)
        self.player.media_loaded.connect(self._on_media_loaded)
        self.player.tracks_changed.connect(self._on_tracks_changed)

    # ── Slot: aksi pengguna ────────────────────────────────────

    def _open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Pilih file media", "", MEDIA_FILTER)
        if path:  # kosong kalau pengguna menekan Batal
            self.player.play(path)

    def _open_subtitle(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Pilih file subtitle", "", SUBTITLE_FILTER)
        if path:
            self.player.load_subtitle(path)

    def _on_volume_changed(self, value: int) -> None:
        self.player.set_volume(value)
        self.volume_label.setText(f"Vol {value}")

    def _on_seek_start(self) -> None:
        self._seeking = True

    def _on_seek_end(self) -> None:
        self._seeking = False
        self.player.seek(self.seek_slider.value())

    def _on_audio_selected(self, index: int) -> None:
        track_id = self.audio_combo.itemData(index)
        if track_id is not None:
            self.player.set_audio_track(track_id)

    def _on_subtitle_selected(self, index: int) -> None:
        if index < 0:
            return
        # itemData = id trek, atau None untuk pilihan "Mati"
        self.player.set_subtitle_track(self.subtitle_combo.itemData(index))

    # ── Slot: kabar dari Player ────────────────────────────────

    def _on_position_changed(self, ms: int) -> None:
        if not self._seeking:
            self.seek_slider.setValue(ms)
        self.position_label.setText(format_ms(ms))

    def _on_duration_changed(self, ms: int) -> None:
        self.seek_slider.setRange(0, ms)
        self.duration_label.setText(format_ms(ms))

    def _on_state_changed(self, state: str) -> None:
        self.play_button.setText("Pause" if state == "playing" else "Play")
        self.play_button.setEnabled(state in ("playing", "paused"))
        self.stop_button.setEnabled(state in ("playing", "paused"))
        if state in ("stopped", "idle"):
            self.seek_slider.setValue(0)
            self.position_label.setText("0:00")

    def _on_media_loaded(self, path: str) -> None:
        self.track_label.setText(Path(path).name)

    def _on_tracks_changed(self, tracks: list) -> None:
        """Isi ulang dropdown audio & subtitle dari daftar trek terbaru."""
        audio = [t for t in tracks if t["type"] == "audio"]
        subs = [t for t in tracks if t["type"] == "sub"]

        # blockSignals: saat mengisi ulang dropdown, jangan sampai
        # currentIndexChanged terpanggil dan mengganti trek mpv.
        self.audio_combo.blockSignals(True)
        self.audio_combo.clear()
        for t in audio:
            self.audio_combo.addItem(t["label"], t["id"])
            if t["selected"]:
                self.audio_combo.setCurrentIndex(self.audio_combo.count() - 1)
        self.audio_combo.setEnabled(len(audio) > 1)
        self.audio_combo.blockSignals(False)

        self.subtitle_combo.blockSignals(True)
        self.subtitle_combo.clear()
        self.subtitle_combo.addItem("Mati", None)
        for t in subs:
            self.subtitle_combo.addItem(t["label"], t["id"])
            if t["selected"]:
                self.subtitle_combo.setCurrentIndex(self.subtitle_combo.count() - 1)
        self.subtitle_combo.setEnabled(len(subs) > 0)
        self.subtitle_combo.blockSignals(False)

    # ── Fullscreen & kontrol sembunyi otomatis ─────────────────

    def toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.exit_fullscreen()
        else:
            self._was_maximized = self.isMaximized()
            self.showFullScreen()
            self._last_cursor_pos = QCursor.pos()
            self._cursor_timer.start()
            self._hide_timer.start()

    def exit_fullscreen(self) -> None:
        if not self.isFullScreen():
            return
        self._cursor_timer.stop()
        self._hide_timer.stop()
        self._show_controls()
        if self._was_maximized:
            self.showMaximized()
        else:
            self.showNormal()

    def _check_cursor_moved(self) -> None:
        pos = QCursor.pos()
        if pos != self._last_cursor_pos:
            self._last_cursor_pos = pos
            self._on_user_activity()

    def _on_user_activity(self) -> None:
        """Mouse bergerak: tampilkan kontrol, mulai hitung 3 detik lagi."""
        if self.isFullScreen():
            self._show_controls()
            self._hide_timer.start()   # start() ulang = reset hitungan

    def _hide_controls(self) -> None:
        # Jangan sembunyikan kalau mouse sedang di atas panel kontrol
        if self.controls.underMouse():
            self._hide_timer.start()
            return
        self.controls.hide()
        self.video_widget.setCursor(Qt.CursorShape.BlankCursor)

    def _show_controls(self) -> None:
        self.controls.show()
        self.video_widget.unsetCursor()

    # ── Library & pemindaian (M3) ──────────────────────────

    def _add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Pilih folder musik/video")
        if not folder:
            return
        folder = repo.add_library_folder(self.db, folder)
        self._start_scan([folder])

    def _rescan_library(self) -> None:
        if not repo.list_library_folders(self.db):
            self.library_label.setText("Belum ada folder. Klik \"Tambah Folder\" dulu.")
            return
        self._start_scan(None)   # None = semua folder library

    def _start_scan(self, folders: list[str] | None) -> None:
        if not self.scanner.start(folders):
            return  # masih ada pemindaian yang berjalan
        self.add_folder_button.setEnabled(False)
        self.rescan_button.setEnabled(False)
        self.scan_progress.setRange(0, 0)   # range 0..0 = animasi "sibuk"
        self.scan_progress.show()
        self.library_label.setText("Mencari file…")

    def _on_scan_progress(self, done: int, total: int, folder: str) -> None:
        # Slot ini berjalan di thread UI, jadi aman menyentuh widget.
        if total > 0:
            self.scan_progress.setRange(0, total)
            self.scan_progress.setValue(done)
        self.library_label.setText(
            f"Memindai {Path(folder).name}: {format_count(done)} / {format_count(total)} file"
        )

    def _on_scan_finished(self, result: ScanResult) -> None:
        self.scan_progress.hide()
        self.add_folder_button.setEnabled(True)
        self.rescan_button.setEnabled(True)
        self._refresh_library_stats(result)

    def _on_scan_failed(self, message: str) -> None:
        QMessageBox.warning(self, "Pemindaian gagal", message)

    def _refresh_library_stats(self, result: ScanResult | None = None) -> None:
        """Tampilkan jumlah lagu/video, plus ringkasan pindai terakhir."""
        counts = repo.count_media(self.db)
        if not repo.list_library_folders(self.db):
            text = "Belum ada musik. Tambah folder untuk mulai."
        else:
            text = f"Library: {format_count(counts['audio'])} lagu · {format_count(counts['video'])} video"

        tooltip = ""
        if result is not None:
            text += (
                f"  —  +{result.added} baru, {result.updated} diperbarui, "
                f"{result.removed} dihapus"
            )
            if result.stopped:
                text += " (dihentikan)"
            if result.errors:
                # File rusak ditampilkan sebagai pesan, bukan crash (PRD 6)
                text += f", ⚠ {len(result.errors)} file dilewati (arahkan mouse ke sini)"
                tooltip = "\n".join(result.errors[:20])
                if len(result.errors) > 20:
                    tooltip += f"\n… dan {len(result.errors) - 20} lainnya"
            if result.missing_folders:
                text += f", ⚠ {len(result.missing_folders)} folder tidak ditemukan"
                tooltip = "\n".join(
                    ["Folder tidak ditemukan (dilewati, data aman):"] + result.missing_folders
                    + (["", tooltip] if tooltip else [])
                )
        self.library_label.setText(text)
        self.library_label.setToolTip(tooltip)

    # ── Saat jendela ditutup ───────────────────────────────────

    def closeEvent(self, event) -> None:
        # Hentikan pemindaian dengan rapi SEBELUM menutup database.
        self.scanner.stop(wait=True)
        self.player.cleanup()
        self.db.close()
        super().closeEvent(event)
