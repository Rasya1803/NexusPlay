"""NexusPlay — Fungsi-fungsi query database.

SEMUA SQL aplikasi tinggal di file ini. UI dan pemindai tidak menulis SQL
sendiri; mereka memanggil fungsi di sini.

Aturan di file ini:
1. Semua nilai dari luar dimasukkan lewat parameter (`?` atau `:nama`),
   TIDAK PERNAH disambung ke string SQL. Ini mencegah SQL injection
   dan juga masalah tanda kutip di judul seperti "Don't Stop Me Now".
2. Fungsi yang dipakai pemindai secara massal (upsert, delete, dll.)
   TIDAK memanggil commit(). Pemindai yang memutuskan kapan commit
   (tiap 200 file), karena commit satu per satu sangat lambat.
3. Fungsi untuk satu aksi pengguna (tambah/hapus folder) langsung commit.
"""

import os
import sqlite3
from pathlib import Path


# ── Bantuan path ───────────────────────────────────────────────

def normalize_folder(path: str | Path) -> str:
    """Ubah path folder jadi bentuk baku (absolut) supaya tidak tersimpan ganda.

    Contoh: "music" dan "C:/Users/RASYA/music/" → "C:\\Users\\RASYA\\music"
    """
    return str(Path(path).resolve())


def _prefix(folder: str) -> str:
    """Awalan path untuk semua file DI DALAM folder.

    Kenapa perlu separator di akhir? Supaya folder "C:\\Music" tidak ikut
    mencocokkan "C:\\Music Lama\\lagu.mp3".
    Untuk root drive ("D:\\"), separator sudah ada, jadi tidak ditambah lagi.
    """
    return folder if folder.endswith(os.sep) else folder + os.sep


# ── Folder library (FR-20) ─────────────────────────────────────

def add_library_folder(conn: sqlite3.Connection, path: str | Path) -> str:
    """Tambahkan folder ke library. Kalau sudah ada, diabaikan.

    Mengembalikan path yang sudah dinormalisasi.
    """
    folder = normalize_folder(path)
    # INSERT OR IGNORE: kalau path sudah ada (kolom UNIQUE), tidak error,
    # cukup dilewati.
    conn.execute("INSERT OR IGNORE INTO library_folders (path) VALUES (?)", (folder,))
    conn.commit()
    return folder


def list_library_folders(conn: sqlite3.Connection) -> list[str]:
    """Semua folder library, urut abjad."""
    rows = conn.execute("SELECT path FROM library_folders ORDER BY path").fetchall()
    return [row["path"] for row in rows]


def remove_library_folder(conn: sqlite3.Connection, path: str | Path) -> int:
    """Hapus folder dari library BESERTA media di dalamnya.

    Pengecualian: file yang juga berada di folder library lain (misalnya
    folder induk juga terdaftar) tidak ikut dihapus.
    Mengembalikan jumlah media yang terhapus.
    """
    folder = normalize_folder(path)
    conn.execute("DELETE FROM library_folders WHERE path = ?", (folder,))

    prefix = _prefix(folder)
    other_prefixes = [_prefix(p) for p in list_library_folders(conn)]

    # substr(path, 1, N) = awalan → "path diawali awalan".
    # Kita tidak memakai LIKE karena tanda % dan _ di nama folder
    # akan dianggap wildcard oleh LIKE.
    rows = conn.execute(
        "SELECT id, path FROM media WHERE substr(path, 1, ?) = ?",
        (len(prefix), prefix),
    ).fetchall()
    ids = [
        (row["id"],)
        for row in rows
        if not any(row["path"].startswith(p) for p in other_prefixes)
    ]
    conn.executemany("DELETE FROM media WHERE id = ?", ids)
    delete_orphans(conn)
    conn.commit()
    return len(ids)


# ── Artis & album ──────────────────────────────────────────────

def get_or_create_artist(conn: sqlite3.Connection, name: str | None) -> int | None:
    """Kembalikan id artis bernama `name`; buat baru kalau belum ada.

    Nama kosong/None → None (media tanpa artis).
    """
    if not name:
        return None
    conn.execute("INSERT OR IGNORE INTO artists (name) VALUES (?)", (name,))
    row = conn.execute("SELECT id FROM artists WHERE name = ?", (name,)).fetchone()
    return row["id"]


