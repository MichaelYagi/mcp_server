import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
KB_DIR = SCRIPT_DIR / "entries"

def kb_search(query):
    query = query.strip().lower()
    results = []

    for file in KB_DIR.glob("*.json"):
        with open(file, encoding="utf-8") as f:
            entry = json.load(f)

        haystack = " ".join([
            entry.get("title", ""),
            entry.get("content", "")
        ]).lower()

        if query in haystack:
            results.append(entry)

    return results
