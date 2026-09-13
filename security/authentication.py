from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Sequence


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


@dataclass(frozen=True, slots=True)
class AuthPrincipal:
    user_id: int
    username: str | None = None
    full_name: str | None = None


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    user_id: int
    role: UserRole = UserRole.USER
    username: str | None = None
    full_name: str | None = None

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN


class AuthenticationConfigurationError(ValueError):
    """Raised when authentication setup is invalid or missing."""
    pass


class AuthenticationFailedError(PermissionError):
    """Raised when an unauthenticated user attempts an operation."""
    pass


def normalize_user_id(value: int | str | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return None
    match = re.search(r"-?\d+", text)
    if not match:
        return None
    try:
        return int(match.group(0))
    except ValueError:
        return None


def parse_allowlist(raw_value: str | Sequence[int | str] | None) -> list[int]:
    if raw_value is None:
        return []
    if isinstance(raw_value, (list, tuple, set)):
        items = list(raw_value)
    else:
        items = re.split(r"[\s,;]+", str(raw_value).strip())

    normalized: list[int] = []
    seen: set[int] = set()
    for item in items:
        uid = normalize_user_id(item)
        if uid is None:
            continue
        if uid not in seen:
            normalized.append(uid)
            seen.add(uid)
    return normalized


class Authenticator:
    """Centralized Telegram user authenticator enforcing strict allowlists."""

    def __init__(
        self,
        allowed_user_ids: Sequence[int | str] | str | None,
        admin_user_ids: Sequence[int | str] | str | None = None,
    ) -> None:
        self._allowed_ids: set[int] = set(parse_allowlist(allowed_user_ids))
        self._admin_ids: set[int] = set(parse_allowlist(admin_user_ids))

        # Fail fast: application MUST fail fast if allowlist is empty or missing
        if not self._allowed_ids:
            raise AuthenticationConfigurationError(
                "CRITICAL SECURITY: ALLOWED_TELEGRAM_USER_IDS is empty or not configured. "
                "Jarvis refuses to start without a valid allowed user list to prevent unauthorized access."
            )

    @property
    def allowed_user_ids(self) -> frozenset[int]:
        return frozenset(self._allowed_ids)

    @property
    def admin_user_ids(self) -> frozenset[int]:
        return frozenset(self._admin_ids)

    def is_allowed(self, user_id: int | str | None) -> bool:
        normalized = normalize_user_id(user_id)
        if normalized is None:
            return False
        return normalized in self._allowed_ids

    def is_admin(self, user_id: int | str | None) -> bool:
        normalized = normalize_user_id(user_id)
        if normalized is None:
            return False
        return normalized in self._admin_ids and normalized in self._allowed_ids

    def authenticate(
        self,
        user_id: int | str | None,
        username: str | None = None,
        full_name: str | None = None,
    ) -> AuthenticatedUser:
        normalized = normalize_user_id(user_id)
        if normalized is None or normalized not in self._allowed_ids:
            raise AuthenticationFailedError(
                f"Access denied: Telegram user {user_id} is not authorized."
            )

        role = UserRole.ADMIN if normalized in self._admin_ids else UserRole.USER
        return AuthenticatedUser(
            user_id=normalized,
            role=role,
            username=username,
            full_name=full_name,
        )


# Backward compatibility helper functions
def is_user_allowed(user_id: int | str | None, allowlist: Iterable[int | str] | None = None) -> bool:
    normalized = normalize_user_id(user_id)
    if normalized is None or allowlist is None:
        return False
    ids = {normalize_user_id(val) for val in allowlist}
    ids.discard(None)
    return normalized in ids


def register_allowed_user(
    user_id: int | str | None,
    env_path: str | Path | None = None,
    allowlist: list[int] | None = None,
) -> list[int]:
    from pathlib import Path
    normalized_user_id = normalize_user_id(user_id)
    if normalized_user_id is None:
        return list(allowlist or [])

    existing = list(allowlist or [])
    if normalized_user_id not in existing:
        existing.append(normalized_user_id)

    env_file = Path(env_path) if env_path else Path(__file__).resolve().parents[1] / ".env"
    try:
        text = env_file.read_text(encoding="utf-8") if env_file.exists() else ""
        lines = []
        replaced = False
        for line in text.splitlines():
            if line.strip().startswith("ALLOWED_TELEGRAM_USER_IDS="):
                lines.append(f"ALLOWED_TELEGRAM_USER_IDS={','.join(str(item) for item in sorted(set(existing)))}")
                replaced = True
                continue
            if line.strip() and not line.strip().startswith("#"):
                lines.append(line)
        if not replaced:
            lines.append(f"ALLOWED_TELEGRAM_USER_IDS={','.join(str(item) for item in sorted(set(existing)))}")
        env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError:
        pass

    return sorted(set(existing))
