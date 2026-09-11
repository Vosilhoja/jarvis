import re
import logging
import pyautogui
import pyperclip
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from handlers.auth import restricted
from core.task_queue import task_queue_manager
from core.executor import task_executor
from services.ai_client import parse_user_instruction_to_plan

logger = logging.getLogger("jarvis")

# Включаем Failsafe (перемещение мыши в левый верхний угол мгновенно прерывает операцию)
pyautogui.FAILSAFE = True

@restricted
async def handle_text_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Разбирает низкоуровневые точечные команды или передает сложные естественные фразы
    в ИИ планировщик и многошаговую очередь задач.
    """
    raw_text = update.message.text
    if not raw_text:
        return

    text = raw_text.strip()
    lower = text.lower()
    chat_id = update.effective_chat.id

    # 1. Быстрые директивные команды мыши/клавиатуры
    if lower.startswith("mouse:") or lower.startswith("мышь:"):
        coords = re.sub(r"^(mouse:|мышь:)", "", text, flags=re.IGNORECASE).strip()
        try:
            x, y = map(int, coords.split(","))
            pyautogui.moveTo(x, y, duration=0.25)
            await update.message.reply_text(f"🖱 Курсор перемещён в {x}, {y}")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Пример: `mouse: 800,600` ({e})", parse_mode="Markdown")
        return

    if lower in ("click", "клик", "лкм"):
        pyautogui.click()
        await update.message.reply_text("🖱 ЛКМ клик выполнен.")
        return
    elif lower in ("rclick", "пкм"):
        pyautogui.click(button="right")
        await update.message.reply_text("🖱 ПКМ клик выполнен.")
        return
    elif lower in ("dclick", "двойной клик"):
        pyautogui.doubleClick()
        await update.message.reply_text("🖱 Двойной клик выполнен.")
        return

    if lower.startswith("key:") or lower.startswith("клавиша:"):
        payload = re.sub(r"^(key:|клавиша:)", "", text, flags=re.IGNORECASE).strip()
        keys = [k.strip().lower() for k in payload.split("+")]
        try:
            pyautogui.hotkey(*keys)
            await update.message.reply_text(f"⌨ Нажато: `{' + '.join(keys)}`", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Ошибка: {e}")
        return

    if lower.startswith("type:") or lower.startswith("напечатай:"):
        payload = re.sub(r"^(type:|напечатай:)", "", text, flags=re.IGNORECASE).strip()
        try:
            pyperclip.copy(payload)
            pyautogui.hotkey("ctrl", "v")
            await update.message.reply_text("⌨ Текст успешно напечатан.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Ошибка ввода текста: {e}")
        return

    if lower.startswith("scroll:") or lower.startswith("скролл:"):
        amount_str = re.sub(r"^(scroll:|скролл:)", "", text, flags=re.IGNORECASE).strip()
        try:
            amount = int(amount_str)
            pyautogui.scroll(amount)
            await update.message.reply_text(f"📜 Скролл на {amount} выполнен.")
        except Exception as e:
            await update.message.reply_text("⚠️ Ошибка. Пример: `scroll: -300`", parse_mode="Markdown")
        return

    # 2. Все остальные естественные фразы (многозадачные запросы, вопросы к ИИ, поиск программ)
    session = task_queue_manager.get_session(chat_id)
    recent_actions = [h["intent"] for h in session.history[-5:]]

    # Индикатор набора текста
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    plan_steps = parse_user_instruction_to_plan(text, recent_actions)
    session.add_steps(plan_steps)

    # Запуск последовательного исполнения задач
    await task_executor.process_user_queue(session, context.bot)
