"""NexusPlay — Kelas pembungkus mesin pemutar (mpv).

Kelas `Player` membungkus seluruh interaksi dengan mpv.
UI tidak boleh memanggil mpv langsung; semua lewat kelas ini.

Konsep penting:
- **Sinyal (Signal):** cara Qt mengirim pesan antar objek.
  Contoh: saat posisi berubah, `Player` memancarkan sinyal
  `position_changed`, dan widget seek slider mendengarkannya.
- **Slot:** fungsi yang dipanggil saat sinyal dipancarkan.
- **QTimer:** timer berulang; di sini dipakai untuk menanyakan
  posisi putar setiap 100 ms (polling).
"""

import os
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal


# ── Pastikan libmpv bisa ditemukan ─────────────────────────────
# python-mpv mencari mpv-2.dll / libmpv-2.dll di PATH.
# Kita tambahkan folder proyek ke PATH supaya DLL yang kita
# simpan di situ langsung terdeteksi.
_project_root = str(Path(__file__).resolve().parent.parent.parent)
os.environ["PATH"] = _project_root + os.pathsep + os.environ["PATH"]

import mpv  # noqa: E402  (import harus setelah PATH diatur)


class Player(QObject):
    """Pembungkus mesin pemutar mpv.

    Semua interaksi pemutaran (play, pause, seek, volume) lewat
    kelas ini. Widget UI cukup menghubungkan (connect) sinyal-sinyal
    di bawah ke slot/fungsi mereka.

    Sinyal:
        position_changed(int)  – posisi sekarang dalam milidetik
        duration_changed(int)  – durasi total dalam milidetik
        state_changed(str)     – 'playing', 'paused', 'stopped', atau 'idle'
        track_finished()       – trek selesai diputar
        media_loaded(str)      – path file yang berhasil dimuat
        error_occurred(str)    – pesan error
        tracks_changed(list)   – daftar trek audio/subtitle berubah
    """

    # ── Sinyal Qt ──────────────────────────────────────────────
    position_changed = Signal(int)    # milidetik
    duration_changed = Signal(int)    # milidetik
    state_changed = Signal(str)       # 'playing' | 'paused' | 'stopped' | 'idle'
    track_finished = Signal()
    media_loaded = Signal(str)        # path file
    error_occurred = Signal(str)      # pesan error
    tracks_changed = Signal(list)     # list of dict, lihat _read_tracks()

    def __init__(self, wid: int | None = None, parent: QObject | None = None) -> None:
        """Buat pemutar.

        wid: nomor jendela native tempat video digambar (dari
             VideoWidget.window_id()). Kalau None, video muncul di
             jendela mpv terpisah.
        """
        super().__init__(parent)

        # ── State internal ─────────────────────────────────────
        self._state: str = "idle"
        self._duration_ms: int = 0
        self._current_path: str = ""
        self._tracks: list[dict] = []

        # ── Inisialisasi mpv ───────────────────────────────────
        # ytdl=False                → tidak perlu youtube-dl
        # input_default_bindings=False, input_vo_keyboard=False
        #                           → keyboard ditangani Qt, bukan mpv
        # input_cursor=False        → mpv tidak memproses klik mouse
        # hwdec="auto-safe"         → dekode hardware bila aman (FR-4)
        # sub_auto="fuzzy"          → muat .srt/.ass yang namanya mirip
        #                             nama file video (FR-6)
        # keep_open=False           → setelah selesai, mpv kembali idle
        options = dict(
            ytdl=False,
            input_default_bindings=False,
            input_vo_keyboard=False,
            input_cursor=False,
            cursor_autohide=False,
            hwdec="auto-safe",
            sub_auto="fuzzy",
            keep_open=False,
        )
        if wid is not None:
            options["wid"] = str(wid)
        self._mpv = mpv.MPV(**options)

        # Volume awal 100%
        self._mpv.volume = 100

        # ── Timer polling ──────────────────────────────────────
        # Setiap 100 ms, cek posisi dan durasi dari mpv,
        # lalu pancarkan sinyal ke UI.
        # Kenapa polling? Karena callback mpv berjalan di thread lain,
        # dan kita tidak boleh menyentuh widget Qt dari thread lain.
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(100)
        self._poll_timer.timeout.connect(self._poll)

    # ── Metode publik (dipanggil oleh UI) ──────────────────────

    def play(self, path: str) -> None:
        """Mulai memutar file dari `path`.

        Contoh: player.play("C:/Music/lagu.mp3")
        """
        self._current_path = path
        self._duration_ms = 0
        self._tracks = []
        self._mpv.play(path)
        self._mpv.pause = False
        self._poll_timer.start()
        self._set_state("playing")
        self.media_loaded.emit(path)

    def pause(self) -> None:
        """Jeda pemutaran."""
        if self._state == "playing":
            self._mpv.pause = True
            self._set_state("paused")

    def resume(self) -> None:
        """Lanjutkan pemutaran setelah jeda."""
        if self._state == "paused":
            self._mpv.pause = False
            self._set_state("playing")

    def toggle_pause(self) -> None:
        """Jeda ↔ lanjut. Cocok untuk tombol play/pause."""
        if self._state == "playing":
            self.pause()
        elif self._state == "paused":
            self.resume()

    def stop(self) -> None:
        """Hentikan pemutaran."""
        self._mpv.stop()
        self._poll_timer.stop()
        self._duration_ms = 0
        self._tracks = []
        self.tracks_changed.emit([])
        self._set_state("stopped")

    def seek(self, position_ms: int) -> None:
        """Loncat ke posisi tertentu (dalam milidetik).

        Contoh: player.seek(30000)  → loncat ke detik ke-30
        """
        seconds = position_ms / 1000.0
        try:
            self._mpv.seek(seconds, reference="absolute")
        except SystemError:
            pass  # mpv belum siap, abaikan

    def set_volume(self, level: int) -> None:
        """Atur volume (0–100)."""
        clamped = max(0, min(100, level))
        self._mpv.volume = clamped

    # ── Trek audio & subtitle (FR-6) ───────────────────────────

    def audio_tracks(self) -> list[dict]:
        """Daftar trek audio di file yang sedang diputar."""
        return [t for t in self._tracks if t["type"] == "audio"]

    def subtitle_tracks(self) -> list[dict]:
        """Daftar trek subtitle (tertanam maupun file eksternal)."""
        return [t for t in self._tracks if t["type"] == "sub"]

    def set_audio_track(self, track_id: int) -> None:
        """Pilih trek audio berdasarkan id dari audio_tracks()."""
        self._mpv.aid = track_id

    def set_subtitle_track(self, track_id: int | None) -> None:
        """Pilih trek subtitle. None = matikan subtitle."""
        self._mpv.sid = track_id if track_id is not None else "no"

    def load_subtitle(self, path: str) -> None:
        """Muat file subtitle eksternal (.srt/.ass) dan langsung pilih."""
        try:
            self._mpv.command("sub-add", path, "select")
        except Exception as e:
            self.error_occurred.emit(f"Gagal memuat subtitle: {e}")

    # ── Properti (membaca state) ───────────────────────────────

    @property
    def volume(self) -> int:
        """Volume saat ini (0–100)."""
        try:
            return int(self._mpv.volume or 100)
        except Exception:
            return 100

    @property
    def position_ms(self) -> int:
        """Posisi pemutaran saat ini dalam milidetik."""
        try:
            pos = self._mpv.time_pos
            return int(pos * 1000) if pos is not None else 0
        except Exception:
            return 0

    @property
    def duration_ms(self) -> int:
        """Durasi total dalam milidetik."""
        return self._duration_ms

    @property
    def state(self) -> str:
        """State saat ini: 'idle', 'playing', 'paused', 'stopped'."""
        return self._state

    @property
    def current_path(self) -> str:
        """Path file yang sedang diputar."""
        return self._current_path

    # ── Metode internal ────────────────────────────────────────

    def _set_state(self, new_state: str) -> None:
        """Ubah state dan pancarkan sinyal jika berubah."""
        if new_state != self._state:
            self._state = new_state
            self.state_changed.emit(new_state)

    def _poll(self) -> None:
        """Dipanggil setiap 100 ms oleh QTimer.

        Membaca posisi dan durasi dari mpv, lalu memancarkan sinyal.
        Juga mendeteksi apakah trek sudah selesai.
        """
        try:
            # ── Posisi ─────────────────────────────────────────
            pos = self._mpv.time_pos
            if pos is not None:
                self.position_changed.emit(int(pos * 1000))

            # ── Durasi (hanya pancarkan kalau berubah) ─────────
            dur = self._mpv.duration
            if dur is not None:
                dur_ms = int(dur * 1000)
                if dur_ms != self._duration_ms:
                    self._duration_ms = dur_ms
                    self.duration_changed.emit(dur_ms)

            # ── Daftar trek (hanya pancarkan kalau berubah) ────
            tracks = self._read_tracks()
            if tracks != self._tracks:
                self._tracks = tracks
                self.tracks_changed.emit(tracks)

            # ── Deteksi trek selesai ───────────────────────────
            # Saat mpv idle (tidak ada file) dan state kita masih
            # 'playing', berarti trek baru saja selesai.
            # Syarat _duration_ms > 0: file sempat termuat. Tanpa ini,
            # jeda singkat sebelum file termuat bisa dikira "selesai".
            idle = self._mpv.idle_active
            if idle and self._duration_ms > 0 and self._state in ("playing", "paused"):
                self._poll_timer.stop()
                self._set_state("idle")
                self.track_finished.emit()

        except Exception as e:
            # mpv belum siap atau error — abaikan polling ini
            self.error_occurred.emit(str(e))

    def _read_tracks(self) -> list[dict]:
        """Baca daftar trek dari mpv dan sederhanakan jadi dict kecil.

        Contoh hasil:
            [{"id": 1, "type": "audio", "label": "Japanese", "selected": True},
             {"id": 1, "type": "sub",   "label": "film.srt", "selected": True}]
        """
        result = []
        for t in self._mpv.track_list or []:
            if t.get("type") not in ("audio", "sub"):
                continue
            # Label: judul trek > bahasa > nama file eksternal > "Trek N"
            label = (
                t.get("title")
                or t.get("lang")
                or (Path(t["external-filename"]).name if t.get("external-filename") else None)
                or f"Trek {t['id']}"
            )
            result.append({
                "id": t["id"],
                "type": t["type"],
                "label": label,
                "selected": bool(t.get("selected")),
            })
        return result

    # ── Pembersihan ────────────────────────────────────────────

    def cleanup(self) -> None:
        """Bersihkan resource mpv. Panggil saat aplikasi ditutup."""
        self._poll_timer.stop()
        try:
            self._mpv.terminate()
        except Exception:
            pass
