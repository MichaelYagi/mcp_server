import json
import uuid
from datetime import datetime
from pathlib import Path

KB_DIR = Path("knowledge/entries")
VER_DIR = Path("knowledge/versions")

def kb_update_versioned(entry_id, title=None, content=None, tags=None):
    file = KB_DIR / f"{entry_id}.json"
    if not file.exists():
        return {"error": "Entry not found", "id": entry_id}

    with open(file) as f:
        entry = json.load(f)

    # Save version
    VER_DIR.mkdir(parents=True, exist_ok=True)
    version_file = VER_DIR / f"{entry_id}-{uuid.uuid4()}.json"
    entry["_version_timestamp"] = datetime.utcnow().isoformat()
    with open(version_file, "w") as vf:
        json.dump(entry, vf, indent=2)

    # Apply updates
    if title is not None:
        entry["title"] = title
    if content is not None:
        entry["content"] = content
    if tags is not None:
        entry["tags"] = tags

    with open(file, "w") as f:
        json.dump(entry, f, indent=2)

    return entry
