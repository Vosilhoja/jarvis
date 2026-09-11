"""
Главный модуль меню Jarvis.
ReplyKeyboard (нижняя клавиатура) — категории.
InlineKeyboard (в сообщении) — функции категории.
"""
import os
import shutil
import logging
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import ContextTypes

from handlers.auth import restricted
from services.screenshot import get_monitors_info
from core.task_queue import task_queue_manager
from core.app_resolver import app_resolver

logger = logging.getLogger("jarvis")

# ═══════════════════════════════════════════════════════════
#  НИЖНЯЯ КЛАВИАТУРА — КАТЕГОРИИ (ReplyKeyboardMarkup)
#  Всегда видна рядом с полем ввода, как кнопки под эмодзи.
# ═══════════════════════════════════════════════════════════

def get_reply_keyboard() -> ReplyKeyboardMarkup:
    """Нижняя постоянная клавиатура с категориями."""
    keyboard = [
        [KeyboardButton("🖥 Система"),      KeyboardButton("🎵 Медиа / Звук")],
        [KeyboardButton("📁 Файлы"),         KeyboardButton("🌐 Сеть")],
        [KeyboardButton("🚀 Приложения"),    KeyboardButton("🖱 Управление ПК")],
        [KeyboardButton("📸 Скриншот"),      KeyboardButton("📋 Процессы")],
        [KeyboardButton("🤖 ИИ-чат"),        KeyboardButton("⏰ Напоминания")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)


# ═══════════════════════════════════════════════════════════
#  INLINE-КЛАВИАТУРЫ ДЛЯ КАЖДОЙ КАТЕГОРИИ
# ═══════════════════════════════════════════════════════════

def kb_system() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Инфо о системе",   callback_data="sys_info"),
         InlineKeyboardButton("🌡 Температура",       callback_data="sys_temp")],
        [InlineKeyboardButton("🔋 Аккумулятор",       callback_data="sys_battery"),
         InlineKeyboardButton("🖥 Разрешение экрана", callback_data="sys_resolution")],
        [InlineKeyboardButton("🌐 IP-адреса",         callback_data="sys_ip"),
         InlineKeyboardButton("📋 Буфер обмена",      callback_data="sys_clipboard")],
        [InlineKeyboardButton("💡 Яркость +",         callback_data="bright_up"),
         InlineKeyboardButton("💡 Яркость —",         callback_data="bright_down")],
        [InlineKeyboardButton("⌨ Подсветка клавы",    callback_data="sys_kbd_backlight"),
         InlineKeyboardButton("🖥 Выкл. монитор",     callback_data="sys_monitor_off")],
        [InlineKeyboardButton("🔇 Режим Тихий час",   callback_data="sys_dnd"),
         InlineKeyboardButton("🛠 Диспетчер устр.",   callback_data="sys_devmgmt")],
        [InlineKeyboardButton("📅 Планировщик задач", callback_data="sys_taskschd"),
         InlineKeyboardButton("📜 Просмотр событий",  callback_data="sys_eventvwr")],
        [InlineKeyboardButton("🔒 Заблокировать",     callback_data="sys_lock"),
         InlineKeyboardButton("😴 Режим сна",         callback_data="sys_sleep")],
        [InlineKeyboardButton("🔁 Перезагрузка",      callback_data="confirm_restart"),
         InlineKeyboardButton("⛔ Выключить ПК",      callback_data="confirm_shutdown")],
        [InlineKeyboardButton("🧹 Очистить %TEMP%",   callback_data="sys_clean_temp"),
         InlineKeyboardButton("🗑 Очистить корзину",  callback_data="sys_empty_bin")],
    ])


def kb_media() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏮ Назад",        callback_data="med_prev"),
         InlineKeyboardButton("⏯ Play/Pause",   callback_data="med_play"),
         InlineKeyboardButton("⏭ Вперёд",       callback_data="med_next")],
        [InlineKeyboardButton("🔉 Тише (—10%)", callback_data="vol_down"),
         InlineKeyboardButton("🔇 Mute",         callback_data="vol_mute"),
         InlineKeyboardButton("🔊 Громче (+10%)",callback_data="vol_up")],
        [InlineKeyboardButton("🎚 Громкость 0%", callback_data="vol_set_0"),
         InlineKeyboardButton("🎚 25%",          callback_data="vol_set_25"),
         InlineKeyboardButton("🎚 50%",          callback_data="vol_set_50"),
         InlineKeyboardButton("🎚 100%",         callback_data="vol_set_100")],
        [InlineKeyboardButton("⏹ Стоп",          callback_data="med_stop"),
         InlineKeyboardButton("🎬 YouTube",       callback_data="app_youtube")],
    ])


