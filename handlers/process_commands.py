import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from handlers.auth import restricted
from services.system_info import get_top_processes, kill_process_by_pid

logger = logging.getLogger("jarvis")

def build_process_keyboard(processes: list, sort_by: str) -> InlineKeyboardMarkup:
    """Генерирует клавиатуру со списком процессов и кнопками переключения сортировки."""
    buttons = []
    # Кнопки для каждого процесса, чтобы можно было легко завершить
    for p in processes:
        btn_text = f"❌ {p['name'][:18]} (PID: {p['pid']}, {p['memory_mb']}MB, {p['cpu_percent']}%)"
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"kill_proc_{p['pid']}")])

    nav_row = [
        InlineKeyboardButton("📊 По RAM" if sort_by != "memory" else "✅ По RAM", callback_data="procs_sort_ram"),
        InlineKeyboardButton("⚡ По CPU" if sort_by != "cpu" else "✅ По CPU", callback_data="procs_sort_cpu"),
    ]
    buttons.append(nav_row)
    buttons.append([InlineKeyboardButton("🔄 Обновить", callback_data=f"procs_refresh_{sort_by}")])
    buttons.append([InlineKeyboardButton("⬅ В главное меню", callback_data="main_menu")])

    return InlineKeyboardMarkup(buttons)

@restricted
async def show_processes(update: Update, context: ContextTypes.DEFAULT_TYPE, sort_by: str = "memory"):
    """Отображает топ запущенных процессов."""
    procs = get_top_processes(limit=8, sort_by=sort_by)
    text = (
        f"📋 *Топ процессов (сортировка: {'CPU' if sort_by == 'cpu' else 'ОЗУ'}):*\n\n"
        "Нажмите на строку с процессом, чтобы завершить его, или введите команду `/kill <PID>`."
    )
    kb = build_process_keyboard(procs, sort_by)

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
        except Exception:
            await update.callback_query.answer("Список обновлен")
    elif update.message:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")

@restricted
async def handle_kill_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершает процесс по клику на кнопку."""
    query = update.callback_query
    pid_str = query.data.replace("kill_proc_", "")
    try:
        pid = int(pid_str)
        success = kill_process_by_pid(pid)
        if success:
            await query.answer(f"✅ Процесс {pid} успешно завершён!", show_alert=True)
        else:
            await query.answer(f"⚠️ Не удалось завершить {pid} (процесс уже закрыт или нет прав).", show_alert=True)
    except Exception as e:
        await query.answer(f"Ошибка: {e}", show_alert=True)

    # Обновляем список
    await show_processes(update, context, sort_by="memory")

@restricted
async def cmd_kill_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /kill <PID>."""
    if not context.args:
        await update.message.reply_text("Использование: `/kill <PID>` (например, `/kill 1234`)", parse_mode="Markdown")
        return
    try:
        pid = int(context.args[0])
        success = kill_process_by_pid(pid)
        if success:
            await update.message.reply_text(f"✅ Процесс с PID {pid} завершён.")
        else:
            await update.message.reply_text(f"⚠️ Не удалось завершить процесс с PID {pid}.")
    except ValueError:
        await update.message.reply_text("⚠️ Неверный формат PID. Должно быть число.")
