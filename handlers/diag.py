import sys
import os
import platform
import logging
from telegram import Update
from telegram.ext import ContextTypes
from handlers.auth import restricted
import config
from services.ai_client import ask_gemini

logger = logging.getLogger("jarvis")

@restricted
async def cmd_diag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда диагностики системы Jarvis:
    - Версия Python и ОС
    - Проверка pywin32 / win32com
    - Тестовый вызов Gemini API
    - Статус и путь файла .env
    - Текущие ID владельцев
    """
    lines = ["🛠 *Диагностика Jarvis AI Agent*\n"]

    # 1. Python и ОС
    lines.append(f"🐍 *Python:* `{sys.version.split()[0]}` ({platform.architecture()[0]})")
    lines.append(f"💻 *ОС:* `{platform.system()} {platform.release()} (Build {platform.version()})`")
    lines.append(f"📍 *Интерпретатор:* `{sys.executable}`")

    # 2. win32com / pywin32
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        lines.append("🪟 *pywin32 / win32com:* ✅ Установлен и работает корректно")
    except Exception as e:
        lines.append(f"🪟 *pywin32 / win32com:* ❌ Ошибка: `{e}`")

    # 3. .env статус
    env_path = config.BASE_DIR / ".env"
    if env_path.exists():
        lines.append(f"📄 *.env:* ✅ Найден (`{env_path}`)")
    else:
        lines.append(f"📄 *.env:* ❌ Файл не найден по пути `{env_path}`")

    # 4. Владелец
    lines.append(f"👤 *Разрешенные User ID:* `{config.ALLOWED_USER_IDS or 'Не заданы (автопривязка)'}`")
    lines.append(f"🤖 *Модель ИИ:* `{config.AI_MODEL_NAME}` (Fallback: `{config.AI_FALLBACK_MODEL_NAME}`)")

    # 5. Тестовый запрос к Gemini
    try:
        test_gemini = ask_gemini("Ответь одним словом: 'Работает'")
        lines.append(f"🧠 *Тест Gemini API:* ✅ {test_gemini.strip()[:100]}")
    except Exception as e:
        lines.append(f"🧠 *Тест Gemini API:* ❌ Ошибка: `{e}`")

    report_text = "\n".join(lines)
    await update.message.reply_text(report_text, parse_mode="Markdown")
