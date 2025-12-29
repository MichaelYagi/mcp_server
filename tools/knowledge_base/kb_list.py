import json
from pathlib import Path

KB_DIR = Path("knowledge/entries")

def kb_list():
    entries = []
    for file in KB_DIR.glob("*.json"):
        with open(file) as f:
            entries.append(json.load(f))
    return entries
