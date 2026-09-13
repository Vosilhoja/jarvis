"""Security and authorization primitives for Jarvis."""

from .authentication import AuthPrincipal, is_user_allowed, normalize_user_id, register_allowed_user
from .authorization import AuthorizationDecision, AuthorizationPolicy
from .path_policy import PathDecision, PathPolicy
from .policy_engine import PolicyDecision, PolicyEngine

__all__ = [
    "AuthPrincipal",
    "AuthorizationDecision",
    "AuthorizationPolicy",
    "PathDecision",
    "PathPolicy",
    "PolicyDecision",
    "PolicyEngine",
    "is_user_allowed",
    "normalize_user_id",
    "register_allowed_user",
]
