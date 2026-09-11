import os
import logging
from pathlib import Path
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from telegram.ext import ContextTypes
from handlers.auth import restricted

logger = logging.getLogger("jarvis")

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB лимит Telegram для ботов

def get_desktop_path() -> Path:
    """Возвращает путь к рабочему столу текущего пользователя Windows."""
    return Path(os.environ.get("USERPROFILE", "C:\\Users\\Default")) / "Desktop"

@restricted
async def show_files_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, current_path: Path | None = None):
    """Показывает файлы и папки рабочего стола/выбранной директории."""
    if current_path is None or not current_path.exists():
        current_path = get_desktop_path()

    # Сохраняем текущий путь в контекст
    context.user_data["current_files_dir"] = str(current_path)

    buttons = []
    try:
        items = list(current_path.iterdir())
        # Сортируем: сначала папки, затем файлы
        items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
    except Exception as e:
        items = []
        logger.error(f"Не удалось прочитать директорию {current_path}: {e}")

    # Кнопка перехода на уровень выше
    if current_path.parent and current_path != current_path.parent:
        buttons.append([InlineKeyboardButton("📁 .. (На уровень выше)", callback_data="file_up")])

    # Выводим до 10 элементов для компактности клавиатуры
    for idx, item in enumerate(items[:10]):
        if item.is_dir():
            icon = "📁"
            callback = f"file_open_{idx}"
        else:
            icon = "📄"
            callback = f"file_dl_{idx}"
        btn_name = f"{icon} {item.name[:25]}"
        buttons.append([InlineKeyboardButton(btn_name, callback_data=callback)])

    # Кнопка возврата в главное меню
    buttons.append([InlineKeyboardButton("⬅ Главное меню", callback_data="main_menu")])

    # Кэшируем список элементов в user_data для callback
    context.user_data["listed_files"] = [str(x) for x in items[:10]]

    text = f"📂 *Файловый менеджер*\n\nТекущий путь:\n`{current_path}`"
    kb = InlineKeyboardMarkup(buttons)

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
        except Exception:
            await update.callback_query.answer()
    elif update.message:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")

@restricted
async def handle_file_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатия в файловом менеджере (переход/скачивание)."""
    query = update.callback_query
    data = query.data
    current_dir_str = context.user_data.get("current_files_dir", str(get_desktop_path()))
    current_path = Path(current_dir_str)
    listed_files = context.user_data.get("listed_files", [])

    if data == "file_up":
        parent = current_path.parent
        await show_files_menu(update, context, parent)
        return

    if data.startswith("file_open_"):
        idx = int(data.replace("file_open_", ""))
        if 0 <= idx < len(listed_files):
            target_dir = Path(listed_files[idx])
            if target_dir.is_dir():
                await show_files_menu(update, context, target_dir)
                return

    if data.startswith("file_dl_"):
        idx = int(data.replace("file_dl_", ""))
        if 0 <= idx < len(listed_files):
            target_file = Path(listed_files[idx])
            if target_file.is_file():
                size = target_file.stat().st_size
                if size > MAX_FILE_SIZE_BYTES:
                    await query.answer("⚠️ Файл слишком большой (> 50 МБ) для отправки в Telegram.", show_alert=True)
                    return
                await query.answer(f"Отправляю {target_file.name}...")
                with open(target_file, "rb") as f:
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=InputFile(f, filename=target_file.name),
                        caption=f"📄 {target_file.name} ({round(size / (1024*1024), 2)} MB)"
                    )
                return

    await query.answer()
