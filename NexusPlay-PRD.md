# PRD: NexusPlay — Media Player Musik & Video dengan Database

|                     |                                                                                    |
| ------------------- | ---------------------------------------------------------------------------------- |
| **Versi**           | 0.1 (draft)                                                                        |
| **Pemilik**         | Pais                                                                               |
| **Tanggal**         | 12 Oktober 2026                                                                    |
| **Platform target** | Desktop (Windows 10/11 dulu; Linux/macOS menyusul)                                 |
| **Bahasa & stack**  | Python 3.12+, PySide6 (Qt 6), libmpv, SQLite                                       |
| **Dev environment** | Antigravity (agent-assisted IDE)                                                   |
| **Tujuan utama**    | Membuat media player pribadi yang modern, sambil belajar Python lewat projek nyata |

---

## 1. Ringkasan

NexusPlay adalah pemutar media desktop yang memutar **musik dan video** dari satu aplikasi, dengan **library berbasis database SQLite**: koleksi otomatis terindeks, bisa dicari, dibuat playlist, dilanjutkan dari posisi terakhir, dan punya statistik dengar/tonton.

Pembeda dari player biasa:

1. **Satu library untuk musik dan video**, bukan dua aplikasi terpisah.
2. **Desain modern**: tema gelap, warna aksen yang mengikuti cover album, mini-player.
3. **Offline-first dan privat**: semua data di komputer sendiri, tanpa akun, tanpa telemetri.
4. **Fitur gaya streaming** (antrean pintar, lirik tersinkron, statistik, sleep timer) untuk file lokal.

## 2. Masalah & Tujuan

**Masalah:**

- Player klasik kuat di format tapi tampilannya kuno dan library-nya lemah.
- Aplikasi streaming punya UX bagus tapi tidak untuk file lokal milik sendiri.
- Musik dan video lokal biasanya dikelola terpisah, tanpa pencarian, riwayat, atau resume yang rapi.

**Tujuan produk:**

1. Memutar hampir semua format audio/video umum dengan mulus.
2. Library cepat dan bisa dicari walau berisi ribuan file.
3. UI yang enak dipakai setiap hari.

**Tujuan belajar (sama pentingnya):** 4. Pais paham struktur proyek, SQL dasar, dan cara kerja player. Tidak ada kode yang tidak bisa dijelaskan sendiri.

**Bukan tujuan (non-goals) untuk v1:**

- Layanan streaming online, akun, sinkronisasi cloud.
- Mengunduh video/musik dari internet.
- Mobile app dan web app.
- Editor video/audio.
- Pengelolaan DRM atau konten berhak cipta pihak ketiga.

## 3. Pengguna & Skenario

Pengguna utama: Pais, pemula Python, punya koleksi musik dan video lokal, memakai PC Windows.

Skenario inti:

- Menambah folder musik, lalu seluruh lagu muncul rapi per artis/album dalam hitungan detik.
- Menonton film, menutup aplikasi di tengah, membukanya lagi, dan lanjut dari menit terakhir.
- Mengetik "coldplay" di pencarian dan langsung melihat lagu, album, dan video terkait.
- Mendengarkan musik sambil bekerja dengan mini-player yang selalu di atas.

## 4. Riset: Tren Fitur Terbaru → Keputusan untuk NexusPlay

Fitur dipilih dari tren player/streaming yang aktif di 2026, lalu disaring supaya realistis untuk satu pengembang pemula.

