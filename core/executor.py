import io
import time
import logging
import asyncio
from types import SimpleNamespace
from typing import Tuple, Callable, Dict, Awaitable
from telegram import Bot, InputFile, InlineKeyboardButton, InlineKeyboardMarkup

from core.intent_schema import StepModel
from core.task_queue import UserTaskSession, task_queue_manager
from core.execution.common import resolve_path_aliases
import core.execution as actions
from security.policy_engine import policy_engine

logger = logging.getLogger("jarvis")

# Intent'ы, которые никогда не должны требовать доп. подтверждения от
# PolicyEngine, т.к. они сами являются частью diалога подтверждения/чата
# и не производят никакого side-effect'а.
_POLICY_EXEMPT_INTENTS = {"chat_reply", "clarify"}

# Intent dispatch table for O(1) modular execution
INTENT_HANDLER_MAP: Dict[str, Callable[[StepModel, UserTaskSession, Bot], Awaitable[Tuple[bool, str]]]] = {
    # Applications
    "open_application": actions.handle_open_application,
    "close_application": actions.handle_close_application,
    "list_installed_apps": actions.handle_list_installed_apps,

    # File System & Explorer
    "open_explorer_path": actions.handle_open_explorer_path,
    "create_folder": actions.handle_create_folder,
    "create_file": actions.handle_create_file,
    "move_item": actions.handle_move_item,
    "copy_item": actions.handle_copy_item,
    "rename_item": actions.handle_rename_item,
    "search_files": actions.handle_search_files,
    "delete_item": actions.handle_delete_item,

    # Screenshots
    "take_screenshot": actions.handle_take_screenshot,

    # Reminders & Scenarios
    "set_reminder": actions.handle_set_reminder,
    "list_reminders": actions.handle_list_reminders,
    "cancel_reminder": actions.handle_cancel_reminder,
    "create_scenario": actions.handle_create_scenario,
    "run_scenario": actions.handle_run_scenario,
    "focus_mode": actions.handle_focus_mode,

    # Search & Web
    "open_website": actions.handle_open_website,
    "web_search": actions.handle_web_search,
    "download_from_wikipedia": actions.handle_download_from_wikipedia,
    "download_file": actions.handle_download_file,
    "get_weather": actions.handle_get_weather,
    "get_exchange_rate": actions.handle_get_exchange_rate,

    # System Controls & Monitors
    "switch_virtual_desktop": actions.handle_switch_virtual_desktop,
    "create_virtual_desktop": actions.handle_create_virtual_desktop,
    "delete_virtual_desktop": actions.handle_delete_virtual_desktop,
    "list_running_processes": actions.handle_list_running_processes,
    "kill_process": actions.handle_kill_process,
    "get_disk_space": actions.handle_get_disk_space,
    "set_volume": actions.handle_set_volume,
    "set_brightness": actions.handle_set_brightness,
    "media_control": actions.handle_media_control,
    "get_system_status": actions.handle_get_system_status,
    "lock_pc": actions.handle_lock_pc,
    "start_guard": actions.handle_start_guard,
    "stop_guard": actions.handle_stop_guard,
    "sleep_pc": actions.handle_sleep_pc,
    "shutdown_pc": actions.handle_shutdown_pc,
    "restart_pc": actions.handle_restart_pc,
    "cleanup_temp": actions.handle_cleanup_temp,
    "watch_process": actions.handle_watch_process,
    "chat_reply": actions.handle_chat_reply,
    "clarify": actions.handle_clarify,
    "clear_browser_cache": actions.handle_clear_browser_cache,
    "create_restore_point": actions.handle_create_restore_point,
    "set_wallpaper": actions.handle_set_wallpaper,
    "toggle_caps_lock": actions.handle_toggle_caps_lock,
    "list_audio_devices": actions.handle_list_audio_devices,
    "set_process_volume": actions.handle_set_process_volume,
    "close_active_window": actions.handle_close_active_window,
    "laptop_screen_sleep": actions.handle_laptop_screen_sleep,
}