def get_or_create_album(
    conn: sqlite3.Connection,
    title: str | None,
    artist_id: int | None,
    year: int | None = None,
) -> int | None:
    """Kembalikan id album (judul + artis); buat baru kalau belum ada.

    JEBAKAN SQL: tabel albums punya UNIQUE (title, artist_id), tapi di SQLite
    dua nilai NULL dianggap BERBEDA. Jadi album tanpa artis bisa tersimpan
    berkali-kali kalau kita hanya mengandalkan INSERT OR IGNORE.
    Solusinya: cari dulu dengan `artist_id IS ?`. Operator IS menganggap
    NULL sama dengan NULL, sedangkan `=` tidak (NULL = NULL hasilnya NULL).
    """
    if not title:
        return None
    row = conn.execute(
        "SELECT id, year FROM albums WHERE title = ? AND artist_id IS ?",
        (title, artist_id),
    ).fetchone()
    if row is not None:
        # Lengkapi tahun kalau sebelumnya belum diketahui
        if year and not row["year"]:
            conn.execute("UPDATE albums SET year = ? WHERE id = ?", (year, row["id"]))
        return row["id"]

    cur = conn.execute(
        "INSERT INTO albums (title, artist_id, year) VALUES (?, ?, ?)",
        (title, artist_id, year),
    )
    return cur.lastrowid


def album_has_cover(conn: sqlite3.Connection, album_id: int) -> bool:
    """True kalau album sudah punya file cover."""
    row = conn.execute("SELECT cover_path FROM albums WHERE id = ?", (album_id,)).fetchone()
    return bool(row and row["cover_path"])


def set_album_cover(conn: sqlite3.Connection, album_id: int, cover_path: str) -> None:
    """Simpan lokasi file cover album."""
    conn.execute("UPDATE albums SET cover_path = ? WHERE id = ?", (cover_path, album_id))


# ── Media ──────────────────────────────────────────────────────

def get_file_index(conn: sqlite3.Connection, folder: str) -> dict[str, tuple[int, int]]:
    """Peta {path: (file_size, file_mtime)} untuk semua media di dalam folder.

    Dipakai pemindai untuk tahu file mana yang baru, berubah, atau hilang.
    """
    prefix = _prefix(folder)
    rows = conn.execute(
        "SELECT path, file_size, file_mtime FROM media WHERE substr(path, 1, ?) = ?",
        (len(prefix), prefix),
    ).fetchall()
    return {row["path"]: (row["file_size"], row["file_mtime"]) for row in rows}


# Kolom yang diisi/diperbarui oleh pemindai. Kolom milik pengguna
# (is_favorite, is_pinned, resume_ms, play_count, last_played_at, added_at)
# sengaja TIDAK ada di sini, supaya tidak tertimpa saat pindai ulang.
_SCANNED_COLUMNS = (
    "kind", "path", "title", "artist_id", "album_id", "track_no", "genre",
    "duration_ms", "width", "height", "file_size", "file_mtime",
)

# SQL disusun SEKALI dari daftar nama kolom tetap di atas (bukan dari
# input pengguna), jadi aman. Nilai-nilainya tetap lewat parameter :nama.
_UPSERT_SQL = (
    f"INSERT INTO media ({', '.join(_SCANNED_COLUMNS)}) "
    f"VALUES ({', '.join(':' + c for c in _SCANNED_COLUMNS)}) "
    "ON CONFLICT (path) DO UPDATE SET "
    + ", ".join(f"{c} = excluded.{c}" for c in _SCANNED_COLUMNS if c != "path")
    + " RETURNING id"
)


def upsert_media(conn: sqlite3.Connection, values: dict) -> int:
    """Masukkan media baru, atau perbarui kalau path-nya sudah ada.

    "Upsert" = UPdate + inSERT. Karena kolom `path` UNIQUE, file yang sama
    TIDAK mungkin tersimpan dua kali, berapa kali pun dipindai.
    `excluded.kolom` artinya "nilai yang tadinya mau di-INSERT".

    values: dict berisi semua kunci di _SCANNED_COLUMNS.
    Mengembalikan id media.
    """
    row = conn.execute(_UPSERT_SQL, values).fetchone()
    return row["id"]


def delete_media_by_paths(conn: sqlite3.Connection, paths: list[str]) -> None:
    """Hapus media berdasarkan path (untuk file yang hilang dari disk).

    Riwayat dan item playlist ikut terhapus otomatis karena ON DELETE CASCADE.
    """
    conn.executemany("DELETE FROM media WHERE path = ?", [(p,) for p in paths])


