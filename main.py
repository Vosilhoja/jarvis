import sys
import asyncio
import logging
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN, validate_config
from logger_setup import setup_logging
from handlers.menu import cmd_start, menu_callback_router
from handlers.remote_control import handle_text_command
from handlers.process_commands import cmd_kill_text
from handlers.ai_chat import cmd_clear_ai_history
from handlers.voice import handle_voice_message
from services.notifier import notifier
from scheduler import background_monitoring_loop

logger = setup_logging()

async def post_init(application: Application):
    """Инициализация фоновых служб после запуска бота."""
    notifier.set_bot(application.bot)
    # Запускаем фоновый цикл мониторинга и напоминаний
    asyncio.create_task(background_monitoring_loop())
    logger.info("Фоновые службы и нотификатор успешно зарегистрированы.")

def main():
    try:
        validate_config()
    except RuntimeError as e:
        logger.error(f"Ошибка конфигурации: {e}")
        print(f"\n[ОШИБКА] {e}\n", file=sys.stderr)
        sys.exit(1)

    logger.info("Инициализация резидента Jarvis AI Agent...")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # Команды
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_start))
    app.add_handler(CommandHandler("kill", cmd_kill_text))
    app.add_handler(CommandHandler("clear", cmd_clear_ai_history))

    # Кнопки меню и подтверждений
    app.add_handler(CallbackQueryHandler(menu_callback_router))

    # Голосовые сообщения (Telegram Voice / Audio)
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice_message))

    # Текстовые команды и естественный язык
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_command))

    logger.info("Jarvis успешно запущен и слушает Telegram (long polling)...")
    try:
        app.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.critical(f"Критическая ошибка в работе бота: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
