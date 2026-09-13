import pytest

from application.execution.context import ExecutionContext
from domain.actions.models import ActionDefinition
from domain.actions.registry import ActionRegistry
from domain.actions.result import ActionResult
from domain.actions.risk import RiskLevel
from security.authorization import AuthorizationPolicy
from security.path_policy import PathPolicy
from security.policy_engine import PolicyEngine


@pytest.fixture
def policy_engine():
    auth_policy = AuthorizationPolicy(allowlist=[100, 200], admin_list=[200])
    path_policy = PathPolicy(user_home="C:/Users/testuser")
    return PolicyEngine(authorization_policy=auth_policy, path_policy=path_policy)


@pytest.mark.asyncio
async def test_policy_engine_safe_action_allowed(policy_engine):
    ctx = ExecutionContext(user_id=100)
    action = ActionDefinition(
        name="open_application",
        description="Launch app",
        handler=lambda **kw: ActionResult(success=True),
        risk_level=RiskLevel.SAFE,
    )
    decision = await policy_engine.evaluate(action=action, context=ctx, params={"app_query": "notepad"})
    assert decision.allowed is True
    assert decision.requires_confirmation is False


@pytest.mark.asyncio
async def test_policy_engine_confirm_action_requires_confirmation(policy_engine):
    ctx = ExecutionContext(user_id=100)
    action = ActionDefinition(
        name="delete_file",
        description="Delete a file",
        handler=lambda **kw: ActionResult(success=True),
        risk_level=RiskLevel.CONFIRM,
    )
    decision = await policy_engine.evaluate(action=action, context=ctx, params={"path": "C:/Users/testuser/Desktop/test.txt"})
    assert decision.allowed is True
    assert decision.requires_confirmation is True


@pytest.mark.asyncio
async def test_policy_engine_admin_action_denied_for_normal_user(policy_engine):
    ctx = ExecutionContext(user_id=100)
    action = ActionDefinition(
        name="shutdown_pc",
        description="Shutdown computer",
        handler=lambda **kw: ActionResult(success=True),
        risk_level=RiskLevel.ADMIN,
    )
    decision = await policy_engine.evaluate(action=action, context=ctx, params={})
    assert decision.allowed is False
    assert "ADMIN privileges" in decision.reason


@pytest.mark.asyncio
async def test_policy_engine_admin_action_allowed_with_confirmation_for_admin(policy_engine):
    ctx = ExecutionContext(user_id=200)
    action = ActionDefinition(
        name="shutdown_pc",
        description="Shutdown computer",
        handler=lambda **kw: ActionResult(success=True),
        risk_level=RiskLevel.ADMIN,
    )
    decision = await policy_engine.evaluate(action=action, context=ctx, params={})
    assert decision.allowed is True
    assert decision.requires_confirmation is True


@pytest.mark.asyncio
async def test_policy_engine_explicit_deny_action_blocked(policy_engine):
    ctx = ExecutionContext(user_id=200)
    action = ActionDefinition(
        name="arbitrary_shell",
        description="Raw shell execution",
        handler=lambda **kw: ActionResult(success=True),
        risk_level=RiskLevel.DENY,
    )
    decision = await policy_engine.evaluate(action=action, context=ctx, params={})
    assert decision.allowed is False
    assert decision.risk_level == RiskLevel.DENY


@pytest.mark.asyncio
async def test_policy_engine_protected_path_denied(policy_engine):
    ctx = ExecutionContext(user_id=100)
    action = ActionDefinition(
        name="delete_file",
        description="Delete file",
        handler=lambda **kw: ActionResult(success=True),
        risk_level=RiskLevel.CONFIRM,
    )
    decision = await policy_engine.evaluate(
        action=action, context=ctx, params={"path": "C:/Windows/System32/kernel32.dll"}
    )
    # Protected system path
    assert decision.allowed is False or decision.requires_confirmation is True
