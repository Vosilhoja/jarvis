"""File and folder keyboard actions."""
import os
import re
import asyncio
from pathlib import Path
from handlers.menu.common import safe_reply

async def handle_files(update, context, text: str) -> bool:
    if text == "🗂 Рабочий стол":
        from handlers.files import show_files_menu
        await show_files_menu(update, context); return True
    if text == "⬇️ Загрузки":
        from services.extra_functions import get_downloads_list
        raw = re.sub(r'([_\*\[\]])', r'\\\1', get_downloads_list())
        await safe_reply(update, f"⬇️ *Последние загрузки:*\n\n{raw}"); return True
    if text == "📂 Документы":
        docs = Path.home() / "Documents"; lines = []
        try:
            for item in sorted(docs.iterdir())[:12]:
                lines.append(("📁" if item.is_dir() else "📄") + " " + re.sub(r'([_\*\[\]])', r'\\\1', item.name))
        except Exception as exc: lines = [f"Ошибка: {exc}"]
        await safe_reply(update, "📂 *Документы:*\n\n" + "\n".join(lines)); return True
    if text == "📦 Размер папок":
        from services.extra_functions import get_desktop_folder_sizes
        await safe_reply(update, "📦 *Размеры папок на рабочем столе:*\n\n" + re.sub(r'([_\*\[\]])', r'\\\1', get_desktop_folder_sizes())); return True
    if text == "🔍 Найти файл":
        context.user_data["awaiting_file_search"] = True
        await update.message.reply_text("🔍 *Напишите имя или часть названия файла для поиска:*", parse_mode="Markdown"); return True
    if text == "📝 Поиск в файлах":
        context.user_data["awaiting_file_content_search"] = True
        await update.message.reply_text(
            "📝 *Введите текст для поиска внутри файлов:*\n\n"
            "Поддерживаются TXT, MD, CSV, LOG, DOCX и PDF.",
            parse_mode="Markdown",
        ); return True
    if text == "📂 Что изменилось сегодня":
        context.user_data["awaiting_folder_changes"] = True
        await update.message.reply_text("📂 *Какую папку проверить?*\n\nМожно алиасом: `рабочий стол`, `загрузки`, `документы` — или полным путём.", parse_mode="Markdown"); return True
    if text == "📁 Открыть Проводник":
        await asyncio.to_thread(os.system, "explorer.exe")
        await update.message.reply_text("📁 Проводник запущен"); return True
    return False