def kb_files() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗂 Рабочий стол",   callback_data="file_desktop"),
         InlineKeyboardButton("⬇️ Загрузки",        callback_data="file_downloads")],
        [InlineKeyboardButton("📂 Документы",       callback_data="file_documents"),
         InlineKeyboardButton("📦 Размер папок",    callback_data="file_sizes")],
        [InlineKeyboardButton("🔍 Найти файл",      callback_data="file_search_prompt"),
         InlineKeyboardButton("🗑 Очистить корзину",callback_data="sys_empty_bin")],
        [InlineKeyboardButton("📁 Открыть Проводник", callback_data="app_explorer")],
    ])


def kb_network() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 Мой IP (внешний)",  callback_data="net_public_ip"),
         InlineKeyboardButton("🏠 Локальный IP",      callback_data="net_local_ip")],
        [InlineKeyboardButton("📡 Адаптеры сети",     callback_data="net_adapters"),
         InlineKeyboardButton("📶 Wi-Fi сети",        callback_data="net_wifi")],
        [InlineKeyboardButton("🏓 Ping 8.8.8.8",      callback_data="net_ping_google"),
         InlineKeyboardButton("🏓 Ping Яндекс",       callback_data="net_ping_yandex")],
    ])


def kb_apps() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Chrome",      callback_data="app_chrome"),
         InlineKeyboardButton("📨 Telegram",    callback_data="app_telegram")],
        [InlineKeyboardButton("💻 VS Code",     callback_data="app_vscode"),
         InlineKeyboardButton("📁 Проводник",   callback_data="app_explorer")],
        [InlineKeyboardButton("🧮 Калькулятор", callback_data="app_calc"),
         InlineKeyboardButton("📝 Блокнот",     callback_data="app_notepad")],
        [InlineKeyboardButton("🎨 Paint",       callback_data="app_mspaint"),
         InlineKeyboardButton("⚙️ Панель упр.", callback_data="app_control")],
        [InlineKeyboardButton("💻 CMD",         callback_data="app_cmd"),
         InlineKeyboardButton("🔵 PowerShell",  callback_data="app_powershell")],
        [InlineKeyboardButton("🎮 YouTube",     callback_data="app_youtube"),
         InlineKeyboardButton("🛡 Defender",    callback_data="app_defender")],
        [InlineKeyboardButton("📊 Диспетчер задач", callback_data="app_taskmgr")],
    ])


def kb_control() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🖱 Меню мыши",      callback_data="menu_remote")],
        [InlineKeyboardButton("⌨ Enter",           callback_data="key_enter"),
         InlineKeyboardButton("⌨ Escape",          callback_data="key_escape"),
         InlineKeyboardButton("⌨ Win",             callback_data="key_win")],
        [InlineKeyboardButton("⌨ Alt+F4",          callback_data="key_altf4"),
         InlineKeyboardButton("⌨ Ctrl+C",          callback_data="key_ctrlc"),
         InlineKeyboardButton("⌨ Ctrl+V",          callback_data="key_ctrlv")],
        [InlineKeyboardButton("⌨ Alt+Tab",         callback_data="key_alttab"),
         InlineKeyboardButton("⌨ Win+D (Раб.стол)",callback_data="key_wind")],
        [InlineKeyboardButton("📋 Прочитать буфер",callback_data="sys_clipboard"),
         InlineKeyboardButton("📋 Рабочие столы",  callback_data="menu_desktops")],
    ])


def kb_screenshot() -> InlineKeyboardMarkup:
    monitors = get_monitors_info()
    buttons = [[InlineKeyboardButton("🖼 Все мониторы (панорама)", callback_data="scr_0")]]
    for m in monitors:
        if m["index"] > 0:
            buttons.append([InlineKeyboardButton(f"🖥 {m['name']}", callback_data=f"scr_{m['index']}")])
    return InlineKeyboardMarkup(buttons)