| Tren yang terlihat                                                                                                                 | Sumber                                                                   | Keputusan untuk NexusPlay                                    |
| ---------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ | ------------------------------------------------------------ |
| Antrean yang bisa dikontrol penuh (shuffle, smart shuffle, repeat, sleep timer, rekomendasi lanjutan)                              | Spotify                                                                  | Queue panel + shuffle cerdas lokal + sleep timer (M5, M9)    |
| Statistik dengar ("Listening stats", ringkasan 4 minggu)                                                                           | Spotify                                                                  | Halaman Statistik dari tabel `play_history` (M7)             |
| Pin item favorit di atas library                                                                                                   | Apple Music (iOS 26)                                                     | Pin artis/album/playlist (M7)                                |
| Transisi antar lagu cerdas: crossfade pintar, AutoMix beat-matching berbasis ML                                                    | Apple Music                                                              | Gapless + crossfade sederhana (M9). AutoMix = fase 2 (riset) |
| Lirik tersinkron, terjemahan, dan pelafalan lirik                                                                                  | Spotify, Apple Music                                                     | Lirik tersinkron lokal `.lrc` (M8). Terjemahan = fase 2      |
| Playlist dibuat lewat perintah bahasa natural dengan AI                                                                            | Spotify, Apple Music                                                     | Fase 2, opsional dan opt-in                                  |
| Subtitle AI offline (Whisper lokal) di player video, sudah didemokan untuk VLC di CES 2025 dan ada di beberapa player pihak ketiga | VLC, LLPlayer, dll.                                                      | Fase 2: generate subtitle offline dengan `faster-whisper`    |
| Picture-in-picture, mini-player, casting, kontrol kecepatan, volume boost                                                          | Ulasan player Windows 2026                                               | PiP/mini-player (M6), speed (M9). Casting = fase 2           |
| Dekode hardware, dukungan 4K/HEVC/MKV, A-B repeat, equalizer, subtitle finder                                                      | MPC-HC, PotPlayer, GOM                                                   | Dekode hardware via mpv, A-B loop, EQ (M2, M9)               |
| Library media bergaya aplikasi (thumbnail, indeks audio/video, playlist) di VLC 4.0                                                | VLC 4.0 (rencana; belum terkonfirmasi rilis stabil dari hasil riset ini) | Library SQLite sendiri (M3)                                  |
| UI selaras desain Windows 11 (Fluent/transparan)                                                                                   | Ulasan player Windows 2026                                               | Gaya modern gelap, sudut membulat, efek halus (bagian 8)     |

> Catatan: tren di atas dikumpulkan dari artikel dan halaman paket per Oktober 2026. Sebelum membangun fitur fase 2, cek ulang status terbarunya.

## 5. Kebutuhan Fungsional

Prioritas: **Must** = wajib untuk MVP, **Should** = v1.0, **Could** = bila sempat, **Fase 2** = riset/eksperimen setelah v1.0.

### 5.1 Pemutaran

| ID    | Kebutuhan                                                                          | Prioritas |
| ----- | ---------------------------------------------------------------------------------- | --------- |
| FR-1  | Putar file audio (MP3, FLAC, AAC/M4A, OGG/Opus, WAV)                               | Must      |
| FR-2  | Putar file video (MP4, MKV, AVI, WebM, MOV) dengan layar video tertanam di jendela | Must      |
| FR-3  | Kontrol dasar: play/pause, seek, volume, mute, next/prev                           | Must      |
| FR-4  | Dekode hardware otomatis bila tersedia                                             | Should    |
| FR-5  | Kecepatan putar 0.5x–2x                                                            | Should    |
| FR-6  | Subtitle eksternal (`.srt`, `.ass`) otomatis terdeteksi, pilih trek audio/subtitle | Should    |
| FR-7  | A-B loop                                                                           | Could     |
| FR-8  | Gapless playback antar lagu                                                        | Should    |
| FR-9  | Crossfade (durasi 0–12 detik, bisa dimatikan)                                      | Could     |
| FR-10 | Equalizer 10 band + preset                                                         | Could     |
| FR-11 | Fullscreen, kontrol video menyembunyikan diri saat diam                            | Must      |

### 5.2 Library & Database

