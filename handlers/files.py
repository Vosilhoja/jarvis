import os
import re
import logging
from pathlib import Path
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from telegram.ext import ContextTypes
from handlers.auth import restricted

logger = logging.getLogger("jarvis")

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB лимит Telegram для ботов
PAGE_SIZE = 8


def get_user_home() -> Path:
    """Возвращает домашнюю директорию текущего пользователя независимо от ОС."""
    return Path(os.environ.get("USERPROFILE") or os.environ.get("HOME") or Path.home())


def safe_user_path(path: str | os.PathLike[str] | None) -> Path:
    """Нормализует путь и ограничивает доступ только пользовательскими папками."""
    if path is None:
        return get_desktop_path()

    resolved = Path(path).expanduser()
    if not resolved.is_absolute():
        resolved = get_user_home() / resolved

    root = get_user_home().resolve()
    try:
        if resolved.resolve().is_relative_to(root):
            return resolved.resolve()
    except (RuntimeError, ValueError):
        pass

    # Если путь не находится в домашней папке, но он существует как диск/корень,
    # разрешаем только стандартные системные каталоги рабочего стола и загрузок.
    for allowed_root in get_system_roots():
        try:
            if resolved.resolve().is_relative_to(allowed_root.resolve()):
                return resolved.resolve()
        except (RuntimeError, ValueError):
            pass

    return get_desktop_path().resolve()


def get_desktop_path() -> Path:
    """Возвращает путь к рабочему столу текущего пользователя."""
    return get_user_home() / "Desktop"


def get_system_roots() -> list[Path]:
    """Возвращает список доступных корней/дисков системы."""
    roots = []
    user_home = get_user_home()
    for candidate in ["Desktop", "Downloads", "Documents", "Pictures"]:
        path = user_home / candidate
        if path.exists():
            roots.append(path)

    # Диски / корни файловой системы
    if os.name == "nt":
        for drive_letter in "CDEFGHIJK":
            p = Path(f"{drive_letter}:\\")
            if p.exists():
                roots.append(p)
    else:
        roots.append(Path("/"))
    return roots

