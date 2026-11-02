"""NexusPlay — StatsView (FR-29, FR-30).

Halaman Statistik & Riwayat Putar:
- Kartu ringkasan: Waktu Dengar (4 minggu), Total Putar (4 minggu), dan Jumlah Favorit.
- Tabel Top Lagu (4 minggu terakhir) berdasarkan `GROUP BY media_id`.
- Tabel Top Artis (4 minggu terakhir) berdasarkan `GROUP BY artist_id`.
- Tabel Riwayat Terakhir Diputar (`play_history`).
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from nexusplay.ui.widgets.player_bar import format_ms


def format_duration_human(ms: int) -> str:
    """Ubah milidetik menjadi teks durasi ramah pengguna (contoh: '1 jam 24 mnt')."""
    if ms <= 0:
        return "0 dtk"
    total_sec = int(ms // 1000)
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    seconds = total_sec % 60
    if hours > 0:
        return f"{hours} jam {minutes} mnt"
    if minutes > 0:
        return f"{minutes} mnt {seconds} dtk"
    return f"{seconds} dtk"


class StatCard(QFrame):
    """Kartu metrik ringkasan statistik."""

    def __init__(self, title: str, value: str, subtitle: str = "", accent: str = "#7C5CFF", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("StatCard")
        self.setStyleSheet(f"""
            QFrame#StatCard {{
                background-color: #151922;
                border: 1px solid #262C3B;
                border-top: 3px solid {accent};
                border-radius: 12px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)

        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("color: #8B93A7; font-size: 12px; font-weight: 600; background: transparent;")

        self.value_lbl = QLabel(value)
        self.value_lbl.setStyleSheet("color: #E8EAF0; font-size: 22px; font-weight: bold; background: transparent;")

        self.sub_lbl = QLabel(subtitle)
        self.sub_lbl.setStyleSheet("color: #555E70; font-size: 11px; background: transparent;")

        layout.addWidget(self.title_lbl)
        layout.addWidget(self.value_lbl)
        layout.addWidget(self.sub_lbl)

    def update_data(self, value: str, subtitle: str = "") -> None:
        self.value_lbl.setText(value)
        self.sub_lbl.setText(subtitle)