| ID    | Kebutuhan                                                                                   | Prioritas |
| ----- | ------------------------------------------------------------------------------------------- | --------- |
| FR-20 | Tambah/hapus folder library; pindai rekursif                                                | Must      |
| FR-21 | Baca metadata audio (judul, artis, album, track, genre, durasi, cover) via `mutagen`        | Must      |
| FR-22 | Video: judul dari nama file, durasi, resolusi, thumbnail                                    | Should    |
| FR-23 | Pemindaian berjalan di latar belakang, UI tetap responsif, ada indikator progres            | Must      |
| FR-24 | Pindai ulang inkremental: hanya file baru/berubah/hilang (berdasar `path`, `mtime`, `size`) | Should    |
| FR-25 | Tampilan library: Lagu, Album, Artis, Video, Favorit                                        | Must      |
| FR-26 | Pencarian cepat lintas judul/artis/album (SQLite FTS5)                                      | Should    |
| FR-27 | Favorit (hati) dan pin                                                                      | Should    |
| FR-28 | Resume: ingat posisi terakhir tiap video (dan podcast/audio panjang)                        | Must      |
| FR-29 | Riwayat putar + jumlah putar                                                                | Should    |
| FR-30 | Statistik: top lagu/artis 4 minggu terakhir, total waktu dengar                             | Could     |

### 5.3 Playlist & Antrean

| ID    | Kebutuhan                                                                              | Prioritas |
| ----- | -------------------------------------------------------------------------------------- | --------- |
| FR-40 | Buat, ubah nama, hapus playlist; tambah/hapus/urutkan item (drag & drop)               | Must      |
| FR-41 | Panel antrean: lihat, susun ulang, hapus, "putar berikutnya"                           | Must      |
| FR-42 | Shuffle dan repeat (off / semua / satu)                                                | Must      |
| FR-43 | Smart shuffle lokal: hindari artis yang sama berturut-turut dan lagu yang baru diputar | Could     |
| FR-44 | Sleep timer (15/30/60 menit atau sampai lagu selesai)                                  | Should    |
| FR-45 | Ekspor/impor playlist `.m3u8`                                                          | Could     |

### 5.4 Tampilan & Pengalaman

| ID    | Kebutuhan                                                              | Prioritas |
| ----- | ---------------------------------------------------------------------- | --------- |
| FR-60 | Layar "Sedang Diputar" dengan cover besar dan warna aksen dari cover   | Should    |
| FR-61 | Mini-player (jendela kecil selalu di atas)                             | Should    |
| FR-62 | Lirik tersinkron dari file `.lrc` atau tag tertanam, sorot baris aktif | Could     |
| FR-63 | Pintasan keyboard global di dalam aplikasi (bagian 9)                  | Must      |
| FR-64 | Tema gelap (default) dan terang                                        | Could     |
| FR-65 | Drag & drop file/folder ke jendela untuk memutar atau menambah         | Should    |
| FR-66 | Integrasi tombol media sistem dan notifikasi lagu (Windows)            | Could     |

### 5.5 Fase 2 (riset setelah v1.0)

| ID    | Kebutuhan                                                                                 |
| ----- | ----------------------------------------------------------------------------------------- |
| FR-80 | Subtitle AI offline dengan `faster-whisper` (model diunduh sekali, opt-in), ekspor `.srt` |
| FR-81 | Playlist lewat perintah bahasa natural (model lokal atau API opsional, opt-in)            |
| FR-82 | AutoMix: transisi beat-matched antar lagu                                                 |
| FR-83 | Terjemahan lirik                                                                          |
| FR-84 | Casting ke perangkat DLNA/Chromecast                                                      |
| FR-85 | Pembersih metadata otomatis (judul/artis berantakan)                                      |

## 6. Kebutuhan Non-Fungsional

| Aspek         | Target                                                                                                              |
| ------------- | ------------------------------------------------------------------------------------------------------------------- |
| Performa      | Aplikasi siap pakai < 2 detik; pindai 5.000 lagu < 60 detik pada pindai pertama; UI tidak membeku lebih dari 100 ms |
| Memori        | < 300 MB saat idle dengan library 10.000 item                                                                       |
| Stabilitas    | File rusak/tidak didukung tidak membuat aplikasi crash, tampilkan pesan dan lewati                                  |
| Privasi       | Tanpa telemetri; data hanya di komputer pengguna; fitur yang butuh internet/AI bersifat opt-in dan dijelaskan jelas |
| Keamanan      | Query SQL selalu berparameter (`?`), jangan menyambung string dari input pengguna                                   |
| Aksesibilitas | Seluruh fitur utama bisa dipakai dengan keyboard; kontras teks memenuhi WCAG AA                                     |
| Portabilitas  | Path dan pemisah file lewat `pathlib`; ada abstraksi supaya mesin pemutar bisa diganti                              |

