# Audit of Existing Jarvis Codebase (Current Architecture)

## 1. Executive Summary & Overview
Jarvis is a Windows-centric Telegram personal AI assistant designed to run as a resident operator on Windows 10/11.
Currently, it operates as a monolithic application where incoming requests (Telegram text commands, buttons, or voice messages) are received in Telegram handlers, optionally interpreted through Google Gemini into JSON steps, and executed via a giant `if/elif` dispatcher in `core/executor.py` or directly through `handlers/menu.py` calling `services/extra_functions.py`.

---

## 2. Request Flow Analysis
### User Request Lifecycle:
1. **Telegram Ingestion**:
   - `main.py` configures `python-telegram-bot` (`Application`) with handlers:
     - `CommandHandler`: `/start`, `/menu`, `/kill`, `/clear`, `/diag`, `/autostart`.
     - `CallbackQueryHandler`: `menu_callback_router` in `handlers/menu.py`.
     - `MessageHandler(filters.VOICE | filters.AUDIO)`: `handle_voice_message` in `handlers/voice.py`.
     - `MessageHandler(filters.TEXT & ~filters.COMMAND)`: `handle_text_command` in `handlers/remote_control.py`.
2. **Authentication Gate**:
   - Every handler is wrapped with `@restricted` from `handlers/auth.py`.
   - Checks user against `ALLOWED_USER_IDS`. Previously allowed self-assignment if allowlist was empty (now gated by baseline validation).
3. **Intent & Planning (Where Gemini is Called)**:
   - If user interacts via reply keyboard buttons: handled directly in `handlers/menu.py` (`handle_reply_keyboard`).
   - If user types free text or speaks voice:
     - Local regex/fast actions (`mouse:`, `drag:`, `click`, etc.) executed immediately.
     - Otherwise `services.ai_client.parse_user_instruction_to_plan` sends the prompt + full registered intents documentation to Gemini (`AI_MODEL_CHAIN`, e.g. `gemini-2.0-flash`).
     - Gemini returns structured JSON: `{"steps": [{"intent": "...", "params": {...}}]}`.
     - Each step is validated against Pydantic schema in `core/intent_schema.py`.
4. **Action Execution**:
   - Validated steps are enqueued into `session.queue` in `core/task_queue.py`.
   - `task_executor.process_user_queue()` iterates over steps and calls `execute_step()` in `core/executor.py`.
   - `core/executor.py` has a giant `if/elif` statement spanning over 400 lines dispatching ~75+ distinct actions.
   - For direct menu buttons, `handlers/menu.py` directly executes calls to `services/extra_functions.py`, `services/system_info.py`, etc., completely bypassing the executor!

---

## 3. Windows Operations & Subsystems
- **App Discovery & Launch**: `core/app_resolver.py` scans Start Menu, Registry, Desktop, and PATH, caching them in `data/apps_cache.json`. RapidFuzz fuzzy matches queries; ties or ambiguities can be arbitrated by Gemini.
- **System & Power**: `handlers/system_commands.py` & `services/extra_functions.py` use `os.system("shutdown ...")`, `ctypes.windll.user32.LockWorkStation()`, `os.system("rundll32.exe powrprof.dll...")`.
- **Media & Audio**: `services/media_control.py` uses `pycaw`, `comtypes`, and `ctypes` for master volume, per-process volume, brightness (via WMI/PowerShell/screen_brightness_control).
- **Desktops**: `services/desktops_control.py` uses registry keys (`HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\VirtualDesktops`) and hotkey injection (`ctrl+win+left/right`).
- **Screen & Vision**: `services/screenshot.py` uses `mss` and `Pillow`.
- **Security Guard**: `services/security_guard.py` spawns a background thread polling mouse coordinates via `pyautogui` / `GetCursorPos` and locks the station upon movement > 3px.

---

## 4. State Management & Storage
- **JSON Storage**:
  - `data/reminders.json` (via `ReminderManager` in `scheduler.py`)
  - `data/apps_cache.json` (via `AppResolver` in `core/app_resolver.py`)
  - `data/user_context.json` & `data/scenarios.json` (defined in `config.py`)
- **In-Memory State**:
  - `TaskQueueManager` in `core/task_queue.py` stores `UserTaskSession` with asyncio queues in memory.
  - `context.user_data` in Telegram handlers stores conversational history (`gemini_history`) and waiting states (`awaiting_brightness`, etc.).
  - `notifier.py` stores in-memory timestamps for alert throttling.
- **Process State**:
  - Unsupervised background tasks: `asyncio.create_task(_watch())` in `core/executor.py` monitors processes with `psutil.pid_exists` without a central registry or persistence.

---

## 5. Background Workers & Supervisors
1. **Watchdog (`watchdog.py`)**:
   - External supervisor running `main.py` via `subprocess.Popen`.
   - Implements crash-loop backoff and logs stdout/stderr to `bot_stdout.txt` / `bot_stderr.txt`.
