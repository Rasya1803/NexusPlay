"""Tes untuk nexusplay/library/scanner.py.

File audio uji dibuat sendiri dengan modul `wave` bawaan Python (1 detik
hening), lalu diberi tag ID3 dengan mutagen. Tidak perlu file lagu asli.

Jalankan:  python -m pytest -v
"""

import os
import time
import wave
from pathlib import Path

import pytest
from mutagen.id3 import TALB, TIT2, TPE1, TPE2, TRCK
from mutagen.wave import WAVE

from nexusplay.db import repositories as repo
from nexusplay.db.connection import open_database
from nexusplay.library.scanner import scan_folder


@pytest.fixture
def conn():
    c = open_database(":memory:")
    yield c
    c.close()


def make_wav(path: Path, title=None, artist=None, album=None, albumartist=None, track=None) -> Path:
    """Buat file WAV 1 detik, opsional dengan tag."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\x00\x00" * 8000)
    frames = [(TIT2, title), (TPE1, artist), (TALB, album), (TPE2, albumartist), (TRCK, track)]
    if any(value for _, value in frames):
        f = WAVE(path)
        f.add_tags()
        for frame_cls, value in frames:
            if value:
                f.tags.add(frame_cls(encoding=3, text=value))
        f.save()
    return path


def media_count(conn) -> int:
    return conn.execute("SELECT COUNT(*) FROM media").fetchone()[0]


# ── Dasar ──────────────────────────────────────────────────────

def test_scan_adds_only_media_files(conn, tmp_path):
    make_wav(tmp_path / "a.wav")
    make_wav(tmp_path / "sub" / "dalam" / "b.wav")   # rekursif
    (tmp_path / "catatan.txt").write_text("bukan media")
    (tmp_path / "film.mkv").write_bytes(b"")         # video, tanpa prober

    result = scan_folder(conn, str(tmp_path))

    assert result.added == 3
    assert repo.count_media(conn) == {"audio": 2, "video": 1}


def test_tags_are_read(conn, tmp_path):
    make_wav(tmp_path / "x.wav", title="Yellow", artist="Coldplay", album="Parachutes", track="5/10")
    scan_folder(conn, str(tmp_path))

    row = conn.execute(
        "SELECT m.title, m.track_no, ar.name AS artist, al.title AS album "
        "FROM media m "
        "JOIN artists ar ON ar.id = m.artist_id "
        "JOIN albums  al ON al.id = m.album_id"
    ).fetchone()
    assert (row["title"], row["track_no"], row["artist"], row["album"]) == \
           ("Yellow", 5, "Coldplay", "Parachutes")


def test_title_falls_back_to_filename(conn, tmp_path):
    make_wav(tmp_path / "Lagu Tanpa Tag.wav")
    scan_folder(conn, str(tmp_path))
    assert conn.execute("SELECT title FROM media").fetchone()["title"] == "Lagu Tanpa Tag"


def test_compilation_is_one_album(conn, tmp_path):
    """Album artist sama → satu album, walau artis lagunya berbeda."""
    make_wav(tmp_path / "1.wav", title="A", artist="Artis 1", album="Hits 2026", albumartist="Various")
    make_wav(tmp_path / "2.wav", title="B", artist="Artis 2", album="Hits 2026", albumartist="Various")
    scan_folder(conn, str(tmp_path))

    assert conn.execute("SELECT COUNT(*) FROM albums").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM artists").fetchone()[0] == 3


# ── Inkremental (FR-24) ────────────────────────────────────────

def test_rescan_does_not_duplicate(conn, tmp_path):
    for i in range(3):
        make_wav(tmp_path / f"{i}.wav")
    scan_folder(conn, str(tmp_path))

    second = scan_folder(conn, str(tmp_path))

    assert (second.added, second.updated, second.unchanged) == (0, 0, 3)
    assert media_count(conn) == 3


def test_changed_file_is_updated(conn, tmp_path):
    path = make_wav(tmp_path / "a.wav", title="Lama")
    scan_folder(conn, str(tmp_path))

    make_wav(path, title="Baru")
    later = time.time() + 10
    os.utime(path, (later, later))   # pastikan mtime berubah
    result = scan_folder(conn, str(tmp_path))

    assert result.updated == 1
    assert conn.execute("SELECT title FROM media").fetchone()["title"] == "Baru"


def test_deleted_file_is_removed(conn, tmp_path):
    make_wav(tmp_path / "tetap.wav")
    gone = make_wav(tmp_path / "hilang.wav", artist="Artis Hilang", album="Album Hilang")
    scan_folder(conn, str(tmp_path))

    gone.unlink()
    result = scan_folder(conn, str(tmp_path))

    assert result.removed == 1
    assert media_count(conn) == 1
    # Artis & album yang tidak dipakai lagi ikut dibersihkan
    assert conn.execute("SELECT COUNT(*) FROM artists").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM albums").fetchone()[0] == 0


def test_missing_folder_keeps_data(conn, tmp_path):
    """Flashdisk dicabut → folder tidak ada → data JANGAN dihapus."""
    folder = tmp_path / "usb"
    make_wav(folder / "a.wav")
    scan_folder(conn, str(folder))

    folder.rename(tmp_path / "usb_dicabut")
    result = scan_folder(conn, str(folder))

    assert result.missing_folders == [str(folder.resolve())]
    assert media_count(conn) == 1


def test_stopped_scan_does_not_delete(conn, tmp_path):
    make_wav(tmp_path / "a.wav")
    scan_folder(conn, str(tmp_path))

    result = scan_folder(conn, str(tmp_path), should_stop=lambda: True)

    assert result.stopped
    assert media_count(conn) == 1


# ── Ketahanan ──────────────────────────────────────────────────

def test_corrupt_file_is_skipped(conn, tmp_path):
    make_wav(tmp_path / "bagus.wav")
    (tmp_path / "rusak.flac").write_bytes(os.urandom(2048))

    result = scan_folder(conn, str(tmp_path))

    assert result.added == 1
    assert len(result.errors) == 1
    assert "rusak.flac" in result.errors[0]


def test_progress_is_reported(conn, tmp_path):
    for i in range(45):
        make_wav(tmp_path / f"{i:02}.wav")
    calls = []
    scan_folder(conn, str(tmp_path), on_progress=lambda done, total: calls.append((done, total)))

    assert calls[0] == (0, 45)
    assert calls[-1] == (45, 45)


def test_thousand_files(conn, tmp_path):
    """Kriteria M3: 1.000 file terindeks, pindai ulang tidak menggandakan."""
    for i in range(1000):
        make_wav(tmp_path / f"album{i // 100}" / f"{i:04}.wav",
                 title=f"Lagu {i}", artist=f"Artis {i % 20}", album=f"Album {i // 100}")

    start = time.perf_counter()
    first = scan_folder(conn, str(tmp_path))
    first_secs = time.perf_counter() - start

    start = time.perf_counter()
    second = scan_folder(conn, str(tmp_path))
    second_secs = time.perf_counter() - start

    print(f"\npindai pertama: {first_secs:.2f} s, pindai ulang: {second_secs:.2f} s")
    assert first.added == 1000
    assert second.unchanged == 1000
    assert media_count(conn) == 1000
    assert second_secs < first_secs