class StatsView(QWidget):
    """Halaman Statistik Mendengarkan & Riwayat Putar."""

    play_media_requested = Signal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._top_tracks: list[dict] = []
        self._recent_history: list[dict] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(16)

        # ── Header ──────────────────────────────────────────────
        header_col = QVBoxLayout()
        header_col.setSpacing(2)
        title_label = QLabel("Statistik & Riwayat")
        title_label.setStyleSheet("color: #E8EAF0; font-size: 24px; font-weight: bold;")
        subtitle_label = QLabel("Ringkasan aktivitas 4 minggu terakhir (28 hari) & riwayat pemutaran")
        subtitle_label.setStyleSheet("color: #8B93A7; font-size: 13px;")
        header_col.addWidget(title_label)
        header_col.addWidget(subtitle_label)
        layout.addLayout(header_col)

        # ── Kartu Ringkasan ─────────────────────────────────────
        cards_row = QHBoxLayout()
        cards_row.setSpacing(14)

        self.card_time = StatCard("WAKTU DENGAR (4 MINGGU)", "0 dtk", "Sepanjang waktu: 0 dtk", "#7C5CFF")
        self.card_plays = StatCard("JUMLAH PUTAR (4 MINGGU)", "0 kali", "Dihitung saat didengar ≥30d / ≥50%", "#22D3EE")
        self.card_favs = StatCard("KOLEKSI FAVORIT", "0 item", "Lagu & video bertanda ♥", "#FF5C7A")

        cards_row.addWidget(self.card_time, 1)
        cards_row.addWidget(self.card_plays, 1)
        cards_row.addWidget(self.card_favs, 1)
        layout.addLayout(cards_row)

        # ── Baris Tengah: Top Lagu & Top Artis ──────────────────
        mid_row = QHBoxLayout()
        mid_row.setSpacing(16)

        # Kiri: Top Lagu
        left_col = QVBoxLayout()
        left_col.setSpacing(6)
        lbl_top_tracks = QLabel("🔥 Top Lagu (4 Minggu Terakhir)")
        lbl_top_tracks.setStyleSheet("color: #E8EAF0; font-size: 15px; font-weight: 600;")
        self.top_tracks_table = self._create_table(["#", "Judul", "Artis", "Diputar"])
        self.top_tracks_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.top_tracks_table.setColumnWidth(0, 36)
        self.top_tracks_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.top_tracks_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.top_tracks_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.top_tracks_table.setColumnWidth(3, 72)
        self.top_tracks_table.cellDoubleClicked.connect(self._on_top_track_double_clicked)

        left_col.addWidget(lbl_top_tracks)
        left_col.addWidget(self.top_tracks_table, 1)

        # Kanan: Top Artis
        right_col = QVBoxLayout()
        right_col.setSpacing(6)
        lbl_top_artists = QLabel("👑 Top Artis (4 Minggu Terakhir)")
        lbl_top_artists.setStyleSheet("color: #E8EAF0; font-size: 15px; font-weight: 600;")
        self.top_artists_table = self._create_table(["#", "Artis", "Diputar", "Waktu Dengar"])
        self.top_artists_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.top_artists_table.setColumnWidth(0, 36)
        self.top_artists_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.top_artists_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.top_artists_table.setColumnWidth(2, 72)
        self.top_artists_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        right_col.addWidget(lbl_top_artists)
        right_col.addWidget(self.top_artists_table, 1)

        mid_row.addLayout(left_col, 3)
        mid_row.addLayout(right_col, 2)
        layout.addLayout(mid_row, 1)

        # ── Bawah: Riwayat Terakhir Diputar ─────────────────────
        hist_col = QVBoxLayout()
        hist_col.setSpacing(6)
        lbl_history = QLabel("🕒 Riwayat Terakhir Diputar (Klik 2x untuk memutar)")
        lbl_history.setStyleSheet("color: #E8EAF0; font-size: 15px; font-weight: 600;")

        self.history_table = self._create_table(["Waktu (UTC)", "Judul", "Artis", "Didengar"])
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.history_table.setColumnWidth(3, 86)
        self.history_table.cellDoubleClicked.connect(self._on_history_double_clicked)

        hist_col.addWidget(lbl_history)
        hist_col.addWidget(self.history_table, 1)
        layout.addLayout(hist_col, 1)

    def _create_table(self, headers: list[str]) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setShowGrid(False)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setStyleSheet("""
            QTableWidget {
                background-color: #11141B;
                alternate-background-color: #151922;
                color: #E8EAF0;
                border: 1px solid #262C3B;
                border-radius: 8px;
                outline: none;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #1A1F2C;
            }
            QTableWidget::item:selected {
                background-color: #1D2230;
                color: #FFFFFF;
            }
            QHeaderView::section {
                background-color: #151922;
                color: #8B93A7;
                font-size: 11px;
                font-weight: 600;
                padding: 6px 8px;
                border: none;
                border-bottom: 1px solid #262C3B;
            }
        """)
        return table

    def set_stats_data(
        self,
        summary: dict[str, int],
        top_tracks: list[dict],
        top_artists: list[dict],
        recent_history: list[dict],
    ) -> None:
        """Perbarui seluruh kartu dan tabel statistik."""
        self._top_tracks = top_tracks
        self._recent_history = recent_history

        total_ms = summary.get("total_listened_ms", 0)
        all_time_ms = summary.get("all_time_listened_ms", 0)
        total_plays = summary.get("total_plays", 0)
        fav_count = summary.get("favorite_count", 0)

        self.card_time.update_data(
            format_duration_human(total_ms),
            f"Sepanjang waktu: {format_duration_human(all_time_ms)}",
        )
        self.card_plays.update_data(
            f"{total_plays} kali",
            "Dihitung saat didengar ≥30d atau ≥50%",
        )
        self.card_favs.update_data(
            f"{fav_count} item",
            "Lagu & video bertanda ♥",
        )

        # Isi tabel Top Lagu
        self.top_tracks_table.setRowCount(len(top_tracks))
        for row, t in enumerate(top_tracks):
            rank_item = QTableWidgetItem(str(row + 1))
            rank_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            rank_item.setForeground(QColor("#7C5CFF") if row < 3 else Qt.GlobalColor.darkGray)

            title_item = QTableWidgetItem(t.get("title") or "Tanpa Judul")
            artist_item = QTableWidgetItem(t.get("artist") or "Artis tidak diketahui")
            artist_item.setForeground(Qt.GlobalColor.lightGray)

            plays_item = QTableWidgetItem(f"{t.get('period_plays', 0)}x")
            plays_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            plays_item.setForeground(QColor("#22D3EE"))

            self.top_tracks_table.setItem(row, 0, rank_item)
            self.top_tracks_table.setItem(row, 1, title_item)
            self.top_tracks_table.setItem(row, 2, artist_item)
            self.top_tracks_table.setItem(row, 3, plays_item)
            self.top_tracks_table.setRowHeight(row, 34)

        # Isi tabel Top Artis
        self.top_artists_table.setRowCount(len(top_artists))
        for row, ar in enumerate(top_artists):
            rank_item = QTableWidgetItem(str(row + 1))
            rank_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            rank_item.setForeground(QColor("#7C5CFF") if row < 3 else Qt.GlobalColor.darkGray)

            name_item = QTableWidgetItem(ar.get("artist") or "Tanpa Artis")
            plays_item = QTableWidgetItem(f"{ar.get('period_plays', 0)}x")
            plays_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            plays_item.setForeground(QColor("#22D3EE"))

            dur_item = QTableWidgetItem(format_duration_human(ar.get("period_listened_ms") or 0))
            dur_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            dur_item.setForeground(Qt.GlobalColor.darkGray)

            self.top_artists_table.setItem(row, 0, rank_item)
            self.top_artists_table.setItem(row, 1, name_item)
            self.top_artists_table.setItem(row, 2, plays_item)
            self.top_artists_table.setItem(row, 3, dur_item)
            self.top_artists_table.setRowHeight(row, 34)

        # Isi tabel Riwayat Terakhir Diputar
        self.history_table.setRowCount(len(recent_history))
        for row, h in enumerate(recent_history):
            time_item = QTableWidgetItem(str(h.get("played_at") or "-"))
            time_item.setForeground(Qt.GlobalColor.darkGray)

            title_item = QTableWidgetItem(h.get("title") or "Tanpa Judul")
            artist_item = QTableWidgetItem(h.get("artist") or ("Video" if h.get("kind") == "video" else "Artis tidak diketahui"))
            artist_item.setForeground(Qt.GlobalColor.lightGray)

            listened_item = QTableWidgetItem(format_ms(h.get("listened_ms") or 0))
            listened_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            listened_item.setForeground(Qt.GlobalColor.darkGray)

            self.history_table.setItem(row, 0, time_item)
            self.history_table.setItem(row, 1, title_item)
            self.history_table.setItem(row, 2, artist_item)
            self.history_table.setItem(row, 3, listened_item)
            self.history_table.setRowHeight(row, 34)

    def _on_top_track_double_clicked(self, row: int, _col: int) -> None:
        if 0 <= row < len(self._top_tracks):
            self.play_media_requested.emit(self._top_tracks[row])

    def _on_history_double_clicked(self, row: int, _col: int) -> None:
        if 0 <= row < len(self._recent_history):
            self.play_media_requested.emit(self._recent_history[row])

