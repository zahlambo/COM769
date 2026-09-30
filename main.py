import json
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

DB_PATH = Path(__file__).parent / "db.json"
_lock = threading.Lock()


class TodoItemIn(BaseModel):
    name: str
    is_complete: bool = False


class TodoItem(TodoItemIn):
    id: int


def load_db() -> dict:
    if not DB_PATH.exists():
        return {"next_id": 1, "todos": []}
    return json.loads(DB_PATH.read_text(encoding="utf-8"))


def save_db(db: dict) -> None:
    # Write to a temp file first so a crash mid-write can't corrupt db.json.
    tmp = DB_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(db, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(DB_PATH)


def find_index(todos: list[dict], todo_id: int) -> int:
    for i, todo in enumerate(todos):
        if todo["id"] == todo_id:
            return i
    raise HTTPException(status_code=404, detail=f"Todo {todo_id} not found")


app = FastAPI(title="My API", version="v1")


@app.get("/api/Todo", response_model=list[TodoItem], tags=["Todo"])
def list_todos():
    with _lock:
        return load_db()["todos"]


@app.post("/api/Todo", response_model=TodoItem, status_code=status.HTTP_201_CREATED, tags=["Todo"])
def create_todo(item: TodoItemIn):
    with _lock:
        db = load_db()
        todo = {"id": db["next_id"], **item.model_dump()}
        db["todos"].append(todo)
        db["next_id"] += 1
        save_db(db)
        return todo


@app.get("/api/Todo/{id}", response_model=TodoItem, tags=["Todo"])
def get_todo(id: int):
    with _lock:
        todos = load_db()["todos"]
        return todos[find_index(todos, id)]


@app.put("/api/Todo/{id}", response_model=TodoItem, tags=["Todo"])
def update_todo(id: int, item: TodoItemIn):
    with _lock:
        db = load_db()
        i = find_index(db["todos"], id)
        db["todos"][i] = {"id": id, **item.model_dump()}
        save_db(db)
        return db["todos"][i]


@app.delete("/api/Todo/{id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Todo"])
def delete_todo(id: int):
    with _lock:
        db = load_db()
        db["todos"].pop(find_index(db["todos"], id))
        save_db(db)
