"""NexusPlay — Membaca metadata file audio dan video.

- Audio: tag (judul, artis, album, dll.) dibaca dengan `mutagen` (FR-21).
- Video: judul dari nama file; durasi & resolusi dibaca dengan mpv
  tanpa jendela dan tanpa suara (FR-22).

Modul ini TIDAK menyentuh database. Ia hanya mengubah "file di disk"
menjadi objek `MediaInfo`. Pemindai yang menyimpannya ke database.

Konsep penting:
- **dataclass:** cara singkat membuat kelas yang isinya hanya data.
  Python otomatis membuatkan __init__, __repr__, dan __eq__.
- **Exception sendiri (MetadataError):** supaya pemindai bisa membedakan
  "file ini rusak, lewati saja" dari bug lain di kode.
"""

import re
from base64 import b64decode
from dataclasses import dataclass
from pathlib import Path

import mutagen
from mutagen.flac import Picture
from mutagen.id3 import ID3

# ── Ekstensi yang didukung (FR-1, FR-2) ────────────────────────
AUDIO_EXTS = {".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wav"}
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".webm", ".mov"}


class MetadataError(Exception):
    """File tidak bisa dibaca (rusak atau format tidak dikenali)."""


@dataclass
class MediaInfo:
    """Hasil pembacaan satu file media."""

    kind: str                       # "audio" atau "video"
    path: str
    title: str
    file_size: int
    file_mtime: int                 # waktu terakhir diubah (detik)
    artist: str | None = None
    album: str | None = None
    album_artist: str | None = None  # untuk album kompilasi
    year: int | None = None
    track_no: int | None = None
    genre: str | None = None
    duration_ms: int | None = None
    width: int | None = None
    height: int | None = None


def media_kind(path: Path) -> str | None:
    """'audio', 'video', atau None kalau ekstensinya tidak didukung."""
    ext = path.suffix.lower()
    if ext in AUDIO_EXTS:
        return "audio"
    if ext in VIDEO_EXTS:
        return "video"
    return None


# ── Bantuan kecil ──────────────────────────────────────────────

# Untuk file yang tag ID3-nya tidak diterjemahkan mode easy (contoh: WAV),
# kita petakan sendiri nama "easy" → kode frame ID3.
_ID3_FRAMES = {
    "title": "TIT2",
    "artist": "TPE1",
    "album": "TALB",
    "albumartist": "TPE2",
    "date": "TDRC",
    "tracknumber": "TRCK",
    "genre": "TCON",
}


def _first(tags, key: str) -> str | None:
    """Ambil nilai pertama sebuah tag sebagai teks, atau None.

    Tag di mutagen selalu berupa list, misalnya {"artist": ["Coldplay"]},
    karena satu lagu bisa punya beberapa artis.
    """
    try:
        if isinstance(tags, ID3):
            frame = tags.get(_ID3_FRAMES.get(key, ""))
            values = frame.text if frame is not None else None
        else:
            values = tags.get(key)
    except Exception:
        return None
    if not values:
        return None
    text = str(values[0]).strip()
    return text or None


def _parse_int(text: str | None) -> int | None:
    """Ambil angka pertama dari teks: "3/12" → 3, "2019-05-01" → 2019."""
    if not text:
        return None
    match = re.search(r"\d+", text)
    return int(match.group()) if match else None


def _file_stat(path: Path) -> tuple[int, int]:
    """(ukuran byte, mtime dalam detik bulat)."""
    st = path.stat()
    return st.st_size, int(st.st_mtime)


# ── Audio ──────────────────────────────────────────────────────

def read_audio(path: Path) -> MediaInfo:
    """Baca tag dan durasi file audio.

    Kalau tag judul kosong, judul diambil dari nama file (tanpa ekstensi).
    Melempar MetadataError kalau file rusak / tidak dikenali.
    """
    size, mtime = _file_stat(path)
    try:
        # easy=True → nama tag seragam ("title", "artist", ...) untuk
        # MP3, M4A, FLAC, OGG, dll., walau format aslinya berbeda-beda.
        audio = mutagen.File(path, easy=True)
    except Exception as e:
        raise MetadataError(f"{path.name}: {e}") from e
    if audio is None:
        raise MetadataError(f"{path.name}: format audio tidak dikenali")

    tags = audio.tags or {}
    length = getattr(audio.info, "length", None)

    return MediaInfo(
        kind="audio",
        path=str(path),
        title=_first(tags, "title") or path.stem,
        file_size=size,
        file_mtime=mtime,
        artist=_first(tags, "artist"),
        album=_first(tags, "album"),
        album_artist=_first(tags, "albumartist"),
        year=_parse_int(_first(tags, "date")),
        track_no=_parse_int(_first(tags, "tracknumber")),
        genre=_first(tags, "genre"),
        duration_ms=int(length * 1000) if length else None,
    )