## 7. Arsitektur

### 7.1 Tech stack

| Lapisan                    | Pilihan                                                                                      | Alasan                                                                                             |
| -------------------------- | -------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| UI                         | **PySide6** (Qt 6, seri 6.11.x per pertengahan 2026; pakai versi stabil terbaru saat instal) | Matang, tampilan modern bisa dibuat dengan stylesheet (QSS), resmi dari Qt                         |
| Mesin pemutar              | **libmpv** lewat paket `python-mpv` (butuh Python 3.9+ dan file libmpv di komputer)          | Format dan fitur sangat lengkap: hardware decode, speed, A-B loop, filter audio, gapless, subtitle |
| Database                   | **SQLite** lewat modul `sqlite3` bawaan Python, tanpa ORM                                    | Tanpa server, satu file, cocok untuk belajar SQL langsung                                          |
| Metadata audio             | **mutagen** (seri 1.47.x)                                                                    | Baca tag ID3/Vorbis/MP4/FLAC dan cover                                                             |
| Metadata video & thumbnail | libmpv (durasi/resolusi), `ffmpeg` opsional untuk thumbnail                                  | Hindari dependensi tambahan di awal                                                                |
| Test                       | **pytest**                                                                                   | Standar                                                                                            |
| Paket jadi (akhir)         | **PyInstaller**                                                                              | Satu folder/exe untuk dibagikan                                                                    |

> Cadangan: bila memasang libmpv terlalu merepotkan, ganti sementara ke `QMediaPlayer` (Qt Multimedia) untuk M1–M2. Karena itu mesin pemutar dibungkus kelas `Player` supaya mudah ditukar.

### 7.2 Struktur proyek

```
nexusplay/
├── PRD.md
├── README.md
├── pyproject.toml
├── main.py                    # titik masuk
├── nexusplay/
│   ├── app.py                 # inisialisasi QApplication, tema, jendela utama
│   ├── core/
│   │   ├── player.py          # bungkus python-mpv (play, pause, seek, sinyal posisi)
│   │   ├── queue.py           # logika antrean, shuffle, repeat
│   │   └── sleep_timer.py
│   ├── library/
│   │   ├── scanner.py         # pindai folder (berjalan di thread latar)
│   │   ├── metadata.py        # mutagen + info video
│   │   └── lyrics.py          # parser .lrc
│   ├── db/
│   │   ├── connection.py      # buka koneksi, PRAGMA, migrasi
│   │   ├── schema.sql
│   │   └── repositories.py    # fungsi query: media, playlist, history, stats
│   ├── ui/
│   │   ├── main_window.py
│   │   ├── theme.py           # token warna + QSS
│   │   ├── views/             # library, album, artis, video, playlist, stats, now_playing
│   │   ├── widgets/           # player_bar, seek_slider, cover_card, queue_panel
│   │   └── mini_player.py
│   └── resources/             # ikon SVG, font, gambar
├── data/                      # nexusplay.db (dibuat otomatis, jangan di-commit)
└── tests/
    ├── test_queue.py
    ├── test_scanner.py
    ├── test_repositories.py
    └── test_lrc.py
```

### 7.3 Prinsip arsitektur

- **UI tidak bicara langsung ke SQL atau mpv.** UI memanggil `Player`, `Queue`, dan fungsi di `repositories.py`.
- **Pekerjaan berat di thread latar** (pemindaian, thumbnail) dan memberi kabar ke UI lewat sinyal Qt. Jangan sentuh widget dari thread lain.
- **Satu sumber kebenaran** untuk status pemutaran: kelas `Player` memancarkan sinyal (`position_changed`, `state_changed`, `track_finished`); semua widget hanya mendengarkan.
- **Migrasi skema** lewat `PRAGMA user_version` supaya perubahan database di masa depan tidak merusak data.

