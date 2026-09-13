import os
import ctypes
import logging
from telegram import Update
from telegram.ext import ContextTypes
from handlers.auth import restricted
from services.screenshot import take_screenshot, get_monitors_info
from services.system_info import get_system_metrics

logger = logging.getLogger("jarvis")

@restricted
async def cmd_lock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Блокировка экрана Windows."""
    try:
        ctypes.windll.user32.LockWorkStation()
        if update.callback_query:
            await update.callback_query.answer("🔒 Рабочая станция заблокирована!", show_alert=True)
        elif update.message:
            await update.message.reply_text("🔒 Рабочая станция заблокирована.")
    except Exception as e:
        logger.error(f"Ошибка при блокировке экрана: {e}")
        if update.callback_query:
            await update.callback_query.answer(f"Ошибка: {e}", show_alert=True)

@restricted
async def cmd_sleep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Перевод Windows в спящий режим."""
    try:
        if update.callback_query:
            await update.callback_query.answer("😴 Компьютер переходит в спящий режим...", show_alert=True)
            await update.callback_query.message.reply_text("😴 ПК уходит в сон. До связи!")
        # rundll32.exe powrprof.dll,SetSuspendState 0,1,0
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
    except Exception as e:
        logger.error(f"Ошибка при переходе в сон: {e}")

@restricted
async def cmd_shutdown_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выключение ПК с таймером 30 секунд."""
    os.system("shutdown /s /t 30")
    text = (
        "⛔ *Команда на выключение отправлена!*\n\n"
        "ПК будет выключен через 30 секунд.\n"
        "Чтобы отменить выключение, нажмите кнопку ниже или введите на ПК: `shutdown /a`"
    )
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚫 Отменить выключение", callback_data="cancel_shutdown")],
        [InlineKeyboardButton("⬅ В главное меню", callback_data="main_menu")]
    ])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")

@restricted
async def cmd_restart_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Перезагрузка ПК с таймером 30 секунд."""
    os.system("shutdown /r /t 30")
    text = (
        "🔁 *Команда на перезагрузку отправлена!*\n\n"
        "ПК перезагрузится через 30 секунд.\n"
        "Чтобы отменить перезагрузку, нажмите кнопку ниже или введите на ПК: `shutdown /a`"
    )
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚫 Отменить перезагрузку", callback_data="cancel_shutdown")],
        [InlineKeyboardButton("⬅ В главное меню", callback_data="main_menu")]
    ])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")

@restricted
async def cmd_cancel_shutdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена запланированного выключения/перезагрузки."""
    os.system("shutdown /a")
    if update.callback_query:
        await update.callback_query.answer("✅ Выключение/перезагрузка отменена!", show_alert=True)
        from handlers.menu import get_main_keyboard
        await update.callback_query.edit_message_text(
            "✅ Выключение ПК успешно отменено.",
            reply_markup=get_main_keyboard()
        )

@restricted
async def cmd_sysinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вывод подробной информации о ресурсах системы."""
    metrics = get_system_metrics()
    
    disks_text = ""
    for d in metrics["disks"]:
        dev = str(d['device']).replace('\\', '/')
        mp = str(d['mountpoint']).replace('\\', '/')
        disks_text += f"  • {dev} ({mp}): {d['percent']}% (исп. {d['used_gb']} / {d['total_gb']} GB)\n"
    if not disks_text:
        disks_text = "  • Нет доступных дисков\n"

    text = (
        f"🖥 *Состояние системы*\n\n"
        f"⚡ *CPU:* {metrics['cpu_percent']}%\n"
        f"🎛 *Ядра:* {metrics['cpu_cores']}\n"
        f"🧠 *RAM:* {metrics['ram_percent']}% ({metrics['ram_used_mb']} / {metrics['ram_total_mb']} MB)\n"
        f"💾 *Дисковые накопители:*\n{disks_text}\n"
        f"⏱ *Время работы ПК:* {metrics['uptime']}\n"
        f"🚀 *Включён с:* `{metrics['boot_time']}`\n"
    )
    
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Обновить", callback_data="sys_info")],
        [InlineKeyboardButton("⬅ В главное меню", callback_data="main_menu")]
    ])

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
        except Exception:
            await update.callback_query.answer("Информация актуальна")
    elif update.message:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")

@restricted
async def send_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE, monitor_index: int | None = None, desktop_num: int | None = None, reply_markup=None):
    """Создает и отправляет скриншот пользователю (поддерживает выбор монитора и виртуального рабочего стола)."""
    chat_id = update.effective_chat.id
    status_msg = None
    if update.callback_query:
        await update.callback_query.answer("📸 Делаю снимок экрана...")
    else:
        status_msg = await update.message.reply_text("📸 Делаю снимок экрана...")

    try:
        if desktop_num is not None and desktop_num > 0:
            from services.screenshot import take_desktop_screenshot
            buf = take_desktop_screenshot(desktop_num, monitor_index)
            name = f"Рабочий стол {desktop_num}"
        else:
            buf = take_screenshot(monitor_index)
            name = "Текущий экран" if monitor_index in (None, 0) else f"Монитор {monitor_index}"
        
        caption = f"📸 Снимок: *{name}*"
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=buf,
            caption=caption,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка при создании скриншота: {e}", exc_info=True)
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Ошибка создания скриншота: {e}")
    finally:
        if status_msg:
            try:
                await status_msg.delete()
            except Exception:
                pass
