# main.py
from mio.ascii_art import get_random_ascii
from mio.personality import greet_user
from mio.memory import load_user_name, save_user_name
from modules.menu import main_menu
from rich.console import Console
from rich.panel import Panel
from time import sleep
from rich.console import Console
from rich.progress import track
import os

def play_mio_voice():
    print("[DEBUG] Memutar suara Mio..")
    os.system("paplay /home/dapzy/project/mio_assistant/assets/audio/ayam.mp3 &")

def startup_loader():
    console = Console()
    console.print("[italic magenta]M-Mio lagi bangun dulu ya...[/italic magenta]")
    for step in track(range(20), description="💤 Bangunin Mio..."):
        sleep(0.05)
    console.print("[bold magenta]Etto... aku sudah siap~ (⁄ ⁄>⁄ ▽ ⁄<⁄ ⁄)[/bold magenta]\n")

console = Console()

def main():
    setup_user()
    play_mio_voice()
    show_intro()
    main_menu()

def show_intro():
    console.clear()
    ascii_art = get_random_ascii()
    name = load_user_name()
    greeting = greet_user(name)
    
    console.print(Panel.fit(ascii_art, title="Mio-chan", subtitle="(///▽///)", style="bold magenta"))
    console.print(f"[bold magenta]{greeting}[/bold magenta]\n")

def setup_user():
    name = load_user_name()
    if name == "Daffa":
        return  # default name OK
    console.print("[cyan]Halo! Sebelum mulai, boleh aku tahu siapa namamu?[/cyan]")
    name = console.input("[bold green]Namamu: [/bold green]").strip()
    if name:
        save_user_name(name)

def main():
    setup_user()
    show_intro()
    main_menu()

if __name__ == "__main__":
    main()
