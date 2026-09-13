# Jarvis architecture baseline

This repository remains a Windows-oriented bot with monolithic orchestration and a thin domain layer. The purpose of this baseline is to establish a safe transition path without rewriting the product in one pass.

## Current state

- Telegram bot remains the primary entrypoint through `main.py`.
- Execution flow and action logic are still concentrated in `core/executor.py` and `handlers/*`.
- Critical security issues were fixed by hardening user allow-list parsing and path validation before introducing the next layer.

## New security baseline

- `security/authentication.py` normalizes and validates Telegram user IDs.
- `security/authorization.py` enforces allow-list authorization and confirmation-sensitive risk levels.
- `security/path_policy.py` checks normalized absolute paths and blocks protected Windows roots.
- `security/policy_engine.py` centralizes action authorization and path policy decisions.

## Action contract baseline

- `domain/actions/risk.py` defines `ActionResult` and `RiskLevel`.
- `domain/actions/registry.py` provides a registry for named actions.
- `application/execution/context.py` stores execution metadata for a single runtime action.
- `application/execution/executor.py` executes a named action via registry + policy evaluation.

## Migration rule

The monolithic executor can remain as a compatibility façade until the feature set moves to the new execution layer. New code should prefer the registry and policy evaluation path rather than adding more `if/elif` branches to the old executor.