## 8. Desain UI/UX

**Arah desain:** sederhana, modern, tenang. Konten (cover, video) jadi bintang; kontrol minimal dan konsisten.

### 8.1 Tata letak

```
┌───────────────────────────────────────────────────────────────┐
│  ◀ ▶   🔍 Cari lagu, album, video…                   ⚙  ▢ ✕ │
├──────────────┬────────────────────────────────────┬───────────┤
│  NexusPlay   │  Beranda                           │ Antrean   │
│              │  ┌────┐ ┌────┐ ┌────┐ ┌────┐       │ 1 Lagu A  │
│  ⌂ Beranda   │  │cover│ │cover│ │cover│ │cover│     │ 2 Lagu B  │
│  ♪ Musik     │  └────┘ └────┘ └────┘ └────┘       │ 3 Lagu C  │
│  ▶ Video     │  Terakhir diputar                   │           │
│  ♥ Favorit   │  ───────────────────────            │ Lirik ▸   │
│  ≡ Playlist  │  Lagu · Artis · Durasi              │           │
│  ▤ Statistik │  Lagu · Artis · Durasi              │           │
├──────────────┴────────────────────────────────────┴───────────┤
│ [cover] Judul — Artis   ⏮ ⏯ ⏭   ━━●━━━━ 1:23/3:45   🔊 ━●━ ⛶ │
└───────────────────────────────────────────────────────────────┘
```

- **Sidebar kiri:** navigasi utama, bisa diciutkan jadi ikon saja.
- **Area tengah:** konten view aktif (grid cover, daftar lagu, rak video).
- **Panel kanan (bisa disembunyikan):** antrean dan lirik.
- **Bar pemutar bawah:** selalu terlihat; klik cover membuka layar "Sedang Diputar".
- **Mode video:** video mengisi area tengah; kontrol melayang dan hilang setelah 3 detik tanpa gerakan; `F` untuk fullscreen.

### 8.2 Token desain (tema gelap)

| Token        | Nilai                                                                                  |
| ------------ | -------------------------------------------------------------------------------------- |
| `bg`         | `#0B0D12`                                                                              |
| `surface`    | `#151922`                                                                              |
| `surface-2`  | `#1D2230`                                                                              |
| `border`     | `#262C3B`                                                                              |
| `text`       | `#E8EAF0`                                                                              |
| `text-muted` | `#8B93A7`                                                                              |
| `accent`     | gradien `#7C5CFF` → `#22D3EE` (default); diganti warna dominan cover saat lagu diputar |
| `danger`     | `#FF5C7A`                                                                              |
| Radius       | 12 px (kartu), 999 px (tombol bulat/chip)                                              |
| Spasi        | skala 4 / 8 / 12 / 16 / 24 / 32 px                                                     |
| Font         | Inter (disertakan), cadangan Segoe UI                                                  |
| Animasi      | 150–250 ms ease-out untuk hover, buka panel, ganti view                                |

### 8.3 Prinsip interaksi

- Satu aksi utama per layar; aksi sekunder masuk menu titik tiga.
- Status kosong yang ramah ("Belum ada musik. Tambah folder untuk mulai.") dengan tombol langsung.
- Semua elemen interaktif punya status hover, fokus (cincin aksen), dan nonaktif.
- Warna aksen dari cover harus lolos cek kontras; bila terlalu terang/gelap, pakai aksen default.

## 9. Pintasan Keyboard

