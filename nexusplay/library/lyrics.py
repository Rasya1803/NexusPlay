"""NexusPlay — Parser lirik tersinkron `.lrc` & pembaca lirik (FR-62).

Konsep yang dipelajari di file ini:
1. **Regular Expression (`re`)**: Pola pencocokan teks untuk mengekstrak angka
   menit, detik, dan milidetik dari cap waktu seperti `[01:23.45]`.
2. **Dataclass (`@dataclass`)**: Kelas ringan penyimpan data baris lirik
   (`time_ms` dan `text`).
3. **Pencarian baris aktif**: Menentukan baris lirik mana yang sedang dinyanyikan
   pada posisi waktu `position_ms` tertentu.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import mutagen

# Pola regex untuk cap waktu LRC:
# [mm:ss.xx] atau [mm:ss.xxx] atau [mm:ss:xx] atau [mm:ss]
_TIMESTAMP_RE = re.compile(r"\[(\d{1,3}):(\d{2})(?:[.:](\d{1,3}))?\]")

# Pola regex untuk tag offset di header LRC: [offset:+500] atau [offset:-200]
_OFFSET_RE = re.compile(r"^\s*\[offset:\s*([+-]?\d+)\s*\]\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class LyricLine:
    """Satu baris lirik beserta waktu mulai dalam milidetik."""

    time_ms: int
    text: str


def _fraction_to_ms(frac_str: str | None) -> int:
    """Ubah bagian pecahan detik pada tag LRC menjadi milidetik.

    Contoh:
    - None    -> 0 ms
    - "5"     -> 500 ms (persepuluh detik)
    - "45"    -> 450 ms (perseratus detik / centiseconds)
    - "456"   -> 456 ms (milidetik)
    """
    if not frac_str:
        return 0
    if len(frac_str) == 1:
        return int(frac_str) * 100
    if len(frac_str) == 2:
        return int(frac_str) * 10
    return int(frac_str[:3])


def parse_lrc(content: str) -> list[LyricLine]:
    """Urai isi teks format `.lrc` menjadi daftar `LyricLine` urut waktu.

    Mendukung:
    - Cap waktu standar `[mm:ss.xx]` dan `[mm:ss.xxx]`
    - Beberapa cap waktu dalam satu baris (`[00:10.00][00:30.00]Reff`)
    - Tag `[offset:+/-ms]` untuk menggeser waktu seluruh lirik
    - Mengabaikan tag metadata seperti `[ar:Artis]`, `[ti:Judul]`
    """
    if not content:
        return []

    offset_ms = 0
    raw_entries: list[tuple[int, str]] = []

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        offset_match = _OFFSET_RE.match(line)
        if offset_match:
            offset_ms = int(offset_match.group(1))
            continue

        matches = list(_TIMESTAMP_RE.finditer(line))
        if not matches:
            continue

        # Teks lirik berada setelah cap waktu terakhir pada baris tersebut
        lyric_text = line[matches[-1].end():].strip()

        for m in matches:
            minutes = int(m.group(1))
            seconds = int(m.group(2))
            frac_ms = _fraction_to_ms(m.group(3))
            base_ms = minutes * 60_000 + seconds * 1_000 + frac_ms
            raw_entries.append((base_ms, lyric_text))

    result = [
        LyricLine(time_ms=max(0, base_ms + offset_ms), text=text)
        for base_ms, text in raw_entries
    ]
    result.sort(key=lambda item: item.time_ms)
    return result


def active_line_index(lines: list[LyricLine], position_ms: int) -> int:
    """Cari indeks baris lirik yang sedang aktif pada posisi `position_ms`.

    Mengembalikan:
    - Indeks `i` terakhir yang memenuhi `lines[i].time_ms <= position_ms`.
    - `-1` bila `lines` kosong atau lagu belum mencapai waktu baris pertama.
    """
    if not lines or position_ms < 0:
        return -1

    active_idx = -1
    for idx, line in enumerate(lines):
        if line.time_ms <= position_ms:
            active_idx = idx
        else:
            break
    return active_idx


def read_lrc_file(lrc_path: str | Path) -> list[LyricLine]:
    """Baca file `.lrc` dari disk dengan fallback encoding yang aman."""
    path = Path(lrc_path)
    if not path.is_file():
        return []

    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = path.read_text(encoding=encoding)
            return parse_lrc(text)
        except UnicodeDecodeError:
            continue
        except OSError:
            return []
    return []


def find_lrc_file(media_path: str | Path) -> Path | None:
    """Cari file `.lrc` pendamping di sebelah file media (contoh: `lagu.mp3` -> `lagu.lrc`)."""
    p = Path(media_path)
    candidate = p.with_suffix(".lrc")
    if candidate.is_file():
        return candidate
    candidate_upper = p.with_suffix(".LRC")
    if candidate_upper.is_file():
        return candidate_upper
    return None


def _extract_embedded_lyrics_text(media_path: Path) -> str:
    """Coba ambil teks lirik yang tertanam di dalam tag file audio via mutagen."""
    try:
        audio = mutagen.File(media_path)
    except Exception:
        return ""

    if audio is None or not getattr(audio, "tags", None):
        return ""

    tags = audio.tags

    # 1. ID3 (MP3): tag USLT (Unsynchronised lyrics/text)
    for key in list(tags.keys()):
        if key.startswith("USLT"):
            frame = tags[key]
            text = getattr(frame, "text", "")
            if isinstance(text, str) and text.strip():
                return text

    # 2. Vorbis/FLAC/Opus & MP4 (M4A)
    for tag_key in ("lyrics", "LYRICS", "unsyncedlyrics", "UNSYNCEDLYRICS", "\xa9lyr"):
        if tag_key in tags:
            val = tags[tag_key]
            if isinstance(val, list) and val:
                return str(val[0])
            if isinstance(val, str):
                return val

    return ""


def load_lyrics_for_media(media_path: str | Path) -> list[LyricLine]:
    """Muat lirik untuk sebuah file media (prioritas: file `.lrc` lokal, lalu tag tertanam)."""
    if not media_path:
        return []

    p = Path(media_path)
    lrc_file = find_lrc_file(p)
    if lrc_file is not None:
        lines = read_lrc_file(lrc_file)
        if lines:
            return lines

    if p.is_file():
        embedded = _extract_embedded_lyrics_text(p)
        if embedded:
            parsed = parse_lrc(embedded)
            if parsed:
                return parsed

    return []