def delete_orphans(conn: sqlite3.Connection) -> None:
    """Hapus album dan artis yang sudah tidak dipakai media mana pun.

    Catatan `IS NOT NULL` di subquery: kalau daftar NOT IN berisi NULL,
    hasil `x NOT IN (...)` jadi NULL (bukan TRUE) dan TIDAK ADA baris
    yang terhapus. Jebakan klasik SQL!
    """
    conn.execute(
        "DELETE FROM albums WHERE id NOT IN "
        "(SELECT album_id FROM media WHERE album_id IS NOT NULL)"
    )
    conn.execute(
        "DELETE FROM artists "
        "WHERE id NOT IN (SELECT artist_id FROM media  WHERE artist_id IS NOT NULL) "
        "  AND id NOT IN (SELECT artist_id FROM albums WHERE artist_id IS NOT NULL)"
    )


def count_media(conn: sqlite3.Connection) -> dict[str, int]:
    """Jumlah media per jenis, contoh: {"audio": 1234, "video": 56}."""
    counts = {"audio": 0, "video": 0}
    for row in conn.execute("SELECT kind, COUNT(*) AS n FROM media GROUP BY kind"):
        counts[row["kind"]] = row["n"]
    return counts


# ── Query Pembacaan Data UI (M4) ───────────────────────────────

def list_media(
    conn: sqlite3.Connection,
    kind: str | None = None,
    sort_by: str = "title",
) -> list[sqlite3.Row]:
    """Ambil daftar media dengan info artis dan album untuk UI.

    kind: 'audio', 'video', atau None (semua).
    """
    sql = """
        SELECT
            m.id, m.kind, m.path, m.title, m.track_no, m.genre,
            m.duration_ms, m.width, m.height, m.file_size,
            m.is_favorite, m.resume_ms, m.play_count,
            ar.name AS artist,
            al.title AS album,
            al.cover_path AS cover_path
        FROM media m
        LEFT JOIN artists ar ON ar.id = m.artist_id
        LEFT JOIN albums  al ON al.id = m.album_id
    """
    params: list = []
    if kind:
        sql += " WHERE m.kind = ?"
        params.append(kind)

    if sort_by == "track_no":
        sql += " ORDER BY al.title COLLATE NOCASE, m.track_no ASC, m.title COLLATE NOCASE"
    elif sort_by == "artist":
        sql += " ORDER BY ar.name COLLATE NOCASE, al.title COLLATE NOCASE, m.track_no ASC, m.title COLLATE NOCASE"
    else:
        sql += " ORDER BY m.title COLLATE NOCASE"

    return conn.execute(sql, params).fetchall()


def get_media(conn: sqlite3.Connection, media_id: int) -> sqlite3.Row | None:
    """Ambil satu media berdasarkan id dengan info artis dan album."""
    sql = """
        SELECT
            m.id, m.kind, m.path, m.title, m.track_no, m.genre,
            m.duration_ms, m.width, m.height, m.file_size,
            m.is_favorite, m.resume_ms, m.play_count,
            ar.name AS artist,
            al.title AS album,
            al.cover_path AS cover_path
        FROM media m
        LEFT JOIN artists ar ON ar.id = m.artist_id
        LEFT JOIN albums  al ON al.id = m.album_id
        WHERE m.id = ?
    """
    return conn.execute(sql, (media_id,)).fetchone()


