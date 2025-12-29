import json
from pathlib import Path

KB_DIR = Path("knowledge/entries")

def kb_get(entry_id):
    file = KB_DIR / f"{entry_id}.json"
    if not file.exists():
        return {"error": "Entry not found"}

    with open(file) as f:
        return json.load(f)
