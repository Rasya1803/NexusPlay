"""NexusPlay — Layar Sedang Diputar (Now Playing View) (FR-60, Minimal Dark).

Menampilkan sampul album berukuran 300x300 px (`radius = 8px`) dengan tata letak
tipografi Swiss rata-kiri yang bersih di atas kanvas `#0A0A0B` tanpa kartu gradien.
"""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from nexusplay.ui.theme import (
    COLORS,
    extract_accent_color,
    icon_pixmap,
    set_button_icon,
)
from nexusplay.ui.widgets.player_bar import format_ms


def _rounded_pixmap(pixmap: QPixmap, size: int, radius: int) -> QPixmap:
    """Buat QPixmap persegi berukuran `size` x `size` dengan sudut membulat."""
    scaled = pixmap.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    x = max(0, (scaled.width() - size) // 2)
    y = max(0, (scaled.height() - size) // 2)
    cropped = scaled.copy(x, y, size, size)

    result = QPixmap(size, size)
    result.fill(Qt.GlobalColor.transparent)

    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    path = QPainterPath()
    path.addRoundedRect(0, 0, size, size, radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, cropped)
    painter.end()
    return result


class NowPlayingView(QWidget):
    """Tampilan penuh 'Sedang Diputar' bergaya Swiss Minimal Dark (FR-60)."""

    back_requested = Signal()

    COVER_SIZE = 300
    COVER_RADIUS = 8

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._accent_color: str = COLORS["accent"]
        self._current_track: dict | None = None
        self._setup_ui()
        self._apply_accent(self._accent_color)

    def _setup_ui(self) -> None:
        c = COLORS
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(32, 24, 32, 24)
        root_layout.setSpacing(24)

        # ── Baris Atas: Tombol Kembali ─────────────────────────
        top_bar = QHBoxLayout()
        self.btn_back = QPushButton("Kembali")
        self.btn_back.setProperty("variant", "ghost")
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.setFixedHeight(34)
        set_button_icon(self.btn_back, "arrow-left", c["text-muted"], 16)
        self.btn_back.clicked.connect(self.back_requested.emit)
        top_bar.addWidget(self.btn_back)
        top_bar.addStretch()
        root_layout.addLayout(top_bar)

        # ── Konten Tengah: Sampul 300x300 + Kolom Tipografi Swiss ──
        root_layout.addStretch(1)

        center_row = QHBoxLayout()
        center_row.addStretch(1)

        self.hero_card = QFrame()
        self.hero_card.setObjectName("nowPlayingCard")
        self.hero_card.setStyleSheet("QFrame#nowPlayingCard { background: transparent; border: none; }")

        hero_layout = QHBoxLayout(self.hero_card)
        hero_layout.setContentsMargins(0, 0, 0, 0)
        hero_layout.setSpacing(40)

        # Kiri: Sampul Album Persegi 300x300
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(self.COVER_SIZE, self.COVER_SIZE)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setStyleSheet(f"""
            background-color: {c["surface"]};
            border: 1px solid {c["border"]};
            border-radius: {self.COVER_RADIUS}px;
        """)
        self._set_placeholder_cover("audio")
        hero_layout.addWidget(self.cover_label)

        # Kanan: Kolom Tipografi Rata-Kiri
        meta_col = QVBoxLayout()
        meta_col.setContentsMargins(0, 8, 0, 8)
        meta_col.setSpacing(10)
        meta_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.badge_label = QLabel("SEDANG DIPUTAR")
        self.badge_label.setProperty("role", "caption")
        meta_col.addWidget(self.badge_label)

        self.title_label = QLabel("Belum Ada Media Diputar")
        self.title_label.setProperty("role", "display")
        self.title_label.setWordWrap(True)
        self.title_label.setMinimumWidth(280)
        self.title_label.setMaximumWidth(460)
        meta_col.addWidget(self.title_label)

        self.artist_label = QLabel(
            "Pilih lagu atau video dari pustaka untuk mulai memutar"
        )
        self.artist_label.setWordWrap(True)
        self.artist_label.setMaximumWidth(460)
        self.artist_label.setStyleSheet(
            f"font-size: 16px; font-weight: 500; color: {c['text-muted']}; background: transparent;"
        )
        meta_col.addWidget(self.artist_label)

        self.meta_label = QLabel("")
        self.meta_label.setWordWrap(True)
        self.meta_label.setMaximumWidth(460)
        self.meta_label.setStyleSheet(
            f"font-size: 13px; color: {c['text-disabled']}; background: transparent;"
        )
        meta_col.addWidget(self.meta_label)

        hero_layout.addLayout(meta_col)

        center_row.addWidget(self.hero_card)
        center_row.addStretch(1)
        root_layout.addLayout(center_row)

        root_layout.addStretch(1)

    def _set_placeholder_cover(self, kind: str = "audio") -> None:
        icon_name = "film" if kind == "video" else "music"
        self.cover_label.setText("")
        self.cover_label.setPixmap(icon_pixmap(icon_name, COLORS["text-muted"], 56))

    # ── API Publik ─────────────────────────────────────────────

    @property
    def accent_color(self) -> str:
        """Warna aksen aktif saat ini (hex)."""
        return self._accent_color

    def set_track(self, track: dict | None, accent_color: str | None = None) -> None:
        """Perbarui tampilan dengan data trek yang sedang diputar."""
        self._current_track = track

        if not track:
            self.title_label.setText("Belum Ada Media Diputar")
            self.artist_label.setText(
                "Pilih lagu atau video dari pustaka untuk mulai memutar"
            )
            self.meta_label.setText("")
            self._set_placeholder_cover("audio")
            self._apply_accent(COLORS["accent"])
            return

        title = track.get("title") or Path(track.get("path", "")).stem or "Tanpa Judul"
        artist = track.get("artist") or "Artis Tidak Diketahui"
        album = track.get("album") or ""
        year = track.get("year")
        duration_ms = track.get("duration_ms") or 0

        self.title_label.setText(title)
        self.artist_label.setText(artist)

        meta_parts = []
        if album:
            meta_parts.append(album)
        if year:
            meta_parts.append(str(year))
        if duration_ms > 0:
            meta_parts.append(format_ms(duration_ms))
        self.meta_label.setText("  ·  ".join(meta_parts))

        cover_path = track.get("cover_path")
        resolved_accent = accent_color or extract_accent_color(cover_path)
        self._apply_accent(resolved_accent)

        pixmap_loaded = False
        if cover_path and Path(str(cover_path)).is_file():
            raw_pixmap = QPixmap(str(cover_path))
            if not raw_pixmap.isNull():
                rounded = _rounded_pixmap(raw_pixmap, self.COVER_SIZE, self.COVER_RADIUS)
                self.cover_label.setText("")
                self.cover_label.setPixmap(rounded)
                pixmap_loaded = True

        if not pixmap_loaded:
            self._set_placeholder_cover(track.get("kind") or "audio")

    def _apply_accent(self, color_hex: str) -> None:
        """Terapkan warna aksen tunggal pada label status SEDANG DIPUTAR."""
        self._accent_color = color_hex or COLORS["accent"]
        self.badge_label.setStyleSheet(f"""
            color: {self._accent_color};
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 1px;
            background: transparent;
        """)
