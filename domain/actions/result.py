from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ActionResult:
    success: bool
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)
    error_code: str | None = None
    retryable: bool = False

    def __bool__(self) -> bool:
        return self.success

    @classmethod
    def from_legacy(cls, value: Any) -> "ActionResult":
        if isinstance(value, cls):
            return value
        if isinstance(value, tuple) and len(value) == 2:
            ok, payload = value
            if isinstance(payload, dict):
                return cls(success=bool(ok), message="", data=payload)
            return cls(success=bool(ok), message=str(payload))
        if isinstance(value, bool):
            return cls(success=value, message="OK" if value else "Failed")
        if value is None:
            return cls(success=False, message="No result")
        return cls(success=True, message=str(value))
