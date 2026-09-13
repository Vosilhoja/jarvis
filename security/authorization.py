from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Sequence

from security.authentication import AuthenticatedUser, UserRole, normalize_user_id


class Permission(str, Enum):
    VIEW_SYSTEM = "VIEW_SYSTEM"
    RUN_SAFE_ACTION = "RUN_SAFE_ACTION"
    RUN_CONFIRM_ACTION = "RUN_CONFIRM_ACTION"
    RUN_ADMIN_ACTION = "RUN_ADMIN_ACTION"
    MANAGE_REMINDERS = "MANAGE_REMINDERS"
    MANAGE_WATCHERS = "MANAGE_WATCHERS"
    VIEW_AUDIT_LOG = "VIEW_AUDIT_LOG"


USER_DEFAULT_PERMISSIONS: frozenset[Permission] = frozenset(
    {
        Permission.VIEW_SYSTEM,
        Permission.RUN_SAFE_ACTION,
        Permission.RUN_CONFIRM_ACTION,
        Permission.MANAGE_REMINDERS,
        Permission.MANAGE_WATCHERS,
    }
)

ADMIN_DEFAULT_PERMISSIONS: frozenset[Permission] = frozenset(
    {
        Permission.VIEW_SYSTEM,
        Permission.RUN_SAFE_ACTION,
        Permission.RUN_CONFIRM_ACTION,
        Permission.RUN_ADMIN_ACTION,
        Permission.MANAGE_REMINDERS,
        Permission.MANAGE_WATCHERS,
        Permission.VIEW_AUDIT_LOG,
    }
)


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    allowed: bool
    requires_confirmation: bool = False
    reason: str = ""


class AuthorizationPolicy:
    """Deny by default authorization policy mapping authenticated roles/users to permissions."""

    def __init__(
        self,
        allowlist: Iterable[int | str] | None = None,
        admin_list: Iterable[int | str] | None = None,
    ) -> None:
        self.allowlist = tuple(allowlist or ())
        self.admin_list = tuple(admin_list or ())

    def has_permission(self, user: AuthenticatedUser, permission: Permission) -> bool:
        if user.role == UserRole.ADMIN:
            return permission in ADMIN_DEFAULT_PERMISSIONS
        return permission in USER_DEFAULT_PERMISSIONS

    def evaluate(
        self,
        *,
        user_id: int | str | None,
        risk_level: str | Any = "low",
        action_name: str | None = None,
        user: AuthenticatedUser | None = None,
    ) -> AuthorizationDecision:
        normalized_user_id = normalize_user_id(user_id)
        if normalized_user_id is None:
            return AuthorizationDecision(
                allowed=False,
                requires_confirmation=False,
                reason="Denied by default: anonymous or invalid user.",
            )

        allowed_ids = {normalize_user_id(u) for u in self.allowlist}
        allowed_ids.discard(None)
        if normalized_user_id not in allowed_ids:
            return AuthorizationDecision(
                allowed=False,
                requires_confirmation=False,
                reason=f"User {normalized_user_id} is not in authorized allowlist.",
            )

        admin_ids = {normalize_user_id(u) for u in self.admin_list}
        admin_ids.discard(None)
        is_admin = normalized_user_id in admin_ids or (user is not None and user.is_admin)

        level_str = str(getattr(risk_level, "value", risk_level)).lower()

        if level_str == "deny":
            return AuthorizationDecision(
                allowed=False,
                requires_confirmation=False,
                reason=f"Action '{action_name or 'unknown'}' is explicitly forbidden (DENY).",
            )

        if level_str == "admin":
            if not is_admin:
                return AuthorizationDecision(
                    allowed=False,
                    requires_confirmation=False,
                    reason=f"Action '{action_name or 'unknown'}' requires ADMIN privileges.",
                )
            return AuthorizationDecision(
                allowed=True,
                requires_confirmation=True,
                reason=f"Action '{action_name or 'unknown'}' requires ADMIN confirmation.",
            )

        if level_str == "confirm":
            return AuthorizationDecision(
                allowed=True,
                requires_confirmation=True,
                reason=f"Action '{action_name or 'unknown'}' requires user confirmation.",
            )

        return AuthorizationDecision(allowed=True, requires_confirmation=False)
