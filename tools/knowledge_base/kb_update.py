import json
from pathlib import Path

KB_DIR = Path("knowledge/entries")

def kb_update(entry_id, title=None, content=None, tags=None):
    file = KB_DIR / f"{entry_id}.json"
    if not file.exists():
        return {"error": "Entry not found", "id": entry_id}

    with open(file) as f:
        entry = json.load(f)

    if title is not None:
        entry["title"] = title
    if content is not None:
        entry["content"] = content
    if tags is not None:
        entry["tags"] = tags

    with open(file, "w") as f:
        json.dump(entry, f, indent=2)

    return entry
