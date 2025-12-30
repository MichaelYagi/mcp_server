from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"

def delete_todo(todo_id):
    file_path = DATA_DIR / f"{todo_id}.json"
    if not file_path.exists():
        return {"deleted": False}

    file_path.unlink()
    return {"deleted": True}
