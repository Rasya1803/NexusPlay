
"""NexusPlay — Pemindai folder library (FR-20, FR-23, FR-24).

Alur:  folder di disk → metadata.py → repositories.py → database

File ini punya tiga lapisan:
1. `scan_folder()`  — fungsi Python biasa, TANPA Qt. Mudah dites dengan pytest.
2. `ScanWorker`     — QObject yang menjalankan scan_folder() di thread latar
                      dan mengabarkan progres lewat sinyal.
3. `LibraryScanner` — "remote control" untuk UI: start(), stop(), dan
                      mengurus pembuatan/pembersihan QThread.

Konsep penting:
- **Thread latar:** pemindaian ribuan file butuh waktu. Kalau dijalankan
  di thread utama (thread UI), jendela membeku. Jadi kita pindahkan ke
  QThread terpisah.
- **Jangan sentuh widget dari thread lain.** Worker hanya memancarkan
  sinyal; Qt otomatis mengantarkan sinyal itu ke thread UI (queued
  connection), dan UI yang memperbarui progress bar.
- **Satu koneksi database per thread.** Worker membuka koneksinya sendiri.
"""

import os
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, QThread, Signal, Slot

from nexusplay.db import repositories as repo
from nexusplay.db.connection import COVERS_DIR, open_database
from nexusplay.library.metadata import (
    MediaInfo,
    MetadataError,
    VideoProber,
    media_kind,
    read_audio,
    read_cover,
    read_video,
)

# Commit tiap sekian file. Commit = tulis ke disk = lambat, jadi jangan
# tiap file; tapi jangan juga terlalu jarang supaya progres tidak hilang
# kalau aplikasi ditutup di tengah jalan.
BATCH_SIZE = 200

# Kabari UI tiap sekian file (memancarkan sinyal per file itu boros).
PROGRESS_EVERY = 20


@dataclass
class ScanResult:
    """Ringkasan hasil pemindaian."""

    added: int = 0
    updated: int = 0
    unchanged: int = 0
    removed: int = 0
    errors: list[str] = field(default_factory=list)
    missing_folders: list[str] = field(default_factory=list)
    stopped: bool = False

    def merge(self, other: "ScanResult") -> None:
        """Gabungkan hasil folder lain ke hasil ini."""
        self.added += other.added
        self.updated += other.updated
        self.unchanged += other.unchanged
        self.removed += other.removed
        self.errors += other.errors
        self.missing_folders += other.missing_folders
        self.stopped = self.stopped or other.stopped


# ── 1. Logika inti (tanpa Qt) ──────────────────────────────────

def find_media_files(folder: Path) -> list[Path]:
    """Semua file audio/video di folder dan subfolder-nya (rekursif).

    os.walk dipakai karena aman terhadap folder yang tidak bisa dibuka
    (misalnya karena izin akses): folder itu cukup dilewati.
    """
    found = []
    for root, _dirs, files in os.walk(folder):
        for name in files:
            path = Path(root) / name
            if media_kind(path):
                found.append(path)
    found.sort()
    return found


def scan_folder(
    conn: sqlite3.Connection,
    folder: str,
    *,
    get_prober: Callable[[], VideoProber | None] = lambda: None,
    covers_dir: Path | None = None,
    on_progress: Callable[[int, int], None] | None = None,
    should_stop: Callable[[], bool] = lambda: False,
) -> ScanResult:
    """Pindai satu folder secara inkremental dan simpan ke database.

    get_prober:  fungsi yang mengembalikan VideoProber (dibuat hanya kalau
                 benar-benar ada video). Bawaan: tanpa prober.
    covers_dir:  folder tujuan file cover album. None = cover tidak disimpan.
    on_progress: dipanggil dengan (selesai, total).
    should_stop: kalau mengembalikan True, pemindaian berhenti dengan rapi.
    """
    result = ScanResult()
    folder = repo.normalize_folder(folder)

    # Pengaman: kalau folder tidak ada (misalnya flashdisk dicabut),
    # JANGAN anggap semua isinya hilang. Lewati saja.
    if not Path(folder).is_dir():
        result.missing_folders.append(folder)
        return result

    files = find_media_files(Path(folder))
    total = len(files)
    known = repo.get_file_index(conn, folder)   # {path: (size, mtime)}
    on_disk: set[str] = set()

    if on_progress:
        on_progress(0, total)

    pending = 0  # jumlah perubahan yang belum di-commit
    for done, path in enumerate(files, start=1):
        if should_stop():
            result.stopped = True
            break

        key = str(path)
        on_disk.add(key)
        try:
            st = path.stat()
            stamp = (st.st_size, int(st.st_mtime))

            if known.get(key) == stamp:
                # File sama persis seperti saat pindai sebelumnya → lewati.
                result.unchanged += 1
            else:
                if media_kind(path) == "audio":
                    info = read_audio(path)
                else:
                    info = read_video(path, get_prober())
                save_media(conn, info, covers_dir)
                if key in known:
                    result.updated += 1
                else:
                    result.added += 1
                pending += 1
        except (MetadataError, OSError) as e:
            # File rusak / tidak bisa dibaca: catat, lalu lanjut ke file
            # berikutnya. Satu file jelek tidak boleh menghentikan semuanya.
            result.errors.append(str(e))

        if pending >= BATCH_SIZE:
            conn.commit()
            pending = 0
        if on_progress and (done % PROGRESS_EVERY == 0 or done == total):
            on_progress(done, total)

    # Hapus media yang filenya sudah tidak ada di disk (keputusan M3: 1a).
    # Hanya kalau pemindaian selesai penuh; kalau dihentikan di tengah,
    # `on_disk` belum lengkap dan kita bisa salah menghapus.
    if not result.stopped:
        missing = [p for p in known if p not in on_disk]
        repo.delete_media_by_paths(conn, missing)
        result.removed = len(missing)
        repo.delete_orphans(conn)

    conn.commit()
    return result


