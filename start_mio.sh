#!/bin/bash
cd /home/dapzy/project/mio_assistant || exit 1
source .venv/bin/activate

# Play suara intro di background
mpv --no-terminal --volume=100 assets/audio/ayam.mp3 &

# Jalankan Mio Assistant TANPA nunggu mpv selesai
python main.py

# Setelah selesai, biar terminal gak langsung nutup:
exec bash 
