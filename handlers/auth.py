import logging
from functools import wraps
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from config import ALLOWED_USER_IDS, BASE_DIR
from security.authentication import register_allowed_user as secure_register_allowed_user
from security.authentication import is_user_allowed as secure_is_user_allowed

logger = logging.getLogger("jarvis")


def register_allowed_user(user_id: int) -> None:
    """Добавляет пользователя в список владельцев и сохраняет его в .env."""
    normalized = secure_register_allowed_user(user_id, env_path=BASE_DIR / ".env", allowlist=list(ALLOWED_USER_IDS))
    ALLOWED_USER_IDS[:] = normalized


def is_user_allowed(user_id: int | None) -> bool:
    """Проверяет, входит ли пользователь в белый список разрешённых ID."""
    return secure_is_user_allowed(user_id, ALLOWED_USER_IDS)


def restricted(func):
    """Защищает команды от неавторизованных Telegram-пользователей."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if user is None:
            return

        if not is_user_allowed(user.id):
            user_info = f"id={user.id}, username=@{user.username}, full_name='{user.full_name}'"
            logger.warning(f"⛔ Несанкционированная попытка доступа от {user_info}")

            if update.callback_query:
                await update.callback_query.answer("⛔ Доступ запрещён. Вы не являетесь владельцем этого ПК.", show_alert=True)
            elif update.message:
                await update.message.reply_text("⛔ Доступ запрещён. Этот бот настроен на работу только с владельцем.")
            return

        return await func(update, context, *args, **kwargs)
    return wrapper