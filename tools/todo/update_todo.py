import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"

def update_todo(todo_id, title=None, description=None, status=None, due_by=None):
    file_path = DATA_DIR / f"{todo_id}.json"
    if not file_path.exists():
        return {"error": "Todo not found"}

    with open(file_path) as f:
        todo = json.load(f)

    if title is not None:
        todo["title"] = title
    if description is not None:
        todo["description"] = description
    if status is not None:
        todo["status"] = status
    if due_by is not None:
        todo["due_by"] = due_by

    with open(file_path, "w") as f:
        json.dump(todo, f, indent=2)

    return todo
