import logging
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from config import ALLOWED_USER_IDS

logger = logging.getLogger("jarvis")

def is_user_allowed(user_id: int | None) -> bool:
    """Проверяет, входит ли пользователь в белый список разрешённых ID."""
    if user_id is None:
        return False
    return user_id in ALLOWED_USER_IDS

def restricted(func):
    """
    Декоратор для строгой проверки подлинности пользователя Telegram.
    Разрешает доступ только пользователям из ALLOWED_USER_IDS.
    Все остальные попытки блокируются и логируются с уровнем WARNING.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if user is None or not is_user_allowed(user.id):
            user_info = f"id={user.id}, username=@{user.username}, full_name='{user.full_name}'" if user else "Unknown User"
            logger.warning(f"⛔ Несанкционированная попытка доступа от {user_info}")
            
            if update.callback_query:
                await update.callback_query.answer("⛔ Доступ запрещён. Вы не являетесь владельцем этого ПК.", show_alert=True)
            elif update.message:
                await update.message.reply_text("⛔ Доступ запрещён. Этот бот настроен на работу только с владельцем.")
            return

        return await func(update, context, *args, **kwargs)
    return wrapper
