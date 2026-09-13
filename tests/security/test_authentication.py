import pytest

from security.authentication import (
    AuthenticatedUser,
    AuthenticationConfigurationError,
    AuthenticationFailedError,
    Authenticator,
    UserRole,
    normalize_user_id,
    parse_allowlist,
)
from security.authorization import (
    AuthorizationDecision,
    AuthorizationPolicy,
    Permission,
)


def test_normalize_and_parse_allowlist():
    assert normalize_user_id(12345) == 12345
    assert normalize_user_id("  98765 ") == 98765
    assert normalize_user_id("invalid") is None
    assert normalize_user_id(None) is None

    assert parse_allowlist("100, 200; 300\n400") == [100, 200, 300, 400]
    assert parse_allowlist(["100", 200, "100"]) == [100, 200]
    assert parse_allowlist("") == []
    assert parse_allowlist(None) == []


def test_empty_allowlist_fails_fast():
    with pytest.raises(AuthenticationConfigurationError) as exc_info:
        Authenticator(allowed_user_ids="")
    assert "CRITICAL SECURITY" in str(exc_info.value)

    with pytest.raises(AuthenticationConfigurationError):
        Authenticator(allowed_user_ids=None)

    with pytest.raises(AuthenticationConfigurationError):
        Authenticator(allowed_user_ids=[])


def test_allowed_and_denied_user_authentication():
    auth = Authenticator(allowed_user_ids="100, 200", admin_user_ids="200")

    # Allowed normal user
    assert auth.is_allowed(100) is True
    assert auth.is_admin(100) is False
    user = auth.authenticate(100, username="user_100")
    assert isinstance(user, AuthenticatedUser)
    assert user.user_id == 100
    assert user.role == UserRole.USER
    assert user.is_admin is False

    # Allowed admin user
    assert auth.is_allowed(200) is True
    assert auth.is_admin(200) is True
    admin = auth.authenticate(200, username="admin_200")
    assert admin.role == UserRole.ADMIN
    assert admin.is_admin is True

    # Denied user
    assert auth.is_allowed(999) is False
    with pytest.raises(AuthenticationFailedError):
        auth.authenticate(999)


def test_authorization_deny_by_default():
    policy = AuthorizationPolicy(allowlist=[100, 200], admin_list=[200])

    # Anonymous user denied
    decision = policy.evaluate(user_id=None, risk_level="safe")
    assert decision.allowed is False

    # Unlisted user denied
    decision = policy.evaluate(user_id=999, risk_level="safe")
    assert decision.allowed is False
    assert "not in authorized allowlist" in decision.reason

    # Normal user on admin action denied
    decision = policy.evaluate(user_id=100, risk_level="admin", action_name="shutdown_pc")
    assert decision.allowed is False
    assert "requires ADMIN privileges" in decision.reason

    # Admin user on admin action requires confirmation
    decision = policy.evaluate(user_id=200, risk_level="admin", action_name="shutdown_pc")
    assert decision.allowed is True
    assert decision.requires_confirmation is True

    # Confirm action requires confirmation for normal user too
    decision = policy.evaluate(user_id=100, risk_level="confirm", action_name="delete_file")
    assert decision.allowed is True
    assert decision.requires_confirmation is True

    # Safe action allowed without confirmation
    decision = policy.evaluate(user_id=100, risk_level="safe", action_name="get_system_status")
    assert decision.allowed is True
    assert decision.requires_confirmation is False

    # Explicit DENY risk level always rejected
    decision = policy.evaluate(user_id=200, risk_level="deny", action_name="arbitrary_shell")
    assert decision.allowed is False


def test_role_permissions():
    policy = AuthorizationPolicy(allowlist=[100, 200], admin_list=[200])
    normal_user = AuthenticatedUser(user_id=100, role=UserRole.USER)
    admin_user = AuthenticatedUser(user_id=200, role=UserRole.ADMIN)

    assert policy.has_permission(normal_user, Permission.RUN_SAFE_ACTION) is True
    assert policy.has_permission(normal_user, Permission.RUN_ADMIN_ACTION) is False
    assert policy.has_permission(normal_user, Permission.VIEW_AUDIT_LOG) is False

    assert policy.has_permission(admin_user, Permission.RUN_ADMIN_ACTION) is True
    assert policy.has_permission(admin_user, Permission.VIEW_AUDIT_LOG) is True