def kb_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]])


# ═══════════════════════════════════════════════════════════
#  /start КОМАНДА
# ═══════════════════════════════════════════════════════════

@restricted
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает приветствие и нижнюю клавиатуру категорий."""
    user = update.effective_user
    welcome_text = (
        f"🤖 *Jarvis — Ваш персональный ИИ-ассистент*\n\n"
        f"Привет, {user.first_name or 'Шеф'}! Готов к работе.\n\n"
        "📌 *Кнопки категорий закреплены внизу* (рядом со смайликом)\n\n"
        "• Нажмите кнопку категории → получите список функций\n"
        "• Пишите голосом или текстом любые команды\n"
        "• Многошаговые задачи: «открой хром, сделай скриншот, напомни через 5 мин»"
    )
    reply_kb = get_reply_keyboard()
    msg = update.message or (update.callback_query and update.callback_query.message)
    if msg:
        await msg.reply_text(welcome_text, reply_markup=reply_kb, parse_mode="Markdown")
    if update.callback_query:
        await update.callback_query.answer()


# ═══════════════════════════════════════════════════════════
#  ОБРАБОТЧИК НАЖАТИЙ НИЖНЕЙ КЛАВИАТУРЫ (ReplyKeyboard)
#  Вызывается из handle_text_command в remote_control.py
# ═══════════════════════════════════════════════════════════

async def handle_reply_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Обрабатывает нажатия кнопок нижней клавиатуры (категории).
    Возвращает True если кнопка была обработана, иначе False.
    """
    text = (update.message.text or "").strip()
    lower = text.lower()

    if "🖥 система" in text or text == "🖥 Система":
        await update.message.reply_text("🖥 *Управление системой:*", reply_markup=kb_system(), parse_mode="Markdown")
        return True

    if "🎵 медиа" in text or text == "🎵 Медиа / Звук":
        await update.message.reply_text("🎵 *Звук и медиа:*", reply_markup=kb_media(), parse_mode="Markdown")
        return True

    if text == "📁 Файлы":
        await update.message.reply_text("📁 *Файлы и папки:*", reply_markup=kb_files(), parse_mode="Markdown")
        return True

    if text == "🌐 Сеть":
        await update.message.reply_text("🌐 *Сеть и интернет:*", reply_markup=kb_network(), parse_mode="Markdown")
        return True

    if text == "🚀 Приложения":
        await update.message.reply_text("🚀 *Быстрый запуск приложений:*", reply_markup=kb_apps(), parse_mode="Markdown")
        return True

    if text == "🖱 Управление ПК":
        await update.message.reply_text("🖱 *Управление мышью и клавиатурой:*", reply_markup=kb_control(), parse_mode="Markdown")
        return True

    if text == "📸 Скриншот":
        monitors = get_monitors_info()
        if len(monitors) <= 2:
            from handlers.system_commands import send_screenshot
            await send_screenshot(update, context, monitor_index=0)
        else:
            await update.message.reply_text("📸 *Выберите экран:*", reply_markup=kb_screenshot(), parse_mode="Markdown")
        return True

    if text == "📋 Процессы":
        from handlers.process_commands import show_processes
        await show_processes(update, context, sort_by="memory")
        return True

    if text == "🤖 ИИ-чат":
        await update.message.reply_text(
            "🤖 *Режим ИИ-чата активен.*\n\nПросто пишите или говорите голосом — Jarvis поймёт и выполнит любой запрос!\n\n"
            "_Примеры:_\n• «Расскажи анекдот»\n• «Открой ютуб и сделай скриншот»\n• «Напомни через 15 минут позвонить»",
            parse_mode="Markdown"
        )
        return True

    if text == "⏰ Напоминания":
        from scheduler import reminder_manager
        chat_id = update.effective_chat.id
        active = reminder_manager.get_active_reminders(chat_id)
        if not active:
            t = "⏰ *Напоминания:*\n\nАктивных напоминаний нет.\n\n_Чтобы создать: «напомни через 20 минут проверить почту»_"
        else:
            t = "⏰ *Ваши активные напоминания:*\n\n"
            for r in active:
                t += f"• «{r['text']}» — `{r['next_trigger_at']}`\n"
        await update.message.reply_text(t, parse_mode="Markdown")
        return True

    return False


