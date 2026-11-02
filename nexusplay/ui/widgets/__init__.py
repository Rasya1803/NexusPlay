"""NexusPlay — Widgets package.

Berisi komponen UI yang dapat digunakan kembali:
- PlayerBar: Bar pemutar bawah
- Sidebar: Navigasi kiri
- VideoWidget: Layar penampil video
"""

from nexusplay.ui.widgets.lyrics_panel import LyricsPanel
from nexusplay.ui.widgets.player_bar import PlayerBar
from nexusplay.ui.widgets.queue_panel import QueuePanel
from nexusplay.ui.widgets.sidebar import Sidebar
from nexusplay.ui.widgets.video_widget import VideoWidget

__all__ = [
    "LyricsPanel",
    "PlayerBar",
    "QueuePanel",
    "Sidebar",
    "VideoWidget",
]
