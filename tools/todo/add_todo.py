import json
import uuid
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"

def add_todo(title, description=None, due_by=None):
    todo_id = str(uuid.uuid4())

    todo = {
        "id": todo_id,
        "title": title,
        "description": description or "",
        "status": "open",
        "due_by": due_by,
        "created_at": datetime.utcnow().isoformat()
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_DIR / f"{todo_id}.json", "w") as f:
        json.dump(todo, f, indent=2)

    return todo
