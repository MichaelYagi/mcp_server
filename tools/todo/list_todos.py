import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"

def list_todos():
    if not DATA_DIR.exists():
        return []

    todos = []
    for file in DATA_DIR.glob("*.json"):
        with open(file) as f:
            todos.append(json.load(f))

    return todos
