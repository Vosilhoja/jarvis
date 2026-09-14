"""Facade for reply-keyboard routing.

The individual domains live in small routers.  This module intentionally keeps
only ordering, shared input state, and the public compatibility entry point.
"""

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes

from handlers.menu.input_flows import (
    clear_awaiting,
    looks_like_keyboard_button,
    parse_desktop_selection,
)
from handlers.menu.keyboards import (
    get_main_reply_keyboard,
    get_system_reply_keyboard,
    get_media_reply_keyboard,
    get_files_reply_keyboard,
    get_network_reply_keyboard,
    get_apps_reply_keyboard,
    get_control_reply_keyboard,
    get_screenshot_reply_keyboard,
    get_tools_reply_keyboard,
)
from handlers.menu.input_router import handle_pending_input
from handlers.menu.system_router import handle_system
from handlers.menu.media_router import handle_media
from handlers.menu.files_router import handle_files
from handlers.menu.network_router import handle_network
from handlers.menu.apps_router import handle_apps
from handlers.menu.control_router import handle_control
from handlers.menu.tools_router import handle_tools


CATEGORY_MAP = {
    "🖥 Система": (get_system_reply_keyboard, "🖥 *Меню системы:*"),
    "🎵 Медиа / Звук": (get_media_reply_keyboard, "🎵 *Меню звука и медиа:*"),
    "📁 Файлы": (get_files_reply_keyboard, "📁 *Меню файлов и папок:*"),
    "🌐 Сеть": (get_network_reply_keyboard, "🌐 *Меню сети и интернета:*"),
    "🚀 Приложения": (get_apps_reply_keyboard, "🚀 *Быстрый запуск приложений:*"),
    "🖱 Управление ПК": (
        get_control_reply_keyboard,
        "🖱 *Управление окнами, клавишами и ПК:*",
    ),
    "📸 Скриншот": (
        get_screenshot_reply_keyboard,
        "📸 *Выберите рабочий стол для скриншота:*",
    ),
    "🧰 Инструменты": (get_tools_reply_keyboard, "🧰 *Инструменты:*"),
}


async def handle_reply_keyboard(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """Обрабатывает нажатия всех кнопок клавиатуры."""
    text = (update.message.text or "").strip()

    if text in ("⬅️ Назад в меню", "назад в меню", "главное меню", "/menu"):
        context.user_data.pop("ai_mode", None)
        context.user_data.pop("menu_section", None)
        clear_awaiting(context)
        await update.message.reply_text(
            "🏠 *Главное меню:* выберите категорию",
            reply_markup=get_main_reply_keyboard(),
            parse_mode="Markdown",
        )
        return True

    if await handle_pending_input(update, context, text):
        return True

    if text in CATEGORY_MAP:
        context.user_data.pop("ai_mode", None)
        keyboard_fn, title = CATEGORY_MAP[text]
        await update.message.reply_text(
            title, reply_markup=keyboard_fn(), parse_mode="Markdown"
        )
        return True

    # Keep the historical precedence: screenshot/system, media, files, network,
    # apps, controls, and tools are checked in that order.
    for router in (
        handle_system,
        handle_media,
        handle_files,
        handle_network,
        handle_apps,
        handle_control,
        handle_tools,
    ):
        if await router(update, context, text):
            return True
    return False


__all__ = ["handle_reply_keyboard"]
