from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Iterable


ALLOW = "ALLOW"
DENY = "DENY"
CONFIRM = "CONFIRM"


@dataclass(frozen=True, slots=True)
class PathDecision:
    action: str
    reason: str = ""
    normalized_path: str | None = None


class PathPolicy:
    """Restricts filesystem access to safe user-owned roots and blocks Windows system folders."""

    def __init__(
        self,
        allowed_roots: Iterable[str | os.PathLike[str]] | None = None,
        user_home: str | os.PathLike[str] | None = None,
    ) -> None:
        user_home_value = user_home or Path.home()
        self.user_home = self._coerce_path(user_home_value)
        default_roots = [
            self.user_home,
            self.user_home / "Desktop",
            self.user_home / "Documents",
            self.user_home / "Downloads",
            self.user_home / "Pictures",
            self.user_home / "Videos",
            self.user_home / "Music",
        ]
        self.allowed_roots = [self._coerce_path(root) for root in (allowed_roots or default_roots)]

    @staticmethod
    def _coerce_path(value: str | os.PathLike[str] | Path) -> Path | PureWindowsPath:
        text = str(value).replace("\\", "/")
        if re.match(r"^[A-Za-z]:/", text):
            return PureWindowsPath(text)
        return Path(text).expanduser()

    def _as_windows_path(self, value: str | os.PathLike[str] | Path) -> PureWindowsPath:
        text = str(value).replace("\\", "/")
        if re.match(r"^[A-Za-z]:/", text):
            return PureWindowsPath(text)
        if str(self.user_home).startswith("C:") or str(self.user_home).startswith("D:"):
            return PureWindowsPath(str(self.user_home).replace("\\", "/") + "/" + str(value).lstrip("./"))
        return PureWindowsPath(str(value))

    def normalize(self, value: str | os.PathLike[str] | None) -> Path | PureWindowsPath:
        if value is None:
            return self.user_home
        text = str(value).strip()
        if not text:
            return self.user_home
        expanded = os.path.expandvars(os.path.expanduser(text))
        if re.match(r"^[A-Za-z]:/", expanded.replace("\\", "/")):
            return PureWindowsPath(expanded.replace("\\", "/"))
        path = Path(expanded)
        if not path.is_absolute():
            path = (self.user_home / path)
        return path

    def _is_within(self, candidate: Path | PureWindowsPath, root: Path | PureWindowsPath) -> bool:
        try:
            candidate.relative_to(root)
            return True
        except (TypeError, ValueError):
            return False

    def check(self, value: str | os.PathLike[str] | None, *, operation: str = "read") -> PathDecision:
        normalized = self.normalize(value)
        candidate_text = str(normalized).replace("\\", "/")
        protected_roots = [
            PureWindowsPath("C:/Windows"),
            PureWindowsPath("C:/Windows/System32"),
            PureWindowsPath("C:/Program Files"),
            PureWindowsPath("C:/Program Files (x86)"),
            PureWindowsPath("C:/Program Files/WindowsApps"),
            PureWindowsPath("C:/WindowsApps"),
        ]

        for root in protected_roots:
            if self._is_within(normalized, root):
                if operation in {"write", "delete", "execute", "modify"}:
                    return PathDecision(
                        action=CONFIRM,
                        reason=f"Path {candidate_text} touches a protected Windows system location; confirmation is required.",
                        normalized_path=candidate_text,
                    )
                return PathDecision(
                    action=DENY,
                    reason=f"Access to protected Windows path {candidate_text} is denied.",
                    normalized_path=candidate_text,
                )

        for root in self.allowed_roots:
            if self._is_within(normalized, root):
                if normalized.name.lower() == ".env" or "secrets" in [part.lower() for part in getattr(normalized, "parts", [])]:
                    return PathDecision(
                        action=CONFIRM,
                        reason="This path appears to be an environment or secrets file and requires explicit confirmation.",
                        normalized_path=candidate_text,
                    )
                return PathDecision(action=ALLOW, normalized_path=candidate_text)

        return PathDecision(
            action=DENY,
            reason=f"Path {candidate_text} is outside the allowed project/user roots.",
            normalized_path=candidate_text,
        )

    def ensure_allowed(self, value: str | os.PathLike[str] | None, *, operation: str = "read") -> Path | PureWindowsPath:
        decision = self.check(value, operation=operation)
        if decision.action == DENY:
            raise ValueError(decision.reason)
        return self.normalize(value)
