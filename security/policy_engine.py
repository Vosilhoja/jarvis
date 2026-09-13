from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from domain.actions.risk import RiskLevel, get_action_risk_level
from security.authorization import AuthorizationPolicy
from security.path_policy import PathDecision, PathPolicy


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool = True
    requires_confirmation: bool = False
    reason: str = ""
    path_decision: PathDecision | None = None
    risk_level: RiskLevel = RiskLevel.SAFE


class PolicyEngine:
    """Central Policy Engine validating authentication, authorization, risk levels, and path safety."""

    def __init__(
        self,
        authorization_policy: AuthorizationPolicy | None = None,
        path_policy: PathPolicy | None = None,
    ) -> None:
        self.authorization_policy = authorization_policy or AuthorizationPolicy()
        self.path_policy = path_policy or PathPolicy()

    async def evaluate(
        self,
        *,
        action: Any,
        context: Any,
        params: dict[str, Any] | None = None,
    ) -> PolicyDecision:
        params = params or {}
        user_id = getattr(context, "user_id", None)
        action_name = getattr(action, "name", str(action))

        # 1. Determine Risk Level
        risk_level = getattr(action, "risk_level", None)
        if not isinstance(risk_level, RiskLevel):
            risk_level = get_action_risk_level(action_name)

        # 2. Check explicitly forbidden operations
        if risk_level == RiskLevel.DENY:
            return PolicyDecision(
                allowed=False,
                requires_confirmation=False,
                reason=f"Action '{action_name}' is explicitly forbidden by security policy (DENY).",
                risk_level=RiskLevel.DENY,
            )

        # 3. Authorize user & role
        auth_decision = self.authorization_policy.evaluate(
            user_id=user_id,
            risk_level=risk_level,
            action_name=action_name,
        )
        if not auth_decision.allowed:
            return PolicyDecision(
                allowed=False,
                requires_confirmation=False,
                reason=auth_decision.reason,
                risk_level=risk_level,
            )

        requires_confirmation = bool(auth_decision.requires_confirmation)
        reason = auth_decision.reason

        # 4. Path Validation for file/directory params
        path_value = None
        for key in (
            "path",
            "target_path",
            "source",
            "destination",
            "file_path",
            "folder_path",
            "root",
            "parent",
        ):
            if key in params and params[key]:
                path_value = params[key]
                break

        if path_value is not None:
            op = "read"
            if any(k in action_name for k in ("write", "create", "delete", "move", "copy", "cleanup", "zip")):
                op = "write" if not "delete" in action_name else "delete"
            path_decision = self.path_policy.check(path_value, operation=op)

            if path_decision.action == "DENY":
                return PolicyDecision(
                    allowed=False,
                    requires_confirmation=False,
                    reason=path_decision.reason,
                    path_decision=path_decision,
                    risk_level=risk_level,
                )
            if path_decision.action == "CONFIRM":
                requires_confirmation = True
                reason = path_decision.reason

        return PolicyDecision(
            allowed=True,
            requires_confirmation=requires_confirmation,
            reason=reason,
            risk_level=risk_level,
        )
