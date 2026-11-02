"""NexusPlay — Layar Sedang Diputar (Now Playing View) (FR-60).

Menampilkan sampul album berukuran besar di tengah layar, informasi lengkap
trek (judul, artis, album, tahun, durasi), serta latar dan aksen dinamis
yang mengikuti warna dominan sampul album.
"""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from nexusplay.ui.theme import COLORS, extract_accent_color
from nexusplay.ui.widgets.player_bar import format_ms


def _rounded_pixmap(pixmap: QPixmap, size: int, radius: int) -> QPixmap:
    """Buat QPixmap persegi berukuran `size` x `size` dengan sudut membulat."""
    scaled = pixmap.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    # Potong bagian tengah bila gambar tidak persegi
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
    """Tampilan penuh 'Sedang Diputar' dengan sampul besar & aksen dinamis (FR-60)."""

    back_requested = Signal()

    COVER_SIZE = 280
    COVER_RADIUS = 18

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
        root_layout.setSpacing(16)

        # ── Baris Atas: Tombol Kembali & Label Status ──────────
        top_bar = QHBoxLayout()
        self.btn_back = QPushButton("← Kembali")
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.setFixedHeight(36)
        self.btn_back.clicked.connect(self.back_requested.emit)
        top_bar.addWidget(self.btn_back)

        top_bar.addStretch()

        self.badge_label = QLabel("SEDANG DIPUTAR")
        self.badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_bar.addWidget(self.badge_label)

        top_bar.addStretch()
        # Penyeimbang ruang kanan agar badge tetap di tengah
        spacer = QWidget()
        spacer.setFixedWidth(100)
        spacer.setStyleSheet("background: transparent;")
        top_bar.addWidget(spacer)

        root_layout.addLayout(top_bar)

        # ── Kartu Utama (Hero Card) di Tengah ──────────────────
        root_layout.addStretch(1)

        center_row = QHBoxLayout()
        center_row.addStretch(1)

        self.hero_card = QFrame()
        self.hero_card.setObjectName("nowPlayingCard")
        self.hero_card.setMinimumWidth(460)
        self.hero_card.setMaximumWidth(640)

        card_layout = QVBoxLayout(self.hero_card)
        card_layout.setContentsMargins(40, 36, 40, 36)
        card_layout.setSpacing(16)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # Sampul Album Besar
        self.cover_label = QLabel("🎵")
        self.cover_label.setFixedSize(self.COVER_SIZE, self.COVER_SIZE)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(
            self.cover_label, alignment=Qt.AlignmentFlag.AlignHCenter
        )

        card_layout.addSpacing(8)

        # Judul Lagu / Video
        self.title_label = QLabel("Belum Ada Media Diputar")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet(
            f"font-size: 22px; font-weight: 700; color: {c['text']}; background: transparent;"
        )
        card_layout.addWidget(self.title_label)

        # Nama Artis
        self.artist_label = QLabel("Pilih lagu atau video dari pustaka untuk mulai memutar")
        self.artist_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.artist_label.setWordWrap(True)
        card_layout.addWidget(self.artist_label)

        # Info Album & Durasi
        self.meta_label = QLabel("")
        self.meta_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.meta_label.setStyleSheet(
            f"font-size: 13px; color: {c['text-muted']}; background: transparent;"
        )
        card_layout.addWidget(self.meta_label)

        center_row.addWidget(self.hero_card)
        center_row.addStretch(1)
        root_layout.addLayout(center_row)

        root_layout.addStretch(1)

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
            self.artist_label.setText("Pilih lagu atau video dari pustaka untuk mulai memutar")
            self.meta_label.setText("")
            self.cover_label.setPixmap(QPixmap())
            self.cover_label.setText("🎵")
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
        self.meta_label.setText("  •  ".join(meta_parts))

        cover_path = track.get("cover_path")
        resolved_accent = accent_color or extract_accent_color(cover_path)
        self._apply_accent(resolved_accent)

        # Muat gambar sampul bila tersedia
        pixmap_loaded = False
        if cover_path and Path(str(cover_path)).is_file():
            raw_pixmap = QPixmap(str(cover_path))
            if not raw_pixmap.isNull():
                rounded = _rounded_pixmap(raw_pixmap, self.COVER_SIZE, self.COVER_RADIUS)
                self.cover_label.setText("")
                self.cover_label.setPixmap(rounded)
                pixmap_loaded = True

        if not pixmap_loaded:
            self.cover_label.setPixmap(QPixmap())
            icon = "🎬" if track.get("kind") == "video" else "🎵"
            self.cover_label.setText(icon)

    def _apply_accent(self, color_hex: str) -> None:
        """Terapkan warna aksen dinamis ke kartu, border sampul, dan teks artis."""
        self._accent_color = color_hex
        c = COLORS
        qc = QColor(color_hex)
        r, g, b = qc.red(), qc.green(), qc.blue()

        self.badge_label.setStyleSheet(f"""
            background-color: rgba({r}, {g}, {b}, 36);
            color: {color_hex};
            border: 1px solid rgba({r}, {g}, {b}, 90);
            border-radius: 12px;
            padding: 4px 14px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1px;
        """)

        self.hero_card.setStyleSheet(f"""
            QFrame#nowPlayingCard {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 rgba({r}, {g}, {b}, 48),
                    stop: 0.65 {c["surface"]},
                    stop: 1 {c["surface"]}
                );
                border: 1px solid rgba({r}, {g}, {b}, 85);
                border-radius: 20px;
            }}
        """)

        self.cover_label.setStyleSheet(f"""
            background-color: rgba({r}, {g}, {b}, 28);
            border: 2px solid rgba({r}, {g}, {b}, 110);
            border-radius: {self.COVER_RADIUS}px;
            font-size: 88px;
        """)

        self.artist_label.setStyleSheet(
            f"font-size: 16px; font-weight: 600; color: {color_hex}; background: transparent;"
        )

