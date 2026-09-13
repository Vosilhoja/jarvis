import logging
from telegram import Update
from telegram.ext import ContextTypes

from handlers.auth import restricted
from services.stt_client import transcribe_audio_bytes
from core.task_queue import task_queue_manager
from core.executor import task_executor
from services.ai_client import parse_user_instruction_to_plan

logger = logging.getLogger("jarvis")

@restricted
async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Принимает голосовое сообщение, транскрибирует через Gemini STT
    и отправляет распознанный текст в единый пайплайн исполнения задач.
    """
    voice = update.message.voice or update.message.audio
    if not voice:
        return

    chat_id = update.effective_chat.id
    status_msg = await update.message.reply_text("🎤 Распознаю голосовое сообщение...")

    try:
        # Скачиваем файл из Telegram в память
        file = await context.bot.get_file(voice.file_id)
        audio_bytes = await file.download_as_bytearray()

        # Выполняем транскрипцию в пуле потоков, т.к. это может блокировать
        import asyncio
        loop = asyncio.get_running_loop()
        recognized_text = await loop.run_in_executor(None, transcribe_audio_bytes, bytes(audio_bytes), "audio/ogg")
        if not recognized_text:
            await status_msg.edit_text("🤷‍♂️ Не удалось распознать речь. Попробуйте сказать четче.")
            return

        await status_msg.edit_text(f"🎤 *Распознал:* «_{recognized_text}_»", parse_mode="Markdown")

        # Если активен ИИ-режим — передаём в Gemini-диалог
        if context.user_data.get("ai_mode"):
            from handlers.ai_chat import handle_ai_message
            # Подменяем текст сообщения на распознанный и вызываем ИИ-обработчик
            update.message.text = recognized_text
            await handle_ai_message(update, context)
        else:
            # Передаем в единый планировщик задач
            session = task_queue_manager.get_session(chat_id)
            recent_actions = [h["intent"] for h in session.history[-5:]]

            # Попробуем локальный парсер для команд управления (низкая задержка, приватность)
            try:
                from services.local_ai import is_control_query, parse_user_instruction_to_plan_local
                if is_control_query(recognized_text):
                    logger.info("voice: detected control query in recognized speech; invoking local parser")
                    plan_steps = await loop.run_in_executor(None, parse_user_instruction_to_plan_local, recognized_text, recent_actions)
                    if plan_steps:
                        logger.info("voice: local parser returned %d steps", len(plan_steps))
                        session.add_steps(plan_steps)
                        await task_executor.process_user_queue(session, context.bot)
                        return
                    else:
                        logger.info("voice: local parser returned no actionable steps; falling back to cloud parser")
            except Exception as ex:
                logger.warning("voice: local parser exception, falling back to cloud: %s", ex)

            # fallback: облачный парсер
            logger.info("voice: invoking cloud parser for instruction")
            plan_steps = await loop.run_in_executor(None, parse_user_instruction_to_plan, recognized_text, recent_actions)
            session.add_steps(plan_steps)
            await task_executor.process_user_queue(session, context.bot)

    except Exception as e:
        logger.error(f"Ошибка при обработке голоса: {e}", exc_info=True)
        await status_msg.edit_text(f"⚠️ Ошибка обработки голосового сообщения: {e}")
