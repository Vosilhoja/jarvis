import os
import shutil
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from handlers.auth import restricted
from services.screenshot import get_monitors_info
from core.task_queue import task_queue_manager
from core.app_resolver import app_resolver

logger = logging.getLogger("jarvis")

def get_main_keyboard() -> InlineKeyboardMarkup:
    """Генерирует расширенную главную клавиатуру Jarvis."""
    keyboard = [
        [
            InlineKeyboardButton("📸 Скриншот", callback_data="menu_screenshot"),
            InlineKeyboardButton("🖥 Инфо о системе", callback_data="sys_info"),
        ],
        [
            InlineKeyboardButton("🎛 Рабочие столы", callback_data="menu_desktops"),
            InlineKeyboardButton("🔊 Звук / Медиа", callback_data="menu_media"),
        ],
        [
            InlineKeyboardButton("⏰ Напоминания", callback_data="menu_reminders"),
            InlineKeyboardButton("📋 Процессы", callback_data="menu_procs"),
        ],
        [
            InlineKeyboardButton("🔒 Заблокировать", callback_data="sys_lock"),
            InlineKeyboardButton("😴 Сон", callback_data="sys_sleep"),
        ],
        [
            InlineKeyboardButton("🔁 Перезагрузка", callback_data="confirm_restart"),
            InlineKeyboardButton("⛔ Выключить", callback_data="confirm_shutdown"),
        ],
        [
            InlineKeyboardButton("🖱 Мышь/Клавиши", callback_data="menu_remote"),
            InlineKeyboardButton("📁 Файлы", callback_data="menu_files"),
        ],
        [
            InlineKeyboardButton("🤖 Возможности ИИ", callback_data="menu_ai_help"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

@restricted
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Точка входа /start для авторизованного владельца."""
    user = update.effective_user
    welcome_text = (
        f"🤖 *Jarvis — Резидентный ИИ-ассистент готов к работе!*\n\n"
        f"Приветствую, {user.first_name or 'Сэр'}! Я обладаю полным доступом к управлению компьютером.\n\n"
        "Вы можете:\n"
        "• Отправлять *голосовые сообщения* с любыми составными поручениями.\n"
        "• Писать сложные многошаговые команды («_перейди на 1 рабочий стол, открой яндекс музыку, сделай скриншот_»).\n"
        "• Запускать программы с неточными названиями и опечатками («_открой музыку от яндекса_»).\n"
        "• Просить найти что-то в Википедии или скачать статью прямо на рабочий стол.\n"
        "• Управлять виртуальными столами, звуком, процессами и напоминаниями."
    )
    kb = get_main_keyboard()
    if update.callback_query:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=kb, parse_mode="Markdown")
    elif update.message:
        await update.message.reply_text(welcome_text, reply_markup=kb, parse_mode="Markdown")

@restricted
async def menu_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Центральный роутер callback-кнопок."""
    query = update.callback_query
    data = query.data
    chat_id = update.effective_chat.id
    session = task_queue_manager.get_session(chat_id)

    # 1. Возврат в главное меню
    if data == "main_menu":
        await cmd_start(update, context)
        return

    # 2. Подтверждение удаления файлов
    if data == "confirm_delete_yes":
        conf = session.pending_confirmation
        if conf and conf.get("action") == "delete":
            path_str = conf["path"]
            try:
                if os.path.isdir(path_str):
                    shutil.rmtree(path_str)
                elif os.path.isfile(path_str):
                    os.remove(path_str)
                await query.edit_message_text(f"✅ Файл/папка успешно удалена: `{path_str}`", parse_mode="Markdown")
            except Exception as e:
                await query.edit_message_text(f"❌ Ошибка удаления: {e}")
            session.pending_confirmation = None
        return

    if data == "confirm_delete_no":
        session.pending_confirmation = None
        await query.edit_message_text("🚫 Удаление отменено.")
        return

    # 3. Выбор приложения при нечетком поиске
    if data.startswith("launch_app_"):
        app_name = data.replace("launch_app_", "")
        for app in app_resolver.apps_index:
            if app["display_name"].startswith(app_name):
                app_resolver.launch_app(app)
                await query.edit_message_text(f"✅ Запущено: *{app['display_name']}*", parse_mode="Markdown")
                return
        await query.answer("Приложение не найдено")
        return

    # 4. Виртуальные рабочие столы
    if data == "menu_desktops":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("1️⃣ Стол 1", callback_data="dt_1"), InlineKeyboardButton("2️⃣ Стол 2", callback_data="dt_2"), InlineKeyboardButton("3️⃣ Стол 3", callback_data="dt_3")],
            [InlineKeyboardButton("⬅ Налево", callback_data="dt_left"), InlineKeyboardButton("Вправо ➡", callback_data="dt_right")],
            [InlineKeyboardButton("➕ Создать рабочий стол", callback_data="dt_new")],
            [InlineKeyboardButton("⬅ Главное меню", callback_data="main_menu")]
        ])
        await query.edit_message_text("🎛 *Управление виртуальными рабочими столами Windows:*", reply_markup=kb, parse_mode="Markdown")
        return

    if data.startswith("dt_"):
        from services.desktops_control import switch_to_desktop_number, switch_desktop_direction, create_virtual_desktop
        val = data.replace("dt_", "")
        if val in ("1", "2", "3"):
            switch_to_desktop_number(int(val))
            await query.answer(f"Стол {val}")
        elif val == "left":
            switch_desktop_direction("left")
            await query.answer("Стол влево")
        elif val == "right":
            switch_desktop_direction("right")
            await query.answer("Стол вправо")
        elif val == "new":
            create_virtual_desktop()
            await query.answer("Новый стол создан")
        return

    # 5. Звук и медиа
    if data == "menu_media":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⏮ Назад", callback_data="med_prev"), InlineKeyboardButton("⏯ Play/Pause", callback_data="med_play"), InlineKeyboardButton("⏭ Вперед", callback_data="med_next")],
            [InlineKeyboardButton("🔉 Тише (-10%)", callback_data="vol_down"), InlineKeyboardButton("🔇 Mute", callback_data="vol_mute"), InlineKeyboardButton("🔊 Громче (+10%)", callback_data="vol_up")],
            [InlineKeyboardButton("⬅ Главное меню", callback_data="main_menu")]
        ])
        await query.edit_message_text("🔊 *Управление звуком и медиаплеером:*", reply_markup=kb, parse_mode="Markdown")
        return

    if data.startswith("med_") or data.startswith("vol_"):
        from services.media_control import change_volume, media_play_pause, media_next, media_prev
        if data == "med_play":
            media_play_pause()
            await query.answer("Play/Pause")
        elif data == "med_next":
            media_next()
            await query.answer("Следующий трек")
        elif data == "med_prev":
            media_prev()
            await query.answer("Предыдущий трек")
        elif data == "vol_up":
            msg = change_volume("up")
            await query.answer(msg)
        elif data == "vol_down":
            msg = change_volume("down")
            await query.answer(msg)
        elif data == "vol_mute":
            msg = change_volume("mute")
            await query.answer(msg)
        return

    # 6. Напоминания
    if data == "menu_reminders":
        from scheduler import reminder_manager
        active = reminder_manager.get_active_reminders(chat_id)
        if not active:
            text = "⏰ *Напоминания:*\n\nУ вас пока нет активных напоминаний.\nЧтобы создать, просто напишите: «_напомни через 20 минут проверить почту_»."
        else:
            text = "⏰ *Ваши активные напоминания:*\n\n"
            for r in active:
                text += f"• «{r['text']}» — `{r['next_trigger_at']}`\n"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅ В главное меню", callback_data="main_menu")]])
        await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
        return

    # 7. Скриншот
    if data == "menu_screenshot":
        monitors = get_monitors_info()
        from handlers.menu import get_screenshot_keyboard
        if len(monitors) <= 2:
            from handlers.system_commands import send_screenshot
            await send_screenshot(update, context, monitor_index=0)
            return
        await query.edit_message_text("📸 *Выберите экран:*", reply_markup=get_screenshot_keyboard(), parse_mode="Markdown")
        return

    if data.startswith("scr_"):
        idx_str = data.replace("scr_", "")
        idx = int(idx_str) if idx_str != "all" else 0
        from handlers.system_commands import send_screenshot
        await send_screenshot(update, context, monitor_index=idx)
        return

    # 8. Система
    if data == "sys_info":
        from handlers.system_commands import cmd_sysinfo
        await cmd_sysinfo(update, context)
        return

    if data == "sys_lock":
        from handlers.system_commands import cmd_lock
        await cmd_lock(update, context)
        return

    if data == "sys_sleep":
        from handlers.system_commands import cmd_sleep
        await cmd_sleep(update, context)
        return

    # 9. Процессы
    if data == "menu_procs" or data.startswith("procs_"):
        from handlers.process_commands import show_processes
        sort = "cpu" if "cpu" in data else "memory"
        await show_processes(update, context, sort_by=sort)
        return

    if data.startswith("kill_proc_"):
        from handlers.process_commands import handle_kill_callback
        await handle_kill_callback(update, context)
        return

    # 10. Пульт
    if data == "menu_remote":
        from handlers.remote_control import show_remote_control_menu
        await show_remote_control_menu(update, context)
        return

    if data.startswith("mouse_"):
        from handlers.remote_control import handle_remote_callback
        await handle_remote_callback(update, context)
        return

    # 11. Файлы
    if data == "menu_files" or data.startswith("file_"):
        from handlers.files import show_files_menu, handle_file_callback
        if data == "menu_files":
            await show_files_menu(update, context)
        else:
            await handle_file_callback(update, context)
        return

    # 12. Подтверждение выключения/перезагрузки
    if data in ("confirm_shutdown", "confirm_restart"):
        act = "выключить" if data == "confirm_shutdown" else "перезагрузить"
        text = f"⚠️ *Вы действительно хотите {act} компьютер?*"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"⚠️ Да, {act}!", callback_data=f"do_{'shutdown' if 'shutdown' in data else 'restart'}")],
            [InlineKeyboardButton("❌ Отмена", callback_data="main_menu")]
        ])
        await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
        return

    if data == "do_shutdown":
        from handlers.system_commands import cmd_shutdown_execute
        await cmd_shutdown_execute(update, context)
        return

    if data == "do_restart":
        from handlers.system_commands import cmd_restart_execute
        await cmd_restart_execute(update, context)
        return

    if data == "menu_ai_help":
        help_text = (
            "🤖 *Возможности ИИ-агента Jarvis:*\n\n"
            "• *Голос:* просто отправьте голосовое сообщение с любым поручением.\n"
            "• *Многошаговые цепочки:* «Перейди в 1 рабочий стол, запусти Яндекс Музыку и сделай скриншот».\n"
            "• *Работа с файлами:* «Создай на рабочем столе папку Проект и скачай туда с википедии статью про Python».\n"
            "• *Умный поиск:* находит приложения даже сленгом и опечатками («открой янд музыку», «запусти хром»).\n"
            "• *Проактивность:* предупреждает о перегрузке CPU, нехватке диска и зависших окнах."
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Главное меню", callback_data="main_menu")]])
        await query.edit_message_text(help_text, reply_markup=kb, parse_mode="Markdown")
        return

    await query.answer()

def get_screenshot_keyboard() -> InlineKeyboardMarkup:
    monitors = get_monitors_info()
    buttons = [[InlineKeyboardButton("🖼 Все мониторы (панорама)", callback_data="scr_0")]]
    for m in monitors:
        if m["index"] > 0:
            buttons.append([InlineKeyboardButton(f"🖥 {m['name']}", callback_data=f"scr_{m['index']}")])
    buttons.append([InlineKeyboardButton("⬅ Назад в меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)
