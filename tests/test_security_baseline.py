import pytest

from application.execution.context import ExecutionContext
from domain.actions.models import ActionDefinition
from domain.actions.result import ActionResult
from domain.actions.risk import RiskLevel
from domain.actions.registry import ActionRegistry
from security.authentication import is_user_allowed, normalize_user_id, parse_allowlist
from security.authorization import AuthorizationPolicy
from security.path_policy import PathPolicy


def test_allowlist_parsing_supports_common_formats():
    assert parse_allowlist("123,456\n789") == [123, 456, 789]
    assert parse_allowlist(" 123 ; 456 ; 123 ") == [123, 456]
    assert normalize_user_id("id=42") == 42


def test_user_authz_denies_unknown_user():
    policy = AuthorizationPolicy(allowlist=[123, 456])
    decision = policy.evaluate(user_id=999, risk_level=RiskLevel.CONFIRM, action_name="delete_file")
    assert decision.allowed is False
    assert decision.requires_confirmation is False
    assert ("not authorized" in decision.reason.lower() or "not in authorized allowlist" in decision.reason.lower())


def test_path_policy_blocks_system32_and_env_files():
    policy = PathPolicy(user_home="C:/Users/testuser")
    deny = policy.check("C:/Windows/System32/drivers/etc/hosts", operation="read")
    assert deny.action == "DENY"

    confirm = policy.check("C:/Users/testuser/.env", operation="write")
    assert confirm.action == "CONFIRM"


def test_action_registry_and_result_work_together():
    registry = ActionRegistry()

    async def sample_action(context=None, **kwargs):
        return ActionResult(
            success=True,
            message="Folder created",
            data={"path": kwargs["path"]},
            artifacts=[kwargs["path"]],
        )

    registry.register(
        ActionDefinition(
            name="create_folder",
            description="Create a folder",
            handler=sample_action,
            risk_level=RiskLevel.LOW,
            permissions=frozenset({"files.write"}),
        )
    )

    action = registry.get("create_folder")
    assert action.name == "create_folder"
    assert action.risk_level == RiskLevel.LOW
    assert is_user_allowed(123, [123, 456]) is True

    ctx = ExecutionContext(user_id=123)
    assert ctx.user_id == 123
    assert ctx.path_policy is None


@pytest.mark.asyncio
async def test_policy_engine_requires_confirmation_for_protected_path():
    from security.policy_engine import PolicyEngine

    class DummyAction:
        name = "write_secret"
        risk_level = RiskLevel.LOW

    ctx = ExecutionContext(user_id=123, metadata={"allowlist": [123]})
    engine = PolicyEngine(
        authorization_policy=AuthorizationPolicy(allowlist=[123]),
        path_policy=PathPolicy(user_home="C:/Users/testuser"),
    )

    decision = await engine.evaluate(action=DummyAction(), context=ctx, params={"path": "C:/Users/testuser/.env"})
    assert decision.allowed is True
    assert decision.requires_confirmation is True
