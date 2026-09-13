from __future__ import annotations

import inspect
from typing import Any

from domain.actions.result import ActionResult
from domain.actions.registry import ActionRegistry
from security.policy_engine import PolicyEngine


class ExecutionExecutor:
    def __init__(self, registry: ActionRegistry, policy: PolicyEngine | None = None) -> None:
        self.registry = registry
        self.policy = policy or PolicyEngine()

    async def execute(
        self,
        action_name: str,
        params: dict[str, Any],
        context: Any,
    ) -> ActionResult:
        action = self.registry.get(action_name)

        decision = await self.policy.evaluate(
            action=action,
            context=context,
            params=params,
        )

        if not decision.allowed:
            return ActionResult(
                success=False,
                message=decision.reason,
                error_code="ACTION_DENIED",
            )

        if decision.requires_confirmation:
            return ActionResult(
                success=False,
                message="Confirmation required",
                error_code="CONFIRMATION_REQUIRED",
            )

        try:
            result = action.handler(**params, context=context)
            if inspect.isawaitable(result):
                result = await result
            return ActionResult.from_legacy(result)
        except Exception as exc:  # pragma: no cover - defensive guard for registry actions
            return ActionResult(
                success=False,
                message=str(exc),
                error_code="ACTION_FAILED",
            )


def execute_action(
    registry: ActionRegistry,
    action_name: str,
    params: dict[str, Any],
    context: Any,
    policy: PolicyEngine | None = None,
) -> ActionResult:
    executor = ExecutionExecutor(registry, policy=policy)
    return executor.execute(action_name, params, context)
