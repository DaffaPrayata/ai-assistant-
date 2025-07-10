import argparse
import json
import os
import sys
import logging # Hanya satu kali import logging
from pathlib import Path
from typing import List, Dict, Optional
import yt_dlp
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn, TimeElapsedColumn
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel
import re
import subprocess
import datetime # Untuk mode output 'date'
# import browser_cookie3 # Hapus import ini karena sudah diurus yt-dlp internal

# --- HAPUS BLOK TEST browser_cookie3 DARI GLOBAL SCOPE ---
# try:
#     cj = browser_cookie3.firefox(domain_name='bilibili.tv')
#     print("Cookies berhasil dimuat:")
#     print(cj)
# except Exception as e:
#     print(f"Gagal memuat cookies: {e}")
# --------------------------------------------------------

# Inisialisasi console Rich
console = Console()

# Regex untuk validasi URL YouTube
YOUTUBE_URL_REGEX = re.compile(r"^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$")
# Regex untuk validasi URL Bilibili/Bstation
BILIBILI_URL_REGEX = re.compile(r"^(https?://)?(www\.)?(bilibili\.com|bilibili\.tv)/.+$")

# --- DEFAULT CONFIGURATION ---
DEFAULT_CONFIG = {
    "default_format": "mp3",
    "output_folder": "Downloads/",
    "mp3_quality": "320k",
    "mp4_quality": "720p",
    "error_behavior": "skip", # 'skip' or 'abort'
    "output_mode": "separate", # 'separate', 'date', 'channel'
    "auto_open": False,
    "verbose": False,
    "bstation_cookie_browser": "firefox" # Default browser untuk cookies Bstation
}

