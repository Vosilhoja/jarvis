import logging
from telegram import Update
from telegram.ext import ContextTypes
from handlers.auth import restricted
from services.ai_client import ask_gemini
from core.task_queue import task_queue_manager
from core.executor import task_executor


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
        # Если сообщение похоже на команду управления — сначала попробовать локальный планировщик
        import asyncio
        loop = asyncio.get_running_loop()
        try:
            from services.local_ai import is_control_query, parse_user_instruction_to_plan_local
            if is_control_query(user_text):
                logger.info("ai_chat: detected control query, routing to local parser")
                plan_steps = await loop.run_in_executor(None, parse_user_instruction_to_plan_local, user_text, [])
                if plan_steps:
                    logger.info("ai_chat: local parser returned %d steps", len(plan_steps))
                    session = task_queue_manager.get_session(update.effective_chat.id)
                    session.add_steps(plan_steps)
                    await task_executor.process_user_queue(session, context.bot)
                    return
                else:
                    logger.info("ai_chat: local parser returned no actionable steps; falling back to cloud")
        except Exception as ex:
            # Если локальный парсер недоступен или упал — fallback на облако
            logger.warning("ai_chat: local parser raised exception, falling back to cloud: %s", ex)

        # ask_gemini может быть блокирующим (сетевая операция) — выполняем в пуле потоков
        logger.info("ai_chat: invoking cloud Gemini for general query")
        reply = await loop.run_in_executor(None, ask_gemini, user_text, history)

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
