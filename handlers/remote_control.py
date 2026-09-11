import re
import logging
import pyautogui
import pyperclip
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from handlers.auth import restricted

logger = logging.getLogger("jarvis")

# Включаем Failsafe (перемещение мыши в левый верхний угол (0,0) мгновенно прерывает выполнение)
pyautogui.FAILSAFE = True

STEP = 50  # Шаг перемещения курсора по умолчанию в пикселях

def get_remote_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для удалённого управления мышью и клавиатурой."""
    keyboard = [
        [
            InlineKeyboardButton("↖", callback_data="mouse_move_-50_-50"),
            InlineKeyboardButton("⬆ Вверх", callback_data="mouse_move_0_-50"),
            InlineKeyboardButton("↗", callback_data="mouse_move_50_-50"),
        ],
        [
            InlineKeyboardButton("⬅ Влево", callback_data="mouse_move_-50_0"),
            InlineKeyboardButton("🎯 ЛКМ", callback_data="mouse_click_left"),
            InlineKeyboardButton("Вправо ➡", callback_data="mouse_move_50_0"),
        ],
        [
            InlineKeyboardButton("↙", callback_data="mouse_move_-50_50"),
            InlineKeyboardButton("⬇ Вниз", callback_data="mouse_move_0_50"),
            InlineKeyboardButton("↘", callback_data="mouse_move_50_50"),
        ],
        [
            InlineKeyboardButton("🖱 Двойной клик", callback_data="mouse_click_double"),
            InlineKeyboardButton("🖱 ПКМ", callback_data="mouse_click_right"),
        ],
        [
            InlineKeyboardButton("📜 Скролл ⬆", callback_data="mouse_scroll_300"),
            InlineKeyboardButton("📜 Скролл ⬇", callback_data="mouse_scroll_-300"),
        ],
        [
            InlineKeyboardButton("📸 Скриншот", callback_data="scr_all"),
            InlineKeyboardButton("⬅ Главное меню", callback_data="main_menu"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

@restricted
async def show_remote_control_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает пульт дистанционного управления."""
    x, y = pyautogui.position()
    text = (
        "🖱 *Удалённое управление компьютером*\n\n"
        f"Текущие координаты курсора: `X={x}, Y={y}`\n\n"
        "Используйте кнопки для навигации или отправляйте текстовые команды:\n"
        "• `mouse: 500,300` — переместить курсор в координаты X,Y\n"
        "• `click` или `rclick` или `dclick` — клик мышью\n"
        "• `type: Привет мир` — напечатать текст (поддерживает русский!)\n"
        "• `key: win+d` — нажать комбинацию (например `ctrl+c`, `alt+tab`, `enter`, `esc`)\n"
        "• `scroll: 500` или `scroll: -500` — прокрутка колесика"
    )
    kb = get_remote_keyboard()
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    elif update.message:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")

@restricted
async def handle_remote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает кнопки движения, кликов и скролла."""
    query = update.callback_query
    data = query.data

    try:
        if data.startswith("mouse_move_"):
            parts = data.replace("mouse_move_", "").split("_")
            dx, dy = int(parts[0]), int(parts[1])
            x, y = pyautogui.position()
            pyautogui.moveTo(x + dx, y + dy, duration=0.15)
            new_x, new_y = pyautogui.position()
            await query.answer(f"Курсор: {new_x}, {new_y}")

        elif data == "mouse_click_left":
            pyautogui.click()
            await query.answer("ЛКМ клик")

        elif data == "mouse_click_right":
            pyautogui.click(button="right")
            await query.answer("ПКМ клик")

        elif data == "mouse_click_double":
            pyautogui.doubleClick()
            await query.answer("Двойной клик")

        elif data.startswith("mouse_scroll_"):
            amount = int(data.replace("mouse_scroll_", ""))
            pyautogui.scroll(amount)
            await query.answer(f"Скролл: {amount}")

    except Exception as e:
        logger.error(f"Ошибка в handle_remote_callback: {e}")
        await query.answer(f"Ошибка: {e}", show_alert=True)

@restricted
async def handle_text_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Разбирает текстовые команды управления или передает их в Gemini AI.
    """
    raw_text = update.message.text
    if not raw_text:
        return

    text = raw_text.strip()
    lower = text.lower()

    # 1. Перемещение мыши: mouse: X,Y или мышь: X,Y
    if lower.startswith("mouse:") or lower.startswith("мышь:"):
        coords = re.sub(r"^(mouse:|мышь:)", "", text, flags=re.IGNORECASE).strip()
        try:
            x, y = map(int, coords.split(","))
            pyautogui.moveTo(x, y, duration=0.25)
            await update.message.reply_text(f"🖱 Курсор перемещён в {x}, {y}")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Ошибка формата. Пример: `mouse: 800,600` ({e})", parse_mode="Markdown")
        return

    # 2. Клики
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

    # 3. Нажатие клавиш: key: win+d / клавиша: enter
    if lower.startswith("key:") or lower.startswith("клавиша:"):
        payload = re.sub(r"^(key:|клавиша:)", "", text, flags=re.IGNORECASE).strip()
        keys = [k.strip().lower() for k in payload.split("+")]
        try:
            pyautogui.hotkey(*keys)
            await update.message.reply_text(f"⌨ Нажато: `{' + '.join(keys)}`", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Ошибка нажатия клавиш: {e}")
        return

    # 4. Ввод текста: type: Привет / напечатай: Привет
    if lower.startswith("type:") or lower.startswith("напечатай:"):
        payload = re.sub(r"^(type:|напечатай:)", "", text, flags=re.IGNORECASE).strip()
        try:
            # Для надежной поддержки Unicode/кириллицы используем буфер обмена
            old_clip = pyperclip.paste()
            pyperclip.copy(payload)
            pyautogui.hotkey("ctrl", "v")
            await update.message.reply_text("⌨ Текст успешно напечатан.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Ошибка ввода текста: {e}")
        return

    # 5. Скролл: scroll: 500 / скролл: -300
    if lower.startswith("scroll:") or lower.startswith("скролл:"):
        amount_str = re.sub(r"^(scroll:|скролл:)", "", text, flags=re.IGNORECASE).strip()
        try:
            amount = int(amount_str)
            pyautogui.scroll(amount)
            await update.message.reply_text(f"📜 Скролл на {amount} выполнен.")
        except Exception as e:
            await update.message.reply_text("⚠️ Ошибка. Пример: `scroll: -300`", parse_mode="Markdown")
        return

    # Если ни одна команда не подошла — отправляем вопрос в Gemini AI
    from handlers.ai_chat import handle_ai_message
    await handle_ai_message(update, context)
