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

# Failsafe: движение мыши в левый верхний угол прерывает операцию
pyautogui.FAILSAFE = True

@restricted
async def handle_text_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает текстовые сообщения:
    1. Кнопки нижней клавиатуры (категории меню) → menu.handle_reply_keyboard
    2. Быстрые директивные команды (mouse:, key:, type:, scroll:)
    3. Всё остальное → ИИ планировщик Gemini
    """
    raw_text = update.message.text
    if not raw_text:
        return

    text = raw_text.strip()
    chat_id = update.effective_chat.id
    logger.info(f"Получено текстовое сообщение от {chat_id}: '{text}'")
    lower = text.lower()

    # 0. Нажатия кнопок нижней постоянной клавиатуры
    from handlers.menu import handle_reply_keyboard
    if await handle_reply_keyboard(update, context):
        return

    # 0.1. Ожидание ввода поиска файла
    if context.user_data.get("awaiting_file_search"):
        context.user_data.pop("awaiting_file_search")
        from services.extra_functions import search_files
        result = search_files(text)
        await update.message.reply_text(result, parse_mode="Markdown")
        return

    # 1. Быстрые директивные команды мыши
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

    # 2. Всё остальное → ИИ (Gemini)
    session = task_queue_manager.get_session(chat_id)
    recent_actions = [h["intent"] for h in session.history[-5:]]

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    plan_steps = parse_user_instruction_to_plan(text, recent_actions)
    session.add_steps(plan_steps)

    await task_executor.process_user_queue(session, context.bot)


@restricted
async def show_remote_control_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню управления мышью с InlineKeyboard."""
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("↖", callback_data="mouse_ul"), InlineKeyboardButton("⬆", callback_data="mouse_up"), InlineKeyboardButton("↗", callback_data="mouse_ur")],
        [InlineKeyboardButton("⬅", callback_data="mouse_left"), InlineKeyboardButton("🖱 Клик", callback_data="mouse_click"), InlineKeyboardButton("➡", callback_data="mouse_right")],
        [InlineKeyboardButton("↙", callback_data="mouse_dl"), InlineKeyboardButton("⬇", callback_data="mouse_down"), InlineKeyboardButton("↘", callback_data="mouse_dr")],
        [InlineKeyboardButton("🖱 ПКМ", callback_data="mouse_rclick"), InlineKeyboardButton("🖱 2x Клик", callback_data="mouse_dclick")],
        [InlineKeyboardButton("📜 Скролл ⬆", callback_data="mouse_scroll_up"), InlineKeyboardButton("📜 Скролл ⬇", callback_data="mouse_scroll_down")],
    ])
    msg = update.message or (update.callback_query and update.callback_query.message)
    if update.callback_query:
        await update.callback_query.edit_message_text("🖱 *Управление мышью:*", reply_markup=kb, parse_mode="Markdown")
    elif update.message:
        await update.message.reply_text("🖱 *Управление мышью:*", reply_markup=kb, parse_mode="Markdown")


@restricted
async def handle_remote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатия кнопок пульта мыши."""
    query = update.callback_query
    data = query.data
    step = 50

    MOUSE_ACTIONS = {
        "mouse_up":     lambda: pyautogui.move(0, -step),
        "mouse_down":   lambda: pyautogui.move(0, step),
        "mouse_left":   lambda: pyautogui.move(-step, 0),
        "mouse_right":  lambda: pyautogui.move(step, 0),
        "mouse_ul":     lambda: pyautogui.move(-step, -step),
        "mouse_ur":     lambda: pyautogui.move(step, -step),
        "mouse_dl":     lambda: pyautogui.move(-step, step),
        "mouse_dr":     lambda: pyautogui.move(step, step),
        "mouse_click":  lambda: pyautogui.click(),
        "mouse_rclick": lambda: pyautogui.click(button="right"),
        "mouse_dclick": lambda: pyautogui.doubleClick(),
        "mouse_scroll_up":   lambda: pyautogui.scroll(3),
        "mouse_scroll_down": lambda: pyautogui.scroll(-3),
    }

    action = MOUSE_ACTIONS.get(data)
    if action:
        try:
            action()
            await query.answer("✅")
        except Exception as e:
            await query.answer(f"Ошибка: {e}", show_alert=True)
    else:
        await query.answer()
