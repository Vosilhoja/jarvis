import logging
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from config import ALLOWED_USER_ID

logger = logging.getLogger("jarvis")

def restricted(func):
    """
    Декоратор для строгой проверки подлинности пользователя Telegram.
    Разрешает доступ только пользователю с ALLOWED_USER_ID.
    Все остальные попытки блокируются и логируются с уровнем WARNING.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if user is None or user.id != ALLOWED_USER_ID:
            user_info = f"id={user.id}, username=@{user.username}, full_name='{user.full_name}'" if user else "Unknown User"
            logger.warning(f"⛔ Несанкционированная попытка доступа от {user_info}")
            
            if update.callback_query:
                await update.callback_query.answer("⛔ Доступ запрещён. Вы не являетесь владельцем этого ПК.", show_alert=True)
            elif update.message:
                await update.message.reply_text("⛔ Доступ запрещён. Этот бот настроен на работу только с одним владельцем.")
            return

        return await func(update, context, *args, **kwargs)
    return wrapper
