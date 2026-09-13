"""Agent rules enforcement helpers

Provides programmatic access to the AGENT_RULES and helpers used by test discovery and CI.
"""
from pathlib import Path
import json

RULES_PATH = Path(__file__).parent.parent / 'AGENT_RULES.md'

# Minimal machine-friendly rules encoded here too
RULES = [
    "safety_first",
    "least_privilege",
    "audit_logging",
    "dry_run_capability",
    "local_first_routing",
    "library_preference",
    "confirmation_escalation",
    "prompt_and_output_validation",
    "fail_safe_and_rollback",
    "transparency",
]


def get_rules_text() -> str:
    try:
        return RULES_PATH.read_text(encoding='utf-8')
    except Exception:
        return "".join([f"- {r}\n" for r in RULES])


def is_dangerous_function_name(name: str) -> bool:
    """Heuristic: detect dangerous names that should not be auto-executed."""
    n = name.lower()
    keywords = ('shutdown', 'restart', 'format', 'delete', 'erase', 'factory', 'reboot', 'poweroff')
    return any(k in n for k in keywords)


def require_confirmation_for_intent(intent: str) -> bool:
    """Decide whether a given intent name should require explicit confirmation.
    Conservative default: anything that looks dangerous per is_dangerous_function_name.
    """
    return is_dangerous_function_name(intent)


def write_auto_registry(data: dict, path: Path) -> None:
    try:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass
