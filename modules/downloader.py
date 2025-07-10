# modules/downloader.py
import sys
from pathlib import Path

# Asumsi file all_downloader.py lo ada di root project
from all_downloader import YouTubeDownloader

def run_downloader_interface(platform: str = "youtube"):
    """
    Fungsi ini dipanggil dari menu utama Mio.
    Ia akan langsung meluncurkan mode interaktif downloader bawaanmu
    dengan platform preset (YouTube atau Bstation).
    """
    config_path = "config/settings.json"

    # Inisialisasi class bawaan
    downloader = YouTubeDownloader(config_path=config_path)

    # Set platform langsung
    downloader._selected_platform = platform

    # Langsung jalanin mode interaktif
    downloader.interactive_mode()