| Tombol                | Aksi                          |
| --------------------- | ----------------------------- |
| `Space`               | Play/pause                    |
| `←` / `→`             | Mundur / maju 5 detik         |
| `Shift+←` / `Shift+→` | Mundur / maju 30 detik        |
| `↑` / `↓`             | Volume naik/turun             |
| `M`                   | Mute                          |
| `N` / `P`             | Berikutnya / sebelumnya       |
| `S`                   | Shuffle                       |
| `R`                   | Repeat (siklus)               |
| `F`                   | Fullscreen (`Esc` keluar)     |
| `Ctrl+F`              | Fokus ke pencarian            |
| `Ctrl+Q`              | Tampilkan/sembunyikan antrean |
| `Ctrl+L`              | Tampilkan/sembunyikan lirik   |

## 10. Skema Database

Disimpan di `data/nexusplay.db`. Aktifkan `PRAGMA foreign_keys = ON` pada setiap koneksi dan `journal_mode = WAL`.

```sql
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
CREATE VIRTUAL TABLE media_fts USING fts5 (title, artist, album);
```

**Aturan data:**

- Hitung sebagai "diputar" bila didengar ≥ 30 detik atau ≥ 50% durasi (mana yang lebih dulu); baru saat itu `play_count` naik dan baris `play_history` dibuat.
- `resume_ms` direset ke 0 bila posisi > 95% durasi.
- File yang hilang dari disk ditandai/dihapus pada pindai ulang; riwayat ikut terhapus karena `ON DELETE CASCADE`. Putuskan di M3 apakah file hilang disembunyikan dulu atau langsung dihapus.
- Contoh query statistik (4 minggu terakhir): gabungkan `play_history` dengan `media`, filter `played_at >= datetime('now', '-28 days')`, `GROUP BY media_id`, `ORDER BY COUNT(*) DESC`.

## 11. Milestone

Satu milestone = satu sesi kerja yang selesai, jalan, diuji, lalu di-commit. Jangan lompat urutan.

| #   | Milestone                                                                                      | Hasil / selesai kalau                                                       | Konsep yang dipelajari                     |
| --- | ---------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- | ------------------------------------------ |
| M0  | Setup: Python 3.12, venv, Git, instal PySide6, jendela kosong tampil                           | `python main.py` membuka jendela bertema gelap                              | venv, pip, struktur proyek                 |
| M1  | `Player` (mpv): putar satu file audio dari path, play/pause/seek/volume lewat tombol sederhana | Lagu terdengar, tombol berfungsi                                            | kelas, sinyal/slot Qt, pustaka eksternal   |
| M2  | Video tertanam di jendela + fullscreen + subtitle eksternal                                    | Video tampil di dalam jendela, `F` fullscreen                               | embed widget (`wid`), event                |
| M3  | Database + pemindai: tambah folder, baca metadata, simpan ke SQLite, thread latar              | 1.000 file terindeks tanpa UI membeku; pindai ulang tidak menggandakan data | SQL dasar, `sqlite3`, threading, `pathlib` |
| M4  | Kerangka UI: sidebar, view Musik/Album/Artis/Video, bar pemutar bawah                          | Klik lagu di library langsung memutar                                       | layout Qt, model/view, QSS                 |
| M5  | Antrean + playlist + shuffle/repeat + drag & drop                                              | Playlist tersimpan setelah restart                                          | struktur data, relasi tabel, urutan        |
| M6  | Resume video, layar Sedang Diputar, warna aksen dari cover, mini-player                        | Video lanjut dari menit terakhir; mini-player selalu di atas                | state, QImage, jendela kedua               |
| M7  | Pencarian FTS5, favorit/pin, riwayat, halaman statistik                                        | Ketik "col" menampilkan hasil < 100 ms                                      | FTS, agregasi SQL (`GROUP BY`)             |
| M8  | Lirik tersinkron `.lrc`                                                                        | Baris aktif tersorot sesuai waktu                                           | parsing teks, regex, timer                 |
| M9  | Gapless, crossfade, equalizer, speed, A-B loop, sleep timer                                    | Semua kontrol berfungsi dan bisa dimatikan                                  | opsi mpv, filter audio                     |
| M10 | Penyempurnaan: pintasan, tema terang, drag & drop file, pesan error ramah                      | Semua kriteria penerimaan terpenuhi                                         | UX, penanganan error                       |
| M11 | Pengemasan dengan PyInstaller + README                                                         | Aplikasi berjalan di komputer tanpa Python                                  | packaging                                  |