# ═══════════════════════════════════════════════════════════
#  ЦЕНТРАЛЬНЫЙ РОУТЕР CallbackQuery (InlineKeyboard кнопки)
# ═══════════════════════════════════════════════════════════

@restricted
async def menu_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает все нажатия InlineKeyboard кнопок."""
    query = update.callback_query
    data = query.data
    chat_id = update.effective_chat.id

    await query.answer()  # Убирает "часики" на кнопке

    # ── Главное меню ──────────────────────────────────────
    if data == "main_menu":
        await cmd_start(update, context)
        return

    # ── Подтверждение удаления файлов ────────────────────
    if data == "confirm_delete_yes":
        session = task_queue_manager.get_session(chat_id)
        conf = session.pending_confirmation
        if conf and conf.get("action") == "delete":
            path_str = conf["path"]
            try:
                if os.path.isdir(path_str):
                    shutil.rmtree(path_str)
                elif os.path.isfile(path_str):
                    os.remove(path_str)
                await query.edit_message_text(f"✅ Удалено: `{path_str}`", parse_mode="Markdown")
            except Exception as e:
                await query.edit_message_text(f"❌ Ошибка: {e}")
            session.pending_confirmation = None
        return

    if data == "confirm_delete_no":
        task_queue_manager.get_session(chat_id).pending_confirmation = None
        await query.edit_message_text("🚫 Удаление отменено.")
        return

    # ── Запуск приложений через app_resolver ─────────────
    if data.startswith("launch_app_"):
        app_name = data.replace("launch_app_", "")
        for app in app_resolver.apps_index:
            if app["display_name"].startswith(app_name):
                app_resolver.launch_app(app)
                await query.edit_message_text(f"✅ Запущено: *{app['display_name']}*", parse_mode="Markdown")
                return
        await query.answer("Приложение не найдено", show_alert=True)
        return

    # ── СИСТЕМА ───────────────────────────────────────────
    if data == "sys_info":
        from handlers.system_commands import cmd_sysinfo
        await cmd_sysinfo(update, context)
        return

    if data == "sys_temp":
        try:
            import psutil
            temps = psutil.sensors_temperatures()
            if temps:
                lines = []
                for name, entries in temps.items():
                    for e in entries:
                        lines.append(f"🌡 {name} / {e.label or 'core'}: {e.current}°C")
                text = "🌡 *Температуры:*\n\n" + "\n".join(lines[:10])
            else:
                text = "🌡 Данные о температуре недоступны (нужны права или WMI)"
        except Exception as e:
            text = f"Ошибка: {e}"
        await query.edit_message_text(text, reply_markup=kb_back(), parse_mode="Markdown")
        return

    if data == "sys_battery":
        from services.extra_functions import get_battery_info
        await query.edit_message_text(get_battery_info(), reply_markup=kb_back(), parse_mode="Markdown")
        return

    if data == "sys_resolution":
        from services.extra_functions import get_screen_resolution
        await query.edit_message_text(get_screen_resolution(), reply_markup=kb_back(), parse_mode="Markdown")
        return

    if data == "sys_ip":
        from services.extra_functions import get_local_ip, get_public_ip
        local = get_local_ip()
        public = get_public_ip()
        await query.edit_message_text(
            f"🌐 *IP-адреса:*\n\n🏠 Локальный: `{local}`\n🌍 Внешний: `{public}`",
            reply_markup=kb_back(), parse_mode="Markdown"
        )
        return

    if data == "sys_clipboard":
        from services.extra_functions import get_clipboard
        text = get_clipboard()
        await query.edit_message_text(f"📋 *Буфер обмена:*\n\n```\n{text}\n```", reply_markup=kb_back(), parse_mode="Markdown")
        return

    if data in ("bright_up", "bright_down"):
        from services.media_control import set_brightness
        # Читаем текущий уровень из WMI (упрощённо)
        level = 70 if data == "bright_up" else 30
        result = set_brightness(level)
        await query.answer(result, show_alert=True)
        return

    if data == "sys_kbd_backlight":
        from services.extra_functions import toggle_keyboard_backlight
        result = toggle_keyboard_backlight()
        await query.edit_message_text(result, reply_markup=kb_back())
        return

    if data == "sys_monitor_off":
        from services.extra_functions import turn_off_monitor
        turn_off_monitor()
        await query.answer("🖥 Монитор выключен (двигайте мышью чтобы включить)", show_alert=True)
        return

    if data == "sys_dnd":
        from services.extra_functions import do_not_disturb_mode
        result = do_not_disturb_mode()
        await query.answer(result, show_alert=True)
        return

    if data == "sys_devmgmt":
        from services.extra_functions import open_device_manager
        result = open_device_manager()
        await query.answer(result, show_alert=True)
        return

    if data == "sys_taskschd":
        from services.extra_functions import open_task_scheduler
        result = open_task_scheduler()
        await query.answer(result, show_alert=True)
        return

    if data == "sys_eventvwr":
        from services.extra_functions import open_event_viewer
        result = open_event_viewer()
        await query.answer(result, show_alert=True)
        return

    if data == "sys_lock":
        from handlers.system_commands import cmd_lock
        await cmd_lock(update, context)
        return

    if data == "sys_sleep":
        from handlers.system_commands import cmd_sleep
        await cmd_sleep(update, context)
        return

    if data == "sys_clean_temp":
        from services.system_monitor import preview_and_cleanup_temp
        count, freed_mb = preview_and_cleanup_temp()
        await query.edit_message_text(f"🧹 Очищено: {count} файлов (~{freed_mb} МБ)", reply_markup=kb_back())
        return

    if data == "sys_empty_bin":
        from services.extra_functions import empty_recycle_bin
        result = empty_recycle_bin()
        await query.edit_message_text(result, reply_markup=kb_back())
        return

    # ── ПОДТВЕРЖДЕНИЕ ВЫКЛЮЧЕНИЯ / ПЕРЕЗАГРУЗКИ ──────────
    if data in ("confirm_shutdown", "confirm_restart"):
        act = "выключить" if "shutdown" in data else "перезагрузить"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"⚠️ Да, {act}!", callback_data=f"do_{'shutdown' if 'shutdown' in data else 'restart'}")],
            [InlineKeyboardButton("❌ Отмена", callback_data="main_menu")]
        ])
        await query.edit_message_text(f"⚠️ *Вы уверены, что хотите {act} ПК?*", reply_markup=kb, parse_mode="Markdown")
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

    # ── МЕДИА ─────────────────────────────────────────────
    if data.startswith("med_") or data.startswith("vol_"):
        from services.media_control import change_volume, media_play_pause, media_next, media_prev, media_stop
        if data == "med_play":
            media_play_pause(); await query.answer("⏯ Play/Pause")
        elif data == "med_next":
            media_next(); await query.answer("⏭ Следующий")
        elif data == "med_prev":
            media_prev(); await query.answer("⏮ Предыдущий")
        elif data == "med_stop":
            media_stop(); await query.answer("⏹ Стоп")
        elif data == "vol_up":
            msg = change_volume("up"); await query.answer(msg)
        elif data == "vol_down":
            msg = change_volume("down"); await query.answer(msg)
        elif data == "vol_mute":
            msg = change_volume("mute"); await query.answer(msg)
        elif data.startswith("vol_set_"):
            lvl = int(data.replace("vol_set_", ""))
            from services.media_control import set_volume_pycaw
            set_volume_pycaw(lvl)
            await query.answer(f"🎚 Громкость: {lvl}%")
        return

    # ── ВИРТУАЛЬНЫЕ РАБОЧИЕ СТОЛЫ ─────────────────────────
    if data == "menu_desktops":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("1️⃣", callback_data="dt_1"), InlineKeyboardButton("2️⃣", callback_data="dt_2"), InlineKeyboardButton("3️⃣", callback_data="dt_3")],
            [InlineKeyboardButton("⬅ Налево", callback_data="dt_left"), InlineKeyboardButton("Вправо ➡", callback_data="dt_right")],
            [InlineKeyboardButton("➕ Создать стол", callback_data="dt_new")],
            [InlineKeyboardButton("🏠 Назад", callback_data="main_menu")]
        ])
        await query.edit_message_text("🎛 *Виртуальные рабочие столы Windows:*", reply_markup=kb, parse_mode="Markdown")
        return

    if data.startswith("dt_"):
        from services.desktops_control import switch_to_desktop_number, switch_desktop_direction, create_virtual_desktop
        val = data[3:]
        if val in ("1","2","3"):
            switch_to_desktop_number(int(val)); await query.answer(f"Стол {val}")
        elif val == "left":
            switch_desktop_direction("left"); await query.answer("⬅ Стол влево")
        elif val == "right":
            switch_desktop_direction("right"); await query.answer("➡ Стол вправо")
        elif val == "new":
            create_virtual_desktop(); await query.answer("➕ Новый стол создан")
        return

    # ── СЕТЬ ──────────────────────────────────────────────
    if data == "net_public_ip":
        from services.extra_functions import get_public_ip
        ip = get_public_ip()
        await query.edit_message_text(f"🌍 *Внешний IP:* `{ip}`", reply_markup=kb_back(), parse_mode="Markdown")
        return

    if data == "net_local_ip":
        from services.extra_functions import get_local_ip
        ip = get_local_ip()
        await query.edit_message_text(f"🏠 *Локальный IP:* `{ip}`", reply_markup=kb_back(), parse_mode="Markdown")
        return

    if data == "net_adapters":
        from services.extra_functions import get_network_adapters
        text = get_network_adapters()
        await query.edit_message_text(f"📡 *Сетевые адаптеры:*\n\n{text}", reply_markup=kb_back(), parse_mode="Markdown")
        return

    if data == "net_wifi":
        from services.extra_functions import get_wifi_networks
        text = get_wifi_networks()
        await query.edit_message_text(f"📶 *Wi-Fi сети:*\n\n{text}", reply_markup=kb_back(), parse_mode="Markdown")
        return

    if data in ("net_ping_google", "net_ping_yandex"):
        from services.extra_functions import ping_host
        host = "8.8.8.8" if "google" in data else "ya.ru"
        result = ping_host(host)
        await query.edit_message_text(f"🏓 *Ping {host}:*\n\n```\n{result}\n```", reply_markup=kb_back(), parse_mode="Markdown")
        return

    # ── ФАЙЛЫ ─────────────────────────────────────────────
    if data == "file_desktop":
        from handlers.files import show_files_menu
        await show_files_menu(update, context)
        return

    if data == "file_downloads":
        from services.extra_functions import get_downloads_list
        text = get_downloads_list()
        await query.edit_message_text(f"⬇️ *Последние загрузки:*\n\n{text}", reply_markup=kb_back(), parse_mode="Markdown")
        return

    if data == "file_documents":
        from pathlib import Path as P
        docs = P.home() / "Documents"
        lines = []
        try:
            for f in sorted(docs.iterdir())[:12]:
                icon = "📁" if f.is_dir() else "📄"
                lines.append(f"{icon} {f.name}")
        except Exception as e:
            lines = [f"Ошибка: {e}"]
        text = "📂 *Документы:*\n\n" + "\n".join(lines)
        await query.edit_message_text(text, reply_markup=kb_back(), parse_mode="Markdown")
        return

    if data == "file_sizes":
        from services.extra_functions import get_desktop_folder_sizes
        text = get_desktop_folder_sizes()
        await query.edit_message_text(f"📦 *Размеры папок на рабочем столе:*\n\n{text}", reply_markup=kb_back(), parse_mode="Markdown")
        return

    if data == "file_search_prompt":
        context.user_data["awaiting_file_search"] = True
        await query.edit_message_text("🔍 *Введите имя или часть имени файла для поиска:*", parse_mode="Markdown")
        return

    if data.startswith("file_"):
        from handlers.files import show_files_menu, handle_file_callback
        if data == "file_menu":
            await show_files_menu(update, context)
        else:
            await handle_file_callback(update, context)
        return

    # ── ПРИЛОЖЕНИЯ ────────────────────────────────────────
    APP_MAP = {
        "app_chrome":     "chrome",
        "app_telegram":   "telegram",
        "app_vscode":     "vscode",
        "app_explorer":   "explorer",
        "app_calc":       "calc",
        "app_notepad":    "notepad",
        "app_mspaint":    "mspaint",
        "app_control":    "control",
        "app_cmd":        "cmd",
        "app_powershell": "powershell",
        "app_taskmgr":    "taskmgr",
        "app_defender":   "defender",
        "app_youtube":    "youtube",
    }
    if data in APP_MAP:
        from services.extra_functions import quick_launch
        result = quick_launch(APP_MAP[data])
        await query.answer(result, show_alert=False)
        return

    # ── УПРАВЛЕНИЕ ПК — ГОРЯЧИЕ КЛАВИШИ ──────────────────
    KEY_MAP = {
        "key_enter":  ["enter"],
        "key_escape": ["escape"],
        "key_win":    ["win"],
        "key_altf4":  ["alt", "f4"],
        "key_ctrlc":  ["ctrl", "c"],
        "key_ctrlv":  ["ctrl", "v"],
        "key_alttab": ["alt", "tab"],
        "key_wind":   ["win", "d"],
    }
    if data in KEY_MAP:
        import pyautogui
        keys = KEY_MAP[data]
        try:
            pyautogui.hotkey(*keys)
            await query.answer(f"⌨ {'+'.join(keys).upper()} нажато")
        except Exception as e:
            await query.answer(f"Ошибка: {e}", show_alert=True)
        return

    # ── ПУЛЬТ МЫШИ ────────────────────────────────────────
    if data == "menu_remote":
        from handlers.remote_control import show_remote_control_menu
        await show_remote_control_menu(update, context)
        return

    if data.startswith("mouse_"):
        from handlers.remote_control import handle_remote_callback
        await handle_remote_callback(update, context)
        return

    # ── СКРИНШОТ ──────────────────────────────────────────
    if data.startswith("scr_"):
        idx_str = data.replace("scr_", "")
        idx = int(idx_str) if idx_str != "all" else 0
        from handlers.system_commands import send_screenshot
        await send_screenshot(update, context, monitor_index=idx)
        return

    # ── ПРОЦЕССЫ ──────────────────────────────────────────
    if data in ("menu_procs",) or data.startswith("procs_"):
        from handlers.process_commands import show_processes
        sort = "cpu" if "cpu" in data else "memory"
        await show_processes(update, context, sort_by=sort)
        return

    if data.startswith("kill_proc_"):
        from handlers.process_commands import handle_kill_callback
        await handle_kill_callback(update, context)
        return

    # ── НАПОМИНАНИЯ ───────────────────────────────────────
    if data == "menu_reminders":
        from scheduler import reminder_manager
        active = reminder_manager.get_active_reminders(chat_id)
        if not active:
            text = "⏰ *Напоминания:*\n\nАктивных нет.\n_«напомни через 20 мин проверить почту»_"
        else:
            text = "⏰ *Активные напоминания:*\n\n"
            for r in active:
                text += f"• «{r['text']}» — `{r['next_trigger_at']}`\n"
        await query.edit_message_text(text, reply_markup=kb_back(), parse_mode="Markdown")
        return

    # ── ИИ СПРАВКА ────────────────────────────────────────
    if data == "menu_ai_help":
        text = (
            "🤖 *Возможности ИИ-агента Jarvis:*\n\n"
            "• *Голос:* отправьте голосовое сообщение с любым поручением\n"
            "• *Многошаговые задачи:* «Перейди на 1 стол, открой музыку, сделай скриншот»\n"
            "• *Умный поиск приложений:* находит по сленгу и опечаткам\n"
            "• *Напоминания:* «напомни через 20 мин проверить почту»\n"
            "• *Интернет-поиск:* «найди в википедии Python»"
        )
        await query.edit_message_text(text, reply_markup=kb_back(), parse_mode="Markdown")
        return


def get_main_keyboard():
    """Алиас для обратной совместимости."""
    return kb_back()


def get_screenshot_keyboard() -> InlineKeyboardMarkup:
    """Алиас для обратной совместимости."""
    return kb_screenshot()
