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

        recognized_text = transcribe_audio_bytes(bytes(audio_bytes), mime_type="audio/ogg")
        if not recognized_text:
            await status_msg.edit_text("🤷‍♂️ Не удалось распознать речь. Попробуйте сказать четче.")
            return

        await status_msg.edit_text(f"🎤 *Распознал:* «_{recognized_text}_»\n⏳ Анализирую задачи...", parse_mode="Markdown")

        # Передаем в единый планировщик задач
        session = task_queue_manager.get_session(chat_id)
        recent_actions = [h["intent"] for h in session.history[-5:]]
        plan_steps = parse_user_instruction_to_plan(recognized_text, recent_actions)

        session.add_steps(plan_steps)
        await task_executor.process_user_queue(session, context.bot)

    except Exception as e:
        logger.error(f"Ошибка при обработке голоса: {e}", exc_info=True)
        await status_msg.edit_text(f"⚠️ Ошибка обработки голосового сообщения: {e}")
