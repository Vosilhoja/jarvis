"""Desktop, window and keyboard control actions."""
import asyncio
import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from handlers.menu.keyboards import get_control_reply_keyboard

KEY_ACTION_MAP = {
    "⌨ Enter": ["enter"], "⌨ Escape": ["escape"], "⌨ Win": ["win"],
    "⌨ Alt+Tab": ["alt", "tab"], "⌨ Alt+F4": ["alt", "f4"],
    "⌨ Win+D": ["win", "d"], "⌨ Ctrl+C": ["ctrl", "c"], "⌨ Ctrl+V": ["ctrl", "v"],
}

async def handle_control(update, context, text: str) -> bool:
    if text in KEY_ACTION_MAP:
        import pyautogui
        keys = KEY_ACTION_MAP[text]
        try:
            pyautogui.hotkey(*keys)
            await update.message.reply_text(f"⌨ Нажато: `{' + '.join(keys).upper()}`", parse_mode="Markdown")
        except Exception as exc:
            await update.message.reply_text(f"Ошибка: {exc}")
        return True
    match = re.search(r"Стол\s+(\d+)", text)
    if match and ("🎛" in text or "📍" in text or "стол" in text.lower()) and "снимок" not in text.lower() and "новый" not in text.lower():
        from services.desktops_control import switch_to_desktop_number
        try:
            ok = await asyncio.to_thread(switch_to_desktop_number, int(match.group(1)))
            if ok:
                await update.message.reply_text(f"🎛 Переключено на *Рабочий стол {int(match.group(1))}*", reply_markup=get_control_reply_keyboard(), parse_mode="Markdown")
            else:
                await update.message.reply_text(f"⚠️ Не удалось подтвердить переход на стол {int(match.group(1))}.")
        except Exception as exc:
            await update.message.reply_text(f"⚠️ Не удалось переключиться на стол {int(match.group(1))}: {exc}")
        return True
    if text == "➕ Новый стол":
        from services.desktops_control import create_virtual_desktop
        try:
            from services.desktops_control import get_desktop_count
            before = await asyncio.to_thread(get_desktop_count)
            total = await asyncio.to_thread(create_virtual_desktop)
            if total > before:
                await update.message.reply_text(f"➕ Создан новый виртуальный рабочий стол! (Всего столов: *{total}*)", reply_markup=get_control_reply_keyboard(), parse_mode="Markdown")
            else:
                await update.message.reply_text("⚠️ Не удалось подтвердить создание рабочего стола.")
        except Exception as exc:
            await update.message.reply_text(f"⚠️ Не удалось создать рабочий стол: {exc}")
        return True
    if text == "🗑 Удалить текущий стол":
        from services.desktops_control import get_current_desktop_number, get_desktop_count
        current, total = get_current_desktop_number(), get_desktop_count()
        if total <= 1:
            await update.message.reply_text("⚠️ Нельзя удалить единственный оставшийся рабочий стол."); return True
        await update.message.reply_text(f"⚠️ *Удалить рабочий стол {current}?* Все открытые на нём окна свернутся на соседний стол.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"⚠️ Да, удалить Стол {current}!", callback_data=f"do_delete_desktop_{current}")], [InlineKeyboardButton("❌ Отмена", callback_data="cancel_action")]]), parse_mode="Markdown"); return True
    if text == "🖱 Пульт мыши":
        from handlers.remote_control import show_remote_control_menu
        await show_remote_control_menu(update, context); return True
    return False
