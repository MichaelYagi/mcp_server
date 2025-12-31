from typing import List
from tools.todo import delete_todo
from tools.todo import list_todos

def delete_all_todos() -> List[str]:
    """
    Delete all todo items.
    Returns a list of the IDs of deleted todos.
    """
    todos = list_todos.list_todos()
    deleted_ids = []

    for todo in todos:
        delete_todo.delete_todo(todo["id"])
        deleted_ids.append(todo["id"])

    return deleted_ids