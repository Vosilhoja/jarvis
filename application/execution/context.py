from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from security.path_policy import PathPolicy


@dataclass(slots=True)
class ExecutionContext:
    user_id: int
    chat_id: int | None = None
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)
    path_policy: PathPolicy | None = None
