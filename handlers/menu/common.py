import re
import logging
from telegram import Update

logger = logging.getLogger("jarvis")

def escape_md(text: str) -> str:
    """Экранирует спецсимволы Markdown v1 в пользовательских данных."""
    return re.sub(r'([_\*\[\]\(\)~`>#+\-=|{}.!])', r'\\\1', str(text))

async def safe_reply(update: Update, text: str, reply_markup=None, parse_mode: str = "Markdown") -> None:
    """Отправляет сообщение с Markdown. При ошибке парсинга — повторяет без форматирования."""
    msg = update.message or (update.callback_query and update.callback_query.message if update.callback_query else None)
    if not msg:
        return
    try:
        await msg.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except Exception as e:
        if "parse" in str(e).lower() or "entity" in str(e).lower():
            plain = re.sub(r'[*_`]', '', text)
            try:
                await msg.reply_text(plain, reply_markup=reply_markup)
            except Exception as e2:
                logger.error(f"safe_reply: не смогли отправить сообщение: {e2}")
        else:
            raise

async def safe_edit(update: Update, text: str, reply_markup=None, parse_mode: str = "Markdown") -> None:
    """Редактирует сообщение с Markdown. При ошибке — без форматирования."""
    cq = update.callback_query
    if not cq:
        return
    try:
        await cq.edit_message_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except Exception as e:
        if "parse" in str(e).lower() or "entity" in str(e).lower():
            plain = re.sub(r'[*_`]', '', text)
            try:
                await cq.edit_message_text(plain, reply_markup=reply_markup)
            except Exception as e2:
                logger.error(f"safe_edit: не смогли отредактировать: {e2}")
        else:
            raise