def read_cover(path: Path) -> tuple[bytes, str] | None:
    """Ambil gambar cover yang tertanam di file audio.

    Mengembalikan (data_gambar, ekstensi) misalnya (b"...", ".jpg"),
    atau None kalau tidak ada cover. Tidak pernah melempar error:
    cover itu bonus, bukan wajib.

    Tiap format menyimpan cover dengan cara berbeda:
    - FLAC        → audio.pictures
    - MP3/WAV     → frame ID3 "APIC"
    - M4A/MP4     → tag "covr"
    - OGG/Opus    → tag "metadata_block_picture" (base64)
    """
    try:
        audio = mutagen.File(path)  # easy=False supaya tag gambar terbaca
        if audio is None:
            return None

        # FLAC
        pictures = getattr(audio, "pictures", None)
        if pictures:
            return pictures[0].data, _ext_from_mime(pictures[0].mime)

        tags = audio.tags
        if not tags:
            return None

        # MP3 / WAV (ID3)
        if hasattr(tags, "getall"):
            apic = tags.getall("APIC")
            if apic:
                return apic[0].data, _ext_from_mime(apic[0].mime)

        # M4A / MP4
        covr = tags.get("covr") if hasattr(tags, "get") else None
        if covr:
            cover = covr[0]
            # imageformat 14 = PNG, selain itu JPEG
            ext = ".png" if getattr(cover, "imageformat", None) == 14 else ".jpg"
            return bytes(cover), ext

        # OGG Vorbis / Opus
        blocks = tags.get("metadata_block_picture") if hasattr(tags, "get") else None
        if blocks:
            pic = Picture(b64decode(blocks[0]))
            return pic.data, _ext_from_mime(pic.mime)
    except Exception:
        return None
    return None


def _ext_from_mime(mime: str | None) -> str:
    return ".png" if mime and "png" in mime.lower() else ".jpg"


# ── Video ──────────────────────────────────────────────────────

class VideoProber:
    """Membaca durasi & resolusi video dengan mpv tanpa jendela.

    Satu objek dipakai untuk BANYAK file (membuat instance mpv itu mahal).
    Panggil `close()` setelah selesai, atau pakai sebagai `with`:

        with VideoProber() as prober:
            prober.probe(Path("film.mkv"))   # → (durasi_ms, lebar, tinggi)
    """

    def __init__(self, timeout: float = 5.0) -> None:
        # Import di dalam fungsi supaya modul ini tetap bisa dipakai
        # (misalnya oleh tes audio) walau libmpv tidak ada.
        # player.py sudah mengatur PATH agar libmpv-2.dll ditemukan.
        from nexusplay.core.player import mpv

        self._mpv_module = mpv
        self._timeout = timeout
        # vo/ao "null" → tidak ada jendela dan tidak ada suara.
        # pause=True   → cukup buka file, tidak perlu memutar.
        self._mpv = mpv.MPV(
            vo="null", ao="null", pause=True, idle=True,
            ytdl=False, config=False, load_scripts=False,
            sub_auto="no", hwdec="no",
        )

    def probe(self, path: Path) -> tuple[int | None, int | None, int | None]:
        """(durasi_ms, lebar, tinggi) — nilai None kalau tidak diketahui.

        Melempar MetadataError kalau mpv gagal membuka file.
        """
        mpv = self._mpv_module

        def done(evt):
            # Dipanggil untuk tiap event file-loaded / end-file.
            # Kembalikan nilai "truthy" untuk berhenti menunggu.
            if evt.event_id.value == mpv.MpvEventID.END_FILE:
                # end-file dengan alasan selain ERROR (misalnya file
                # sebelumnya diganti) diabaikan.
                return "error" if evt.data.reason == mpv.MpvEventEndFile.ERROR else None
            return "loaded"

        try:
            # prepare_and_wait_for_event: pasang "telinga" DULU, baru buka
            # file. Kalau terbalik, event bisa terlewat sebelum kita sempat
            # mendengarkan.
            with self._mpv.prepare_and_wait_for_event(
                "file-loaded", "end-file", cond=done, timeout=self._timeout
            ) as result:
                self._mpv.loadfile(str(path))
            status = result.result()
        except Exception as e:
            raise MetadataError(f"{path.name}: mpv gagal membuka ({e!r})") from e

        if status != "loaded":
            raise MetadataError(f"{path.name}: file video rusak atau tidak didukung")

        duration = self._mpv.duration
        width = height = None
        for track in self._mpv.track_list or []:
            if track.get("type") == "video" and not track.get("albumart"):
                width = track.get("demux-w")
                height = track.get("demux-h")
                break
        return (int(duration * 1000) if duration else None), width, height

    def close(self) -> None:
        try:
            self._mpv.terminate()
        except Exception:
            pass

    def __enter__(self) -> "VideoProber":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def read_video(path: Path, prober: VideoProber | None = None) -> MediaInfo:
    """Baca info video. Judul = nama file tanpa ekstensi.

    prober None → durasi/resolusi dibiarkan kosong (dipakai di tes).
    """
    size, mtime = _file_stat(path)
    duration_ms = width = height = None
    if prober is not None:
        duration_ms, width, height = prober.probe(path)
    return MediaInfo(
        kind="video",
        path=str(path),
        title=path.stem,
        file_size=size,
        file_mtime=mtime,
        duration_ms=duration_ms,
        width=width,
        height=height,
    )
