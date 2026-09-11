import logging
from telegram import Update
from telegram.ext import ContextTypes
from handlers.auth import restricted
from services.ai_client import ask_gemini

logger = logging.getLogger("jarvis")
MAX_HISTORY = 10

@restricted
async def handle_ai_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает свободный текстовый запрос пользователя с помощью Gemini.
    Хранит последние 10 сообщений контекста в памяти процесса (context.user_data).
    """
    user_text = update.message.text
    if not user_text:
        return

    # Отправляем действие "печатает..."
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    history = context.user_data.setdefault("gemini_history", [])

    try:
        reply = ask_gemini(user_text, history)
        
        # Сохраняем в историю
        history.append({"role": "user", "parts": [{"text": user_text}]})
        history.append({"role": "model", "parts": [{"text": reply}]})
        
        # Ограничиваем историю 10 парами сообщений
        context.user_data["gemini_history"] = history[-(MAX_HISTORY * 2):]

        await update.message.reply_text(reply)
    except Exception as e:
        logger.error(f"Ошибка в handle_ai_message: {e}", exc_info=True)
        await update.message.reply_text(f"⚠️ Ошибка обработки запроса: {e}")

@restricted
async def cmd_clear_ai_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Очищает историю диалога с ИИ."""
    context.user_data["gemini_history"] = []
    await update.message.reply_text("🧹 История диалога с Gemini очищена.")