def list_albums(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Daftar album beserta nama artis dan jumlah lagu untuk UI."""
    sql = """
        SELECT
            al.id,
            al.title,
            al.year,
            al.cover_path,
            ar.name AS artist,
            COUNT(m.id) AS track_count,
            COALESCE(SUM(m.duration_ms), 0) AS total_duration_ms
        FROM albums al
        LEFT JOIN artists ar ON ar.id = al.artist_id
        LEFT JOIN media m ON m.album_id = al.id
        GROUP BY al.id
        ORDER BY al.title COLLATE NOCASE
    """
    return conn.execute(sql).fetchall()


def list_artists(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Daftar artis beserta jumlah lagu dan album untuk UI."""
    sql = """
        SELECT
            ar.id,
            ar.name,
            COUNT(DISTINCT m.id) AS track_count,
            COUNT(DISTINCT m.album_id) AS album_count
        FROM artists ar
        LEFT JOIN media m ON m.artist_id = ar.id
        GROUP BY ar.id
        ORDER BY ar.name COLLATE NOCASE
    """
    return conn.execute(sql).fetchall()


# ── Playlist (M5) ──────────────────────────────────────────────

def create_playlist(conn: sqlite3.Connection, name: str) -> int:
    """Buat playlist baru dan kembalikan id-nya."""
    cur = conn.execute("INSERT INTO playlists (name) VALUES (?)", (name.strip(),))
    conn.commit()
    return cur.lastrowid


def list_playlists(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Daftar playlist dengan jumlah trek di dalamnya, urut pin lalu abjad."""
    sql = """
        SELECT
            p.id,
            p.name,
            p.is_pinned,
            p.created_at,
            COUNT(pi.media_id) AS track_count
        FROM playlists p
        LEFT JOIN playlist_items pi ON pi.playlist_id = p.id
        GROUP BY p.id
        ORDER BY p.is_pinned DESC, p.name COLLATE NOCASE ASC
    """
    return conn.execute(sql).fetchall()


def get_playlist(conn: sqlite3.Connection, playlist_id: int) -> sqlite3.Row | None:
    """Ambil info satu playlist berdasarkan id."""
    return conn.execute("SELECT * FROM playlists WHERE id = ?", (playlist_id,)).fetchone()


def rename_playlist(conn: sqlite3.Connection, playlist_id: int, new_name: str) -> None:
    """Ubah nama playlist."""
    conn.execute("UPDATE playlists SET name = ? WHERE id = ?", (new_name.strip(), playlist_id))
    conn.commit()


def delete_playlist(conn: sqlite3.Connection, playlist_id: int) -> None:
    """Hapus playlist beserta isinya (karena ON DELETE CASCADE)."""
    conn.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
    conn.commit()


def toggle_playlist_pin(conn: sqlite3.Connection, playlist_id: int) -> bool:
    """Sematkan (pin) atau lepas pin playlist."""
    row = conn.execute("SELECT is_pinned FROM playlists WHERE id = ?", (playlist_id,)).fetchone()
    if row is None:
        return False
    new_pinned = 0 if row["is_pinned"] else 1
    conn.execute("UPDATE playlists SET is_pinned = ? WHERE id = ?", (new_pinned, playlist_id))
    conn.commit()
    return bool(new_pinned)


def add_media_to_playlist(conn: sqlite3.Connection, playlist_id: int, media_id: int) -> int:
    """Tambahkan media ke akhir playlist. Mengembalikan nomor posisi."""
    row = conn.execute(
        "SELECT COALESCE(MAX(position), -1) + 1 AS next_pos FROM playlist_items WHERE playlist_id = ?",
        (playlist_id,),
    ).fetchone()
    next_pos = row["next_pos"]
    conn.execute(
        "INSERT INTO playlist_items (playlist_id, media_id, position) VALUES (?, ?, ?)",
        (playlist_id, media_id, next_pos),
    )
    conn.commit()
    return next_pos


def remove_from_playlist(conn: sqlite3.Connection, playlist_id: int, position: int) -> None:
    """Hapus satu lagu dari playlist di `position` tertentu dan rapatkan urutan sisanya."""
    conn.execute(
        "DELETE FROM playlist_items WHERE playlist_id = ? AND position = ?",
        (playlist_id, position),
    )
    conn.execute(
        "UPDATE playlist_items SET position = position - 1 WHERE playlist_id = ? AND position > ?",
        (playlist_id, position),
    )
    conn.commit()


def get_playlist_items(conn: sqlite3.Connection, playlist_id: int) -> list[sqlite3.Row]:
    """Daftar semua lagu di dalam playlist sesuai urutan posisi (0, 1, 2, ...)."""
    sql = """
        SELECT
            pi.position,
            m.id, m.kind, m.path, m.title, m.track_no, m.genre,
            m.duration_ms, m.width, m.height, m.file_size,
            m.is_favorite,
            ar.name AS artist,
            al.title AS album,
            al.cover_path AS cover_path
        FROM playlist_items pi
        JOIN media m ON m.id = pi.media_id
        LEFT JOIN artists ar ON ar.id = m.artist_id
        LEFT JOIN albums  al ON al.id = m.album_id
        WHERE pi.playlist_id = ?
        ORDER BY pi.position ASC
    """
    return conn.execute(sql, (playlist_id,)).fetchall()


def reorder_playlist_items(conn: sqlite3.Connection, playlist_id: int, media_ids: list[int]) -> None:
    """Susun ulang posisi seluruh item di dalam playlist (drag & drop)."""
    conn.execute("DELETE FROM playlist_items WHERE playlist_id = ?", (playlist_id,))
    rows = [(playlist_id, m_id, idx) for idx, m_id in enumerate(media_ids)]
    conn.executemany(
        "INSERT INTO playlist_items (playlist_id, media_id, position) VALUES (?, ?, ?)",
        rows,
    )
    conn.commit()