@restricted
async def show_files_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, current_path: Path | None = None, page: int = 0):
    """Полнофункциональный быстрый файловый менеджер с пагинацией и выбором дисков."""
    if current_path is None:
        current_path = get_desktop_path()
    current_path = safe_user_path(current_path)
    if not current_path.exists():
        current_path = get_desktop_path()

    context.user_data["current_files_dir"] = str(current_path)
    context.user_data["current_files_page"] = page

    items = []
    try:
        # Быстрый список элементов
        all_entries = list(current_path.iterdir())
        # Сортируем: сначала папки, затем файлы
        all_entries.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
        items = all_entries
    except Exception as e:
        logger.error(f"Не удалось прочитать директорию {current_path}: {e}")
        items = []

    total_items = len(items)
    max_pages = max(1, (total_items + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, max_pages - 1))
    context.user_data["current_files_page"] = page

    start_idx = page * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    page_items = items[start_idx:end_idx]

    # Кэшируем текущую страницу в context
    context.user_data["listed_files"] = [str(x) for x in page_items]

    buttons = []

    # 1. Быстрые переходы на уровень выше и корень
    nav_row = []
    if current_path.parent and current_path != current_path.parent:
        nav_row.append(InlineKeyboardButton("📁 .. (Вверх)", callback_data="file_up"))
    nav_row.append(InlineKeyboardButton("💻 Диски / Корни", callback_data="file_roots"))
    buttons.append(nav_row)

    # 2. Список файлов и папок текущей страницы
    for idx, item in enumerate(page_items):
        try:
            if item.is_dir():
                icon = "📁"
                callback = f"file_open_{idx}"
                suffix = ""
            else:
                icon = "📄"
                callback = f"file_dl_{idx}"
                size_kb = item.stat().st_size // 1024
                if size_kb > 1024:
                    suffix = f" ({size_kb / 1024:.1f}M)"
                else:
                    suffix = f" ({size_kb}K)"
        except Exception:
            icon = "❓"
            callback = f"file_open_{idx}" if item.is_dir() else f"file_dl_{idx}"
            suffix = ""

        # Укорачиваем длинные имена
        name = item.name
        if len(name) > 22:
            name = name[:19] + "..."
        btn_text = f"{icon} {name}{suffix}"
        buttons.append([InlineKeyboardButton(btn_text, callback_data=callback)])

    # 3. Кнопки пагинации
    page_row = []
    if page > 0:
        page_row.append(InlineKeyboardButton("⬅ Назад", callback_data=f"file_page_{page - 1}"))
    page_row.append(InlineKeyboardButton(f"📄 {page + 1}/{max_pages}", callback_data="file_refresh"))
    if page < max_pages - 1:
        page_row.append(InlineKeyboardButton("Вперед ➡", callback_data=f"file_page_{page + 1}"))
    if page_row:
        buttons.append(page_row)

    # 4. Выход в главное меню
    buttons.append([InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")])

    display_path = str(current_path).replace("\\", "/")
    text = (
        f"📂 *Файловый менеджер*\n\n"
        f"📍 Путь: `{display_path}`\n"
        f"📊 Элементов: *{total_items}* (Стр. {page + 1} из {max_pages})"
    )
    kb = InlineKeyboardMarkup(buttons)

    query = update.callback_query
    if query:
        try:
            await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
        except Exception:
            try:
                await query.edit_message_text(text.replace("*", "").replace("`", ""), reply_markup=kb)
            except Exception:
                await query.answer()
    elif update.message:
        try:
            await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(text.replace("*", "").replace("`", ""), reply_markup=kb)

@restricted
async def show_system_roots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список доступных дисков и стандартных папок."""
    buttons = []
    roots = get_system_roots()
    context.user_data["root_paths"] = [str(r) for r in roots]

    for idx, r in enumerate(roots):
        label = f"💾 {r}" if len(str(r)) <= 3 else f"📁 {r.name}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"file_root_{idx}")])
    buttons.append([InlineKeyboardButton("⬅ Назад в папку", callback_data="file_refresh")])

    text = "💻 *Выберите диск или системную папку:*"
    kb = InlineKeyboardMarkup(buttons)
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
        except Exception:
            await update.callback_query.answer()

@restricted
async def handle_file_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатия в файловом менеджере (навигация/скачивание/пагинация)."""
    query = update.callback_query
    data = query.data
    current_dir_str = context.user_data.get("current_files_dir", str(get_desktop_path()))
    current_path = safe_user_path(current_dir_str)
    listed_files = context.user_data.get("listed_files", [])
    current_page = context.user_data.get("current_files_page", 0)

    if data == "file_refresh":
        await show_files_menu(update, context, current_path, page=current_page)
        return

    if data == "file_roots":
        await show_system_roots(update, context)
        return

    if data.startswith("file_root_"):
        idx = int(data.replace("file_root_", ""))
        roots = context.user_data.get("root_paths", [])
        if 0 <= idx < len(roots):
            await show_files_menu(update, context, safe_user_path(roots[idx]), page=0)
            return

    if data.startswith("file_page_"):
        new_page = int(data.replace("file_page_", ""))
        await show_files_menu(update, context, current_path, page=new_page)
        return

    if data == "file_up":
        parent = current_path.parent
        await show_files_menu(update, context, parent, page=0)
        return

    if data.startswith("file_open_"):
        idx = int(data.replace("file_open_", ""))
        if 0 <= idx < len(listed_files):
            target_dir = safe_user_path(listed_files[idx])
            if target_dir.is_dir():
                await show_files_menu(update, context, target_dir, page=0)
                return

    if data.startswith("file_dl_"):
        idx = int(data.replace("file_dl_", ""))
        if 0 <= idx < len(listed_files):
            target_file = safe_user_path(listed_files[idx])
            if target_file.is_file():
                try:
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
                except Exception as e:
                    await query.answer(f"Ошибка отправки: {e}", show_alert=True)
                return

    await query.answer()
