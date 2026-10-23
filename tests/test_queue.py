"""Tes untuk nexusplay/core/queue.py (PlayQueue).

Menguji seluruh logika:
- Navigasi next/prev
- Mode repeat: off, all, one
- Mode shuffle: menjaga urutan asli saat dinonaktifkan
- Fitur "Putar Berikutnya" (play_next) dan "Tambah ke Antrean" (append)
- Hapus item dan susun ulang posisi (move)
"""

import pytest
from PySide6.QtCore import QCoreApplication

from nexusplay.core.queue import PlayQueue


@pytest.fixture(scope="session")
def qapp():
    """QCoreApplication fixture untuk pengujian sinyal Qt."""
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


def sample_tracks(n: int = 5) -> list[dict]:
    return [{"id": i, "title": f"Song {i}", "artist": f"Artist {i}", "path": f"C:/m/{i}.mp3"} for i in range(1, n + 1)]


def test_queue_initial_state(qapp):
    q = PlayQueue()
    assert q.is_empty()
    assert q.count() == 0
    assert q.current_track is None
    assert q.shuffle is False
    assert q.repeat_mode == "off"


def test_set_tracks_and_navigation(qapp):
    q = PlayQueue()
    tracks = sample_tracks(3)
    q.set_tracks(tracks, start_index=0)

    assert q.count() == 3
    assert q.current_track["title"] == "Song 1"

    # Next ke Song 2
    nxt = q.next()
    assert nxt["title"] == "Song 2"

    # Next ke Song 3
    nxt = q.next()
    assert nxt["title"] == "Song 3"

    # Next saat di akhir (repeat off) -> None dan selesai
    ended_called = []
    q.queue_ended.connect(lambda: ended_called.append(True))
    assert q.next() is None
    assert len(ended_called) == 1

    # Prev kembali ke Song 2
    prv = q.prev()
    assert prv["title"] == "Song 2"


def test_repeat_mode_all(qapp):
    q = PlayQueue()
    tracks = sample_tracks(2)
    q.set_tracks(tracks, start_index=0)
    q.set_repeat_mode("all")

    assert q.current_track["title"] == "Song 1"
    assert q.next()["title"] == "Song 2"
    # Di akhir -> kembali ke Song 1
    assert q.next()["title"] == "Song 1"


def test_repeat_mode_one(qapp):
    q = PlayQueue()
    tracks = sample_tracks(3)
    q.set_tracks(tracks, start_index=1)
    q.set_repeat_mode("one")

    assert q.current_track["title"] == "Song 2"
    assert q.next()["title"] == "Song 2"
    assert q.next()["title"] == "Song 2"


def test_play_next(qapp):
    q = PlayQueue()
    tracks = sample_tracks(3)
    q.set_tracks(tracks, start_index=0)  # Song 1 aktif

    bonus = {"id": 99, "title": "Bonus Track", "path": "C:/m/bonus.mp3"}
    q.play_next(bonus)

    assert q.count() == 4
    # Lagu berikutnya setelah Song 1 harus Bonus Track
    assert q.next()["title"] == "Bonus Track"
    # Setelah itu baru Song 2
    assert q.next()["title"] == "Song 2"


def test_append_and_remove(qapp):
    q = PlayQueue()
    tracks = sample_tracks(3)
    q.set_tracks(tracks, start_index=0)

    extra = {"id": 88, "title": "Extra Track", "path": "C:/m/extra.mp3"}
    q.append(extra)

    assert q.count() == 4
    all_t = q.all_tracks()
    assert all_t[-1]["title"] == "Extra Track"

    # Hapus item terakhir
    q.remove_at(3)
    assert q.count() == 3
    assert q.all_tracks()[-1]["title"] == "Song 3"


def test_move_reorder(qapp):
    q = PlayQueue()
    tracks = sample_tracks(3)  # Song 1 (idx 0), Song 2 (idx 1), Song 3 (idx 2)
    q.set_tracks(tracks, start_index=0)

    # Pindahkan Song 3 dari indeks 2 ke 1
    q.move(2, 1)
    order = [t["title"] for t in q.all_tracks()]
    assert order == ["Song 1", "Song 3", "Song 2"]
    # Lagu aktif tetap Song 1
    assert q.current_track["title"] == "Song 1"


def test_shuffle_toggle_and_restore(qapp):
    q = PlayQueue()
    tracks = sample_tracks(10)
    q.set_tracks(tracks, start_index=3)  # Song 4 aktif

    # Aktifkan shuffle
    q.set_shuffle(True)
    assert q.shuffle is True
    # Lagu yang sedang aktif tetap Song 4
    assert q.current_track["title"] == "Song 4"

    # Nonaktifkan shuffle -> urutan kembali normal 1..10
    q.set_shuffle(False)
    assert q.shuffle is False
    assert [t["title"] for t in q.all_tracks()] == [f"Song {i}" for i in range(1, 11)]
    assert q.current_track["title"] == "Song 4"


def test_cycle_repeat_mode(qapp):
    q = PlayQueue()
    assert q.repeat_mode == "off"
    assert q.cycle_repeat_mode() == "all"
    assert q.cycle_repeat_mode() == "one"
    assert q.cycle_repeat_mode() == "off"
