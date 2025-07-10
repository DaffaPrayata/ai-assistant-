# mio/memory.py
import json
from pathlib import Path

USER_PROFILE_PATH = Path("data/user_profile.json")

def load_user_name() -> str:
    if USER_PROFILE_PATH.exists():
        try:
            with open(USER_PROFILE_PATH, 'r') as f:
                data = json.load(f)
                return data.get("name", "Daffa")
        except Exception:
            return "Daffa"
    return "Daffa"

def save_user_name(name: str):
    USER_PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(USER_PROFILE_PATH, 'w') as f:
        json.dump({"name": name}, f)
