# modules/menu.py
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from modules.downloader import run_downloader_interface
from modules.chat_engine import start_chat_loop
from mio.personality import farewell_message

console = Console()

def main_menu():
    while True:
        console.print(Panel.fit(
            "[bold white]Apa yang ingin kamu lakukan hari ini?[/bold white]\n"
            "[bold cyan]1.[/bold cyan] Chatting bareng Mio\n"
            "[bold cyan]2.[/bold cyan] Download YouTube / MP3\n"
            "[bold cyan]3.[/bold cyan] Download Bstation (BiliBili.tv)\n"
            "[bold cyan]4.[/bold cyan] Keluar dari asisten",
            title="[bold magenta]Menu Mio Assistant[/bold magenta]",
            border_style="magenta"
        ))

        pilihan = Prompt.ask("[bold yellow]Pilih opsi (1-4)[/bold yellow]", choices=["1", "2", "3", "4"])

        if pilihan == "1":
            start_chat_loop()
        elif pilihan == "2":
            run_downloader_interface(platform="youtube")
        elif pilihan == "3":
            run_downloader_interface(platform="bstation")
        elif pilihan == "4":
            console.print(f"[italic magenta]{farewell_message()}[/italic magenta]")
            break
