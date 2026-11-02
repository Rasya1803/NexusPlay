"""NexusPlay — Token warna dan stylesheet (QSS) untuk tema gelap.

Token desain diambil dari PRD bagian 8.2.
Fungsi `dark_stylesheet()` mengembalikan string QSS yang bisa langsung
di-set ke QApplication supaya seluruh widget ikut tema gelap.
Fungsi `extract_accent_color()` mengekstrak warna dominan dari gambar
sampul (cover art) dengan pengecekan kontras WCAG (FR-60).
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage


# ── Token Warna (Tema Gelap) ────────────────────────────────────────

COLORS = {
    "bg":         "#0B0D12",
    "surface":    "#151922",
    "surface-2":  "#1D2230",
    "border":     "#262C3B",
    "text":       "#E8EAF0",
    "text-muted": "#8B93A7",
    "accent":     "#7C5CFF",
    "accent-2":   "#22D3EE",
    "danger":     "#FF5C7A",
}

# ── Token Ukuran ────────────────────────────────────────────────────

RADIUS = 12        # px, untuk kartu
RADIUS_ROUND = 999 # px, untuk tombol bulat / chip
SPACING = [4, 8, 12, 16, 24, 32]  # skala spasi dalam px

# ── Font ────────────────────────────────────────────────────────────

FONT_FAMILY = "Inter"
FONT_FALLBACK = "Segoe UI"


def dark_stylesheet() -> str:
    """Kembalikan stylesheet QSS untuk tema gelap NexusPlay.

    Stylesheet ini mengatur warna latar, teks, border, scrollbar,
    dan beberapa widget umum supaya konsisten dengan token desain.
    """
    c = COLORS
    return f"""
    /* ── Base ─────────────────────────────────────────────── */
    QWidget {{
        background-color: {c["bg"]};
        color: {c["text"]};
        font-family: "{FONT_FAMILY}", "{FONT_FALLBACK}", sans-serif;
        font-size: 14px;
    }}

    /* ── Main Window ──────────────────────────────────────── */
    QMainWindow {{
        background-color: {c["bg"]};
    }}

    /* ── Labels ───────────────────────────────────────────── */
    QLabel {{
        background-color: transparent;
        color: {c["text"]};
    }}

    /* ── Buttons ──────────────────────────────────────────── */
    QPushButton {{
        background-color: {c["surface-2"]};
        color: {c["text"]};
        border: 1px solid {c["border"]};
        border-radius: {RADIUS}px;
        padding: 8px 16px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: {c["accent"]};
        border-color: {c["accent"]};
    }}
    QPushButton:pressed {{
        background-color: {c["surface"]};
    }}
    QPushButton:focus {{
        outline: none;
        border: 2px solid {c["accent"]};
    }}

    /* ── Scrollbar Vertikal ────────────────────────────────── */
    QScrollBar:vertical {{
        background: {c["bg"]};
        width: 8px;
        margin: 0;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: {c["surface-2"]};
        min-height: 30px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c["border"]};
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    /* ── Scrollbar Horizontal ─────────────────────────────── */
    QScrollBar:horizontal {{
        background: {c["bg"]};
        height: 8px;
        margin: 0;
        border-radius: 4px;
    }}
    QScrollBar::handle:horizontal {{
        background: {c["surface-2"]};
        min-width: 30px;
        border-radius: 4px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {c["border"]};
    }}
    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {{
        width: 0;
    }}

    /* ── Tooltip ──────────────────────────────────────────── */
    QToolTip {{
        background-color: {c["surface"]};
        color: {c["text"]};
        border: 1px solid {c["border"]};
        border-radius: 6px;
        padding: 6px 10px;
    }}
    """


# ── Ekstraksi Warna Aksen dari Cover Art (FR-60) ────────────────────


def _relative_luminance(color: QColor) -> float:
    """Hitung luminansi relatif WCAG (0.0 = hitam pekat, 1.0 = putih)."""
    def _channel(val: float) -> float:
        return val / 12.92 if val <= 0.03928 else ((val + 0.055) / 1.055) ** 2.4

    r = _channel(color.redF())
    g = _channel(color.greenF())
    b = _channel(color.blueF())
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(c1: QColor, c2: QColor) -> float:
    """Hitung rasio kontras WCAG antara dua warna (1.0 s/d 21.0)."""
    l1 = _relative_luminance(c1)
    l2 = _relative_luminance(c2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def extract_accent_color(image_path: str | Path | None) -> str:
    """Ambil warna aksen dominan dari gambar sampul (FR-60).

    Langkah:
    1. Perkecil gambar ke 32x32 piksel agar cepat.
    2. Kumpulkan piksel yang berwarna (saturasi cukup, tidak terlalu gelap/terang).
    3. Hitung rata-rata RGB berbobot saturasi.
    4. Pastikan kontrasnya terhadap latar gelap (#0B0D12) minimal 3.0:1
       dan tidak terlalu pucat agar teks putih tetap terbaca.
    5. Jika gambar tidak ada atau hitam-putih/kontras gagal,
       kembali ke warna aksen bawaan (#7C5CFF).
    """
    fallback = COLORS["accent"]
    if not image_path:
        return fallback

    path_str = str(image_path)
    if not Path(path_str).is_file():
        return fallback

    img = QImage(path_str)
    if img.isNull():
        return fallback

    small = img.scaled(
        32, 32,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )

    r_sum = 0.0
    g_sum = 0.0
    b_sum = 0.0
    weight_sum = 0.0

    for y in range(small.height()):
        for x in range(small.width()):
            c = QColor(small.pixel(x, y))
            h, s, v, _ = c.getHsv()
            # Abaikan piksel abu-abu/hitam/putih
            if s < 45 or v < 40 or v > 245:
                continue
            weight = float(s)
            r_sum += c.red() * weight
            g_sum += c.green() * weight
            b_sum += c.blue() * weight
            weight_sum += weight

    if weight_sum <= 0:
        return fallback

    avg = QColor(
        int(r_sum / weight_sum),
        int(g_sum / weight_sum),
        int(b_sum / weight_sum),
    )

    # Tingkatkan saturasi sedikit bila terlalu redup
    h, s, l, _ = avg.getHsl()
    if h < 0:
        return fallback
    s = max(s, 150)
    # Jaga lightness agar kontras dengan #0B0D12 (>= 3:1) sekaligus aman untuk teks terang
    l = max(115, min(165, l))
    adjusted = QColor.fromHsl(h, s, l)

    bg_color = QColor(COLORS["bg"])
    if contrast_ratio(adjusted, bg_color) < 3.0:
        return fallback

    return adjusted.name().upper()

