"""Unit test untuk parser lirik tersinkron `.lrc` (M8 — FR-62)."""

from pathlib import Path

from nexusplay.library.lyrics import (
    LyricLine,
    active_line_index,
    find_lrc_file,
    load_lyrics_for_media,
    parse_lrc,
)


def test_parse_lrc_standard_two_and_three_digit_fractions():
    lrc_text = """
    [ti:Judul Lagu]
    [ar:Nama Artis]
    [00:05.50]Baris pertama
    [00:12.345]Baris kedua
    [01:00]Baris ketiga tanpa pecahan
    """
    lines = parse_lrc(lrc_text)
    assert lines == [
        LyricLine(time_ms=5_500, text="Baris pertama"),
        LyricLine(time_ms=12_345, text="Baris kedua"),
        LyricLine(time_ms=60_000, text="Baris ketiga tanpa pecahan"),
    ]


def test_parse_lrc_multiple_timestamps_and_sorting():
    lrc_text = """
    [00:10.00][00:30.00]Bagian Reff
    [00:20.00]Bait di tengah
    """
    lines = parse_lrc(lrc_text)
    assert lines == [
        LyricLine(time_ms=10_000, text="Bagian Reff"),
        LyricLine(time_ms=20_000, text="Bait di tengah"),
        LyricLine(time_ms=30_000, text="Bagian Reff"),
    ]


def test_parse_lrc_offset_positive_and_negative_clamped():
    lrc_pos = """
    [offset:+500]
    [00:01.00]Halo
    """
    assert parse_lrc(lrc_pos) == [LyricLine(time_ms=1_500, text="Halo")]

    # Offset negatif yang melebihi waktu awal harus dijepit (clamped) ke 0 ms
    lrc_neg = """
    [offset:-2000]
    [00:01.00]Awal
    [00:05.00]Kedua
    """
    assert parse_lrc(lrc_neg) == [
        LyricLine(time_ms=0, text="Awal"),
        LyricLine(time_ms=3_000, text="Kedua"),
    ]


def test_active_line_index_progression():
    lines = [
        LyricLine(time_ms=2_000, text="Satu"),
        LyricLine(time_ms=5_000, text="Dua"),
        LyricLine(time_ms=9_000, text="Tiga"),
    ]

    assert active_line_index([], 3_000) == -1
    assert active_line_index(lines, 0) == -1
    assert active_line_index(lines, 1_999) == -1
    assert active_line_index(lines, 2_000) == 0
    assert active_line_index(lines, 4_999) == 0
    assert active_line_index(lines, 5_000) == 1
    assert active_line_index(lines, 8_500) == 1
    assert active_line_index(lines, 9_000) == 2
    assert active_line_index(lines, 25_000) == 2


def test_find_and_load_lrc_companion_file(tmp_path: Path):
    audio_file = tmp_path / "laguku.mp3"
    lrc_file = tmp_path / "laguku.lrc"

    audio_file.write_bytes(b"dummy")
    lrc_file.write_text("[00:03.20]Selamat pagi\n[00:07.80]Dunia\n", encoding="utf-8")

    assert find_lrc_file(audio_file) == lrc_file
    loaded = load_lyrics_for_media(audio_file)
    assert loaded == [
        LyricLine(time_ms=3_200, text="Selamat pagi"),
        LyricLine(time_ms=7_800, text="Dunia"),
    ]

