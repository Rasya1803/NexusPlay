"""NexusPlay — Unit test untuk Design System Minimal Dark, ekstraksi warna aksen, & kontras WCAG (FR-60)."""

from pathlib import Path

from PySide6.QtGui import QColor, QImage

from nexusplay.ui.theme import (
    COLORS,
    LIGHT_COLORS,
    contrast_ratio,
    dark_stylesheet,
    extract_accent_color,
    icon_pixmap,
)


def test_minimal_dark_tokens_meet_wcag_aa() -> None:
    """Pastikan seluruh pasangan warna teks utama & aksen di Minimal Dark lolos WCAG AA (>= 4.5:1)."""
    bg = QColor(COLORS["bg"])
    assert contrast_ratio(QColor(COLORS["text"]), bg) >= 15.0
    assert contrast_ratio(QColor(COLORS["text-muted"]), bg) >= 7.0
    assert contrast_ratio(QColor(COLORS["accent"]), bg) >= 7.0
    assert contrast_ratio(QColor(COLORS["danger"]), bg) >= 4.5
    assert contrast_ratio(QColor(COLORS["accent"]), QColor(COLORS["on-accent"])) >= 7.0


def test_light_theme_tokens_meet_wcag_aa() -> None:
    """Pastikan token tema terang (FR-64) lolos WCAG AA (>= 4.5:1)."""
    bg = QColor(LIGHT_COLORS["bg"])
    assert contrast_ratio(QColor(LIGHT_COLORS["text"]), bg) >= 15.0
    assert contrast_ratio(QColor(LIGHT_COLORS["text-muted"]), bg) >= 7.0
    assert contrast_ratio(QColor(LIGHT_COLORS["accent"]), bg) >= 4.5
    assert contrast_ratio(QColor(LIGHT_COLORS["danger"]), bg) >= 4.5


def test_extract_accent_color_fallback_on_missing_file() -> None:
    """Jika path kosong atau tidak ada di disk, kembali ke warna aksen default."""
    assert extract_accent_color(None) == COLORS["accent"]
    assert extract_accent_color("") == COLORS["accent"]
    assert extract_accent_color("tidak_ada_file.png") == COLORS["accent"]


def test_extract_accent_color_fallback_on_grayscale(tmp_path: Path) -> None:
    """Gambar abu-abu murni (saturasi = 0) harus kembali ke warna aksen default."""
    img_path = tmp_path / "gray.png"
    img = QImage(64, 64, QImage.Format.Format_RGB32)
    img.fill(QColor(120, 120, 120))
    img.save(str(img_path))

    assert extract_accent_color(img_path) == COLORS["accent"]


def test_extract_accent_color_vibrant_image_meets_wcag_contrast(tmp_path: Path) -> None:
    """Gambar berwarna cerah menghasilkan warna aksen yang kontras (>= 4.5:1) dengan #0A0A0B."""
    img_path = tmp_path / "crimson.png"
    img = QImage(64, 64, QImage.Format.Format_RGB32)
    img.fill(QColor(220, 40, 60))
    img.save(str(img_path))

    extracted = extract_accent_color(img_path)
    assert extracted != COLORS["accent"]

    bg = QColor(COLORS["bg"])
    accent_qcolor = QColor(extracted)
    assert contrast_ratio(accent_qcolor, bg) >= 4.5
    assert accent_qcolor.red() > accent_qcolor.blue()
    assert accent_qcolor.red() > accent_qcolor.green()


def test_lucide_svg_icon_renders_non_null_pixmap() -> None:
    """Pastikan ikon SVG Lucide dapat dirender menjadi QPixmap yang valid."""
    pix = icon_pixmap("play", COLORS["accent"], 20, filled=True)
    assert not pix.isNull()
    assert pix.width() == 20
    assert pix.height() == 20


def test_dark_stylesheet_contains_no_gradients() -> None:
    """Pastikan stylesheet Minimal Dark bebas dari gradien dekoratif."""
    qss = dark_stylesheet()
    assert "qlineargradient" not in qss
    assert COLORS["bg"] in qss
    assert COLORS["accent"] in qss
