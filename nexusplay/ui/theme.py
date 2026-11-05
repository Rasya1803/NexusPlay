"""NexusPlay — Design System 'Minimal Dark' (Minimalism & Swiss Style).

Semua token warna, tipografi (Inter), ikon SVG Lucide, dan stylesheet QSS
global didefinisikan di satu tempat ini agar seluruh antarmuka konsisten,
tenang, dan bebas dari gradien/emoji berlebih.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QGuiApplication,
    QIcon,
    QImage,
    QPainter,
    QPixmap,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget

# ── Lokasi Aset (Font & Ikon SVG Lucide) ────────────────────────────

RESOURCES_DIR = Path(__file__).resolve().parent.parent / "resources"
FONTS_DIR = RESOURCES_DIR / "fonts"
ICONS_DIR = RESOURCES_DIR / "icons"

# ── Token Warna — Minimal Dark (Default) ────────────────────────────
# Seluruh pasangan teks vs latar telah diverifikasi memenuhi kontras WCAG AA:
# - text (#F4F4F5) di atas bg (#0A0A0B)         = 18.0 : 1
# - text-muted (#A1A1AA) di atas bg (#0A0A0B)   =  7.72 : 1
# - accent (#22C55E) di atas bg (#0A0A0B)       =  8.69 : 1
# - on-accent (#0A0A0B) di atas accent          =  8.69 : 1
# - danger (#F87171) di atas bg (#0A0A0B)       =  7.15 : 1

COLORS: dict[str, str] = {
    "bg":            "#0A0A0B",
    "surface":       "#111113",
    "surface-2":     "#18181B",
    "surface-3":     "#222226",
    "border":        "#232327",
    "border-strong": "#3F3F46",
    "text":          "#F4F4F5",
    "text-muted":    "#A1A1AA",
    "text-disabled": "#71717A",
    "accent":        "#22C55E",
    "accent-2":      "#22C55E",
    "on-accent":     "#0A0A0B",
    "danger":        "#F87171",
    "focus-ring":    "#F4F4F5",
}

# Token Tema Terang (disiapkan untuk FR-64 / M10)
LIGHT_COLORS: dict[str, str] = {
    "bg":            "#FFFFFF",
    "surface":       "#FAFAFA",
    "surface-2":     "#F4F4F5",
    "surface-3":     "#E4E4E7",
    "border":        "#E4E4E7",
    "border-strong": "#D4D4D8",
    "text":          "#18181B",
    "text-muted":    "#52525B",
    "text-disabled": "#A1A1AA",
    "accent":        "#15803D",
    "accent-2":      "#15803D",
    "on-accent":     "#FFFFFF",
    "danger":        "#DC2626",
    "focus-ring":    "#18181B",
}

# ── Token Ukuran & Spasi ────────────────────────────────────────────

RADIUS_CONTROL = 6   # px — tombol, input, item menu
RADIUS = 8           # px — kartu, sampul album
RADIUS_ROUND = 999   # px — tombol bulat
SPACING = [4, 8, 12, 16, 24, 32]

# ── Tipografi ───────────────────────────────────────────────────────

FONT_FAMILY = "Inter"
FONT_FALLBACK = "Segoe UI"
_fonts_loaded = False


def load_app_fonts() -> str:
    """Muat file font Inter dari `nexusplay/resources/fonts/` ke QFontDatabase."""
    global _fonts_loaded
    if not _fonts_loaded and FONTS_DIR.is_dir():
        for ttf_path in sorted(FONTS_DIR.glob("*.ttf")):
            QFontDatabase.addApplicationFont(str(ttf_path))
        _fonts_loaded = True

    families = set(QFontDatabase.families())
    return FONT_FAMILY if FONT_FAMILY in families else FONT_FALLBACK


def make_font(
    size_px: int = 14,
    weight: QFont.Weight = QFont.Weight.Normal,
    letter_spacing_px: float = 0.0,
) -> QFont:
    """Buat objek QFont dengan ukuran piksel dan letter-spacing presisi."""
    font = QFont(FONT_FAMILY)
    font.setPixelSize(size_px)
    font.setWeight(weight)
    if letter_spacing_px != 0.0:
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, letter_spacing_px)
    return font


def refresh_style(widget: QWidget) -> None:
    """Paksa Qt mengevaluasi ulang QSS setelah dynamic property berubah."""
    style = widget.style()
    if style is not None:
        style.unpolish(widget)
        style.polish(widget)
    widget.update()


# ── Helper Ikon SVG Lucide ──────────────────────────────────────────

_PIXMAP_CACHE: dict[tuple[str, str, int, bool], QPixmap] = {}


def icon_pixmap(
    name: str,
    color: str | None = None,
    size: int = 18,
    *,
    filled: bool = False,
) -> QPixmap:
    """Render ikon SVG Lucide (`nexusplay/resources/icons/{name}.svg`) ke QPixmap."""
    stroke_color = color or COLORS["text"]
    cache_key = (name, stroke_color, size, filled)
    cached = _PIXMAP_CACHE.get(cache_key)
    if cached is not None:
        return cached

    svg_path = ICONS_DIR / f"{name}.svg"
    if QGuiApplication.instance() is None:
        QGuiApplication([])
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    if not svg_path.is_file():
        return pixmap

    try:
        svg_text = svg_path.read_text(encoding="utf-8")
    except OSError:
        return pixmap

    svg_text = svg_text.replace('stroke="currentColor"', f'stroke="{stroke_color}"')
    svg_text = svg_text.replace('stroke-width="2"', 'stroke-width="1.75"')
    if filled:
        svg_text = svg_text.replace('fill="none"', f'fill="{stroke_color}"')

    renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))
    if renderer.isValid():
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        renderer.render(painter, QRectF(0, 0, size, size))
        painter.end()

    _PIXMAP_CACHE[cache_key] = pixmap
    return pixmap


def icon(
    name: str,
    color: str | None = None,
    size: int = 18,
    *,
    filled: bool = False,
) -> QIcon:
    """Kembalikan QIcon dari ikon SVG Lucide dengan warna token yang ditentukan."""
    return QIcon(icon_pixmap(name, color=color, size=size, filled=filled))


def set_button_icon(
    button: QWidget,
    name: str,
    color: str | None = None,
    size: int = 16,
    *,
    filled: bool = False,
) -> None:
    """Pasang ikon SVG Lucide pada QPushButton dengan ukuran yang rapi."""
    if hasattr(button, "setIcon") and hasattr(button, "setIconSize"):
        button.setIcon(icon(name, color=color, size=size, filled=filled))
        button.setIconSize(QSize(size, size))


# ── Stylesheet QSS Global (Minimal Dark) ────────────────────────────


def dark_stylesheet(accent_color: str | None = None) -> str:
    """Kembalikan stylesheet QSS global untuk tema Minimal Dark."""
    c = COLORS
    accent = accent_color or c["accent"]
    return f"""
    /* ── 1. Dasar & Tipografi ─────────────────────────────── */
    QWidget {{
        background-color: {c["bg"]};
        color: {c["text"]};
        font-family: "{FONT_FAMILY}", "{FONT_FALLBACK}", sans-serif;
        font-size: 14px;
    }}

    QMainWindow, QDialog {{
        background-color: {c["bg"]};
    }}

    QLabel {{
        background-color: transparent;
        color: {c["text"]};
    }}
    QLabel[role="display"] {{
        font-size: 26px;
        font-weight: 600;
        color: {c["text"]};
    }}
    QLabel[role="title"] {{
        font-size: 20px;
        font-weight: 600;
        color: {c["text"]};
    }}
    QLabel[role="heading"] {{
        font-size: 14px;
        font-weight: 600;
        color: {c["text"]};
    }}
    QLabel[role="body-strong"] {{
        font-size: 14px;
        font-weight: 500;
        color: {c["text"]};
    }}
    QLabel[role="muted"] {{
        font-size: 13px;
        font-weight: 400;
        color: {c["text-muted"]};
    }}
    QLabel[role="caption"] {{
        font-size: 11px;
        font-weight: 600;
        color: {c["text-muted"]};
    }}
    QLabel[role="time"] {{
        font-size: 12px;
        font-weight: 500;
        color: {c["text-muted"]};
    }}
    QLabel[role="metric"] {{
        font-size: 26px;
        font-weight: 600;
        color: {c["text"]};
    }}

    /* ── 2. Tombol (Buttons) ──────────────────────────────── */
    QPushButton {{
        background-color: {c["surface-2"]};
        color: {c["text"]};
        border: 1px solid {c["border"]};
        border-radius: {RADIUS_CONTROL}px;
        padding: 6px 14px;
        font-size: 13px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: {c["surface-3"]};
        border-color: {c["border-strong"]};
    }}
    QPushButton:pressed {{
        background-color: {c["surface"]};
    }}
    QPushButton:focus {{
        outline: none;
        border: 1px solid {c["focus-ring"]};
    }}
    QPushButton:disabled {{
        color: {c["text-disabled"]};
        background-color: {c["surface"]};
        border-color: {c["border"]};
    }}

    /* Varian Tombol Utama (Satu Aksen) */
    QPushButton[variant="primary"] {{
        background-color: {accent};
        color: {c["on-accent"]};
        border: 1px solid {accent};
        font-weight: 600;
    }}
    QPushButton[variant="primary"]:hover {{
        background-color: {accent};
        border-color: {c["text"]};
    }}

    /* Varian Tombol Ikon / Ghost (Tanpa Kotak) */
    QPushButton[variant="icon"],
    QPushButton[variant="ghost"] {{
        background-color: transparent;
        color: {c["text-muted"]};
        border: 1px solid transparent;
        border-radius: {RADIUS_CONTROL}px;
        padding: 4px;
    }}
    QPushButton[variant="icon"]:hover,
    QPushButton[variant="ghost"]:hover {{
        background-color: {c["surface-2"]};
        color: {c["text"]};
    }}
    QPushButton[variant="icon"]:pressed,
    QPushButton[variant="ghost"]:pressed {{
        background-color: {c["surface-3"]};
    }}
    QPushButton[variant="icon"][active="true"],
    QPushButton[variant="ghost"][active="true"] {{
        background-color: {c["surface-2"]};
        color: {accent};
        border: 1px solid {c["border"]};
    }}

    /* Varian Tombol Play Utama (Bulat, Aksen) */
    QPushButton[variant="play"] {{
        background-color: {accent};
        color: {c["on-accent"]};
        border: none;
        border-radius: 20px;
        padding: 0px;
    }}
    QPushButton[variant="play"]:hover {{
        background-color: {c["text"]};
    }}
    QPushButton[variant="play"]:pressed {{
        background-color: {accent};
    }}

    /* Varian Tombol Bahaya (Hapus) */
    QPushButton[variant="danger"] {{
        background-color: transparent;
        color: {c["text-muted"]};
        border: 1px solid {c["border"]};
    }}
    QPushButton[variant="danger"]:hover {{
        background-color: rgba(248, 113, 113, 0.12);
        color: {c["danger"]};
        border-color: {c["danger"]};
    }}

    /* ── 3. Sidebar Navigasi ──────────────────────────────── */
    QWidget#Sidebar {{
        background-color: {c["surface"]};
        border-right: 1px solid {c["border"]};
    }}
    QPushButton#NavButton {{
        background-color: transparent;
        color: {c["text-muted"]};
        border: none;
        border-left: 2px solid transparent;
        border-radius: {RADIUS_CONTROL}px;
        text-align: left;
        padding: 8px 12px;
        font-size: 13px;
        font-weight: 500;
    }}
    QPushButton#NavButton:hover {{
        background-color: {c["surface-2"]};
        color: {c["text"]};
    }}
    QPushButton#NavButton:checked {{
        background-color: {c["surface-2"]};
        color: {c["text"]};
        font-weight: 600;
        border-left: 2px solid {accent};
        border-top-left-radius: 0px;
        border-bottom-left-radius: 0px;
    }}

    /* ── 4. Bar Pencarian & Input ─────────────────────────── */
    QWidget#TopSearchBar,
    QWidget#VideoTopBar,
    QWidget#NowPlayingTopBar {{
        background-color: {c["bg"]};
        border-bottom: 1px solid {c["border"]};
    }}
    QLineEdit {{
        background-color: {c["surface-2"]};
        color: {c["text"]};
        border: 1px solid {c["border"]};
        border-radius: {RADIUS_CONTROL}px;
        padding: 0 12px;
        font-size: 13px;
        selection-background-color: {c["surface-3"]};
    }}
    QLineEdit:hover {{
        border-color: {c["border-strong"]};
    }}
    QLineEdit:focus {{
        background-color: {c["surface-2"]};
        border: 1px solid {c["focus-ring"]};
    }}

    /* ── 5. Tabel Lagu & Video (Minimalis, Tanpa Zebra) ──── */
    QTableWidget {{
        background-color: {c["bg"]};
        alternate-background-color: {c["bg"]};
        color: {c["text"]};
        border: none;
        outline: none;
        gridline-color: transparent;
        selection-background-color: {c["surface-3"]};
        selection-color: {c["text"]};
    }}
    QTableWidget::item {{
        padding: 8px 10px;
        border-bottom: 1px solid {c["surface-2"]};
    }}
    QTableWidget::item:hover {{
        background-color: {c["surface-2"]};
    }}
    QTableWidget::item:selected {{
        background-color: {c["surface-3"]};
        color: {c["text"]};
    }}
    QHeaderView {{
        background-color: {c["bg"]};
        border: none;
    }}
    QHeaderView::section {{
        background-color: {c["bg"]};
        color: {c["text-muted"]};
        font-size: 11px;
        font-weight: 600;
        padding: 8px 10px;
        border: none;
        border-bottom: 1px solid {c["border"]};
    }}

    /* Tabel di dalam Kartu (contoh: Statistik) */
    QTableWidget[embedded="true"] {{
        background-color: {c["surface"]};
        alternate-background-color: {c["surface"]};
        border: 1px solid {c["border"]};
        border-radius: {RADIUS}px;
    }}
    QTableWidget[embedded="true"] QHeaderView::section {{
        background-color: {c["surface"]};
    }}

    /* ── 6. Daftar (ListWidget — Playlist, Antrean, Lirik) ── */
    QListWidget {{
        background-color: transparent;
        border: none;
        outline: none;
    }}
    QListWidget::item {{
        padding: 8px 10px;
        border-radius: {RADIUS_CONTROL}px;
        color: {c["text-muted"]};
    }}
    QListWidget::item:hover {{
        background-color: {c["surface-2"]};
        color: {c["text"]};
    }}
    QListWidget::item:selected {{
        background-color: {c["surface-3"]};
        color: {c["text"]};
    }}

    /* ── 7. Kartu (Album, Artis, Statistik, Folder) ───────── */
    QFrame#AlbumCard,
    QFrame#ArtistCard,
    QFrame#StatCard,
    QFrame#FolderRow,
    QFrame#NowPlayingQueueCard {{
        background-color: {c["surface"]};
        border: 1px solid {c["border"]};
        border-radius: {RADIUS}px;
    }}
    QFrame#AlbumCard:hover,
    QFrame#ArtistCard:hover,
    QFrame#FolderRow:hover {{
        background-color: {c["surface-2"]};
        border-color: {c["border-strong"]};
    }}

    /* ── 8. Panel Kanan (Antrean & Lirik) & Playlist Sidebar ─ */
    QWidget#QueuePanel,
    QWidget#LyricsPanel {{
        background-color: {c["surface"]};
        border-left: 1px solid {c["border"]};
    }}
    QWidget#PlaylistSidebar {{
        background-color: {c["surface"]};
        border-right: 1px solid {c["border"]};
    }}

    /* ── 9. Player Bar & Mini-Player & Slider ─────────────── */
    QWidget#PlayerBar,
    QWidget#MiniPlayerRoot {{
        background-color: {c["surface"]};
        border-top: 1px solid {c["border"]};
    }}
    QLabel#CoverThumb {{
        background-color: {c["surface-2"]};
        border: 1px solid {c["border"]};
        border-radius: {RADIUS_CONTROL}px;
    }}
    QSlider::groove:horizontal {{
        height: 4px;
        background: {c["surface-3"]};
        border-radius: 2px;
    }}
    QSlider#SeekSlider::sub-page:horizontal {{
        background: {accent};
        border-radius: 2px;
    }}
    QSlider#VolumeSlider::sub-page:horizontal {{
        background: {c["text-muted"]};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {c["text"]};
        width: 10px;
        height: 10px;
        margin: -3px 0;
        border-radius: 5px;
    }}
    QSlider::handle:horizontal:hover {{
        background: {accent};
        width: 12px;
        height: 12px;
        margin: -4px 0;
        border-radius: 6px;
    }}

    /* ── 10. ProgressBar ──────────────────────────────────── */
    QProgressBar {{
        background-color: {c["surface-2"]};
        border: none;
        border-radius: 3px;
        height: 6px;
    }}
    QProgressBar::chunk {{
        background-color: {accent};
        border-radius: 3px;
    }}

    /* ── 11. Menu Konteks & Tooltip ───────────────────────── */
    QMenu {{
        background-color: {c["surface-2"]};
        color: {c["text"]};
        border: 1px solid {c["border"]};
        border-radius: {RADIUS}px;
        padding: 4px;
    }}
    QMenu::item {{
        padding: 6px 14px;
        border-radius: {RADIUS_CONTROL}px;
        font-size: 13px;
    }}
    QMenu::item:selected {{
        background-color: {c["surface-3"]};
        color: {c["text"]};
    }}
    QMenu::separator {{
        height: 1px;
        background: {c["border"]};
        margin: 4px 6px;
    }}
    QToolTip {{
        background-color: {c["surface-2"]};
        color: {c["text"]};
        border: 1px solid {c["border"]};
        border-radius: {RADIUS_CONTROL}px;
        padding: 5px 8px;
        font-size: 12px;
    }}

    /* ── 12. Scrollbar Tipis ──────────────────────────────── */
    QScrollArea {{
        border: none;
        background-color: transparent;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {c["border-strong"]};
        min-height: 30px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c["text-disabled"]};
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 8px;
        margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background: {c["border-strong"]};
        min-width: 30px;
        border-radius: 4px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {c["text-disabled"]};
    }}
    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {{
        width: 0;
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

    Menjamin kontras WCAG AA (>= 4.5 : 1) terhadap latar `#0A0A0B`.
    Bila gambar tidak ditemukan atau monokrom, kembali ke `#22C55E`.
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

    h, s, l, _ = avg.getHsl()
    if h < 0:
        return fallback
    s = max(s, 155)
    l = max(135, min(175, l))
    adjusted = QColor.fromHsl(h, s, l)

    bg_color = QColor(COLORS["bg"])
    while contrast_ratio(adjusted, bg_color) < 4.5 and l < 210:
        l += 8
        adjusted = QColor.fromHsl(h, s, l)

    if contrast_ratio(adjusted, bg_color) < 4.5:
        return fallback

    return adjusted.name().upper()