**MVP = M0–M5.** Sampai M5 NexusPlay sudah berguna sehari-hari. M6–M11 adalah v1.0.

## 12. Kriteria Penerimaan

**MVP (M0–M5):**

- [ ] Memutar minimal MP3, FLAC, M4A, MP4, dan MKV tanpa crash.
- [ ] Menambah folder berisi 1.000+ file: UI tetap bisa digeser/diklik saat pemindaian.
- [ ] Menutup dan membuka ulang aplikasi: library, playlist, dan pengaturan tetap ada.
- [ ] Pindai ulang folder yang sama tidak membuat data ganda.
- [ ] File rusak atau tidak didukung ditampilkan sebagai pesan, bukan crash.
- [ ] Hampir semua aksi utama bisa dilakukan dengan keyboard.
- [ ] Semua query SQL memakai parameter (`?`), tidak ada string yang disambung dari input.

**v1.0 (M6–M11):**

- [ ] Video lanjut dari posisi terakhir; posisi tereset bila hampir selesai.
- [ ] Pencarian menampilkan hasil < 100 ms pada 10.000 item.
- [ ] Warna aksen dari cover tetap terbaca (kontras cukup).
- [ ] Gapless: tidak ada jeda terdengar antar trek album yang memang bersambung.
- [ ] Kebijakan privasi di README: tidak ada data keluar dari komputer kecuali fitur opt-in yang diaktifkan sendiri.
- [ ] Pais bisa menjelaskan alur data: file → pemindai → database → UI → player.

## 13. Risiko & Mitigasi

| Risiko                                                                          | Dampak                        | Mitigasi                                                                |
| ------------------------------------------------------------------------------- | ----------------------------- | ----------------------------------------------------------------------- |
| Proyek terlalu besar untuk pemula                                               | Berhenti di tengah            | MVP kecil (M0–M5), satu milestone satu sesi, fitur baru masuk Backlog   |
| Pemasangan libmpv merepotkan di Windows                                         | Terhambat di M1               | Siapkan panduan di README; cadangan `QMediaPlayer` untuk M1–M2          |
| Video tertanam bermasalah di Linux (Wayland)                                    | Video tidak tampil di Linux   | Target Windows dulu; Linux dites setelah v1.0                           |
| UI membeku saat pindai/thumbnail                                                | Pengalaman buruk              | Semua pekerjaan berat di thread latar + sinyal Qt                       |
| Metadata berantakan                                                             | Library tampak kacau          | Fallback ke nama file; pembersih metadata = fase 2                      |
| Agent menulis kode terlalu banyak tanpa dipahami                                | Tidak belajar                 | Aturan kerja bagian 14                                                  |
| Lisensi: PySide6 (LGPL), mutagen (GPL-2.0+), libmpv (LGPL/GPL tergantung build) | Masalah bila dibagikan/dijual | Untuk pemakaian pribadi aman; cek lisensi sebelum mendistribusikan luas |
| Fitur AI fase 2 mengunduh model besar                                           | Boros disk/bandwidth          | Opt-in, tampilkan ukuran unduhan sebelum mulai                          |

## 14. Workflow di Antigravity

### Aturan kerja (simpan sebagai instruksi/rules proyek, atau tempel di awal setiap sesi)

