import json
import uuid
from pathlib import Path

KB_DIR = Path("knowledge/entries")

def kb_add(title, content, tags):
    entry_id = str(uuid.uuid4())
    entry = {
        "id": entry_id,
        "title": title,
        "content": content,
        "tags": tags
    }

    KB_DIR.mkdir(parents=True, exist_ok=True)

    with open(KB_DIR / f"{entry_id}.json", "w") as f:
        json.dump(entry, f, indent=2)

    return entry
