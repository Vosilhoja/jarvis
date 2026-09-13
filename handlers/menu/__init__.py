import logging
from telegram import Update
from telegram.ext import ContextTypes
from handlers.auth import restricted
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
    get_reply_keyboard,
    get_main_keyboard,
    kb_system,
    kb_media,
    kb_files,
    kb_network,
    kb_apps,
    kb_control,
    kb_back,
)
from handlers.menu.callback_router import menu_callback_router
from handlers.menu.reply_router import handle_reply_keyboard

logger = logging.getLogger("jarvis")

@restricted
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает приветствие и переключает клавиатуру на главную."""
    user = update.effective_user
    logger.info(f"Вызов /start от пользователя id={user.id}")
    welcome_text = (
        f"🤖 *Jarvis — Ваш персональный ИИ-ассистент*\n\n"
        f"Привет, {user.first_name or 'Шеф'}! Все функции в кнопках клавиатуры внизу.\n\n"
        "Нажмите любую категорию — клавиатура откроет соответствующие кнопки!"
    )
    msg = update.message or (update.callback_query and update.callback_query.message)
    if msg:
        await msg.reply_text(welcome_text, reply_markup=get_main_reply_keyboard(), parse_mode="Markdown")
    if update.callback_query:
        await update.callback_query.answer()

__all__ = [
    "cmd_start",
    "menu_callback_router",
    "handle_reply_keyboard",
    "get_main_reply_keyboard",
    "get_system_reply_keyboard",
    "get_media_reply_keyboard",
    "get_files_reply_keyboard",
    "get_network_reply_keyboard",
    "get_apps_reply_keyboard",
    "get_control_reply_keyboard",
    "get_screenshot_reply_keyboard",
    "get_tools_reply_keyboard",
    "get_reply_keyboard",
    "get_main_keyboard",
    "kb_system",
    "kb_media",
    "kb_files",
    "kb_network",
    "kb_apps",
    "kb_control",
    "kb_back",
]
