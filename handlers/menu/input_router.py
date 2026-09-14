"""Handlers for values entered after a keyboard action."""

import asyncio
import io
from telegram import InputFile, Update
from telegram.ext import ContextTypes

from handlers.menu.input_flows import looks_like_keyboard_button, parse_desktop_selection


async def _screenshots(update, context, selection):
    from services.desktops_control import get_desktop_count
    from handlers.system_commands import send_screenshot
    from services.screenshot import take_multiple_desktops_screenshots

    count = get_desktop_count()
    desks = list(range(1, count + 1)) if selection == "all" else [
        n for n in selection if 1 <= n <= count
    ]
    if selection != "all":
        invalid = [n for n in selection if n not in desks]
        if invalid:
            await update.message.reply_text(
                f"⚠️ Столов {', '.join(map(str, invalid))} нет (сейчас 1–{count})."
            )
    if not desks:
        await update.message.reply_text(f"⚠️ Нет подходящих номеров. Сейчас рабочих столов: {count}.")
        return
    if len(desks) == 1:
        await send_screenshot(update, context, monitor_index=0, desktop_num=desks[0])
        return
    await update.message.reply_text(f"📸 Делаю скриншоты столов: {', '.join(map(str, desks))}...")
    try:
        for desk_num, buf in take_multiple_desktops_screenshots(desks, monitor_index=0):
            await context.bot.send_photo(
                chat_id=update.effective_chat.id, photo=buf,
                caption=f"📸 Снимок: Рабочий стол {desk_num}",
            )
        await update.message.reply_text("✅ Скриншоты готовы, вы на исходном рабочем столе.")
    except Exception as exc:
        await update.message.reply_text(f"⚠️ Ошибка скриншота: {exc}")


async def handle_pending_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> bool:
    data = context.user_data
    if data.get("awaiting_screenshot_choice"):
        selection = parse_desktop_selection(text)
        if selection is not None:
            data.pop("awaiting_screenshot_choice", None)
            await _screenshots(update, context, selection)
            return True
        if looks_like_keyboard_button(text):
            data.pop("awaiting_screenshot_choice", None)
        else:
            await update.message.reply_text(
                "⚠️ Неверный формат. Введите числа через запятую или напишите `все`\n"
                "_Пример: `1,3` или `2`_", parse_mode="Markdown")
            return True

    if data.get("awaiting_brightness"):
        data.pop("awaiting_brightness")
        try:
            level = int(text.replace("%", "").strip())
            if not 0 <= level <= 100:
                raise ValueError
            from services.media_control import set_brightness
            await update.message.reply_text(f"💡 {set_brightness(level)}")
        except ValueError:
            await update.message.reply_text("⚠️ Введите число от 0 до 100. Например: `70`", parse_mode="Markdown")
        return True

    if data.get("awaiting_volume"):
        data.pop("awaiting_volume")
        try:
            level = int(text.replace("%", "").strip())
            if not 0 <= level <= 100:
                raise ValueError
            from services.media_control import set_volume_pycaw, change_volume
            if set_volume_pycaw(level):
                result = f"🎙 Громкость установлена на {level}%"
            else:
                result = f"🎙 {change_volume('up' if level > 50 else 'down', level=level)}"
            await update.message.reply_text(result)
        except ValueError:
            await update.message.reply_text("⚠️ Введите число от 0 до 100. Например: `50`", parse_mode="Markdown")
        return True

    if data.get("awaiting_file_search"):
        data.pop("awaiting_file_search")
        from services.extra_functions import search_files
        await update.message.reply_text(await asyncio.to_thread(search_files, text), parse_mode="Markdown")
        return True
    if data.get("awaiting_folder_changes"):
        data.pop("awaiting_folder_changes")
        from adapters.windows.misc_tools import get_folder_changes_today
        await update.message.reply_text(await asyncio.to_thread(get_folder_changes_today, text), parse_mode="Markdown")
        return True
    if data.get("awaiting_app_volume"):
        data.pop("awaiting_app_volume")
        parts = text.rsplit(" ", 1)
        if len(parts) != 2 or not parts[1].isdigit():
            await update.message.reply_text("⚠️ Формат: `имя_процесса процент`. Например: `chrome 30`", parse_mode="Markdown")
            return True
        from adapters.windows.misc_tools import set_process_volume
        await update.message.reply_text(
            await asyncio.to_thread(set_process_volume, parts[0], max(0, min(100, int(parts[1])))),
            parse_mode="Markdown")
        return True
    if data.get("awaiting_file_content_search"):
        data.pop("awaiting_file_content_search")
        from services.file_search import search_file_content
        await update.message.reply_text("🔎 Ищу в содержимом файлов, это может занять до ~25 секунд...")
        await update.message.reply_text(await asyncio.to_thread(search_file_content, text), parse_mode="Markdown")
        return True
    if data.get("awaiting_app_search"):
        data.pop("awaiting_app_search")
        from core.app_resolver import app_resolver
        candidates = app_resolver.find_candidates(text, top_k=3)
        if candidates:
            app, _ = candidates[0]
            if app_resolver.launch_app(app):
                await update.message.reply_text(f"🚀 Запущено: *{app['display_name']}* (найдено по «{text}»)", parse_mode="Markdown")
            else:
                await update.message.reply_text(f"❌ Ошибка запуска {app['display_name']}")
        else:
            await update.message.reply_text(f"⚠️ Программа по запросу «{text}» не найдена.")
        return True
    if data.get("awaiting_qr"):
        data.pop("awaiting_qr", None)
        if not looks_like_keyboard_button(text):
            from services.extra_functions import generate_qr_png
            extra = generate_qr_png(text)
            if extra.photo_bytes:
                await update.message.reply_photo(
                    photo=InputFile(io.BytesIO(extra.photo_bytes), extra.photo_name or "qr.png"),
                    caption=extra.text[:900])
            else:
                await update.message.reply_text(extra.text)
            return True
    if data.get("ai_mode") and not looks_like_keyboard_button(text):
        from handlers.ai_chat import handle_ai_message
        await handle_ai_message(update, context)
        return True
    return False