class StepExecutor:
    """Исполняет шаги интентов, отправляет отчеты и управляет контекстом сессии."""

    async def execute_step(self, step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
        intent = step.intent
        params = step.params
        chat_id = session.user_id

        try:
            if intent not in _POLICY_EXEMPT_INTENTS and not params.get("_policy_confirmed"):
                decision = await policy_engine.evaluate(
                    action=SimpleNamespace(name=intent),
                    context=SimpleNamespace(user_id=chat_id),
                    params=params,
                )
                if not decision.allowed:
                    logger.warning(
                        f"🚫 PolicyEngine отказал в выполнении '{intent}' для {chat_id}: {decision.reason}"
                    )
                    return False, f"🚫 Действие запрещено политикой безопасности: {decision.reason}"

                if decision.requires_confirmation:
                    session.pending_confirmation = {"step": step}
                    kb = InlineKeyboardMarkup([
                        [InlineKeyboardButton("⚠️ Подтвердить", callback_data="policy_confirm_yes")],
                        [InlineKeyboardButton("❌ Отмена", callback_data="policy_confirm_no")],
                    ])
                    await bot.send_message(
                        chat_id=chat_id,
                        text=(
                            f"⚠️ *Требуется подтверждение*\n"
                            f"Действие: `{intent}`\n"
                            f"{decision.reason or 'Операция помечена как рискованная.'}"
                        ),
                        reply_markup=kb,
                        parse_mode="Markdown",
                    )
                    logger.info(f"⏳ Действие '{intent}' от {chat_id} ожидает подтверждения (risk={decision.risk_level}).")
                    return True, "⏳ Запрошено подтверждение действия — ожидаю вашего ответа."

            handler = INTENT_HANDLER_MAP.get(intent)
            if handler:
                return await handler(step, session, bot)

            # Fallback к расширенным функциям (dispatch_extra)
            # ВАЖНО: dispatch_extra синхронный и может содержать блокирующие
            # subprocess-вызовы (ping, tracert, flush dns и т.д. до 45 сек).
            # Обязательно выполняем в отдельном потоке, иначе весь бот
            # замораживается для ВСЕХ пользователей на время вызова,
            # так как main.py использует concurrent_updates(False).
            from services.extra_functions import dispatch_extra
            extra = await asyncio.to_thread(dispatch_extra, intent, params, session)
            if extra is not None:
                if extra.photo_bytes:
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=InputFile(io.BytesIO(extra.photo_bytes), extra.photo_name),
                        caption=extra.text[:900],
                    )
                return extra.success, extra.text

            return False, f"Неизвестный intent: {intent}"

        except Exception as e:
            logger.error(f"Ошибка выполнения шага {intent}: {e}", exc_info=True)
            return False, f"❌ Ошибка в шаге «{intent}»: {e}"


class TaskExecutorService:
    def __init__(self):
        self.executor = StepExecutor()

    async def process_user_queue(self, session: UserTaskSession, bot: Bot):
        """Обрабатывает очередь шагов пользователя по очереди (FIFO)."""
        if session.is_running:
            return

        session.is_running = True
        try:
            while not session.queue.empty():
                step = await session.queue.get()
                session.current_step = step

                # Предохранитель: если шаг выполняется дольше 10 секунд, уведомляем пользователя
                try:
                    step_task = asyncio.create_task(self.executor.execute_step(step, session, bot))
                    done, pending = await asyncio.wait({step_task}, timeout=10.0)
                    if not done:
                        try:
                            await bot.send_message(
                                chat_id=session.user_id,
                                text="⏳ Действие выполняется дольше обычного, пожалуйста подождите...",
                            )
                        except Exception:
                            pass
                        success, report = await step_task
                    else:
                        success, report = step_task.result()
                except Exception as e:
                    success, report = False, f"❌ Ошибка выполнения шага: {e}"

                session.history.append({"intent": step.intent, "success": success, "time": time.time()})
                session.context_memory.setdefault("last_plan_steps", [])
                session.context_memory["last_plan_steps"].append({"intent": step.intent, "params": step.params})
                session.context_memory["last_plan_steps"] = session.context_memory["last_plan_steps"][-30:]

                if step.intent != "chat_reply":
                    from services.formatting import convert_markdown_to_telegram
                    clean_report = convert_markdown_to_telegram(str(report))
                    try:
                        await bot.send_message(chat_id=session.user_id, text=clean_report, parse_mode="Markdown")
                    except Exception:
                        await bot.send_message(chat_id=session.user_id, text=str(report))

                session.queue.task_done()
        finally:
            session.is_running = False
            session.current_step = None


task_executor = TaskExecutorService()
