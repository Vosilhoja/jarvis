from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from domain.actions.result import ActionResult
from domain.actions.risk import RiskLevel

ActionHandler = Callable[..., Awaitable[ActionResult] | ActionResult]


@dataclass(frozen=True, slots=True)
class ActionDefinition:
    name: str
    description: str
    handler: ActionHandler
    risk_level: RiskLevel
    permissions: frozenset[str] = frozenset()
    timeout_seconds: float = 30.0
    retryable: bool = False
