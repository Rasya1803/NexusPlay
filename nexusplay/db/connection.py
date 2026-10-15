"""NexusPlay — Koneksi database dan migrasi skema.

Dua fungsi utama:
- `connect()`  membuka file database dan mengatur PRAGMA.
- `migrate()`  memastikan skema database versi terbaru.

Konsep penting:
- **PRAGMA:** perintah khusus SQLite untuk mengatur perilaku database.
  * `foreign_keys = ON` → SQLite benar-benar menegakkan REFERENCES dan
    ON DELETE CASCADE. Secara bawaan ini MATI dan harus dinyalakan di
    SETIAP koneksi baru.
  * `journal_mode = WAL` → pembaca (UI) dan penulis (pemindai) bisa
    berjalan bersamaan tanpa saling menunggu lama.
  * `user_version` → angka bebas di header file database. Kita pakai
    sebagai "nomor versi skema".
- **Satu koneksi per thread:** objek koneksi sqlite3 tidak boleh dipakai
  bersama oleh dua thread. Thread pemindai membuka koneksinya sendiri.
"""

import sqlite3
from pathlib import Path

# ── Lokasi file ────────────────────────────────────────────────
_PACKAGE_DIR = Path(__file__).resolve().parent          # nexusplay/db/
PROJECT_ROOT = _PACKAGE_DIR.parent.parent               # folder proyek
DATA_DIR = PROJECT_ROOT / "data"                        # tidak di-commit
DB_PATH = DATA_DIR / "nexusplay.db"
COVERS_DIR = DATA_DIR / "covers"
SCHEMA_PATH = _PACKAGE_DIR / "schema.sql"

# Versi skema yang diharapkan kode ini.
SCHEMA_VERSION = 1


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    """Buka koneksi database dan atur PRAGMA.

    path: lokasi file database. None = `data/nexusplay.db`.
          ":memory:" = database sementara di RAM (untuk tes).
    """
    if path is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        path = DB_PATH

    conn = sqlite3.connect(str(path))

    # Baris hasil query bisa diakses seperti dict: row["title"]
    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    # Kalau database sedang dikunci thread lain, tunggu maks 5 detik
    # sebelum menyerah (daripada langsung error "database is locked").
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    """Bawa skema database ke versi SCHEMA_VERSION.

    Cara kerja:
        user_version 0 → database baru/kosong → jalankan schema.sql → jadi 1.
        Kelak, kalau skema berubah, tambahkan langkah `if version < 2: ...`
        di bawah. Data lama tidak hilang karena kita hanya MENAMBAH langkah.
    """
    version = conn.execute("PRAGMA user_version").fetchone()[0]

    if version < 1:
        sql = SCHEMA_PATH.read_text(encoding="utf-8")
        # BEGIN ... COMMIT membuat seluruh skema dibuat dalam satu transaksi:
        # kalau ada satu perintah gagal, tidak ada tabel setengah jadi.
        conn.executescript(
            "BEGIN;\n" + sql + "\nPRAGMA user_version = 1;\nCOMMIT;"
        )
        version = 1

    # Contoh migrasi masa depan:
    # if version < 2:
    #     conn.executescript("BEGIN; ALTER TABLE ...; PRAGMA user_version = 2; COMMIT;")
    #     version = 2


def open_database(path: str | Path | None = None) -> sqlite3.Connection:
    """Jalan pintas: connect() lalu migrate(). Ini yang dipakai aplikasi."""
    conn = connect(path)
    migrate(conn)
    return conn
