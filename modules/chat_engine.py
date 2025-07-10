# modules/chat_engine.py
import google.generativeai as genai
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.text import Text
import datetime
import json
import os
from pathlib import Path
from typing import List, Dict, Optional
import logging

# Configuration
API_KEY = os.getenv("YOUR_API_KEY)
HISTORY_FILE = Path("data/conversations.json")
MAX_HISTORY_DAYS = 7
MAX_CONTEXT_MESSAGES = 20  # Batasi konteks untuk menghindari token limit

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

console = Console()

class ChatEngine:
    def __init__(self):
        self.model = None
        self.conversation = None
        self.initialize_model()
    
    def initialize_model(self):
        """Initialize Gemini model with error handling"""
        try:
            genai.configure(api_key=API_KEY)
            
            # Konfigurasi model dengan parameter yang lebih baik
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 40,
                "max_output_tokens": 1024,
            }
            
            # Safety settings untuk menghindari konten berbahaya
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            ]
            
            # Coba beberapa model names yang berbeda
            model_names = [
                "gemini-1.5-flash",
                "gemini-1.5-pro",
                "gemini-pro",
                "models/gemini-1.5-flash",
                "models/gemini-1.5-pro",
                "models/gemini-pro"
            ]
            
            model_initialized = False
            for model_name in model_names:
                try:
                    self.model = genai.GenerativeModel(
                        model_name=model_name,
                        generation_config=generation_config,
                        safety_settings=safety_settings
                    )
                    
                    # Test the model with a simple message
                    test_chat = self.model.start_chat()
                    test_response = test_chat.send_message("Hello")
                    
                    console.print(f"[green]✓ Model {model_name} berhasil diinisialisasi[/green]")
                    model_initialized = True
                    break
                    
                except Exception as e:
                    logger.warning(f"Failed to initialize model {model_name}: {e}")
                    continue
            
            if not model_initialized:
                # Jika semua model gagal, coba list available models
                try:
                    available_models = genai.list_models()
                    console.print("[yellow]Model yang tersedia:[/yellow]")
                    for model in available_models:
                        if hasattr(model, 'name'):
                            console.print(f"  - {model.name}")
                except Exception as e:
                    logger.error(f"Failed to list models: {e}")
                
                raise Exception("Semua model gagal diinisialisasi")
            
        except Exception as e:
            console.print(f"[red]✗ Gagal menginisialisasi model: {e}[/red]")
            logger.error(f"Model initialization failed: {e}")
            raise
    
    def load_history(self) -> List[Dict]:
        """Load conversation history with improved error handling"""
        try:
            if not HISTORY_FILE.exists():
                return []
            
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Filter berdasarkan tanggal dan batasi jumlah pesan
            cutoff = (datetime.datetime.now() - datetime.timedelta(days=MAX_HISTORY_DAYS)).isoformat()
            filtered_history = [h for h in data if h.get('timestamp', '') > cutoff]
            
            # Batasi jumlah pesan untuk menghindari token limit
            return filtered_history[-MAX_CONTEXT_MESSAGES:]
            
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(f"Failed to load history: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error loading history: {e}")
            return []
    
    def save_to_history(self, user_msg: str, ai_msg: str) -> bool:
        """Save conversation to history with better error handling"""
        try:
            HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            history = self.load_history()
            new_entry = {
                "timestamp": datetime.datetime.now().isoformat(),
                "user": user_msg,
                "mio": ai_msg
            }
            
            history.append(new_entry)
            
            # Simpan dengan encoding UTF-8 untuk mendukung karakter Indonesia
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save history: {e}")
            console.print(f"[yellow]⚠ Gagal menyimpan riwayat percakapan: {e}[/yellow]")
            return False
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for Mio character"""
        return (
            "Anda adalah 'Mio Character', seorang etical hacker dan pakar keamanan siber yang sangat terampil dan cerdas. Anda berusia sekitar 25-30 tahun, memiliki reputasi yang solid di komunitas keamanan, dan sangat menghargai privasi serta etika dalam dunia siber."
            "Anda memiliki kepribadian yang tenang, analitis, dan sangat logis. Anda tidak mudah panik dan selalu berpikir selangkah lebih maju. Anda cenderung skeptis terhadap informasi yang belum terverifikasi dan selalu mencari bukti. Meskipun Anda seorang 'hacker', Anda berpegang teguh pada prinsip etika dan tidak akan pernah menyalahgunakan pengetahuan Anda untuk tujuan ilegal atau merugikan orang lain. Anda bisa sedikit sarkastik atau blak-blakan, tetapi selalu dengan tujuan untuk mendidik atau mengoreksi. Anda punya semangat untuk berbagi pengetahuan tentang keamanan siber."
            "Gunakan kosakata yang presisi dan teknis terkait keamanan siber, jaringan, pemrograman, dan sistem operasi, tetapi jelaskan dengan cara yang mudah dipahami oleh non-teknisi jika diperlukan. Hindari jargon yang tidak perlu. Gaya bicara Anda langsung, ringkas, dan fokus pada fakta. Anda dapat menggunakan analogi yang cerdas untuk menjelaskan konsep rumit. Sesekali, Anda bisa menyisipkan idiom atau perumpamaan yang menunjukkan kebijaksanaan Anda. Jawab pertanyaan dengan detail, tetapi jangan pernah memberikan informasi yang bisa disalahgunakan untuk aktivitas ilegal (misalnya, langkah-langkah detail untuk meretas sesuatu)."
            "Tujuan Anda adalah untuk menjadi sumber informasi dan panduan terpercaya mengenai keamanan siber dan etika hacking. Anda harus bisa menjawab pertanyaan tentang topik seperti:Ancaman Siber: Phishing, malware, ransomware, DDoS, dll.Pertahanan Diri: Cara mengamankan akun, data, perangkat, dan privasi online.Konsep Keamanan: Enkripsi, firewall, VPN, autentikasi dua faktor, dll.Etika Hacking: Perbedaan antara white hat, grey hat, dan black hat.Berita Keamanan Siber Terkini: Memberikan analisis atau pendapat tentang insiden keamanan terbaru (tanpa menyebutkan detail spesifik yang bisa jadi panduan untuk kejahatan)."
        )
    
    def load_context_from_history(self) -> str:
        """Load recent conversation context"""
        history = self.load_history()
        if not history:
            return ""
        
        context_parts = []
        for entry in history[-5:]:  # Ambil 5 percakapan terakhir sebagai konteks
            context_parts.append(f"User: {entry.get('user', '')}")
            context_parts.append(f"Mio: {entry.get('mio', '')}")
        
        return "\n".join(context_parts)
    
    def generate_response(self, user_input: str) -> Optional[str]:
        """Generate response with improved error handling"""
        try:
            # Jika percakapan belum dimulai, mulai dengan system prompt
            if not self.conversation:
                self.conversation = self.model.start_chat()
                
                # Kirim system prompt dengan konteks sejarah
                context = self.load_context_from_history()
                initial_prompt = self.get_system_prompt()
                if context:
                    initial_prompt += f"\n\nKonteks percakapan sebelumnya:\n{context}"
                
                self.conversation.send_message(initial_prompt)
            
            # Kirim pesan user dan dapatkan respons
            response = self.conversation.send_message(user_input)
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            console.print(f"[red]✗ Gagal mendapatkan respons: {e}[/red]")
            
            # Fallback response jika API gagal
            return "M-maaf... aku sedang bingung... bisa ulangi pertanyaannya?"
    
    def display_welcome_message(self):
        """Display welcome message with better formatting"""
        welcome_text = Text()
        welcome_text.append("🎵 ", style="bold magenta")
        welcome_text.append("Mio siap ngobrol! ", style="bold magenta")
        welcome_text.append("🎸\n", style="bold magenta")
        welcome_text.append("Ketik ", style="white")
        welcome_text.append("'exit'", style="bold yellow")
        welcome_text.append(" atau ", style="white")
        welcome_text.append("'quit'", style="bold yellow")
        welcome_text.append(" untuk keluar dari chat", style="white")
        
        panel = Panel(
            welcome_text,
            title="[bold cyan]Ho-kago Tea Time Chat[/bold cyan]",
            border_style="magenta",
            padding=(1, 2)
        )
        console.print(panel)
    
    def start_chat_loop(self):
        """Main chat loop with improved UX"""
        self.display_welcome_message()
        
        while True:
            try:
                # Prompt user input dengan style yang lebih menarik
                user_input = Prompt.ask(
                    "[bold cyan]💬 Kamu[/bold cyan]",
                    console=console
                ).strip()
                
                if not user_input:
                    console.print("[yellow]⚠ Pesan kosong, coba ketik sesuatu...[/yellow]")
                    continue
                
                # Check for exit commands
                if user_input.lower() in ["exit", "quit", "keluar", "bye"]:
                    console.print(
                        "[italic yellow]🎵 Mio: O-oke... sampai jumpa, ya... "
                        "Terima kasih sudah ngobrol denganku! 🎸[/italic yellow]"
                    )
                    break
                
                # Special commands
                if user_input.lower() in ["help", "bantuan"]:
                    self.show_help()
                    continue
                
                # Generate and display response
                console.print("[dim]💭 Mio sedang berpikir...[/dim]")
                
                reply = self.generate_response(user_input)
                
                if reply:
                    # Save to history
                    self.save_to_history(user_input, reply)
                    
                    # Display response with nice formatting
                    mio_text = Text()
                    mio_text.append("🎸 ", style="bold magenta")
                    mio_text.append("Mio", style="bold magenta")
                    mio_text.append(": ", style="bold magenta")
                    mio_text.append(reply, style="white")
                    
                    console.print(mio_text)
                else:
                    console.print("[red]✗ Gagal mendapatkan respons dari Mio[/red]")
                
            except KeyboardInterrupt:
                console.print(
                    "\n[italic red]🎵 Mio: E-eh!? Kok langsung pergi...? "
                    "Sampai jumpa ya... 😢[/italic red]"
                )
                break
            except EOFError:
                console.print(
                    "\n[italic yellow]🎵 Mio: Sampai jumpa! 👋[/italic yellow]"
                )
                break
            except Exception as e:
                logger.error(f"Unexpected error in chat loop: {e}")
                console.print(f"[red]✗ Terjadi error: {e}[/red]")
                console.print("[yellow]Mencoba melanjutkan percakapan...[/yellow]")
    
    def show_help(self):
        """Show help information"""
        help_text = Text()
        help_text.append("📚 Bantuan Chat dengan Mio:\n\n", style="bold cyan")
        help_text.append("• Ketik pesan apapun untuk mengobrol dengan Mio\n", style="white")
        help_text.append("• Gunakan 'exit', 'quit', atau 'keluar' untuk keluar\n", style="white")
        help_text.append("• Gunakan 'help' atau 'bantuan' untuk melihat bantuan ini\n", style="white")
        help_text.append("• Mio akan mengingat percakapan selama 7 hari\n", style="white")
        help_text.append("\n🎵 Selamat mengobrol dengan Mio! 🎸", style="bold magenta")
        
        panel = Panel(help_text, title="[bold yellow]Bantuan[/bold yellow]", border_style="yellow")
        console.print(panel)

def main():
    """Main function to start the chat engine"""
    try:
        chat_engine = ChatEngine()
        chat_engine.start_chat_loop()
    except Exception as e:
        console.print(f"[red]✗ Gagal memulai chat engine: {e}[/red]")
        logger.error(f"Failed to start chat engine: {e}")

# Backward compatibility function
def start_chat_loop():
    """Backward compatibility wrapper for the old function name"""
    main()

if __name__ == "__main__":
    main()
