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

    # 0. Нажатия кнопок постоянной клавиатуры
    if "скриншот" in lower:
        from handlers.system_commands import send_screenshot
        await send_screenshot(update, context, monitor_index=0)
        return
    elif "инфо о системе" in lower or "статус" in lower:
        from handlers.system_commands import cmd_sysinfo
        await cmd_sysinfo(update, context)
        return
    elif "рабочие столы" in lower:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("1️⃣ Стол 1", callback_data="dt_1"), InlineKeyboardButton("2️⃣ Стол 2", callback_data="dt_2"), InlineKeyboardButton("3️⃣ Стол 3", callback_data="dt_3")],
            [InlineKeyboardButton("⬅ Налево", callback_data="dt_left"), InlineKeyboardButton("Вправо ➡", callback_data="dt_right")],
            [InlineKeyboardButton("➕ Создать рабочий стол", callback_data="dt_new")],
        ])
        await update.message.reply_text("🎛 *Управление виртуальными столами:*", reply_markup=kb, parse_mode="Markdown")
        return
    elif "звук / медиа" in lower or "звук" in lower and len(text) < 15:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⏮ Назад", callback_data="med_prev"), InlineKeyboardButton("⏯ Play/Pause", callback_data="med_play"), InlineKeyboardButton("⏭ Вперед", callback_data="med_next")],
            [InlineKeyboardButton("🔉 Тише (-10%)", callback_data="vol_down"), InlineKeyboardButton("🔇 Mute", callback_data="vol_mute"), InlineKeyboardButton("🔊 Громче (+10%)", callback_data="vol_up")],
        ])
        await update.message.reply_text("🔊 *Управление звуком и мультимедиа:*", reply_markup=kb, parse_mode="Markdown")
        return
    elif "напоминания" in lower and len(text) < 15:
        from scheduler import reminder_manager
        active = reminder_manager.get_active_reminders(chat_id)
        if not active:
            t = "⏰ *Напоминания:*\n\nУ вас пока нет активных напоминаний.\nЧтобы создать, просто напишите: «_напомни через 20 минут проверить почту_»."
        else:
            t = "⏰ *Ваши активные напоминания:*\n\n"
            for r in active:
                t += f"• «{r['text']}» — `{r['next_trigger_at']}`\n"
        await update.message.reply_text(t, parse_mode="Markdown")
        return
    elif "процессы" in lower and len(text) < 15:
        from handlers.process_commands import show_processes
        await show_processes(update, context, sort_by="memory")
        return
    elif "заблокировать" in lower:
        from handlers.system_commands import cmd_lock
        await cmd_lock(update, context)
        return
    elif "сон" in lower and len(text) < 8:
        from handlers.system_commands import cmd_sleep
        await cmd_sleep(update, context)
        return
    elif "перезагрузка" in lower and len(text) < 15:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚠️ Да, перезагрузить!", callback_data="do_restart")],
            [InlineKeyboardButton("❌ Отмена", callback_data="main_menu")]
        ])
        await update.message.reply_text("⚠️ *Вы действительно хотите перезагрузить ПК?*", reply_markup=kb, parse_mode="Markdown")
        return
    elif "выключить" in lower and len(text) < 15:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚠️ Да, выключить!", callback_data="do_shutdown")],
            [InlineKeyboardButton("❌ Отмена", callback_data="main_menu")]
        ])
        await update.message.reply_text("⚠️ *Вы действительно хотите выключить ПК?*", reply_markup=kb, parse_mode="Markdown")
        return
    elif "мышь/клавиши" in lower:
        from handlers.remote_control import show_remote_control_menu
        await show_remote_control_menu(update, context)
        return
    elif "файлы" in lower and len(text) < 10:
        from handlers.files import show_files_menu
        await show_files_menu(update, context)
        return
    elif "возможности ии" in lower:
        from handlers.menu import menu_callback_router
        help_text = (
            "🤖 *Возможности ИИ-агента Jarvis:*\n\n"
            "• *Голос:* просто отправьте голосовое сообщение с любым поручением.\n"
            "• *Многошаговые цепочки:* «Перейди в 1 рабочий стол, запусти Яндекс Музыку и сделай скриншот».\n"
            "• *Работа с файлами:* «Создай на рабочем столе папку Проект и скачай туда с википедии статью про Python».\n"
            "• *Умный поиск:* находит приложения даже сленгом и опечатками («открой янд музыку», «запусти хром»).\n"
            "• *Проактивность:* предупреждает о перегрузке CPU, нехватке диска и зависших окнах."
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")
        return
    elif "очистка %temp%" in lower or "очистка" in lower and len(text) < 18:
        from services.system_monitor import preview_and_cleanup_temp
        count, freed_mb = preview_and_cleanup_temp()
        await update.message.reply_text(f"🧹 Очищено временных файлов: {count} (освобождено ~{freed_mb} МБ)")
        return

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
