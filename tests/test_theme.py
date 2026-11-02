"""NexusPlay — Unit test untuk ekstraksi warna aksen & kontras WCAG (FR-60)."""

from pathlib import Path

from PySide6.QtGui import QColor, QImage

from nexusplay.ui.theme import COLORS, contrast_ratio, extract_accent_color


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
    """Gambar berwarna cerah menghasilkan warna aksen yang kontras (>= 3:1) dengan #0B0D12."""
    img_path = tmp_path / "crimson.png"
    img = QImage(64, 64, QImage.Format.Format_RGB32)
    img.fill(QColor(220, 40, 60))
    img.save(str(img_path))

    extracted = extract_accent_color(img_path)
    assert extracted != COLORS["accent"]

    bg = QColor(COLORS["bg"])
    accent_qcolor = QColor(extracted)
    assert contrast_ratio(accent_qcolor, bg) >= 3.0
    # Pastikan rona merah tetap dominan
    assert accent_qcolor.red() > accent_qcolor.blue()
    assert accent_qcolor.red() > accent_qcolor.green()

