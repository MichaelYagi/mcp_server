import json
from pathlib import Path

KB_DIR = Path("knowledge/entries")

def kb_search_tags(tag):
    results = []
    for file in KB_DIR.glob("*.json"):
        with open(file) as f:
            entry = json.load(f)
            if tag in entry.get("tags", []):
                results.append(entry)
    return results
