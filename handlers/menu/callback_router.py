import os
import asyncio
import logging
from telegram import Update
from telegram.ext import ContextTypes
from handlers.auth import restricted
from handlers.menu.keyboards import get_main_reply_keyboard

logger = logging.getLogger("jarvis")

@restricted
async def menu_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает Inline кнопки подтверждений и действий."""
    query = update.callback_query
    data = query.data
    chat_id = update.effective_chat.id

    await query.answer()

    if data == "cancel_action":
        await query.edit_message_text("🚫 Действие отменено.")
        return

    if data in ("policy_confirm_yes", "policy_confirm_no", "confirm_delete_yes", "confirm_delete_no"):
        # Единый обработчик подтверждений PolicyEngine (см. core/executor.py).
        # Раньше кнопки confirm_delete_yes/no отправлялись из
        # core/execution/file_actions.py, но никогда не обрабатывались здесь —
        # клик по ним ничего не делал, а сам файл/папка никогда не удалялись.
        # Теперь и CONFIRM-уровень риска, и старые callback_data ведут в один
        # и тот же поток подтверждения через session.pending_confirmation.
        from core.task_queue import task_queue_manager
        from core.executor import task_executor
        from services.formatting import convert_markdown_to_telegram

        session = task_queue_manager.get_session(chat_id)
        pending = session.pending_confirmation
        session.pending_confirmation = None

        if not pending or "step" not in pending:
            await query.edit_message_text("⚠️ Запрос на подтверждение устарел или уже обработан.")
            return

        if data in ("policy_confirm_no", "confirm_delete_no"):
            await query.edit_message_text("🚫 Действие отменено пользователем.")
            return

        step = pending["step"]
        step.params["_policy_confirmed"] = True
        await query.edit_message_text("⏳ Подтверждено, выполняю…")
        try:
            success, report = await task_executor.executor.execute_step(step, session, bot=context.bot)
        except Exception as e:
            logger.error(f"Ошибка выполнения подтверждённого шага {step.intent}: {e}", exc_info=True)
            success, report = False, f"❌ Ошибка в шаге «{step.intent}»: {e}"

        clean_report = convert_markdown_to_telegram(str(report))
        try:
            await context.bot.send_message(chat_id=chat_id, text=clean_report, parse_mode="Markdown")
        except Exception:
            await context.bot.send_message(chat_id=chat_id, text=str(report))
        return

    if data == "main_menu":
        await query.edit_message_text(
            "🏠 *Главное меню:* выберите категорию",
            reply_markup=None,
            parse_mode="Markdown"
        )
        await query.message.reply_text(
            "🏠 Вы в главном меню",
            reply_markup=get_main_reply_keyboard()
        )
        return

    if data == "do_shutdown":
        from handlers.system_commands import cmd_shutdown_execute
        await cmd_shutdown_execute(update, context)
        return

    if data == "do_restart":
        from handlers.system_commands import cmd_restart_execute
        await cmd_restart_execute(update, context)
        return

    if data == "cancel_shutdown":
        os.system("shutdown /a")
        await query.edit_message_text("✅ Выключение/перезагрузка отменена!")
        return

    if data.startswith("do_delete_desktop_"):
        try:
            num = int(data.rsplit("_", 1)[-1])
        except ValueError:
            await query.edit_message_text("⚠️ Некорректный номер стола.")
            return
        import asyncio
        from services.desktops_control import delete_desktop_number
        from handlers.menu.keyboards import get_control_reply_keyboard
        res = await asyncio.to_thread(delete_desktop_number, num)
        await query.edit_message_text(res)
        await query.message.reply_text(
            "🖱 *Управление окнами, клавишами и ПК:*",
            reply_markup=get_control_reply_keyboard(),
            parse_mode="Markdown"
        )
        return

    if data == "sys_info":
        from handlers.system_commands import cmd_sysinfo
        await cmd_sysinfo(update, context)
        return

    if data.startswith("mouse_"):
        from handlers.remote_control import handle_remote_callback
        await handle_remote_callback(update, context)
        return

    if data.startswith("file_"):
        from handlers.files import show_files_menu, handle_file_callback
        if data == "file_menu":
            await show_files_menu(update, context)
        else:
            await handle_file_callback(update, context)
        return

    if data.startswith("kill_hung_"):
        from services.system_info import kill_process_by_pid
        try:
            pid = int(data.replace("kill_hung_", ""))
            success = kill_process_by_pid(pid)
            if success:
                await query.edit_message_text(f"✅ Процесс {pid} завершён.")
            else:
                await query.edit_message_text(f"⚠️ Не удалось завершить процесс {pid} (уже закрыт или нет прав).")
        except Exception as e:
            await query.edit_message_text(f"⚠️ Ошибка: {e}")
        return

    if data.startswith("kill_proc_"):
        from handlers.process_commands import handle_kill_callback
        await handle_kill_callback(update, context)
        return

    if data in ("procs_sort_ram", "procs_sort_cpu") or data.startswith("procs_refresh_"):
        from handlers.process_commands import show_processes
        sort_by = "cpu" if "cpu" in data else "memory"
        await show_processes(update, context, sort_by=sort_by)
        return

    if data.startswith("scr_"):
        idx_str = data.replace("scr_", "")
        idx = int(idx_str) if idx_str != "all" else 0
        from handlers.system_commands import send_screenshot
        await send_screenshot(update, context, monitor_index=idx)
        return
