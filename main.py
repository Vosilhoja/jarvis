import sys
import os

# winloop — быстрый event loop для asyncio на Windows (аналог uvloop).
# Обязательно ДО любого создания/получения event loop (в т.ч. до импорта
# telegram.ext, который его создаёт внутри run_polling()).
try:
    import winloop
    winloop.install()
except Exception as _e:
    print(f"[JARVIS] winloop недоступен, использую стандартный event loop asyncio: {_e}", file=sys.stderr)

import asyncio
import logging
import traceback
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from telegram import Update
from telegram.request import HTTPXRequest

import pyautogui
pyautogui.FAILSAFE = False

from config import TELEGRAM_BOT_TOKEN, ONLINE_GREETING_ENABLED, validate_config
from logger_setup import setup_logging
from handlers.menu import cmd_start, menu_callback_router
from handlers.remote_control import handle_text_command
from handlers.process_commands import cmd_kill_text
from handlers.ai_chat import cmd_clear_ai_history
from handlers.voice import handle_voice_message
from handlers.diag import cmd_diag
from handlers.auth import restricted
from services.notifier import notifier
from scheduler import background_monitoring_loop

logger = setup_logging()


@restricted
async def cmd_autostart(update: Update, context):
    from services.autostart import ensure_autostart, autostart_status
    msg = ensure_autostart() + "\n\n" + autostart_status()
    await update.message.reply_text(msg)


async def post_init(application: Application):
    """Инициализация фоновых служб после запуска бота."""
    notifier.set_bot(application.bot)
    if ONLINE_GREETING_ENABLED:
        await notifier.send_notification(
            "🟢 Я снова на связи. Локальное управление ПК готово, напоминания и мониторинг запущены.",
            topic_key="jarvis_online",
            min_interval_sec=30,
        )
    asyncio.create_task(background_monitoring_loop())
    try:
        from services.apscheduler_jobs import start_apscheduler_jobs
        start_apscheduler_jobs()
    except Exception as e:
        logger.warning("Не удалось запустить APScheduler (утренний брифинг): %s", e)
    try:
        from services.autostart import ensure_autostart
        logger.info(ensure_autostart())
    except Exception as e:
        logger.warning("Не удалось зарегистрировать автозапуск: %s", e)
    logger.info("Фоновые службы и нотификатор успешно зарегистрированы.")

def acquire_single_instance_lock():
    """Гарантирует, что запущен строго один процесс бота на ПК."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Привязываемся к локальному порту 49876
        s.bind(("127.0.0.1", 49876))
        s.listen(1)
        return s
    except Exception:
        logger.warning("Обнаружен другой работающий экземпляр Jarvis. Завершаем дублирующий процесс.")
        print("[JARVIS] Экземпляр бота уже запущен. Завершение работы дубликата.", file=sys.stderr)
        sys.exit(0)

def main():
    try:
        validate_config()
    except Exception as e:
        tb = traceback.format_exc()
        logger.critical(f"Ошибка конфигурации при старте:\n{tb}")
        print(f"\n[ОШИБКА КОНФИГУРАЦИИ]\n{tb}", file=sys.stderr)
        sys.exit(1)

    _instance_lock = acquire_single_instance_lock()

    logger.info("Инициализация резидента Jarvis AI Agent...")

    try:
        request = HTTPXRequest(
            connect_timeout=20.0,
            read_timeout=30.0,
            write_timeout=20.0,
            pool_timeout=20.0,
        )
        app = (
            Application.builder()
            .token(TELEGRAM_BOT_TOKEN)
            .request(request)
            .post_init(post_init)
            # Обработка разных чатов не должна блокировать друг друга.
            # Очередь конкретного пользователя всё равно сериализует его шаги.
            .concurrent_updates(4)
            .build()
        )

        # Команды
        app.add_handler(CommandHandler("start", cmd_start))
        app.add_handler(CommandHandler("menu", cmd_start))
        app.add_handler(CommandHandler("kill", cmd_kill_text))
        app.add_handler(CommandHandler("clear", cmd_clear_ai_history))
        app.add_handler(CommandHandler("diag", cmd_diag))
        app.add_handler(CommandHandler("autostart", cmd_autostart))

        # Кнопки меню и подтверждений
        app.add_handler(CallbackQueryHandler(menu_callback_router))

        # Голосовые сообщения (Telegram Voice / Audio)
        app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice_message))

        # Текстовые команды и естественный язык
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_command))

        async def error_handler(update, context):
            from telegram.error import TimedOut, NetworkError
            if isinstance(context.error, (TimedOut, NetworkError)):
                logger.warning(f"Telegram network error (non-fatal): {context.error}")
                return
            logger.error(f"Исключение при обработке обновления {update}: {context.error}", exc_info=context.error)

        app.add_error_handler(error_handler)

        logger.info("Jarvis успешно запущен и слушает Telegram (long polling)...")
        app.run_polling(drop_pending_updates=False)

    except Exception as e:
        tb = traceback.format_exc()
        logger.critical(f"Критическая ошибка работы/запуска main():\n{tb}")
        print(f"\n[КРИТИЧЕСКАЯ ОШИБКА MAIN]\n{tb}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
