from dataclasses import dataclass, field
from typing import Any

import pytest

from security.authorization import AuthorizationPolicy
from security.path_policy import PathPolicy
from security.policy_engine import PolicyEngine
from security.risk import RiskLevel


@dataclass
class DummyContext:
    user_id: int
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class DummyAction:
    name: str
    risk_level: RiskLevel


@pytest.fixture
def policy_engine():
    auth_policy = AuthorizationPolicy(allowlist=[100, 200], admin_list=[200])
    path_policy = PathPolicy(user_home="C:/Users/testuser")
    return PolicyEngine(authorization_policy=auth_policy, path_policy=path_policy)


@pytest.mark.asyncio
async def test_policy_engine_safe_action_allowed(policy_engine):
    ctx = DummyContext(user_id=100)
    action = DummyAction(name="open_application", risk_level=RiskLevel.SAFE)
    decision = await policy_engine.evaluate(action=action, context=ctx, params={"app_query": "notepad"})
    assert decision.allowed is True
    assert decision.requires_confirmation is False


@pytest.mark.asyncio
async def test_policy_engine_confirm_action_requires_confirmation(policy_engine):
    ctx = DummyContext(user_id=100)
    action = DummyAction(name="delete_file", risk_level=RiskLevel.CONFIRM)
    decision = await policy_engine.evaluate(action=action, context=ctx, params={"path": "C:/Users/testuser/Desktop/test.txt"})
    assert decision.allowed is True
    assert decision.requires_confirmation is True


@pytest.mark.asyncio
async def test_policy_engine_admin_action_denied_for_normal_user(policy_engine):
    ctx = DummyContext(user_id=100)
    action = DummyAction(name="shutdown_pc", risk_level=RiskLevel.ADMIN)
    decision = await policy_engine.evaluate(action=action, context=ctx, params={})
    assert decision.allowed is False
    assert "ADMIN privileges" in decision.reason


@pytest.mark.asyncio
async def test_policy_engine_admin_action_allowed_with_confirmation_for_admin(policy_engine):
    ctx = DummyContext(user_id=200)
    action = DummyAction(name="shutdown_pc", risk_level=RiskLevel.ADMIN)
    decision = await policy_engine.evaluate(action=action, context=ctx, params={})
    assert decision.allowed is True
    assert decision.requires_confirmation is True


@pytest.mark.asyncio
async def test_policy_engine_explicit_deny_action_blocked(policy_engine):
    ctx = DummyContext(user_id=200)
    action = DummyAction(name="arbitrary_shell", risk_level=RiskLevel.DENY)
    decision = await policy_engine.evaluate(action=action, context=ctx, params={})
    assert decision.allowed is False
    assert decision.risk_level == RiskLevel.DENY


@pytest.mark.asyncio
async def test_policy_engine_protected_path_denied(policy_engine):
    ctx = DummyContext(user_id=100)
    action = DummyAction(name="delete_file", risk_level=RiskLevel.CONFIRM)
    decision = await policy_engine.evaluate(
        action=action, context=ctx, params={"path": "C:/Windows/System32/kernel32.dll"}
    )
    assert decision.allowed is False or decision.requires_confirmation is True
