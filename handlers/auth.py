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
    # Если список пуст, разрешаем первому обратившемуся привязать свой ID
    if not ALLOWED_USER_IDS:
        return True
    return user_id in ALLOWED_USER_IDS

def restricted(func):
    """
    Декоратор для строгой проверки подлинности пользователя Telegram.
    Разрешает доступ только пользователям из ALLOWED_USER_IDS.
    Если список пуст, автоматически запоминает первого написавшего пользователя как владельца.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if user is None:
            return

        # Авто-привязка первого пользователя, если список пуст
        if not ALLOWED_USER_IDS:
            ALLOWED_USER_IDS.append(user.id)
            logger.info(f"🔑 Первый запуск: пользователь id={user.id} (@{user.username}) автоматически назначен владельцем Jarvis!")
            # Сохраняем в .env для постоянства
            try:
                from config import BASE_DIR
                env_path = BASE_DIR / ".env"
                if env_path.exists():
                    content = env_path.read_text(encoding="utf-8")
                    if "ALLOWED_TELEGRAM_USER_IDS=" in content:
                        content = content.replace("ALLOWED_TELEGRAM_USER_IDS=", f"ALLOWED_TELEGRAM_USER_IDS={user.id}")
                    else:
                        content += f"\nALLOWED_TELEGRAM_USER_IDS={user.id}\n"
                    env_path.write_text(content, encoding="utf-8")
            except Exception as e:
                logger.warning(f"Не удалось записать user_id в .env: {e}")

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