2. **Scheduler & Monitor Loop (`scheduler.py`)**:
   - `background_monitoring_loop` spawned in `main.py` via `asyncio.create_task`.
   - Checks reminders every 120s, polls CPU/RAM/Disk thresholds, and checks hung windows (`IsHungAppWindow`).
3. **Ad-hoc Task Watcher**:
   - `watch_process` creates an anonymous `asyncio.create_task` looping with `asyncio.sleep(5)`.

---

## 6. Security Boundaries & Gaps
- **Authentication**:
  - Previously allowed auto-whitelist of any first connecting user (`first user = owner`). Hardened in baseline to fail-fast.
- **Authorization**:
  - Lack of granular roles (`USER` vs `ADMIN`). All allowed users can execute high-risk operations (e.g. shutdown, format/delete, kill processes).
- **Risk Level & Confirmation**:
  - Confirmation logic was ad-hoc: Telegram inline buttons were constructed individually inside handlers (`handlers/menu.py` or `handlers/system_commands.py`) rather than enforced by an action policy engine.
- **Filesystem Security**:
  - Lack of canonical normalized path checks; relative path traversals (`..`), symlinks, or drives (C:\Windows\System32) were not rigorously isolated in all endpoints.
- **Shell & Subprocess Execution**:
  - `services/extra_functions.py` contains multiple `subprocess.Popen(..., shell=True)` and `os.system(...)` calls without strict parameter escaping.
- **Audit Logging**:
  - No structured immutable audit trail of who initiated destructive or administrative actions.

---

## 7. Technical Debt & Anti-Patterns
1. **Giant Monoliths**:
   - `services/extra_functions.py` is ~1332 lines containing network, clipboard, windows tools, hashing, random, QR, and UI automation mixed together.
   - `core/executor.py` contains ~583 lines with an unmaintainable `if/elif` chain.
   - `handlers/menu.py` is ~1072 lines mixing Telegram UI, business logic, system commands, and inline callbacks.
2. **Dual-Path Execution**:
   - Logic in Telegram menus executes directly; logic from NLP goes through `core/executor.py`. Changes to one do not affect the other.
3. **Result Discrepancies**:
   - Actions return arbitrary tuples `(bool, str)`, raw strings, or `ExtraResult` objects instead of a unified `ActionResult`.
4. **No Persistence Layer**:
   - Tasks and active states are lost when the process restarts.

---

## 8. Audit Statistics
- **Critical Issues**: 4 (Empty allowlist auto-bind vulnerability; lack of centralized policy engine; shell=True subprocess calls; anonymous background tasks without cancellation/recovery).
- **High Issues**: 5 (Giant if/elif executor; unmonitored extra_functions monolith; no persistent task engine; lack of strict path traversal validation across all file actions; direct DB-less JSON storage).
- **Medium Issues**: 6 (Inconsistent action return signatures; unmanaged asyncio background tasks; inline keyboards bypassing domain layer; global mutable singletons; unstructured plain-text logging).
- **Low Issues**: 3 (Duplicated helper functions across modules; hardcoded timeouts; lack of type annotations in legacy handlers).

---

## 9. Functions That Must Not Break
- `open_application` (Fuzzy app resolver + launch)
- `close_application` / `kill_process`
- `switch_virtual_desktop` / `create_virtual_desktop`
- `take_screenshot` (Full screen, monitor, virtual desktops)
- `set_volume` / `set_brightness` / `media_control`
- `get_system_status` / `get_disk_space` / `check_system_thresholds`
- `shutdown_pc` / `restart_pc` / `lock_pc` / `sleep_pc`
- `create_folder` / `create_file` / `move_item` / `copy_item` / `delete_item` / `search_files`
- `open_website` / `web_search` / `download_from_wikipedia` / `download_file`
- `set_reminder` / `list_reminders` / `cancel_reminder`
- `security_guard` (Mouse motion trap)
- `transcribe_audio_bytes` (Voice recognition via Gemini)
- `ask_gemini` / `parse_user_instruction_to_plan` (Conversational & Planner)
- Diagnostic & autostart utilities (`cmd_diag`, `ensure_autostart`)

---

## 10. Files Requiring Migration
- `core/executor.py` → Split into `application/execution/executor.py`, `application/execution/context.py`, Action Handlers.
- `core/intent_schema.py` → Domain models & action schemas.
- `core/task_queue.py` → `application/task_engine/*` (SQLite backed).
- `services/extra_functions.py` → Split into `services/{files, windows, network, processes, media, security, clipboard, vision, utilities}/`.
- `handlers/auth.py` → `security/authentication.py` & `security/authorization.py`.
- `handlers/menu.py` → `infrastructure/telegram/handlers/menu.py` (decoupled from direct system calls).
- `handlers/remote_control.py` → Decoupled into `infrastructure/telegram/handlers/`.
- `scheduler.py` → `scheduler/` with APScheduler + SQLite persistence.
- `watchdog.py` → `supervisor/` with health monitoring and exponential backoff.
- `config.py` → `config/settings.py` (Pydantic Settings).
- `logger_setup.py` → Structured logging via `structlog`.