class YouTubeDownloader:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.config_path = Path(config_path)  # ← default: "config.json"

        # --- Step 1: Initial basic logging setup ---
        # Initialize logger with a temporary basic level (e.g., INFO)
        # This logger won't use self.config yet
        self.logger = logging.getLogger(__name__)
        # Ensure handlers are cleared to prevent duplication if setup_logging is called multiple times
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Add a basic console handler if none exist
        if not self.logger.handlers:
            basic_handler = logging.StreamHandler(sys.stdout)
            basic_handler.setLevel(logging.INFO) # Default to INFO for initial setup
            basic_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            basic_handler.setFormatter(basic_formatter)
            self.logger.addHandler(basic_handler)
            self.logger.setLevel(logging.INFO) # Set logger level

        # --- Step 2: Load configuration ---
        self.config = self.load_config()
        
        # --- Step 3: Re-run full logging setup with config settings ---
        # This will now use self.config for 'verbose' and set up file logging
        self.setup_logging() 

        self.downloaded_files = []
        self._current_progress_task = None
        self._progress = None
        self._selected_platform = None 

        Path(self.config['output_folder']).mkdir(parents=True, exist_ok=True)

    # --- DEFINISI setup_logging YANG BENAR (HANYA SATU INI) ---
    def setup_logging(self):
        # Remove all existing handlers from the logger
        # This prevents duplicate handlers if setup_logging is called multiple times (e.g., after config change)
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        log_level = logging.DEBUG if self.config.get('verbose') else logging.INFO
        
        # Set the logger level based on config
        self.logger.setLevel(log_level)

        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level) # Use configured level
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(console_handler)

        # File Handler
        log_folder = Path("logs")
        log_folder.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_folder / 'downloader.log')
        file_handler.setLevel(logging.DEBUG) # Always log DEBUG to file for comprehensive logs
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(file_handler)

        # Mute noisy yt_dlp logs unless verbose is active
        if not self.config.get('verbose', False):
            logging.getLogger('yt_dlp').setLevel(logging.WARNING)
        else:
            logging.getLogger('yt_dlp').setLevel(logging.INFO) # Or DEBUG if you want very detailed yt-dlp logs
    # --------------------------------------------------------------

    def load_config(self) -> Dict:
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                return {**DEFAULT_CONFIG, **config}
            else:
                self.logger.info(f"File konfigurasi tidak ditemukan di '{self.config_path}'. Menggunakan konfigurasi default.")
                return DEFAULT_CONFIG
        except json.JSONDecodeError as e:
            self.logger.error(f"Error membaca file konfigurasi '{self.config_path}': {e}. Menggunakan konfigurasi default.")
            console.print(f"[red]Error: File konfigurasi '{self.config_path}' rusak. Menggunakan default.[/red]")
            return DEFAULT_CONFIG
        except Exception as e:
            self.logger.error(f"Terjadi kesalahan saat memuat konfigurasi: {e}", exc_info=True)
            console.print(f"[red]Error tak terduga saat memuat konfigurasi: {e}. Menggunakan default.[/red]")
            return DEFAULT_CONFIG

    def save_config(self):
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            self.logger.info(f"Konfigurasi berhasil disimpan ke '{self.config_path}'.")
            console.print(f"[bold green]Konfigurasi berhasil disimpan![/bold green]")
        except Exception as e:
            self.logger.error(f"Gagal menyimpan konfigurasi ke '{self.config_path}': {e}", exc_info=True)
            console.print(f"[red]Error: Gagal menyimpan konfigurasi: {e}[/red]")

    # --- HAPUS DEFINISI setup_logging YANG DUPLIKAT INI ---
    # def setup_logging(self):
    #     for handler in logging.root.handlers[:]:
    #         logging.root.removeHandler(handler)

    #     log_level = logging.DEBUG if self.config.get('verbose') else logging.INFO
    #     logging.basicConfig(
    #         level=log_level,
    #         format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    #         handlers=[
    #             logging.StreamHandler(sys.stdout)
    #         ]
    #     )

    #     log_folder = Path("logs")
    #     log_folder.mkdir(parents=True, exist_ok=True)
    #     file_handler = logging.FileHandler(log_folder / 'downloader.log')
    #     file_handler.setLevel(logging.DEBUG)
    #     file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    #     logging.getLogger().addHandler(file_handler)

    #     if not self.config.get('verbose', False):
    #         logging.getLogger('yt_dlp').setLevel(logging.WARNING)

    #     self.logger = logging.getLogger(__name__)
    # ----------------------------------------------------

    def get_output_path(self, format_type: str, info: Dict) -> Path:
        base_path = Path(self.config['output_folder'])
        
        if self.config['output_mode'] == 'separate':
            sub_folder = 'Music' if format_type == 'mp3' else 'Videos'
            base_path = base_path / sub_folder
        elif self.config['output_mode'] == 'date':
            upload_date_str = info.get('upload_date')
            if upload_date_str:
                try:
                    date_obj = datetime.datetime.strptime(upload_date_str, '%Y%m%d')
                    date_folder = date_obj.strftime('%Y-%m')
                    base_path = base_path / date_folder
                except ValueError:
                    self.logger.warning(f"Gagal memparsing upload_date '{upload_date_str}'. Menggunakan folder default.")
            else:
                self.logger.warning("Upload date tidak ditemukan. Menggunakan folder default.")
        elif self.config['output_mode'] == 'channel':
            uploader = info.get('uploader', 'Unknown Channel')
            uploader = "".join(c for c in uploader if c.isalnum() or c in (' ', '-', '_', '.', '[', ']', '(', ')', '#', '&')).strip()
            uploader = uploader[:100]
            if not uploader:
                uploader = "Unknown_Channel"
            base_path = base_path / uploader
        
        base_path.mkdir(parents=True, exist_ok=True)
        return base_path

    def get_ydl_opts(self, format_type: str, output_path: Path) -> Dict:
        base_opts = {
            'outtmpl': str(output_path / '%(title)s.%(ext)s'),
            'ignoreerrors': self.config['error_behavior'] == 'skip',
            'quiet': not self.config.get('verbose', False),
            'no_warnings': not self.config.get('verbose', False),
            'progress_hooks': [self._progress_hook],
            'merge_output_format': 'mkv',
        }

        # Subtitle dan Cookies hanya untuk Bstation, dengan prioritas ke config bstation_cookie_browser
        if self._selected_platform == 'bstation':
            base_opts['cookiesfrombrowser'] = (self.config.get('bstation_cookie_browser', 'firefox'),)
            self.logger.debug(f"[DEBUG] Opsi cookiesfrombrowser: {base_opts['cookiesfrombrowser']}")
            base_opts['writesubtitles'] = True
            base_opts['subtitleslangs'] = ['id'] # Hanya ID untuk Bstation
            base_opts['embedsubtitles'] = True # Otomatis embed untuk Bstation
            base_opts['convertsubs'] = 'srt' # Konversi ke SRT untuk Bstation
            self.logger.debug(f"Menggunakan cookies dari browser '{base_opts['cookiesfrombrowser']}' untuk Bstation. Subtitle ID disematkan.")
        else: # Default untuk YouTube
            # Anda bisa menambahkan opsi subtitle spesifik YouTube di sini jika diperlukan
            base_opts['writesubtitles'] = False # Default off untuk YT kecuali diaktifkan secara eksplisit
            base_opts['embedsubtitles'] = False # Default off
            base_opts['convertsubs'] = None # Default off

        if format_type == 'mp3':
            base_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': self.config.get('mp3_quality', '320k'),
                }],
            })
        elif format_type == 'mp4':
            quality = self.config.get('mp4_quality', '700p') # Default 720p untuk YouTube
            if self._selected_platform == 'bstation':
                quality = '720p' # Kualitas MP4 otomatis 720p untuk Bstation
                console.print("[bold yellow]Kualitas MP4 untuk Bstation diatur otomatis ke 720p.[/bold yellow]")
            
            height = quality.replace('p', '')
            base_opts.update({
                'format': f'bestvideo[height<={height}]+bestaudio/best[height<={height}]',
                'merge_output_format': 'mp4',
            })
        
        self._current_progress_task = None
        self._progress = None
        return base_opts

    def _progress_hook(self, d: Dict):
        if self._progress is None or self._current_progress_task is None:
            return

        if d['status'] == 'downloading':
            if self._progress.tasks[self._current_progress_task].total is None and d.get('total_bytes'):
                self._progress.update(self._current_progress_task, total=d['total_bytes'])

            current_file_name = d.get('filename')
            if current_file_name:
                display_name = current_file_name.split('/')[-1]
            else:
                display_name = "Unduhan"

            downloaded_bytes = d.get('downloaded_bytes', 0)
            self._progress.update(
                self._current_progress_task,
                completed=downloaded_bytes,
                description=f"Downloading: [bold green]{display_name}[/bold green] [dim]{d.get('_percent_str', '')}[/dim] [dim]{d.get('_speed_str', '')}[/dim]"
            )
        elif d['status'] == 'finished':
            self._progress.update(self._current_progress_task, description=f"✓ Processing: [bold green]{d['filename'].split('/')[-1]}[/bold green]")
            if self._progress.tasks[self._current_progress_task].total is not None:
                self._progress.update(self._current_progress_task, completed=self._progress.tasks[self._current_progress_task].total)
            self._progress.stop_task(self._current_progress_task)
        elif d['status'] == 'error':
            self._progress.update(self._current_progress_task, description=f"[red]✗ Error: {d.get('filename', 'Unknown File')}[/red]")
            self._progress.stop_task(self._current_progress_task)


    def download_single(self, url: str, format_type: str) -> bool:
        # Validasi URL ketat berdasarkan platform yang dipilih
        if self._selected_platform == 'youtube' and not YOUTUBE_URL_REGEX.match(url):
            console.print(f"[red]✗ Ini bukan URL YouTube yang valid. Silakan masukkan URL YouTube.[/red]")
            self.logger.warning(f"URL YouTube tidak valid: {url}")
            return False
        elif self._selected_platform == 'bstation' and not BILIBILI_URL_REGEX.match(url):
            console.print(f"[red]✗ Ini bukan URL Bstation yang valid. Silakan masukkan URL Bstation.[/red]")
            self.logger.warning(f"URL Bstation tidak valid: {url}")
            return False
        
        self.logger.info(f"Mulai unduhan '{url}' sebagai '{format_type}' dari {self._selected_platform.capitalize()}")

        try:
            # Dapatkan info video pertama tanpa mengunduh
            with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl_info:
                info = ydl_info.extract_info(url, download=False)
            
            if info.get('_type') == 'playlist':
                console.print(f"[yellow]⚠ URL ini adalah playlist. Bot hanya akan mengunduh item pertama untuk mode URL tunggal.[/yellow]")
                if 'entries' in info and info['entries']:
                    first_entry = info['entries'][0]
                    url = first_entry.get('url', url)
                    info = first_entry
                else:
                    console.print("[red]✗ Tidak ada entri video yang ditemukan di playlist.[/red]")
                    return False

            output_path = self.get_output_path(format_type, info)
            self.display_video_info(info)

            ydl_opts = self.get_ydl_opts(format_type, output_path)

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                self._progress = progress
                self._current_progress_task = progress.add_task(f"Initializing download...", total=None)
                
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as download_ydl:
                        download_ydl.download([url])
                    
                    self.logger.info(f"Unduhan selesai untuk '{url}'.")
                    console.print(f"[bold green]✓ Berhasil mengunduh:[/bold green] [cyan]{info.get('title', 'N/A')}.{format_type}[/cyan]")
                    
                    downloaded_file = None
                    candidate_files = list(output_path.glob(f"{info.get('title', '*')}.*"))
                    if candidate_files:
                        downloaded_file = max(candidate_files, key=os.path.getmtime)
                    
                    if downloaded_file and downloaded_file.exists():
                        self.downloaded_files.append(str(downloaded_file))
                        if self.config.get('auto_open', False):
                            self._open_file(downloaded_file)
                        return True
                    else:
                        console.print(f"[yellow]⚠ Unduhan selesai, tetapi file tidak ditemukan di lokasi yang diharapkan. Judul: {info.get('title', 'N/A')}, Path: {output_path}[/yellow]")
                        self.logger.warning(f"File tidak ditemukan setelah unduhan: {info.get('title', 'N/A')} di {output_path}")
                        return True
                        
                except yt_dlp.DownloadError as de:
                    error_message = str(de)
                    if self.config['error_behavior'] == 'skip':
                        console.print(f"[yellow]⚠ Melewatkan unduhan karena error: {error_message}[/yellow]")
                        self.logger.warning(f"Melewatkan unduhan '{url}' karena error: {error_message}")
                        return False
                    else:
                        console.print(f"[red]✗ Menghentikan unduhan karena error: {error_message}[/red]")
                        self.logger.error(f"Menghentikan unduhan '{url}' karena error: {error_message}")
                        raise
                except KeyboardInterrupt:
                    console.print("\n[yellow]✗ Unduhan dibatalkan oleh pengguna.[/yellow]")
                    self.logger.info(f"Unduhan '{url}' dibatalkan oleh pengguna.")
                    return False
                finally:
                    self._progress = None
                    self._current_progress_task = None
        except Exception as e:
            self.logger.error(f"Terjadi kesalahan saat memproses URL '{url}': {e}", exc_info=self.config.get('verbose', False))
            console.print(f"[red]✗ Terjadi kesalahan saat memproses URL: {e}[/red]")
            return False

    def download_from_file(self, file_path: str, format_type: str) -> List[str]:
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            console.print(f"[red]✗ File tidak ditemukan: {file_path}[/red]")
            self.logger.error(f"File tidak ditemukan untuk unduhan batch: {file_path}")
            return []

        try:
            with open(file_path_obj, 'r') as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            if not urls:
                console.print("[yellow]⚠ File daftar URL kosong atau hanya berisi komentar.[/yellow]")
                self.logger.warning(f"File '{file_path}' kosong atau hanya berisi komentar.")
                return []
            
            console.print(f"\n[bold blue]Mulai mengunduh {len(urls)} URL dari '{file_path_obj.name}'...[/bold blue]")
            failed_urls = []
            for i, url in enumerate(urls, 1):
                console.print(f"\n[bold green]--- Mengunduh ({i}/{len(urls)}): {url} ---[/bold green]")
                # Untuk mode batch dari file, validasi platform per URL bisa menjadi rumit.
                # Kita akan biarkan yt-dlp menangani deteksi situs, tetapi format/kualitas akan sesuai dengan format_type yang dipilih user.
                # Penting: Jika ada URL Bstation di sini, pastikan cookiesfrombrowser diaktifkan di get_ydl_opts
                # (yang sudah diatur jika self._selected_platform adalah 'bstation').
                # Namun, jika file berisi campuran YT dan Bstation, _selected_platform akan konsisten untuk semua URL.
                # Ini adalah batasan mode batch saat ini.
                if not self.download_single(url, format_type):
                    failed_urls.append(url)
            
            console.print(f"\n[bold blue]--- Unduhan Batch Selesai ---[/bold blue]")
            if failed_urls:
                console.print(f"[red]✗ Gagal mengunduh {len(failed_urls)} URL:[/red]")
                for url in failed_urls:
                    console.print(f"  - [dim]{url}[/dim]")
                self.logger.error(f"Gagal mengunduh {len(failed_urls)} URL: {', '.join(failed_urls)}")
            else:
                console.print("[bold green]✓ Semua URL berhasil diunduh![/bold green]")
                self.logger.info("Semua URL di file batch berhasil diunduh.")
            return failed_urls
            
        except FileNotFoundError:
            console.print(f"[red]✗ File tidak ditemukan: {file_path}[/red]")
            self.logger.error(f"FileNotFoundError saat membaca file batch: {file_path}")
            return []
        except Exception as e:
            self.logger.error(f"Terjadi kesalahan saat mengunduh dari file '{file_path}': {e}", exc_info=self.config.get('verbose', False))
            console.print(f"[red]✗ Terjadi kesalahan saat mengunduh dari file: {e}[/red]")
            return []

    def display_video_info(self, info: Dict):
        table = Table(title="Informasi Video", show_header=True, header_style="bold magenta")
        table.add_column("Properti", style="cyan", no_wrap=True)
        table.add_column("Nilai", style="white")
        
        title = info.get('title', 'N/A')
        uploader = info.get('uploader', 'N/A')
        duration_sec = info.get('duration', 0)
        minutes = duration_sec // 60
        seconds = duration_sec % 60
        view_count = info.get('view_count', 0)
        upload_date_str = info.get('upload_date', 'N/A')
        video_id = info.get('id', 'N/A')

        table.add_row("Judul", title)
        table.add_row("Pengunggah", uploader)
        table.add_row("Durasi", f"{minutes}:{seconds:02d} menit")
        table.add_row("Jumlah Tayang", f"{view_count:,}" if isinstance(view_count, (int, float)) else 'N/A')
        table.add_row("Tanggal Publikasi", upload_date_str)
        table.add_row("ID Video", video_id)
        
        console.print(table)

    def _open_file(self, file_path: Path):
        try:
            if sys.platform == "win32":
                os.startfile(file_path)
            elif sys.platform == "darwin": # macOS
                subprocess.run(['open', str(file_path)], check=True)
            else: # Linux
                subprocess.run(['xdg-open', str(file_path)], check=True)
            self.logger.info(f"Mencoba membuka file: {file_path}")
            console.print(f"[bold green]✓ File dibuka otomatis: {file_path.name}[/bold green]")
        except FileNotFoundError:
            console.print(f"[yellow]⚠ Gagal membuka file: Aplikasi untuk '{file_path.suffix}' tidak ditemukan.[/yellow]")
            self.logger.warning(f"Aplikasi tidak ditemukan untuk membuka file: {file_path}")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]✗ Gagal membuka file: {e}[/red]")
            self.logger.error(f"Error saat membuka file '{file_path}': {e}")
        except Exception as e:
            console.print(f"[red]✗ Terjadi kesalahan saat membuka file: {e}[/red]")
            self.logger.error(f"Kesalahan tak terduga saat membuka file '{file_path}': {e}")

    def select_platform(self) -> str:
        """Meminta pengguna untuk memilih platform unduhan."""
        console.print(Panel.fit(
            "[bold blue]Pilih Modus Downloader:[/bold blue]",
            border_style="green"
        ))
        
        while True:
            choice = Prompt.ask(
                "[bold cyan]1.[/bold cyan] [bold white]YouTube Downloader[/bold white]\n"
                "[bold cyan]2.[/bold cyan] [bold white]Bstation Downloader[/bold white]\n"
                "[bold red]0.[/bold red] [bold yellow]Keluar Bot[/bold yellow]\n"
                "[bold magenta]Pilihan Anda[/bold magenta]",
                choices=['1', '2', '0'],
                default='1'
            )
            
            if choice == '1':
                self._selected_platform = 'youtube'
                return 'youtube'
            elif choice == '2':
                self._selected_platform = 'bstation'
                return 'bstation'
            elif choice == '0':
                return 'exit'
            else:
                console.print("[red]Pilihan tidak valid. Silakan coba lagi.[/red]")

    def configure_settings(self):
        console.print("\n[bold blue]Pengaturan Konfigurasi[/bold blue]")
        
        self.config['default_format'] = Prompt.ask(
            "[bold cyan]Format default (mp3/mp4)[/bold cyan]",
            choices=['mp3', 'mp4'],
            default=self.config['default_format']
        )

        self.config['mp3_quality'] = Prompt.ask(
            f"[bold cyan]Kualitas MP3 (mis. 192k, 320k)[/bold cyan] [dim](Default: {self.config['mp3_quality']})[/dim]",
            default=self.config['mp3_quality']
        )

        self.config['mp4_quality'] = Prompt.ask(
            f"[bold cyan]Kualitas MP4 (mis. 720p, 1080p)[/bold cyan] [dim](Default: {self.config['mp4_quality']})[/dim]",
            choices=['360p', '480p', '720p', '1080p', '1440p', '2160p'],
            default=self.config['mp4_quality']
        )

        self.config['error_behavior'] = Prompt.ask(
            f"[bold cyan]Perilaku saat error (skip/abort)[/bold cyan] [dim](Default: {self.config['error_behavior']})[/dim]",
            choices=['skip', 'abort'],
            default=self.config['error_behavior']
        )

        self.config['output_mode'] = Prompt.ask(
            f"[bold cyan]Mode folder output (separate/date/channel)[/bold cyan] [dim](Default: {self.config['output_mode']})[/dim]",
            choices=['separate', 'date', 'channel'],
            default=self.config['output_mode']
        )
        
        self.config['auto_open'] = Confirm.ask(
            f"[bold cyan]Buka file setelah unduhan selesai?[/bold cyan] [dim](Saat ini: {self.config['auto_open']})[/dim]",
            default=self.config['auto_open']
        )

        new_verbose = Confirm.ask(
            f"[bold cyan]Tampilkan log detail (verbose)?[/bold cyan] [dim](Saat ini: {self.config['verbose']})[/dim]",
            default=self.config['verbose']
        )
        if new_verbose != self.config['verbose']:
            self.config['verbose'] = new_verbose
            self.setup_logging()
            console.print(f"[bold yellow]Tingkat logging telah diperbarui menjadi {'verbose' if new_verbose else 'normal'}.[/bold yellow]")

        self.config['bstation_cookie_browser'] = Prompt.ask(
            f"[bold cyan]Browser untuk mengambil cookies Bstation (mis. chrome, firefox, edge)[/bold cyan] [dim](Default: {self.config['bstation_cookie_browser']})[/dim]",
            default=self.config['bstation_cookie_browser']
        )

        if Confirm.ask("Simpan konfigurasi ini?"):
            self.save_config()

    def interactive_mode(self):
        console.print(Panel.fit(
            "[bold blue]Selamat Datang di Advanced Video Downloader Bot![/bold blue]\n"
            "Anda dapat mengunduh video/audio dari YouTube atau Bstation.\n"
            "Ketik 'config' untuk mengubah pengaturan, atau 'quit' untuk keluar.",
            title="Selamat Datang", border_style="green"
        ))
        
        while True:
            # Panggil metode baru untuk memilih platform
            chosen_mode = self.select_platform() # Menggunakan chosen_mode untuk menghindari kebingungan dengan _selected_platform

            if chosen_mode == 'exit':
                console.print("[bold yellow]Terima kasih telah menggunakan bot ini. Sampai jumpa![/bold yellow]")
                break
            
            # _selected_platform sudah diatur di select_platform
            
            try:
                if chosen_mode == 'youtube':
                    console.print("\n[bold green]Anda memilih YouTube Downloader.[/bold green]")
                    url_input = Prompt.ask(f"[bold green]Masukkan URL YouTube (atau 'config', 'quit', 'file:<path>')[/bold green]")
                elif chosen_mode == 'bstation':
                    console.print("\n[bold green]Anda memilih Bstation Downloader.[/bold green]")
                    console.print("[bold yellow]Bot akan otomatis menggunakan cookies Firefox, mengunduh MP4 720p, dan menyematkan subtitle Bahasa Indonesia.[/bold yellow]")
                    url_input = Prompt.ask(f"[bold green]Masukkan URL Bstation (atau 'config', 'quit', 'file:<path>')[/bold green]")
                else: # Ini seharusnya tidak terjadi, tapi sebagai fallback
                    continue
                
                if url_input.lower() in ['quit', 'exit', 'q']:
                    console.print("[bold yellow]Terima kasih telah menggunakan bot ini. Sampai jumpa![/bold yellow]")
                    break
                elif url_input.lower() == 'config':
                    self.configure_settings()
                    continue # Kembali ke pilihan platform setelah konfigurasi
                elif url_input.startswith('file:'):
                    file_path = url_input[5:].strip()
                    if not Path(file_path).exists():
                        console.print(f"[red]✗ File tidak ditemukan: {file_path}[/red]")
                        self.logger.warning(f"File batch tidak ditemukan: {file_path}")
                        continue
                    
                    if chosen_mode == 'youtube':
                        format_type = Prompt.ask(
                            "[bold cyan]Pilih format unduhan (mp3/mp4)[/bold cyan]",
                            choices=['mp3', 'mp4'],
                            default=self.config['default_format']
                        )
                    else: # chosen_mode == 'bstation'
                        format_type = 'mp4' # Otomatis MP4 untuk Bstation
                        console.print("[bold cyan]Format unduhan untuk Bstation otomatis: MP4[/bold cyan]")
                    
                    self.download_from_file(file_path, format_type)
                else:
                    # Ini adalah unduhan URL tunggal
                    if chosen_mode == 'youtube':
                        format_type = Prompt.ask(
                            "[bold cyan]Pilih format unduhan (mp3/mp4)[/bold cyan]",
                            choices=['mp3', 'mp4'],
                            default=self.config['default_format']
                        )
                    else: # chosen_mode == 'bstation'
                        format_type = 'mp4' # Otomatis MP4 untuk Bstation
                        console.print("[bold cyan]Format unduhan untuk Bstation otomatis: MP4[/bold cyan]")
                        
                    self.download_single(url_input, format_type)
                
                if not Confirm.ask("\n[bold blue]Unduh lagi?[/bold blue]"):
                    console.print("[bold yellow]Terima kasih telah menggunakan bot ini. Sampai jumpa![/bold yellow]")
                    break
                    
            except KeyboardInterrupt:
                console.print("\n[yellow]✗ Proses dibatalkan oleh pengguna.[/yellow]")
                self.logger.info("Proses interaktif dibatalkan oleh pengguna.")
                break
            except Exception as e:
                self.logger.error(f"Terjadi kesalahan tak terduga dalam mode interaktif: {e}", exc_info=self.config.get('verbose', False))
                console.print(f"[red]✗ Terjadi kesalahan: {e}[/red]")
                continue

