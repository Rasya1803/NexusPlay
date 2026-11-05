# NexusPlay — Design System "Minimal Dark" (MASTER)

Spesifikasi desain utama untuk seluruh UI NexusPlay (PySide6 + QSS).

- **Gaya:** Minimalism & Swiss Style (variance 2, motion 2, density 6)
- **Tipografi:** Inter (Regular 400, Medium 500, SemiBold 600, Bold 700) + fallback Segoe UI
- **Ikonografi:** Lucide SVG Icons (`stroke-width="1.75"`, tanpa emoji)

---

## 1. Prinsip Desain

| # | Prinsip | Artinya untuk NexusPlay |
|---|---------|-------------------------|
| 1 | **Konten yang utama** | Cover album dan video yang paling berwarna di layar. Elemen UI pakai warna netral abu-abu. |
| 2 | **Satu aksen saja** | Warna hanya untuk: tombol Play, progres seek, indikator menu aktif, baris lirik aktif, dan cincin fokus. Tidak ada gradien. |
| 3 | **Hierarki lewat tipografi & jarak** | Bedakan elemen lewat ukuran, ketebalan font, dan jarak. Hindari border tebal atau kotak berlapis. |
| 4 | **Garis tipis, bukan kotak** | Pemisah pakai garis 1 px dengan opasitas rendah. Kartu tanpa bayangan. |
| 5 | **Ikon garis yang konsisten** | Ganti semua emoji dengan ikon SVG Lucide, ketebalan garis 1.75. |
| 6 | **Gerakan seperlunya** | Perubahan state langsung atau maksimal 150–200 ms. Tidak ada animasi dekoratif. |

---

## 2. Token Warna — Tema Gelap (default)

| Token | Hex | Dipakai untuk | Kontras ke `bg` |
|-------|-----|---------------|-----------------|
| `bg` | `#0A0A0B` | Latar area konten utama | — |
| `surface` | `#111113` | Sidebar, player bar, panel kanan | — |
| `surface-2` | `#18181B` | Hover baris/tombol, kolom input | — |
| `surface-3` | `#222226` | Pressed, item terpilih | — |
| `border` | `#232327` | Garis pemisah 1 px, outline input | — |
| `border-strong` | `#3F3F46` | Border input saat hover | 1.89 (dekoratif) |
| `text` | `#F4F4F5` | Judul, teks utama | **18.0 : 1** |
| `text-muted` | `#A1A1AA` | Artis, album, durasi, label | **7.72 : 1** |
| `text-disabled` | `#71717A` | Hanya untuk state nonaktif | 4.09 : 1 |
| `accent` | `#22C55E` | Play, progres seek, menu aktif, lirik aktif | **8.69 : 1** |
| `on-accent` | `#0A0A0B` | Ikon/teks di atas aksen | **8.69 : 1** |
| `danger` | `#F87171` | Error, aksi hapus | **7.15 : 1** |
| `focus-ring` | `#F4F4F5` | Outline fokus keyboard (2 px) | 18.0 : 1 |

### Tema Terang (untuk M10 / FR-64)

| Token | Hex | Kontras |
|-------|-----|---------|
| `bg` | `#FFFFFF` | — |
| `surface` | `#FAFAFA` | — |
| `surface-2` | `#F4F4F5` | — |
| `border` | `#E4E4E7` | — |
| `text` | `#18181B` | 17.72 : 1 |
| `text-muted` | `#52525B` | 7.73 : 1 |
| `accent` | `#15803D` | 5.02 : 1 |
| `on-accent` | `#FFFFFF` | 5.02 : 1 |
| `danger` | `#DC2626` | 4.83 : 1 |

---

## 3. Tipografi & Ukuran

- **Font:** `Inter` (`nexusplay/resources/fonts/`), cadangan `Segoe UI`.
- **Radius kontrol:** `6 px`
- **Radius kartu/cover:** `8 px`
- **Tinggi baris tabel:** `40 px`
- **Lebar sidebar:** `220 px`
- **Lebar panel kanan (antrean/lirik):** `320 px`
- **Tinggi player bar:** `80 px`