def save_media(conn: sqlite3.Connection, info: MediaInfo, covers_dir: Path | None) -> int:
    """Simpan satu MediaInfo ke database (artis, album, media, cover)."""
    artist_id = repo.get_or_create_artist(conn, info.artist)

    # Album dikelompokkan berdasarkan "album artist" kalau ada. Ini penting
    # untuk album kompilasi: 15 lagu dengan 15 artis berbeda tetap 1 album.
    album_artist = info.album_artist or info.artist
    album_artist_id = (
        artist_id if album_artist == info.artist
        else repo.get_or_create_artist(conn, album_artist)
    )
    album_id = repo.get_or_create_album(conn, info.album, album_artist_id, info.year)

    media_id = repo.upsert_media(conn, {
        "kind": info.kind,
        "path": info.path,
        "title": info.title,
        "artist_id": artist_id,
        "album_id": album_id,
        "track_no": info.track_no,
        "genre": info.genre,
        "duration_ms": info.duration_ms,
        "width": info.width,
        "height": info.height,
        "file_size": info.file_size,
        "file_mtime": info.file_mtime,
    })

    # Cover cukup diambil sekali per album, dari lagu pertama yang punya.
    if album_id and covers_dir and not repo.album_has_cover(conn, album_id):
        cover = read_cover(Path(info.path))
        if cover:
            data, ext = cover
            covers_dir.mkdir(parents=True, exist_ok=True)
            cover_file = covers_dir / f"{album_id}{ext}"
            cover_file.write_bytes(data)
            repo.set_album_cover(conn, album_id, str(cover_file))

    return media_id


# ── 2. Worker untuk thread latar ───────────────────────────────

class ScanWorker(QObject):
    """Menjalankan pemindaian di thread latar.

    Sinyal:
        progress(int, int, str) – (selesai, total, path folder)
        finished(object)        – ScanResult
        failed(str)             – error tak terduga (bug), bukan file rusak
    """

    progress = Signal(int, int, str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, folders: list[str] | None = None, db_path: str | None = None) -> None:
        super().__init__()
        self._folders = folders          # None = semua folder library
        self._db_path = db_path
        self._stop_requested = False

    def stop(self) -> None:
        """Minta berhenti. Dipanggil dari thread UI; cukup menyalakan bendera."""
        self._stop_requested = True

    @Slot()
    def run(self) -> None:
        """Isi kerja thread. Dipanggil otomatis saat QThread mulai."""
        result = ScanResult()
        prober: VideoProber | None = None

        def get_prober() -> VideoProber | None:
            # mpv baru dinyalakan saat bertemu video pertama.
            nonlocal prober
            if prober is None:
                try:
                    prober = VideoProber()
                except Exception as e:
                    result.errors.append(f"mpv tidak tersedia, durasi video dilewati: {e}")
                    prober = False  # type: ignore[assignment]  # jangan coba lagi
            return prober or None

        conn = None
        try:
            # Koneksi KHUSUS thread ini.
            conn = open_database(self._db_path)
            folders = self._folders if self._folders is not None else repo.list_library_folders(conn)
            for folder in folders:
                if self._stop_requested:
                    result.stopped = True
                    break
                part = scan_folder(
                    conn, folder,
                    get_prober=get_prober,
                    covers_dir=COVERS_DIR,
                    on_progress=lambda done, total, f=folder: self.progress.emit(done, total, f),
                    should_stop=lambda: self._stop_requested,
                )
                result.merge(part)
        except Exception as e:
            self.failed.emit(f"Pemindaian gagal: {e!r}")
        finally:
            if prober:
                prober.close()
            if conn is not None:
                conn.close()
            self.finished.emit(result)


# ── 3. Pengendali untuk UI ─────────────────────────────────────

class LibraryScanner(QObject):
    """Antarmuka sederhana untuk UI: start(), stop(), is_running().

    Sinyal diteruskan dari ScanWorker:
        progress(int, int, str), finished(object), failed(str)
    """

    progress = Signal(int, int, str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread: QThread | None = None
        self._worker: ScanWorker | None = None

    def is_running(self) -> bool:
        return self._thread is not None

    def start(self, folders: list[str] | None = None) -> bool:
        """Mulai pindai. False kalau masih ada pemindaian yang berjalan."""
        if self.is_running():
            return False

        self._thread = QThread()
        self._worker = ScanWorker(folders)
        # moveToThread: slot-slot worker akan dijalankan DI thread baru.
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.progress)
        self._worker.failed.connect(self.failed)
        self._worker.finished.connect(self._on_worker_finished)

        self._thread.start()
        return True

    def stop(self, wait: bool = False) -> None:
        """Minta pemindaian berhenti. wait=True → tunggu sampai thread selesai."""
        if self._worker is not None:
            self._worker.stop()
        if wait and self._thread is not None:
            self._thread.quit()
            self._thread.wait(10_000)

    @Slot(object)
    def _on_worker_finished(self, result: ScanResult) -> None:
        # Berjalan di thread UI. Bereskan thread, lalu teruskan hasilnya.
        thread, worker = self._thread, self._worker
        self._thread = self._worker = None
        if thread is not None:
            thread.quit()
            thread.wait()
            thread.deleteLater()
        if worker is not None:
            worker.deleteLater()
        self.finished.emit(result)
