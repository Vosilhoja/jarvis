"""Thread-safe, atomic JSON persistence for small local state files."""
from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

import msgspec
from filelock import FileLock


class JsonStore:
    """Load and save one small JSON document without partial writes."""

    def __init__(self, path: Path, default: Any):
        self.path = path
        self.default = default
        self._lock = threading.RLock()

    def load(self) -> Any:
        with self._lock, FileLock(str(self.path) + ".lock", timeout=2):
                try:
                    raw = self.path.read_bytes() if self.path.exists() else b""
                    return msgspec.json.decode(raw) if raw.strip() else self.default
                except (OSError, msgspec.DecodeError):
                    return self.default

    def save(self, value: Any) -> None:
        encoded = msgspec.json.encode(value)
        with self._lock, FileLock(str(self.path) + ".lock", timeout=2):
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
            temp_path.write_bytes(encoded)
            os.replace(temp_path, self.path)
