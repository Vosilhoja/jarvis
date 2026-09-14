"""Backward-compatible import facade for the domain memory service."""
from domain.memory import UserMemory, user_memory

__all__ = ["UserMemory", "user_memory"]
