"""User learning and preference domain logic."""
from __future__ import annotations

import re
import threading
from pathlib import Path
from typing import Any

from domain.storage.json_store import JsonStore


class UserMemory:
    """Stores validated command patterns, never executable code."""

    def __init__(self, path: Path):
        self._store = JsonStore(path, {})
        self.data: dict[str, dict[str, Any]] = self._store.load()
        self._lock = threading.RLock()

    def _save(self) -> None:
        self._store.save(self.data)

    def get(self, user_id: int) -> dict[str, Any]:
        with self._lock:
            return self.data.setdefault(str(user_id), {"preferences": {}, "learned": []})

    def learn_success(self, user_id: int, intent: str, params: dict[str, Any]) -> None:
        with self._lock:
            user = self.get(user_id)
            learned = user.setdefault("learned", [])
            item = {"intent": intent, "params": params}
            if item not in learned:
                learned.append(item)
            user["learned"] = learned[-50:]
            self._save()

    def learn_failure(self, user_id: int, intent: str, params: dict[str, Any]) -> None:
        with self._lock:
            user = self.get(user_id)
            failed = user.setdefault("failed", [])
            failed.append({"intent": intent, "params": params})
            user["failed"] = failed[-50:]
            self._save()

    @staticmethod
    def normalize_phrase(text: str) -> str:
        return re.sub(r"\s+", " ", (text or "").strip().lower())

    def learn_phrase(self, user_id: int, phrase: str, intent: str, params: dict[str, Any]) -> None:
        phrase = self.normalize_phrase(phrase)
        if not phrase:
            return
        with self._lock:
            user = self.get(user_id)
            phrases = user.setdefault("phrases", [])
            phrases[:] = [entry for entry in phrases if entry.get("phrase") != phrase]
            phrases.append({"phrase": phrase, "intent": intent, "params": params})
            user["phrases"] = phrases[-100:]
            self._save()

    def match_phrase(self, user_id: int, phrase: str) -> dict[str, Any] | None:
        normalized = self.normalize_phrase(phrase)
        with self._lock:
            for item in reversed(self.get(user_id).get("phrases", [])):
                if item.get("phrase") == normalized:
                    return dict(item)
        return None

    def learning_context(self, user_id: int, limit: int = 8) -> str:
        with self._lock:
            user = self.get(user_id)
            learned = list(user.get("learned", [])[-limit:])
            phrases = list(user.get("phrases", [])[-limit:])
        if not learned and not phrases:
            return ""
        lines = ["Проверенные предпочтения и команды пользователя:"]
        lines.extend(f"- «{x.get('phrase', '')}» -> {x.get('intent', '')}" for x in phrases)
        lines.extend(f"- успешное действие: {x.get('intent', '')} {x.get('params', {})}" for x in learned)
        return "\n".join(lines)


from config import USER_MEMORY_PATH

user_memory = UserMemory(USER_MEMORY_PATH)
