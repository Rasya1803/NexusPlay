"""NexusPlay — FavoritesView (FR-25, FR-27, Minimal Dark).

Tampilan daftar media (lagu & video) yang ditandai sebagai Favorit.
Mewarisi tabel dan menu klik kanan dari `MusicView` dengan status kosong
khusus halaman Favorit.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from nexusplay.ui.theme import COLORS, icon_pixmap
from nexusplay.ui.views.music_view import MusicView


class FavoritesView(MusicView):
    """Halaman daftar media favorit pengguna."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.title_label.setText("Favorit")
        self.subtitle_label.setText("0 item favorit")
        self._customize_empty_state()

    def _customize_empty_state(self) -> None:
        empty_widget = QWidget()
        empty_layout = QVBoxLayout(empty_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(10)

        icon_label = QLabel()
        icon_label.setPixmap(icon_pixmap("heart", COLORS["text-muted"], 40))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_title = QLabel("Belum ada media favorit")
        empty_title.setProperty("role", "heading")
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_desc = QLabel(
            "Klik ikon hati pada daftar lagu atau bar pemutar bawah\n"
            "untuk menyimpan lagu dan video kesukaan Anda di sini."
        )
        empty_desc.setProperty("role", "muted")
        empty_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_layout.addStretch()
        empty_layout.addWidget(icon_label)
        empty_layout.addWidget(empty_title)
        empty_layout.addWidget(empty_desc)
        empty_layout.addStretch()

        old_empty = self.stack.widget(1)
        self.stack.removeWidget(old_empty)
        old_empty.deleteLater()
        self.stack.addWidget(empty_widget)

    def set_tracks(self, tracks: list[dict]) -> None:
        super().set_tracks(tracks)
        self.subtitle_label.setText(f"{len(tracks)} item favorit")
