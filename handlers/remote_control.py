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
    Обрабатывает текстовые сообщения в порядке приоритета:
    1. Кнопки нижней клавиатуры (категории меню) → menu.handle_reply_keyboard
    2. Ожидание числового ввода (яркость, громкость, поиск файла, скриншот)
    3. Быстрые директивные команды (mouse:, key:, type:, scroll:)
    4. Всё остальное → ИИ планировщик Gemini
    """
    raw_text = update.message.text
    if not raw_text:
        return

    text = raw_text.strip()
    chat_id = update.effective_chat.id
    logger.info(f"Получено текстовое сообщение от {chat_id}: '{text}'")
    lower = text.lower()

    # ── ПРИОРИТЕТ 1: кнопки нижней постоянной клавиатуры ───────
    # handle_reply_keyboard также обрабатывает все awaiting-состояния (скриншот,
    # яркость, громкость, поиск файла/программы) с наивысшим приоритетом —
    # до проверки ai_mode, чтобы ИИ не перехватывал числовой/текстовый ввод.
    from handlers.menu import handle_reply_keyboard
    if await handle_reply_keyboard(update, context):
        return

    # ── ПРИОРИТЕТ 2: защита от ИИ при активном ожидании ввода ──
    # (дополнительная страховка, если handle_reply_keyboard не обработала)
    _AWAITING_KEYS = (
        "awaiting_screenshot_choice", "awaiting_brightness",
        "awaiting_volume", "awaiting_file_search", "awaiting_app_search",
    )
    if any(context.user_data.get(k) for k in _AWAITING_KEYS):
        # Состояние ожидания активно, но не обработано выше — игнорируем
        logger.warning(f"Необработанное awaiting-состояние при тексте: '{text}'")
        return

    # ── ПРИОРИТЕТ 3: быстрые директивные команды ────────────────

    # Естественные команды перехода на сайты: "зайди в сайт гмаил", "открой ютуб", "перейди на..."
    if re.match(r"^(зайди\s*(в|на)?\s*(сайт)?|перейди\s*(в|на)?\s*(сайт)?|открой\s*(сайт)?)\s+", lower):
        from services.web_client import open_url_or_search
        target_site = text
        url = open_url_or_search(target_site)
        await update.message.reply_text(f"🌐 Перехожу: `{url}`", parse_mode="Markdown")
        return

    # Управление мышью: mouse: X,Y или перемести мышь X,Y
    m_mouse = re.match(r"^(mouse:|мышь:|перемести мышь:?)\s*(\d+)[,\s]+(\d+)", lower)
    if m_mouse:
        x, y = int(m_mouse.group(2)), int(m_mouse.group(3))
        try:
            pyautogui.FAILSAFE = False
            pyautogui.moveTo(x, y, duration=0.25)
            await update.message.reply_text(f"🖱 Курсор перемещён в ({x}, {y})")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Ошибка мыши: {e}")
        return

    # Перетаскивание мыши: drag: X1,Y1 to X2,Y2 или drag: X,Y
    if lower.startswith("drag:") or lower.startswith("перетащи:"):
        coords = re.sub(r"^(drag:|перетащи:)", "", text, flags=re.IGNORECASE).strip()
        try:
            pyautogui.FAILSAFE = False
            nums = [int(n.strip()) for n in re.split(r"[,\s]+", coords) if n.strip().isdigit()]
            if len(nums) == 2:
                pyautogui.dragTo(nums[0], nums[1], duration=0.4, button="left")
                await update.message.reply_text(f"🖱 Перетащено в ({nums[0]}, {nums[1]})")
            elif len(nums) == 4:
                pyautogui.moveTo(nums[0], nums[1], duration=0.2)
                pyautogui.dragTo(nums[2], nums[3], duration=0.4, button="left")
                await update.message.reply_text(f"🖱 Перетащено из ({nums[0]}, {nums[1]}) в ({nums[2]}, {nums[3]})")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Ошибка Drag&Drop: {e}")
        return

    if lower in ("click", "клик", "лкм", "кликни"):
        pyautogui.click()
        await update.message.reply_text("🖱 ЛКМ клик выполнен.")
        return
    elif lower in ("rclick", "пкм", "правый клик"):
        pyautogui.click(button="right")
        await update.message.reply_text("🖱 ПКМ клик выполнен.")
        return
    elif lower in ("dclick", "двойной клик", "2x клик"):
        pyautogui.doubleClick()
        await update.message.reply_text("🖱 Двойной клик выполнен.")
        return

    # Горячие клавиши: key: alt+f4
    if lower.startswith("key:") or lower.startswith("клавиша:") or lower.startswith("нажми:"):
        payload = re.sub(r"^(key:|клавиша:|нажми:)", "", text, flags=re.IGNORECASE).strip()
        keys = [k.strip().lower() for k in payload.split("+")]
        try:
            pyautogui.hotkey(*keys)
            await update.message.reply_text(f"⌨ Нажато: `{' + '.join(keys)}`", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Ошибка: {e}")
        return

    # Ввод текста: type: текст
    if lower.startswith("type:") or lower.startswith("напечатай:") or lower.startswith("введи:"):
        payload = re.sub(r"^(type:|напечатай:|введи:)", "", text, flags=re.IGNORECASE).strip()
        try:
            import pyperclip
            pyperclip.copy(payload)
            pyautogui.hotkey("ctrl", "v")
            await update.message.reply_text("⌨ Текст успешно напечатан.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Ошибка ввода текста: {e}")
        return

    # Прокрутка: scroll: 300
    if lower.startswith("scroll:") or lower.startswith("скролл:"):
        amount_str = re.sub(r"^(scroll:|скролл:)", "", text, flags=re.IGNORECASE).strip()
        try:
            amount = int(amount_str)
            pyautogui.scroll(amount)
            await update.message.reply_text(f"📜 Скролл на {amount} выполнен.")
        except Exception as e:
            await update.message.reply_text("⚠️ Ошибка. Пример: `scroll: -300`", parse_mode="Markdown")
        return

    # ── ПРИОРИТЕТ 4: ИИ (Gemini) ─────────────────────────────────
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
