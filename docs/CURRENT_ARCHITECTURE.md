# Audit of Existing Jarvis Codebase (Current Architecture)

## 1. Executive Summary & Overview
Jarvis is a Windows-centric Telegram personal AI assistant designed to run as a resident operator on Windows 10/11.
Following the modularization and performance refactoring, Jarvis uses an asynchronous pipeline:
- Heavy synchronous and OS operations are offloaded from the `asyncio` event loop using `asyncio.to_thread` and native async clients (`httpx.AsyncClient`).
- Monolithic files (`services/extra_functions.py`, `handlers/menu.py`, `core/executor.py`) have been decomposed into dedicated single-responsibility domain modules.
- Fast caches (`TTLCache` in `services/web_client.py` and `orjson` in `core/app_resolver.py`) prevent redundant network latency and disk serialization overhead.

---

## 2. Request Flow & Execution Architecture
### User Request Lifecycle:
1. **Telegram Ingestion**:
   - `main.py` configures `python-telegram-bot` (`Application`) with handlers:
     - `CommandHandler`: `/start`, `/menu`, `/kill`, `/clear`, `/diag`, `/autostart`.
     - `CallbackQueryHandler`: `menu_callback_router` in `handlers/menu/` (via `handlers/menu/callback_router.py`).
     - `MessageHandler(filters.VOICE | filters.AUDIO)`: `handle_voice_message` in `handlers/voice.py` (non-blocking threadpool offload).
     - `MessageHandler(filters.TEXT & ~filters.COMMAND)`: `handle_text_command` in `handlers/remote_control.py`.
2. **Authentication & Policy Gate**:
   - Every handler is wrapped with `@restricted` from `handlers/auth.py`.
   - Security verification is backed by `security/authentication.py`, `security/authorization.py`, `security/risk.py`, and `security/policy_engine.py`.
3. **Intent & Planning (Gemini AI & Local Rule-Engine)**:
   - Reply keyboard interactions are routed non-blockingly via `handlers/menu/reply_router.py`.
   - Free text and voice instructions are parsed via `services/ai_client.py` (or local intent matcher) without stalling the asyncio loop.
4. **Action Execution & Dispatcher**:
   - `core/executor.py` acts as a clean, modular dispatcher using `INTENT_HANDLER_MAP` (O(1) dictionary routing).
   - Execution logic is partitioned under `core/execution/`:
     - `core/execution/app_actions.py`: Open/close/list applications (with `asyncio.to_thread(ask_gemini_app_choice)`).
     - `core/execution/file_actions.py`: File, directory, explorer, search, and copy/move operations.
     - `core/execution/screenshot_actions.py`: Non-blocking multi-desktop screenshot capture.
     - `core/execution/reminder_actions.py`: Reminders, scenarios, and focus mode.
     - `core/execution/search_actions.py`: Web summary, Wikipedia download, file download, weather, and currency exchange rates (backed by native async `httpx` and `TTLCache`).
     - `core/execution/system_actions.py`: Process management, audio, brightness, security guard, lock/sleep/shutdown/restart.
   - Built-in watchdog timer notifies the user with `"⏳ Действие выполняется дольше обычного..."` if any step takes >10 seconds.

---

## 3. Modular Service Breakdown

### `services/` Structure:
- `services/web_client.py`: Native `httpx.AsyncClient` client with 10-minute `TTLCache` for weather and currency rates; 8-second bounded timeouts.
- `services/clipboard_tools.py`: Clipboard inspection, clearing, and history management.
- `services/network_tools.py`: Public/local IP resolution, Wi-Fi networks, network adapters, ping, speed tests.
- `services/power_tools.py`: Battery report and stats, display resolution, system idle time, power schemes, hibernation.
- `services/notes.py`: Notepad and scratchpad creation.
- `services/misc_tools.py`: Recycle bin operations, QR code generator, password generator, system restore, Explorer restart, mouse/keyboard helpers.
- `services/extra_functions.py`: Clean facade maintaining 100% backwards compatibility and providing `dispatch_extra()`.

### `handlers/menu/` Package:
- `handlers/menu/__init__.py`: Public API export (`cmd_start`, `menu_callback_router`, `handle_reply_keyboard`, keyboards).
- `handlers/menu/common.py`: Safe Markdown reply and edit helpers (`safe_reply`, `safe_edit`).
- `handlers/menu/keyboards.py`: Declarative reply and inline keyboard builders.
- `handlers/menu/callback_router.py`: Central Inline button callback router.
- `handlers/menu/reply_router.py`: Reply keyboard actions and interactive user input handlers.

---

## 4. State Management & Storage
- **JSON Storage**:
  - `data/reminders.json` (via `ReminderManager` in `scheduler.py`)
  - `data/apps_cache.json` (accelerated with `orjson` serialization in `core/app_resolver.py`)
  - `data/scenarios.json`
- **In-Memory State**:
  - `TaskQueueManager` (`core/task_queue.py`) maintaining user task queues.
  - `context.user_data` in Telegram handlers for conversational memory and multi-step dialogs.
  - Memory-safe `TTLCache` for repeated API responses.

---

## 5. Security & Risk Engine
- `security/risk.py`: Centralized `RiskLevel` enumeration (`SAFE`, `LOW`, `CONFIRM`, `ADMIN`, `DENY`) and comprehensive `ACTION_RISK_MAP`.
- `security/policy_engine.py`: Policy evaluation engine integrating authentication, role authorization, risk classification, and path boundary checking.
- `security/path_policy.py`: Normalizes filesystem paths, prevents path traversal, and flags unsafe directory operations.
- `security/authentication.py`: Validates token and user identity against configuration.
- `security/authorization.py`: Maps roles (`ADMIN`, `USER`, `GUEST`) to permissible risk levels.

---

## 6. Performance Benchmarks & Latency Improvements
- **Network Actions (`get_weather`, `get_exchange_rate`)**:
  - Previously: Synchronous `requests.get` directly on the event loop (blocking all Telegram users for 1.5–4.0s).
  - Now: `httpx.AsyncClient` with non-blocking event loop execution + `TTLCache`. Cached responses return in < 1ms; cold responses yield without freezing Telegram polling.
- **Application Ambiguity Arbitration (`ask_gemini_app_choice`)**:
  - Previously: Synchronous Gemini HTTP call blocked the event loop for 1.0–3.5s.
  - Now: Offloaded via `await asyncio.to_thread(ask_gemini_app_choice, ...)` — zero event loop stalls.
- **App Resolver Index Loading**:
  - Replaced Python standard library `json.load`/`dump` with `orjson` in `core/app_resolver.py` for sub-millisecond cache reads/writes.
