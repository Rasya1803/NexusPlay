"""NexusPlay — Views package.

Berisi tampilan untuk setiap bagian aplikasi:
- MusicView: Daftar seluruh lagu
- VideoView: Daftar seluruh video
- AlbumView: Koleksi album
- ArtistView: Koleksi artis
- FoldersView: Pengelolaan folder library
"""

from nexusplay.ui.views.music_view import MusicView
from nexusplay.ui.views.video_view import VideoView
from nexusplay.ui.views.album_view import AlbumView
from nexusplay.ui.views.artist_view import ArtistView
from nexusplay.ui.views.folders_view import FoldersView
from nexusplay.ui.views.playlist_view import PlaylistView

__all__ = [
    "MusicView",
    "VideoView",
    "AlbumView",
    "ArtistView",
    "FoldersView",
    "PlaylistView",
]
