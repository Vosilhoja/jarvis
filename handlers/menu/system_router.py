"""System information, screenshots and power actions."""
import asyncio
import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from handlers.menu.keyboards import get_screenshot_reply_keyboard
from handlers.menu.input_flows import ask_for_number


async def handle_system(update, context: ContextTypes.DEFAULT_TYPE, text: str) -> bool:
    if text == "📸 Весь экран":
        from handlers.system_commands import send_screenshot
        await send_screenshot(update, context, monitor_index=0, reply_markup=get_screenshot_reply_keyboard()); return True
    if text == "📝 Выбрать столы вручную":
        context.user_data["awaiting_screenshot_choice"] = True
        await update.message.reply_text("📝 *Введите номера рабочих столов:*\n\n• Один: `1`\n• Несколько: `1,3,5`\n• Все: `все`", parse_mode="Markdown"); return True
    if text == "📸 Все столы подряд":
        from services.desktops_control import get_desktop_count
        from services.screenshot import take_multiple_desktops_screenshots
        count = get_desktop_count(); await update.message.reply_text(f"📸 Делаю скриншоты всех {count} виртуальных столов...")
        try:
            for desk, buf in take_multiple_desktops_screenshots(list(range(1, count + 1)), monitor_index=0):
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=buf, caption=f"📸 Снимок: *Рабочий стол {desk}*", parse_mode="Markdown")
        except Exception as exc:
            await update.message.reply_text(f"⚠️ Ошибка: {exc}")
        await update.message.reply_text("✅ Все скриншоты сделаны, вы вернулись на свой исходный рабочий стол."); return True
    match = re.search(r"Стола?\s+(\d+)", text)
    if match and ("Снимок" in text or "Стол" in text) and not text.startswith(("🎛", "📍 Стол")):
        from handlers.system_commands import send_screenshot
        await send_screenshot(update, context, monitor_index=0, desktop_num=int(match.group(1)), reply_markup=get_screenshot_reply_keyboard()); return True
    if text == "📋 Процессы":
        from handlers.process_commands import show_processes
        await show_processes(update, context, sort_by="memory"); return True
    if text == "🤖 ИИ-чат":
        context.user_data["ai_mode"] = True
        await update.message.reply_text("🤖 *Режим ИИ-диалога:*\n\nВы можете просто писать текст или отправлять голосовые сообщения. Jarvis поймет любую задачу!\n\n_Для выхода нажмите_ ⬅️ *Назад в меню*", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("⬅️ Назад в меню")]], resize_keyboard=True, is_persistent=True), parse_mode="Markdown"); return True
    if text == "⏰ Напоминания":
        from scheduler import reminder_manager
        active = reminder_manager.get_active_reminders(update.effective_chat.id)
        msg = "⏰ *Напоминания:*\n\nАктивных напоминаний нет.\n\n_Чтобы создать: «напомни через 20 минут проверить почту»_" if not active else "⏰ *Ваши активные напоминания:*\n\n" + "".join(f"• «{r['text']}» — `{r['next_trigger_at']}`\n" for r in active)
        await update.message.reply_text(msg, parse_mode="Markdown"); return True
    if text == "📊 Инфо о системе":
        from handlers.system_commands import cmd_sysinfo
        await cmd_sysinfo(update, context); return True
    if text == "🌡 Температура":
        from services.system_info import get_cpu_temperature
        temp = get_cpu_temperature(); result = f"🌡 *Температура процессора:* `{temp}°C`\n\nСтатус: " + ("🟢 В норме" if temp < 75 else "🟡 Повышенная" if temp < 85 else "🔴 Высокая!") if temp is not None else "🌡 Датчик температуры не вернул значение (WMI ThermalZone не передает данные на этой конфигурации)."
        await update.message.reply_text(result, parse_mode="Markdown"); return True
    if text == "🔋 Аккумулятор":
        from services.extra_functions import get_battery_info
        await update.message.reply_text(get_battery_info(), parse_mode="Markdown"); return True
    if text in ("💾 Диски", "🧠 Железо"):
        from services.system_info import get_system_metrics
        from adapters.windows.misc_tools import get_hardware_info
        if text == "🧠 Железо":
            result = await asyncio.to_thread(get_hardware_info)
        else:
            metrics = await asyncio.to_thread(get_system_metrics)
            rows = [
                f"• {disk['device']}: свободно {disk['free_gb']} ГБ из {disk['total_gb']} ГБ ({disk['percent']}%)"
                for disk in metrics.get("disks", [])
            ]
            result = "💾 *Диски:*\n\n" + ("\n".join(rows) if rows else "Данные о дисках не получены.")
        await update.message.reply_text(result, parse_mode="Markdown"); return True
    if text == "📅 Календарь сегодня":
        from services.calendar_client import get_today_events
        await update.message.reply_text("📅 Проверяю Google Calendar..."); await update.message.reply_text(await asyncio.to_thread(get_today_events), parse_mode="Markdown"); return True
    if text == "📈 Недельная сводка":
        from services.usage_stats import get_weekly_report
        await update.message.reply_text("📈 Собираю статистику за неделю..."); await update.message.reply_text(await asyncio.to_thread(get_weekly_report), parse_mode="Markdown"); return True
    if text == "🖥 Разрешение":
        from services.extra_functions import get_screen_resolution
        await update.message.reply_text(get_screen_resolution(), parse_mode="Markdown"); return True
    if text == "🙈 Скрыть все окна":
        from adapters.windows.misc_tools import hide_all_windows_except_active
        await update.message.reply_text(await asyncio.to_thread(hide_all_windows_except_active), parse_mode="Markdown"); return True
    if text == "🌅 Утренний брифинг":
        from services.morning_briefing import build_morning_briefing
        await update.message.reply_text("🌅 Собираю утренний брифинг..."); await update.message.reply_text(await build_morning_briefing(), parse_mode="Markdown"); return True
    if text == "🌐 IP-адреса":
        from services.extra_functions import get_local_ip, get_public_ip
        await update.message.reply_text(f"🌐 *IP-адреса:*\n\n🏠 Локальный: `{get_local_ip()}`\n🌍 Внешний: `{get_public_ip()}`", parse_mode="Markdown"); return True
    if text == "📋 Буфер обмена":
        from services.extra_functions import get_clipboard
        await update.message.reply_text(f"📋 Буфер обмена:\n\n{get_clipboard() or '(пусто)'}"); return True
    if text == "💡 Яркость":
        await ask_for_number(update, context, "awaiting_brightness", "💡 *Яркость:* введите уровень от 0 до 100\n\n_Например: 70_"); return True
    if text == "⌨ Подсветка клавы":
        from services.extra_functions import toggle_keyboard_backlight
        await update.message.reply_text(toggle_keyboard_backlight()); return True
    if text == "🔇 Режим Тихий час":
        from services.extra_functions import do_not_disturb_mode
        await update.message.reply_text(do_not_disturb_mode()); return True
    if text == "🧹 Очистить %TEMP%":
        from services.system_monitor import preview_and_cleanup_temp
        count, freed = preview_and_cleanup_temp(); await update.message.reply_text(f"🧹 Очищено временных файлов: {count} (~{freed} МБ)"); return True
    if text == "🗑 Очистить корзину":
        from services.extra_functions import empty_recycle_bin
        await update.message.reply_text(empty_recycle_bin()); return True
    if text in ("🛡 Включить охрану", "включить охрану"):
        from services.security_guard import security_guard, make_guard_alert_callback
        callback = make_guard_alert_callback(
            context.bot, update.effective_chat.id, loop=asyncio.get_running_loop()
        )
        await update.message.reply_text(
            security_guard.start_guard(on_trigger_callback=callback, delay_sec=5),
            parse_mode="Markdown")
        return True
    if text in ("🛑 Снять с охраны", "снять с охраны", "выключить охрану"):
        from services.security_guard import security_guard
        await update.message.reply_text(security_guard.stop_guard(), parse_mode="Markdown"); return True
    if text == "🔒 Заблокировать":
        from handlers.system_commands import cmd_lock
        await cmd_lock(update, context); return True
    if text == "😴 Режим сна":
        from handlers.system_commands import cmd_sleep
        await cmd_sleep(update, context); return True
    if text == "🔁 Перезагрузка":
        await update.message.reply_text(
            "⚠️ *Вы уверены, что хотите перезагрузить компьютер?*",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚠️ Да, перезагрузить!", callback_data="do_restart")],
                [InlineKeyboardButton("❌ Отмена", callback_data="cancel_action")]]),
            parse_mode="Markdown"); return True
    if text == "⛔ Выключить ПК":
        await update.message.reply_text(
            "⚠️ *Вы уверены, что хотите выключить компьютер?*",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚠️ Да, выключить ПК!", callback_data="do_shutdown")],
                [InlineKeyboardButton("❌ Отмена", callback_data="cancel_action")]]),
            parse_mode="Markdown"); return True
    return False
