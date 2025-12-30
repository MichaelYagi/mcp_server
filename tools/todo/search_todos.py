import json
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"

def search_todos(
    text=None,
    status=None,
    due_before=None,
    due_after=None,
    order_by="due_by",
    ascending=True
):
    if not DATA_DIR.exists():
        return []

    results = []

    for file in DATA_DIR.glob("*.json"):
        with open(file) as f:
            todo = json.load(f)

        if text:
            haystack = f"{todo['title']} {todo['description']}".lower()
            if text.lower() not in haystack:
                continue

        if status and todo["status"] != status:
            continue

        if due_before and todo["due_by"]:
            if todo["due_by"] > due_before:
                continue

        if due_after and todo["due_by"]:
            if todo["due_by"] < due_after:
                continue

        results.append(todo)

    results.sort(
        key=lambda x: x.get(order_by) or "",
        reverse=not ascending
    )

    return results
