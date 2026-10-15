-- NexusPlay — Skema database versi 1 (persis PRD bagian 10).
--
-- File ini dijalankan SEKALI oleh connection.migrate() saat database
-- masih kosong (PRAGMA user_version = 0). Jangan mengubah file ini
-- untuk database yang sudah ada; perubahan skema berikutnya ditambahkan
-- sebagai migrasi baru di connection.py.

CREATE TABLE artists (
  id   INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE albums (
  id         INTEGER PRIMARY KEY,
  title      TEXT NOT NULL,
  artist_id  INTEGER REFERENCES artists(id) ON DELETE SET NULL,
  year       INTEGER,
  cover_path TEXT,
  UNIQUE (title, artist_id)
);

CREATE TABLE library_folders (
  id   INTEGER PRIMARY KEY,
  path TEXT NOT NULL UNIQUE
);

CREATE TABLE media (
  id             INTEGER PRIMARY KEY,
  kind           TEXT NOT NULL CHECK (kind IN ('audio', 'video')),
  path           TEXT NOT NULL UNIQUE,
  title          TEXT NOT NULL,
  artist_id      INTEGER REFERENCES artists(id) ON DELETE SET NULL,
  album_id       INTEGER REFERENCES albums(id)  ON DELETE SET NULL,
  track_no       INTEGER,
  genre          TEXT,
  duration_ms    INTEGER,
  width          INTEGER,
  height         INTEGER,
  file_size      INTEGER,
  file_mtime     INTEGER,
  thumbnail_path TEXT,
  is_favorite    INTEGER NOT NULL DEFAULT 0 CHECK (is_favorite IN (0, 1)),
  is_pinned      INTEGER NOT NULL DEFAULT 0 CHECK (is_pinned IN (0, 1)),
  resume_ms      INTEGER NOT NULL DEFAULT 0,
  play_count     INTEGER NOT NULL DEFAULT 0,
  last_played_at TEXT,
  added_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_media_kind      ON media (kind);
CREATE INDEX idx_media_artist    ON media (artist_id);
CREATE INDEX idx_media_album     ON media (album_id, track_no);
CREATE INDEX idx_media_favorite  ON media (is_favorite) WHERE is_favorite = 1;
CREATE INDEX idx_media_last_play ON media (last_played_at);

CREATE TABLE playlists (
  id         INTEGER PRIMARY KEY,
  name       TEXT NOT NULL,
  is_pinned  INTEGER NOT NULL DEFAULT 0 CHECK (is_pinned IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE playlist_items (
  playlist_id INTEGER NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
  media_id    INTEGER NOT NULL REFERENCES media(id)     ON DELETE CASCADE,
  position    INTEGER NOT NULL,
  PRIMARY KEY (playlist_id, position)
);

CREATE TABLE play_history (
  id          INTEGER PRIMARY KEY,
  media_id    INTEGER NOT NULL REFERENCES media(id) ON DELETE CASCADE,
  played_at   TEXT NOT NULL DEFAULT (datetime('now')),
  listened_ms INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_history_played_at ON play_history (played_at);
CREATE INDEX idx_history_media     ON play_history (media_id);

CREATE TABLE settings (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- Pencarian cepat. rowid diisi sama dengan media.id oleh kode aplikasi.
-- (Tabel dibuat di M3, diisi mulai M7.)
CREATE VIRTUAL TABLE media_fts USING fts5 (title, artist, album);
