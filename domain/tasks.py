"""Persistent task-list domain logic."""
from __future__ import annotations

import uuid
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from domain.storage.json_store import JsonStore


class TaskManager:
    def __init__(self, path: Path):
        self._store = JsonStore(path, [])
        self.tasks: list[dict[str, Any]] = self._store.load()
        self._lock = threading.RLock()

    def _save(self) -> None:
        self._store.save(self.tasks)

    def create(self, user_id: int, title: str, due: str | None, priority: str) -> dict[str, Any]:
        item = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": title.strip(),
            "due": due.strip() if due else None,
            "priority": priority,
            "status": "open",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "completed_at": None,
        }
        with self._lock:
            self.tasks.append(item)
            self._save()
        return item

    def list_for_user(self, user_id: int, status: str = "open") -> list[dict[str, Any]]:
        with self._lock:
            items = [task for task in self.tasks if task.get("user_id") == user_id]
            if status != "all":
                items = [task for task in items if task.get("status") == status]
            return sorted(items, key=lambda task: (task.get("status") != "open", task.get("due") or "9999"))

    def complete(self, user_id: int, task_id: str) -> dict[str, Any] | None:
        needle = task_id.strip().lower()
        with self._lock:
            for task in self.tasks:
                if task.get("user_id") != user_id or task.get("status") == "done":
                    continue
                if str(task.get("id", "")).lower().startswith(needle) or needle in task.get("title", "").lower():
                    task["status"] = "done"
                    task["completed_at"] = datetime.now().isoformat(timespec="seconds")
                    self._save()
                    return dict(task)
        return None


from config import TASKS_DB_PATH

task_manager = TaskManager(TASKS_DB_PATH)
