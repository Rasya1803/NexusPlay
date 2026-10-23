"""NexusPlay — Logika antrean pemutaran (PlayQueue).

Mengelola:
- Daftar antrean lagu yang sedang dan akan diputar.
- Indeks lagu yang sedang aktif.
- Navigasi maju (next) dan mundur (prev).
- Mode pengacakan (shuffle): mengacak urutan pemutaran tanpa merusak urutan asli.
- Mode pengulangan (repeat):
    - 'off': berhenti saat antrean habis.
    - 'all': mengulang seluruh antrean dari awal saat lagu terakhir selesai.
    - 'one': terus mengulang satu lagu yang sedang aktif.
- Penambahan lagu: "Putar Berikutnya" (play_next) dan "Tambah ke Antrean" (append).
"""

import random
from typing import Literal

from PySide6.QtCore import QObject, Signal

RepeatMode = Literal["off", "all", "one"]


class PlayQueue(QObject):
    """Pengelola antrean pemutaran NexusPlay."""

    # Sinyal Qt
    track_changed = Signal(dict)       # Lagu aktif berubah (mengirim dict metadata lagu)
    queue_updated = Signal()           # Daftar antrean berubah (tambah/hapus/susun ulang)
    shuffle_changed = Signal(bool)     # Status shuffle berubah (True / False)
    repeat_changed = Signal(str)       # Mode repeat berubah ('off', 'all', 'one')
    queue_ended = Signal()             # Antrean selesai dan tidak diulang

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._original_tracks: list[dict] = []
        self._play_order: list[int] = []       # Indeks ke _original_tracks
        self._current_index: int = -1          # Posisi di dalam _play_order
        self._shuffle: bool = False
        self._repeat_mode: RepeatMode = "off"

    # ── Properti Status ────────────────────────────────────────

    @property
    def shuffle(self) -> bool:
        """Apakah mode acak (shuffle) aktif."""
        return self._shuffle

    @property
    def repeat_mode(self) -> RepeatMode:
        """Mode pengulangan saat ini: 'off', 'all', atau 'one'."""
        return self._repeat_mode

    @property
    def current_track(self) -> dict | None:
        """Lagu yang sedang aktif saat ini, atau None jika antrean kosong."""
        if 0 <= self._current_index < len(self._play_order):
            orig_idx = self._play_order[self._current_index]
            if 0 <= orig_idx < len(self._original_tracks):
                return self._original_tracks[orig_idx]
        return None

    @property
    def current_index(self) -> int:
        """Indeks posisi antrean saat ini."""
        return self._current_index

    def is_empty(self) -> bool:
        """True jika antrean tidak memiliki lagu."""
        return len(self._play_order) == 0

    def count(self) -> int:
        """Total jumlah lagu dalam antrean."""
        return len(self._play_order)

    def all_tracks(self) -> list[dict]:
        """Daftar seluruh lagu sesuai urutan pemutaran saat ini."""
        return [self._original_tracks[i] for i in self._play_order if 0 <= i < len(self._original_tracks)]

    def upcoming_tracks(self) -> list[dict]:
        """Daftar lagu yang akan diputar setelah lagu aktif saat ini."""
        if self._current_index < 0:
            return self.all_tracks()
        indices = self._play_order[self._current_index + 1:]
        return [self._original_tracks[i] for i in indices if 0 <= i < len(self._original_tracks)]

    # ── Pengaturan Antrean ─────────────────────────────────────

    def set_tracks(self, tracks: list[dict], start_index: int = 0) -> None:
        """Ganti seluruh isi antrean dengan daftar baru dan mulai dari `start_index`."""
        self._original_tracks = list(tracks)
        total = len(self._original_tracks)
        if total == 0:
            self._play_order = []
            self._current_index = -1
            self.queue_updated.emit()
            return

        clamped_start = max(0, min(start_index, total - 1))

        if self._shuffle:
            # Pertahankan lagu yang dipilih di posisi awal, lalu acak sisanya
            remaining = [i for i in range(total) if i != clamped_start]
            random.shuffle(remaining)
            self._play_order = [clamped_start] + remaining
            self._current_index = 0
        else:
            self._play_order = list(range(total))
            self._current_index = clamped_start

        self.queue_updated.emit()
        curr = self.current_track
        if curr is not None:
            self.track_changed.emit(curr)

    def play_next(self, track: dict) -> None:
        """Sisipkan lagu agar diputar tepat setelah lagu yang sedang aktif."""
        self._original_tracks.append(track)
        new_orig_idx = len(self._original_tracks) - 1

        insert_pos = self._current_index + 1 if self._current_index >= 0 else 0
        self._play_order.insert(insert_pos, new_orig_idx)

        # Jika sebelumnya antrean kosong, langsung jadikan lagu ini aktif
        if self._current_index == -1:
            self._current_index = 0
            self.track_changed.emit(track)

        self.queue_updated.emit()

    def append(self, track: dict) -> None:
        """Tambahkan lagu ke paling akhir antrean."""
        self._original_tracks.append(track)
        new_orig_idx = len(self._original_tracks) - 1
        self._play_order.append(new_orig_idx)

        # Jika sebelumnya antrean kosong, jadikan lagu ini aktif
        if self._current_index == -1:
            self._current_index = 0
            self.track_changed.emit(track)

        self.queue_updated.emit()

    def remove_at(self, play_order_index: int) -> None:
        """Hapus lagu dari antrean berdasarkan indeks urutan pemutaran."""
        if not (0 <= play_order_index < len(self._play_order)):
            return

        del self._play_order[play_order_index]

        # Sesuaikan current_index jika lagu yang dihapus sebelum atau pas di indeks aktif
        if len(self._play_order) == 0:
            self._current_index = -1
            self._original_tracks = []
        elif play_order_index < self._current_index:
            self._current_index -= 1
        elif play_order_index == self._current_index:
            # Jika lagu aktif yang dihapus, batasi indeks dan putar lagu di posisi tersebut
            if self._current_index >= len(self._play_order):
                self._current_index = len(self._play_order) - 1
            curr = self.current_track
            if curr:
                self.track_changed.emit(curr)

        self.queue_updated.emit()

    def move(self, from_index: int, to_index: int) -> None:
        """Pindahkan posisi lagu dalam antrean (drag & drop reorder)."""
        if not (0 <= from_index < len(self._play_order) and 0 <= to_index < len(self._play_order)):
            return

        # Simpan indeks asli lagu yang sedang aktif
        active_orig = self._play_order[self._current_index] if 0 <= self._current_index < len(self._play_order) else None

        item = self._play_order.pop(from_index)
        self._play_order.insert(to_index, item)

        # Perbarui posisi current_index agar tetap menunjuk ke lagu aktif yang sama
        if active_orig is not None and active_orig in self._play_order:
            self._current_index = self._play_order.index(active_orig)

        self.queue_updated.emit()

    def clear(self) -> None:
        """Kosongkan seluruh antrean."""
        self._original_tracks.clear()
        self._play_order.clear()
        self._current_index = -1
        self.queue_updated.emit()

    # ── Navigasi Lagu (Next / Prev) ────────────────────────────

    def next(self) -> dict | None:
        """Lanjut ke lagu berikutnya sesuai mode repeat & shuffle.

        Mengembalikan dict lagu berikutnya, atau None jika antrean selesai.
        """
        if self.is_empty():
            return None

        # Mode repeat 'one': putar ulang lagu yang sama
        if self._repeat_mode == "one":
            curr = self.current_track
            if curr:
                self.track_changed.emit(curr)
            return curr

        # Masih ada lagu berikutnya di dalam antrean
        if self._current_index + 1 < len(self._play_order):
            self._current_index += 1
            curr = self.current_track
            if curr:
                self.track_changed.emit(curr)
            return curr

        # Sudah sampai di akhir antrean:
        if self._repeat_mode == "all":
            # Ulang dari awal antrean
            if self._shuffle and len(self._play_order) > 1:
                # Acak ulang untuk putaran berikutnya
                random.shuffle(self._play_order)
            self._current_index = 0
            curr = self.current_track
            if curr:
                self.track_changed.emit(curr)
            return curr

        # Repeat 'off': antrean habis
        self.queue_ended.emit()
        return None

    def prev(self) -> dict | None:
        """Kembali ke lagu sebelumnya dalam urutan pemutaran.

        Mengembalikan dict lagu sebelumnya, atau lagu pertama jika sudah di awal.
        """
        if self.is_empty():
            return None

        if self._current_index > 0:
            self._current_index -= 1
        else:
            self._current_index = 0

        curr = self.current_track
        if curr:
            self.track_changed.emit(curr)
        return curr

    def jump_to(self, play_order_index: int) -> dict | None:
        """Langsung loncat memutar lagu di indeks tertentu dalam antrean."""
        if 0 <= play_order_index < len(self._play_order):
            self._current_index = play_order_index
            curr = self.current_track
            if curr:
                self.track_changed.emit(curr)
            return curr
        return None

    # ── Kontrol Shuffle & Repeat ───────────────────────────────

    def set_shuffle(self, enabled: bool) -> None:
        """Aktifkan atau nonaktifkan mode acak (shuffle)."""
        if self._shuffle == enabled:
            return

        self._shuffle = enabled
        active_orig = self._play_order[self._current_index] if 0 <= self._current_index < len(self._play_order) else None

        if self._shuffle:
            # Acak sisa lagu setelah lagu aktif saat ini
            if len(self._play_order) > 1 and active_orig is not None:
                remaining = [i for i in self._play_order if i != active_orig]
                random.shuffle(remaining)
                self._play_order = [active_orig] + remaining
                self._current_index = 0
            else:
                random.shuffle(self._play_order)
        else:
            # Kembalikan ke urutan asli (0, 1, 2, ...)
            self._play_order = list(range(len(self._original_tracks)))
            if active_orig is not None and 0 <= active_orig < len(self._play_order):
                self._current_index = active_orig

        self.shuffle_changed.emit(self._shuffle)
        self.queue_updated.emit()

    def toggle_shuffle(self) -> bool:
        """Alihkan (toggle) status shuffle antara On dan Off."""
        self.set_shuffle(not self._shuffle)
        return self._shuffle

    def set_repeat_mode(self, mode: RepeatMode) -> None:
        """Atur mode pengulangan: 'off', 'all', atau 'one'."""
        if mode in ("off", "all", "one") and self._repeat_mode != mode:
            self._repeat_mode = mode
            self.repeat_changed.emit(self._repeat_mode)

    def cycle_repeat_mode(self) -> RepeatMode:
        """Siklus mode repeat: off -> all -> one -> off."""
        cycle = {"off": "all", "all": "one", "one": "off"}
        new_mode: RepeatMode = cycle.get(self._repeat_mode, "off")
        self.set_repeat_mode(new_mode)
        return self._repeat_mode
