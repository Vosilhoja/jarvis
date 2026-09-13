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

    if data.startswith("tools_"):
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        _tools_categories = {
            "tools_windows": (
                "🛠 *Оснастки Windows:*",
                [
                    ("📅 Планировщик задач",    "open_tool_task_scheduler"),
                    ("🖥 Диспетчер устройств",  "open_tool_device_manager"),
                    ("📋 Просмотр событий",     "open_tool_event_viewer"),
                    ("⚙️ Службы Windows",        "open_tool_services"),
                    ("🔧 Панель управления",     "open_tool_control"),
                ]
            ),
            "tools_maintenance": (
                "🧹 *Обслуживание системы:*",
                [
                    ("🧹 Очистить %TEMP%",       "tool_clean_temp"),
                    ("🗑 Очистить корзину",      "tool_empty_bin"),
                    ("💾 Отчёт об аккумуляторе", "tool_battery_report"),
                    ("🔄 Перезапустить Проводник","tool_restart_explorer"),
                    ("🛡 Точка восстановления",  "tool_restore_point"),
                ]
            ),
            "tools_network": (
                "⚙️ *Диагностика / Сеть:*",
                [
                    ("🏓 Ping 8.8.8.8",          "tool_ping_google"),
                    ("🏓 Ping ya.ru",             "tool_ping_yandex"),
                    ("🌐 IP-адреса",              "tool_ip_info"),
                    ("💨 Сброс DNS",              "tool_flush_dns"),
                    ("📡 Адаптеры сети",          "tool_net_adapters"),
                ]
            ),
            "tools_media": (
                "📸 *Экран и медиа:*",
                [
                    ("📸 Скриншот экрана",        "tool_screenshot"),
                    ("🌙 Ночной свет",            "tool_night_light"),
                    ("🎨 Тёмная/светлая тема",    "tool_dark_mode"),
                    ("🔊 Звуковые устройства",    "tool_audio_devices"),
                    ("⌨ Подсветка клавы",        "tool_backlight"),
                ]
            ),
        }
        if data in _tools_categories:
            title, items = _tools_categories[data]
            buttons = [[InlineKeyboardButton(label, callback_data=cb)] for label, cb in items]
            buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="tools_back")])
            await query.edit_message_text(title, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
        elif data == "tools_back":
            back_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🛠 Оснастки Windows",      callback_data="tools_windows")],
                [InlineKeyboardButton("🧹 Обслуживание системы",  callback_data="tools_maintenance")],
                [InlineKeyboardButton("⚙️ Диагностика / Сеть",    callback_data="tools_network")],
                [InlineKeyboardButton("📸 Экран и медиа",         callback_data="tools_media")],
            ])
            await query.edit_message_text("🧰 *Инструменты:* выберите категорию", reply_markup=back_kb, parse_mode="Markdown")
        elif data.startswith("open_tool_") or data.startswith("tool_"):
            # Выполняем конкретный инструмент
            await _execute_tool_action(data, query, update, context)
        return

async def _execute_tool_action(data: str, query, update, context):
    """Выполняет действие инструмента по callback_data."""
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton

    _back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ К инструментам", callback_data="tools_back")]])

    try:
        if data == "open_tool_task_scheduler":
            from services.extra_functions import open_task_scheduler
            open_task_scheduler()
            await query.answer("📅 Планировщик открыт")
        elif data == "open_tool_device_manager":
            from services.extra_functions import open_device_manager
            open_device_manager()
            await query.answer("🖥 Диспетчер устройств открыт")
        elif data == "open_tool_event_viewer":
            from services.extra_functions import open_event_viewer
            open_event_viewer()
            await query.answer("📋 Просмотр событий открыт")
        elif data == "open_tool_services":
            import os
            os.system("services.msc")
            await query.answer("⚙️ Службы Windows открыты")
        elif data == "open_tool_control":
            import os
            os.startfile("control")
            await query.answer("🔧 Панель управления открыта")
        elif data == "tool_clean_temp":
            from services.system_monitor import preview_and_cleanup_temp
            count, freed_mb = preview_and_cleanup_temp()
            await query.edit_message_text(
                f"🧹 *Очистка %TEMP%:*\n\nУдалено файлов: `{count}` (~{freed_mb} МБ освобождено)",
                reply_markup=_back_kb, parse_mode="Markdown"
            )
        elif data == "tool_empty_bin":
            from services.extra_functions import empty_recycle_bin
            res = empty_recycle_bin()
            await query.edit_message_text(res, reply_markup=_back_kb)
        elif data == "tool_battery_report":
            from services.power_tools import battery_report
            res = battery_report()
            await query.edit_message_text(res[:3000], reply_markup=_back_kb)
        elif data == "tool_restart_explorer":
            from services.extra_functions import restart_explorer
            res = restart_explorer()
            await query.edit_message_text(res, reply_markup=_back_kb)
        elif data == "tool_restore_point":
            from services.extra_functions import create_restore_point
            res = create_restore_point("Jarvis Manual Point")
            await query.edit_message_text(res[:2000], reply_markup=_back_kb)
        elif data == "tool_ping_google":
            from services.extra_functions import ping_host
            res = ping_host("8.8.8.8")
            await query.edit_message_text(f"🏓 *Ping 8.8.8.8:*\n```\n{res[:1500]}\n```", reply_markup=_back_kb, parse_mode="Markdown")
        elif data == "tool_ping_yandex":
            from services.extra_functions import ping_host
            res = ping_host("ya.ru")
            await query.edit_message_text(f"🏓 *Ping ya.ru:*\n```\n{res[:1500]}\n```", reply_markup=_back_kb, parse_mode="Markdown")
        elif data == "tool_ip_info":
            from services.extra_functions import get_local_ip, get_public_ip
            await query.edit_message_text(
                f"🌐 *IP-адреса:*\n\n🏠 Локальный: `{get_local_ip()}`\n🌍 Внешний: `{get_public_ip()}`",
                reply_markup=_back_kb, parse_mode="Markdown"
            )
        elif data == "tool_flush_dns":
            from services.extra_functions import flush_dns
            res = flush_dns()
            await query.edit_message_text(res, reply_markup=_back_kb)
        elif data == "tool_net_adapters":
            from services.extra_functions import get_network_adapters
            res = get_network_adapters()
            await query.edit_message_text(res[:3000], reply_markup=_back_kb)
        elif data == "tool_screenshot":
            from handlers.system_commands import send_screenshot
            await send_screenshot(update, context, monitor_index=0)
            await query.answer("📸 Скриншот сделан")
        elif data == "tool_night_light":
            from services.extra_functions import open_night_light
            open_night_light()
            await query.answer("🌙 Ночной свет открыт")
        elif data == "tool_dark_mode":
            from services.extra_functions import toggle_dark_mode
            res = toggle_dark_mode()
            await query.edit_message_text(res, reply_markup=_back_kb)
        elif data == "tool_audio_devices":
            from services.extra_functions import list_audio_devices
            res = list_audio_devices()
            await query.edit_message_text(res[:3000], reply_markup=_back_kb)
        elif data == "tool_backlight":
            from services.extra_functions import toggle_keyboard_backlight
            res = toggle_keyboard_backlight()
            await query.edit_message_text(res, reply_markup=_back_kb)
        else:
            await query.answer("⚠️ Действие не реализовано")
    except Exception as e:
        logger.error(f"Ошибка выполнения инструмента {data}: {e}", exc_info=True)
        try:
            await query.edit_message_text(f"⚠️ Ошибка: {e}", reply_markup=_back_kb)
        except Exception:
            await query.answer(f"⚠️ Ошибка: {e}", show_alert=True)

