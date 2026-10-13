"""NexusPlay — Titik masuk aplikasi.

Jalankan dengan:
    python main.py

File ini sengaja sangat pendek. Semua logika ada di dalam
package `nexusplay/`. Ini hanya memanggil fungsi `run()`.
"""

from nexusplay.app import run

if __name__ == "__main__":
    run()
