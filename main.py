import sys
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

logger = setup_logging()

def main():
    try:
        validate_config()
    except RuntimeError as e:
        logger.error(f"Ошибка конфигурации: {e}")
        print(f"\n[ОШИБКА] {e}\n", file=sys.stderr)
        sys.exit(1)

    logger.info("Инициализация Jarvis Telegram Bot...")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Регистрация команд
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_start))
    app.add_handler(CommandHandler("kill", cmd_kill_text))
    app.add_handler(CommandHandler("clear", cmd_clear_ai_history))

    # Обработка нажатий на инлайн-кнопки
    app.add_handler(CallbackQueryHandler(menu_callback_router))

    # Текстовые сообщения (команды управления ПК и свободные вопросы к Gemini)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_command))

    logger.info("Jarvis успешно запущен и слушает Telegram (long polling)...")
    try:
        app.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.critical(f"Критическая ошибка в работе бота: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
