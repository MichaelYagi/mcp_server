import json
from pathlib import Path

KB_DIR = Path("knowledge/entries")

def kb_search(query):
    results = []
    for file in KB_DIR.glob("*.json"):
        with open(file) as f:
            entry = json.load(f)
            if query.lower() in entry["title"].lower() or query.lower() in entry["content"].lower():
                results.append(entry)
    return results
