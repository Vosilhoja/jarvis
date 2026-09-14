"""Backward-compatible import facade for the task domain service."""
from domain.tasks import TaskManager, task_manager

__all__ = ["TaskManager", "task_manager"]
