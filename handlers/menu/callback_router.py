import os
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