# --- MAIN FUNCTION ---
def main():
    parser = argparse.ArgumentParser(
        description="""YouTube/Bstation CLI Downloader Bot - Pengunduh video/audio hibrida CLI/Interaktif.

Penggunaan Contoh CLI:
  Unduh MP4 dari YouTube:
    python youtube_downloader.py -u "https://www.youtube.com/watch?v=VIDEO_ID" -f mp4 -q 1080p

  Unduh MP3 dari Bstation (menggunakan cookies Firefox):
    python youtube_downloader.py -u "https://www.bilibili.tv/en/play/VIDEO_ID" -f mp3 --platform bstation --bstation-cookie-browser firefox

  Unduh daftar URL dari file:
    python youtube_downloader.py -F urls.txt -f mp4

  Jalankan mode interaktif:
    python youtube_downloader.py
""",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument('--url', '-u', help='URL YouTube atau Bstation untuk diunduh (untuk unduhan tunggal)')
    parser.add_argument('--file', '-F', help='Path ke file teks yang berisi daftar URL (satu URL per baris)')
    parser.add_argument('--format', '-f', choices=['mp3', 'mp4'], help='Format unduhan (mp3 atau mp4)')
    parser.add_argument('--quality', '-q', help='Kualitas video/audio (mis. 320k untuk MP3, 720p untuk MP4)')
    parser.add_argument('--output', '-o', help='Folder output kustom')
    parser.add_argument('--error-behavior', choices=['skip', 'abort'], help='Perilaku saat error (skip unduhan atau hentikan semua)')
    parser.add_argument('--output-mode', choices=['separate', 'date', 'channel'], help='Mode pengorganisasian folder output')
    parser.add_argument('--auto-open', action='store_true', help='Buka file setelah unduhan selesai')
    parser.add_argument('--no-auto-open', dest='auto_open', action='store_false', help='Jangan buka file setelah unduhan selesai')
    parser.set_defaults(auto_open=None)

    parser.add_argument('--verbose', '-v', action='store_true', help='Tampilkan log detail yt-dlp dan internal bot')
    parser.add_argument('--no-verbose', dest='verbose', action='store_false', help='Sembunyikan log detail yt-dlp dan internal bot')
    parser.set_defaults(verbose=None)

    parser.add_argument('--config', '-c', default="config.json", help='Path ke file konfigurasi (default: config.json)')
    parser.add_argument('--save-config', action='store_true', help='Simpan konfigurasi default saat ini ke file dan keluar')

    parser.add_argument('--platform', '-p', choices=['youtube', 'bstation'], 
                        help='Secara eksplisit tentukan platform unduhan (default: deteksi otomatis atau YouTube)')
    parser.add_argument('--bstation-cookie-browser', help='Browser untuk mengambil cookies Bstation (mis. chrome, firefox, edge)')

    args = parser.parse_args()

    downloader = YouTubeDownloader(args.config)

    if args.verbose is not None:
        downloader.config['verbose'] = args.verbose
        downloader.setup_logging()
    
    if args.output:
        downloader.config['output_folder'] = args.output
    if args.format:
        downloader.config['default_format'] = args.format
    if args.quality:
        if args.format == 'mp3':
            downloader.config['mp3_quality'] = args.quality
        elif args.format == 'mp4':
            downloader.config['mp4_quality'] = args.quality
    if args.error_behavior:
        downloader.config['error_behavior'] = args.error_behavior
    if args.output_mode:
        downloader.config['output_mode'] = args.output_mode
    if args.auto_open is not None:
        downloader.config['auto_open'] = args.auto_open

    if args.bstation_cookie_browser:
        downloader.config['bstation_cookie_browser'] = args.bstation_cookie_browser

    if args.save_config:
        downloader.save_config()
        if not (args.url or args.file):
            sys.exit(0)

    # Menentukan platform untuk CLI mode
    if args.platform:
        downloader._selected_platform = args.platform
    elif args.url:
        if YOUTUBE_URL_REGEX.match(args.url):
            downloader._selected_platform = 'youtube'
        elif BILIBILI_URL_REGEX.match(args.url):
            downloader._selected_platform = 'bstation'
        else:
            console.print("[red]✗ URL tidak dikenali sebagai YouTube atau Bstation. Menggunakan YouTube sebagai default.[/red]")
            downloader.logger.warning(f"URL tidak dikenal: {args.url}. Menggunakan YouTube default.")
            downloader._selected_platform = 'youtube' # Default ke YouTube jika tidak jelas
    elif args.file:
        console.print("[yellow]⚠ Anda menggunakan unduhan dari file tanpa menentukan platform melalui --platform. Asumsi YouTube sebagai default.[/yellow]")
        console.print("[yellow]   Jika file berisi URL Bstation, pastikan untuk menentukan '--platform bstation' di CLI.[/yellow]")
        downloader._selected_platform = 'youtube' # Default ke YouTube untuk file jika tidak ditentukan

    if args.url or args.file:
        if args.url:
            target_url = args.url
            # Tentukan format untuk CLI jika tidak dispesifikasikan dan platformnya Bstation
            if downloader._selected_platform == 'bstation' and not args.format:
                args.format = 'mp4' # Auto-set MP4 for Bstation CLI
                console.print(f"[dim]Platform Bstation dipilih, format diatur otomatis ke: {args.format}[/dim]")
            elif not args.format:
                args.format = downloader.config['default_format']
                console.print(f"[dim]Menggunakan format default: {args.format}[/dim]")
            
            downloader.download_single(target_url, args.format)
        elif args.file:
            target_file = args.file
            # Tentukan format untuk CLI jika tidak dispesifikasikan dan platformnya Bstation
            if downloader._selected_platform == 'bstation' and not args.format:
                args.format = 'mp4' # Auto-set MP4 for Bstation CLI
                console.print(f"[dim]Platform Bstation dipilih, format diatur otomatis ke: {args.format}[/dim]")
            elif not args.format:
                args.format = downloader.config['default_format']
                console.print(f"[dim]Menggunakan format default: {args.format}[/dim]")

            downloader.download_from_file(target_file, args.format)
    else:
        # Mode interaktif
        downloader.interactive_mode()

if __name__ == "__main__":
    main()