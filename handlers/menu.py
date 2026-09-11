import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from handlers.auth import restricted
from services.screenshot import get_monitors_info

logger = logging.getLogger("jarvis")

def get_main_keyboard() -> InlineKeyboardMarkup:
    """Генерирует главную клавиатуру Jarvis с 2 кнопками в ряд."""
    keyboard = [
        [
            InlineKeyboardButton("📸 Скриншот", callback_data="menu_screenshot"),
            InlineKeyboardButton("🖥 Инфо о системе", callback_data="sys_info"),
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
            InlineKeyboardButton("📋 Процессы", callback_data="menu_procs"),
            InlineKeyboardButton("🖱 Удалённое управление", callback_data="menu_remote"),
        ],
        [
            InlineKeyboardButton("🤖 Спросить ИИ", callback_data="menu_ai_help"),
            InlineKeyboardButton("📁 Файлы", callback_data="menu_files"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_screenshot_keyboard() -> InlineKeyboardMarkup:
    """Генерирует клавиатуру выбора монитора для скриншота."""
    monitors = get_monitors_info()
    buttons = []
    
    # Кнопка для всех мониторов (панорама)
    buttons.append([InlineKeyboardButton("🖼 Все мониторы (панорама)", callback_data="scr_0")])
    
    # Кнопки для каждого физического монитора
    for m in monitors:
        if m["index"] > 0:
            buttons.append([InlineKeyboardButton(f"🖥 {m['name']}", callback_data=f"scr_{m['index']}")])

    buttons.append([InlineKeyboardButton("⬅ Назад в меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)

def get_confirmation_keyboard(action_type: str) -> InlineKeyboardMarkup:
    """Генерирует клавиатуру подтверждения опасных действий."""
    confirm_cb = f"do_{action_type}"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚠️ Да, выполнить!", callback_data=confirm_cb),
            InlineKeyboardButton("❌ Отмена", callback_data="main_menu"),
        ]
    ])

@restricted
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Точка входа /start для авторизованного пользователя."""
    user = update.effective_user
    welcome_text = (
        f"👋 *Здравствуйте, {user.first_name or 'Сэр'}!*\n"
        "Я — *Jarvis*, ваш персональный ассистент по управлению компьютером.\n\n"
        "Выберите нужное действие из меню ниже или просто напишите мне сообщение — "
        "любой текстовый вопрос будет передан в Gemini AI, а команды управления ПК выполнятся мгновенно."
    )
    kb = get_main_keyboard()
    if update.callback_query:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=kb, parse_mode="Markdown")
    elif update.message:
        await update.message.reply_text(welcome_text, reply_markup=kb, parse_mode="Markdown")

@restricted
async def menu_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Центральный диспетчер callback-запросов от inline-кнопок."""
    query = update.callback_query
    data = query.data

    # 1. Возврат в главное меню
    if data == "main_menu":
        await cmd_start(update, context)
        return

    # 2. Меню скриншотов
    if data == "menu_screenshot":
        monitors = get_monitors_info()
        # Если только один монитор (индекс 0 - общий, 1 - единственный экран)
        if len(monitors) <= 2:
            from handlers.system_commands import send_screenshot
            await send_screenshot(update, context, monitor_index=0)
            return
        
        await query.edit_message_text(
            "📸 *Выберите экран для снимка:*",
            reply_markup=get_screenshot_keyboard(),
            parse_mode="Markdown"
        )
        return

    if data.startswith("scr_"):
        idx_str = data.replace("scr_", "")
        idx = int(idx_str) if idx_str != "all" else 0
        from handlers.system_commands import send_screenshot
        await send_screenshot(update, context, monitor_index=idx)
        return

    # 3. Инфо о системе
    if data == "sys_info":
        from handlers.system_commands import cmd_sysinfo
        await cmd_sysinfo(update, context)
        return

    # 4. Блокировка и сон
    if data == "sys_lock":
        from handlers.system_commands import cmd_lock
        await cmd_lock(update, context)
        return

    if data == "sys_sleep":
        from handlers.system_commands import cmd_sleep
        await cmd_sleep(update, context)
        return

    # 5. Подтверждение выключения / перезагрузки
    if data == "confirm_shutdown":
        text = "⚠️ *Вы действительно хотите выключить компьютер?*\n\n(Будет запущен таймер на 30 секунд)"
        await query.edit_message_text(text, reply_markup=get_confirmation_keyboard("shutdown"), parse_mode="Markdown")
        return

    if data == "confirm_restart":
        text = "⚠️ *Вы действительно хотите перезагрузить компьютер?*\n\n(Будет запущен таймер на 30 секунд)"
        await query.edit_message_text(text, reply_markup=get_confirmation_keyboard("restart"), parse_mode="Markdown")
        return

    if data == "do_shutdown":
        from handlers.system_commands import cmd_shutdown_execute
        await cmd_shutdown_execute(update, context)
        return

    if data == "do_restart":
        from handlers.system_commands import cmd_restart_execute
        await cmd_restart_execute(update, context)
        return

    if data == "cancel_shutdown":
        from handlers.system_commands import cmd_cancel_shutdown
        await cmd_cancel_shutdown(update, context)
        return

    # 6. Процессы
    if data == "menu_procs" or data.startswith("procs_"):
        from handlers.process_commands import show_processes
        sort = "cpu" if "cpu" in data else "memory"
        await show_processes(update, context, sort_by=sort)
        return

    if data.startswith("kill_proc_"):
        from handlers.process_commands import handle_kill_callback
        await handle_kill_callback(update, context)
        return

    # 7. Удалённое управление
    if data == "menu_remote":
        from handlers.remote_control import show_remote_control_menu
        await show_remote_control_menu(update, context)
        return

    if data.startswith("mouse_"):
        from handlers.remote_control import handle_remote_callback
        await handle_remote_callback(update, context)
        return

    # 8. Файлы
    if data == "menu_files" or data.startswith("file_"):
        from handlers.files import show_files_menu, handle_file_callback
        if data == "menu_files":
            await show_files_menu(update, context)
        else:
            await handle_file_callback(update, context)
        return

    # 9. Подсказка по Gemini AI
    if data == "menu_ai_help":
        ai_help_text = (
            "🤖 *Режим общения с Gemini AI*\n\n"
            "Вам не нужно нажимать специальных кнопок! Просто напишите любой вопрос обычным сообщением в чат.\n\n"
            "Например:\n"
            "• _«Напиши скрипт на Python для сортировки файлов»_\n"
            "• _«Объясни, как настроить VPN на Windows»_\n"
            "• _«Что такое квантовые вычисления?»_\n\n"
            "Jarvis помнит контекст последних ~10 сообщений. Для очистки истории введите команду `/clear`."
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅ В главное меню", callback_data="main_menu")]])
        await query.edit_message_text(ai_help_text, reply_markup=kb, parse_mode="Markdown")
        return

    await query.answer()
