"""NexusPlay — Token warna dan stylesheet (QSS) untuk tema gelap.

Token desain diambil dari PRD bagian 8.2.
Fungsi `dark_stylesheet()` mengembalikan string QSS yang bisa langsung
di-set ke QApplication supaya seluruh widget ikut tema gelap.
"""


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
