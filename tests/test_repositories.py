"""Tes untuk nexusplay/db (connection + repositories).

Semua tes memakai database ":memory:" (di RAM), jadi cepat dan tidak
menyentuh data/nexusplay.db milikmu.

Jalankan:  python -m pytest -v
"""

import sqlite3

import pytest

from nexusplay.db import repositories as repo
from nexusplay.db.connection import SCHEMA_VERSION, open_database


@pytest.fixture
def conn():
    """Database baru yang kosong untuk SETIAP tes (fixture pytest)."""
    c = open_database(":memory:")
    yield c
    c.close()


def make_media(path: str, **extra) -> dict:
    """Nilai minimal untuk upsert_media."""
    values = {
        "kind": "audio", "path": path, "title": "Lagu", "artist_id": None,
        "album_id": None, "track_no": None, "genre": None, "duration_ms": 1000,
        "width": None, "height": None, "file_size": 10, "file_mtime": 1,
    }
    values.update(extra)
    return values


# ── Migrasi ────────────────────────────────────────────────────

def test_migrate_creates_all_tables(conn):
    names = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master")}
    for table in ("artists", "albums", "library_folders", "media", "playlists",
                  "playlist_items", "play_history", "settings", "media_fts"):
        assert table in names
    assert conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION


def test_migrate_twice_is_safe(conn):
    from nexusplay.db.connection import migrate
    migrate(conn)  # tidak boleh error "table already exists"


def test_foreign_keys_are_on(conn):
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


# ── Media ──────────────────────────────────────────────────────

def test_upsert_twice_does_not_duplicate(conn):
    first = repo.upsert_media(conn, make_media("C:\\m\\a.mp3", title="Lama"))
    second = repo.upsert_media(conn, make_media("C:\\m\\a.mp3", title="Baru"))
    assert first == second
    rows = conn.execute("SELECT title FROM media").fetchall()
    assert [r["title"] for r in rows] == ["Baru"]


def test_upsert_keeps_user_data(conn):
    """Pindai ulang tidak boleh menghapus favorit/resume/play_count."""
    media_id = repo.upsert_media(conn, make_media("C:\\m\\a.mp3"))
    conn.execute(
        "UPDATE media SET is_favorite = 1, resume_ms = 5000, play_count = 7 WHERE id = ?",
        (media_id,),
    )
    repo.upsert_media(conn, make_media("C:\\m\\a.mp3", title="Diubah"))
    row = conn.execute("SELECT * FROM media WHERE id = ?", (media_id,)).fetchone()
    assert (row["is_favorite"], row["resume_ms"], row["play_count"]) == (1, 5000, 7)


def test_title_with_quote_is_safe(conn):
    """Parameter `?` membuat tanda kutip di judul tidak merusak SQL."""
    repo.upsert_media(conn, make_media("C:\\m\\q.mp3", title="Don't Stop'); DROP TABLE media;--"))
    assert conn.execute("SELECT COUNT(*) FROM media").fetchone()[0] == 1


def test_count_media(conn):
    repo.upsert_media(conn, make_media("C:\\m\\a.mp3"))
    repo.upsert_media(conn, make_media("C:\\m\\b.mkv", kind="video"))
    repo.upsert_media(conn, make_media("C:\\m\\c.mkv", kind="video"))
    assert repo.count_media(conn) == {"audio": 1, "video": 2}


def test_delete_cascades_to_history(conn):
    media_id = repo.upsert_media(conn, make_media("C:\\m\\a.mp3"))
    conn.execute("INSERT INTO play_history (media_id) VALUES (?)", (media_id,))
    repo.delete_media_by_paths(conn, ["C:\\m\\a.mp3"])
    assert conn.execute("SELECT COUNT(*) FROM play_history").fetchone()[0] == 0


# ── Artis & album ──────────────────────────────────────────────

def test_get_or_create_artist(conn):
    a = repo.get_or_create_artist(conn, "Coldplay")
    b = repo.get_or_create_artist(conn, "Coldplay")
    assert a == b
    assert repo.get_or_create_artist(conn, None) is None
    assert repo.get_or_create_artist(conn, "") is None


def test_album_without_artist_not_duplicated(conn):
    """Jebakan NULL: UNIQUE (title, artist_id) tidak menolak NULL ganda."""
    a = repo.get_or_create_album(conn, "Tanpa Artis", None)
    b = repo.get_or_create_album(conn, "Tanpa Artis", None)
    assert a == b
    assert conn.execute("SELECT COUNT(*) FROM albums").fetchone()[0] == 1


def test_same_album_title_different_artists(conn):
    x = repo.get_or_create_artist(conn, "X")
    y = repo.get_or_create_artist(conn, "Y")
    assert repo.get_or_create_album(conn, "Greatest Hits", x) != \
           repo.get_or_create_album(conn, "Greatest Hits", y)


def test_delete_orphans(conn):
    artist = repo.get_or_create_artist(conn, "Hilang")
    repo.get_or_create_album(conn, "Album Hilang", artist)
    kept_artist = repo.get_or_create_artist(conn, "Ada")
    kept_album = repo.get_or_create_album(conn, "Album Ada", kept_artist)
    repo.upsert_media(conn, make_media("C:\\m\\a.mp3", artist_id=kept_artist, album_id=kept_album))

    repo.delete_orphans(conn)

    assert [r["name"] for r in conn.execute("SELECT name FROM artists")] == ["Ada"]
    assert [r["title"] for r in conn.execute("SELECT title FROM albums")] == ["Album Ada"]


# ── Folder library ─────────────────────────────────────────────

def test_add_folder_twice(conn, tmp_path):
    repo.add_library_folder(conn, tmp_path)
    repo.add_library_folder(conn, str(tmp_path) + "\\")   # bentuk lain, folder sama
    assert repo.list_library_folders(conn) == [str(tmp_path.resolve())]


def test_remove_folder_deletes_only_its_media(conn, tmp_path):
    music = tmp_path / "Music"
    music_old = tmp_path / "Music Lama"     # nama mirip, awalan sama!
    music.mkdir()
    music_old.mkdir()
    repo.add_library_folder(conn, music)
    repo.add_library_folder(conn, music_old)
    repo.upsert_media(conn, make_media(str(music / "a.mp3")))
    repo.upsert_media(conn, make_media(str(music_old / "b.mp3")))

    removed = repo.remove_library_folder(conn, music)

    assert removed == 1
    paths = [r["path"] for r in conn.execute("SELECT path FROM media")]
    assert paths == [str(music_old / "b.mp3")]


def test_remove_subfolder_keeps_files_of_parent_folder(conn, tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    repo.add_library_folder(conn, tmp_path)
    repo.add_library_folder(conn, sub)
    repo.upsert_media(conn, make_media(str(sub / "a.mp3")))

    assert repo.remove_library_folder(conn, sub) == 0
    assert conn.execute("SELECT COUNT(*) FROM media").fetchone()[0] == 1


def test_check_constraint_rejects_bad_kind(conn):
    with pytest.raises(sqlite3.IntegrityError):
        repo.upsert_media(conn, make_media("C:\\m\\x.txt", kind="dokumen"))
