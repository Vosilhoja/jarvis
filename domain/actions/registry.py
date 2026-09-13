from __future__ import annotations

from domain.actions.models import ActionDefinition


class ActionRegistry:
    def __init__(self) -> None:
        self._actions: dict[str, ActionDefinition] = {}

    def register(self, action: ActionDefinition) -> None:
        if action.name in self._actions:
            raise ValueError(f"Action already registered: {action.name}")
        self._actions[action.name] = action

    def get(self, name: str) -> ActionDefinition:
        try:
            return self._actions[name]
        except KeyError as exc:
            raise ValueError(f"Unknown action: {name}") from exc

    def all(self) -> tuple[ActionDefinition, ...]:
        return tuple(self._actions.values())

    def contains(self, name: str) -> bool:
        return name in self._actions