```
Kamu adalah mentor Python untuk pemula yang sedang membangun NexusPlay.
Baca NexusPlay-PRD.md di root proyek sebelum melakukan apa pun.

Aturan:
1. Kerjakan SATU milestone dalam satu waktu, sesuai urutan di PRD.
2. Sebelum menulis kode, tulis rencana singkat (file yang dibuat/diubah, alasan, urutan langkah) dan tunggu persetujuan saya.
3. Tulis kode dalam potongan kecil. Setelah tiap potongan, jelaskan dengan bahasa Indonesia sederhana apa yang dilakukan dan konsep Python/SQL/Qt yang dipakai.
4. Jangan menambah fitur, library, atau perubahan skema database di luar PRD tanpa bertanya.
5. UI tidak boleh memanggil SQL atau mpv langsung; ikuti arsitektur di bagian 7.3.
6. Semua query SQL berparameter. Pekerjaan berat harus di thread latar.
7. Setelah selesai, beri cara menjalankan, cara mengujinya, dan 2-3 pertanyaan kecil untuk menguji pemahaman saya.
8. Jangan lanjut ke milestone berikutnya sebelum saya bilang "lanjut".
```

### Siklus per milestone

1. **Rencana:** minta rencana milestone, baca, tanyakan yang tidak dipahami.
2. **Bangun:** setujui, agent menulis kode per potongan.
3. **Jalankan:** coba sendiri, cocokkan dengan kolom "Hasil / selesai kalau".
4. **Pahami:** jawab pertanyaan uji; minta penjelasan ulang untuk baris yang belum paham.
5. **Test:** jalankan `pytest` bila milestone punya logika yang bisa diuji.
6. **Commit:** satu commit per milestone (`git commit -m "M3: pemindai + SQLite"`).
7. **Lanjut.**

### Template prompt

Mulai milestone:

```
Kita mulai Milestone [N]: [nama] dari NexusPlay-PRD.md.
Buat rencananya dulu (file, fungsi/kelas, urutan langkah).
Jangan tulis kode sebelum saya setujui.
```

Saat error:

```
Ini error yang muncul: [tempel error lengkap]
Jelaskan dulu artinya dengan bahasa sederhana, lalu usulkan perbaikan terkecil.
Jangan ubah file di luar yang terkait.
```

Sebelum commit:

```
Review kode milestone ini: ada bug, kasus tepi yang belum ditangani, query SQL yang tidak aman, atau bagian yang membingungkan untuk pemula?
```

### Kebiasaan yang disarankan

- Ketik ulang sendiri minimal satu fungsi per milestone tanpa menyalin.
- Sebelum M3, latih SQL dasar (`SELECT`, `INSERT`, `JOIN`, `GROUP BY`) langsung di `sqlite3` agar skema terasa masuk akal.
- Ide fitur baru ditulis di Backlog, jangan dikerjakan di tengah milestone.
- Tambahkan `data/`, `.venv/`, dan `__pycache__/` ke `.gitignore`.

## 15. Backlog

- Visualizer audio
- Podcast (RSS) dan audiobook dengan bookmark bab
- Tag editor di dalam aplikasi
- Pencarian cover album otomatis
- Sinkronisasi playlist antar perangkat
- Mode TV/remote lewat browser lokal

## 16. Sumber Riset

- Spotify: antrean & kontrol shuffle (Tom's Guide), Listening Stats, lirik & terjemahan (TechRadar) — https://www.tomsguide.com/entertainment/music-streaming/spotify-just-got-a-major-music-discovery-upgrade-heres-the-new-features , https://www.techradar.com/tag/spotify
- Apple Music AutoMix, terjemahan & pelafalan lirik, Music Pins (iOS 26) — https://musictech.com/news/gear/apple-music-automix-ai/
- Smart crossfade Apple Music — https://www.techradar.com/audio/apple-music/apple-music-in-ios-18-will-get-a-smart-crossfade-feature-to-upgrade-your-playlists
- Subtitle AI offline di player video — https://screenapp.io/blog/best-video-players-with-ai-subtitles
- Perbandingan player Windows 2026 (PiP, casting, mini-player, Fluent UI) — https://windowsforum.com/windows-news.4/best-free-media-players-for-windows-2026-vlc-gom-fluent-more.432609
- Fitur VLC 4.0 (library, gapless, antarmuka baru) — https://itsfoss.com/vlc-4-features/
- python-mpv (embed lewat `wid`, butuh libmpv, Python ≥ 3.9) — https://pypi.org/project/mpv/
- mutagen — https://mutagen.readthedocs.io/en/latest/
