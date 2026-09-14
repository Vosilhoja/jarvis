"""Shared helpers for Windows adapter modules."""
from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger("jarvis")
CREATE_NO_WINDOW = 0x08000000


def _run(cmd: list[str] | str, timeout: int = 20, shell: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, timeout=timeout, shell=shell,
                          creationflags=CREATE_NO_WINDOW)


def _decode(data: bytes) -> str:
    for enc in ("utf-8", "cp866", "cp1251"):
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode("utf-8", errors="replace")


@dataclass
class ExtraResult:
    success: bool
    text: str
    photo_bytes: Optional[bytes] = None
    photo_name: str = "image.png"
    extra: Dict[str, Any] = field(default_factory=dict)
