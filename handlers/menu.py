"""
Главный модуль меню Jarvis.
Вся навигация построена на ReplyKeyboardMarkup (нижняя клавиатура):
- Нажал "🖥 Система" -> клавиатура меняется на кнопки системы
- Нажал "🎵 Медиа / Звук" -> клавиатура меняется на кнопки медиа
- Нажал "📁 Файлы" -> клавиатура меняется на кнопки файлов
- Нажал "🌐 Сеть" -> клавиатура меняется на кнопки сети
- Нажал "🚀 Приложения" -> клавиатура меняется на кнопки приложений
- Нажал "🖱 Управление ПК" -> клавиатура меняется на кнопки управления ПК
- Нажал "⬅️ Назад в меню" -> клавиатура возвращается к списку категорий
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
#  НИЖНИЕ КЛАВИАТУРЫ (ReplyKeyboardMarkup)
# ═══════════════════════════════════════════════════════════

def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Главная нижняя клавиатура со всеми категориями."""
    keyboard = [
        [KeyboardButton("🖥 Система"),       KeyboardButton("🎵 Медиа / Звук")],
        [KeyboardButton("📁 Файлы"),          KeyboardButton("🌐 Сеть")],
        [KeyboardButton("🚀 Приложения"),     KeyboardButton("🖱 Управление ПК")],
        [KeyboardButton("📸 Скриншот"),       KeyboardButton("📋 Процессы")],
        [KeyboardButton("🤖 ИИ-чат"),         KeyboardButton("⏰ Напоминания")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)


def get_system_reply_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура управления системой."""
    keyboard = [
        [KeyboardButton("📊 Инфо о системе"),  KeyboardButton("🌡 Температура")],
        [KeyboardButton("🔋 Аккумулятор"),      KeyboardButton("🖥 Разрешение")],
        [KeyboardButton("🌐 IP-адреса"),        KeyboardButton("📋 Буфер обмена")],
        [KeyboardButton("💡 Яркость +"),        KeyboardButton("💡 Яркость —")],
        [KeyboardButton("⌨ Подсветка клавы"),   KeyboardButton("🖥 Выкл. монитор")],
        [KeyboardButton("🔇 Режим Тихий час"),  KeyboardButton("🧹 Очистить %TEMP%")],
        [KeyboardButton("🗑 Очистить корзину"), KeyboardButton("🔒 Заблокировать")],
        [KeyboardButton("😴 Режим сна"),        KeyboardButton("🔁 Перезагрузка")],
        [KeyboardButton("⛔ Выключить ПК"),     KeyboardButton("⬅️ Назад в меню")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)


def get_media_reply_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура управления медиа и звуком."""
    keyboard = [
        [KeyboardButton("⏮ Назад трек"),     KeyboardButton("⏯ Play/Pause"), KeyboardButton("⏭ След трек")],
        [KeyboardButton("🔉 Тише (-10%)"),    KeyboardButton("🔇 Mute"),       KeyboardButton("🔊 Громче (+10%)")],
        [KeyboardButton("🎚 Звук 0%"),        KeyboardButton("🎚 Звук 25%"),   KeyboardButton("🎚 Звук 50%"), KeyboardButton("🎚 Звук 100%")],
        [KeyboardButton("⏹ Стоп"),            KeyboardButton("🎬 YouTube"),    KeyboardButton("⬅️ Назад в меню")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)


def get_files_reply_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура файлов и папок."""
    keyboard = [
        [KeyboardButton("🗂 Рабочий стол"),    KeyboardButton("⬇️ Загрузки")],
        [KeyboardButton("📂 Документы"),        KeyboardButton("📦 Размер папок")],
        [KeyboardButton("🔍 Найти файл"),       KeyboardButton("📁 Открыть Проводник")],
        [KeyboardButton("🗑 Очистить корзину"), KeyboardButton("⬅️ Назад в меню")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)


def get_network_reply_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура сети и интернета."""
    keyboard = [
        [KeyboardButton("🌍 Внешний IP"),     KeyboardButton("🏠 Локальный IP")],
        [KeyboardButton("📡 Адаптеры сети"),  KeyboardButton("📶 Wi-Fi сети")],
        [KeyboardButton("🏓 Ping 8.8.8.8"),   KeyboardButton("🏓 Ping Яндекс")],
        [KeyboardButton("⬅️ Назад в меню")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)


def get_apps_reply_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура быстрого запуска приложений."""
    keyboard = [
        [KeyboardButton("🌐 Chrome"),         KeyboardButton("📨 Telegram")],
        [KeyboardButton("💻 VS Code"),        KeyboardButton("📁 Проводник")],
        [KeyboardButton("🧮 Калькулятор"),    KeyboardButton("📝 Блокнот")],
        [KeyboardButton("🎨 Paint"),          KeyboardButton("⚙️ Панель упр.")],
        [KeyboardButton("💻 CMD"),            KeyboardButton("🔵 PowerShell")],
        [KeyboardButton("📊 Диспетчер задач"),KeyboardButton("🛡 Защитник Win")],
        [KeyboardButton("⬅️ Назад в меню")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)


def get_control_reply_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура клавиш и окон ПК."""
    keyboard = [
        [KeyboardButton("⌨ Enter"),           KeyboardButton("⌨ Escape"),    KeyboardButton("⌨ Win")],
        [KeyboardButton("⌨ Alt+Tab"),         KeyboardButton("⌨ Alt+F4"),    KeyboardButton("⌨ Win+D")],
        [KeyboardButton("⌨ Ctrl+C"),          KeyboardButton("⌨ Ctrl+V")],
        [KeyboardButton("🎛 Стол 1"),          KeyboardButton("🎛 Стол 2"),   KeyboardButton("➕ Новый стол")],
        [KeyboardButton("🖱 Пульт мыши"),      KeyboardButton("⬅️ Назад в меню")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)


# Совместимость со старым кодом
def get_reply_keyboard() -> ReplyKeyboardMarkup:
    return get_main_reply_keyboard()

def kb_system() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]])

def kb_media() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]])

def kb_files() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]])

def kb_network() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]])

def kb_apps() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]])

def kb_control() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]])

def kb_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]])


# ═══════════════════════════════════════════════════════════
#  /start КОМАНДА
# ═══════════════════════════════════════════════════════════

@restricted
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает приветствие и переключает клавиатуру на главную."""
    user = update.effective_user
    welcome_text = (
        f"🤖 *Jarvis — Ваш персональный ИИ-ассистент*\n\n"
        f"Привет, {user.first_name or 'Шеф'}! Все функции в кнопках клавиатуры внизу.\n\n"
        "Нажмите любую категорию — клавиатура откроет соответствующие кнопки!"
    )
    msg = update.message or (update.callback_query and update.callback_query.message)
    if msg:
        await msg.reply_text(welcome_text, reply_markup=get_main_reply_keyboard(), parse_mode="Markdown")
    if update.callback_query:
        await update.callback_query.answer()


# ═══════════════════════════════════════════════════════════
#  ОБРАБОТЧИК НАЖАТИЙ НИЖНЕЙ КЛАВИАТУРЫ (ReplyKeyboard)
# ═══════════════════════════════════════════════════════════

async def handle_reply_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Обрабатывает нажатия ВСЕХ кнопок клавиатуры.
    Меняет саму клавиатуру при выборе категории или выполняет действие.
    """
    text = (update.message.text or "").strip()
    lower = text.lower()
    chat_id = update.effective_chat.id

    # ──────────────────────────────────────────────────────────
    # 0. КНОПКА ВОЗВРАТА
    # ──────────────────────────────────────────────────────────
    if text in ("⬅️ Назад в меню", "назад в меню", "главное меню", "/menu"):
        await update.message.reply_text(
            "🏠 *Главное меню:* выберите категорию",
            reply_markup=get_main_reply_keyboard(),
            parse_mode="Markdown"
        )
        return True

    # ──────────────────────────────────────────────────────────
    # 1. ПЕРЕКЛЮЧЕНИЕ КАТЕГОРИЙ (Смена нижней клавиатуры)
    # ──────────────────────────────────────────────────────────
    if text == "🖥 Система":
        await update.message.reply_text(
            "🖥 *Меню системы:*",
            reply_markup=get_system_reply_keyboard(),
            parse_mode="Markdown"
        )
        return True

    if text == "🎵 Медиа / Звук":
        await update.message.reply_text(
            "🎵 *Меню звука и медиа:*",
            reply_markup=get_media_reply_keyboard(),
            parse_mode="Markdown"
        )
        return True

    if text == "📁 Файлы":
        await update.message.reply_text(
            "📁 *Меню файлов и папок:*",
            reply_markup=get_files_reply_keyboard(),
            parse_mode="Markdown"
        )
        return True

    if text == "🌐 Сеть":
        await update.message.reply_text(
            "🌐 *Меню сети и интернета:*",
            reply_markup=get_network_reply_keyboard(),
            parse_mode="Markdown"
        )
        return True

    if text == "🚀 Приложения":
        await update.message.reply_text(
            "🚀 *Быстрый запуск приложений:*",
            reply_markup=get_apps_reply_keyboard(),
            parse_mode="Markdown"
        )
        return True

    if text == "🖱 Управление ПК":
        await update.message.reply_text(
            "🖱 *Управление окнами, клавишами и ПК:*",
            reply_markup=get_control_reply_keyboard(),
            parse_mode="Markdown"
        )
        return True

    if text == "📸 Скриншот":
        from handlers.system_commands import send_screenshot
        await send_screenshot(update, context, monitor_index=0)
        return True

    if text == "📋 Процессы":
        from handlers.process_commands import show_processes
        await show_processes(update, context, sort_by="memory")
        return True

    if text == "🤖 ИИ-чат":
        await update.message.reply_text(
            "🤖 *Режим ИИ-диалога:*\n\n"
            "Вы можете просто писать текст или отправлять голосовые сообщения. Jarvis поймет любую задачу!",
            parse_mode="Markdown"
        )
        return True

    if text == "⏰ Напоминания":
        from scheduler import reminder_manager
        active = reminder_manager.get_active_reminders(chat_id)
        if not active:
            t = "⏰ *Напоминания:*\n\nАктивных напоминаний нет.\n\n_Чтобы создать: «напомни через 20 минут проверить почту»_"
        else:
            t = "⏰ *Ваши активные напоминания:*\n\n"
            for r in active:
                t += f"• «{r['text']}» — `{r['next_trigger_at']}`\n"
        await update.message.reply_text(t, parse_mode="Markdown")
        return True

    # ──────────────────────────────────────────────────────────
    # 2. ФУНКЦИИ СИСТЕМЫ
    # ──────────────────────────────────────────────────────────
    if text == "📊 Инфо о системе":
        from handlers.system_commands import cmd_sysinfo
        await cmd_sysinfo(update, context)
        return True

    if text == "🌡 Температура":
        try:
            import psutil
            temps = psutil.sensors_temperatures()
            if temps:
                lines = []
                for name, entries in temps.items():
                    for e in entries:
                        lines.append(f"🌡 {name} / {e.label or 'core'}: {e.current}°C")
                res = "🌡 *Температуры:*\n\n" + "\n".join(lines[:10])
            else:
                res = "🌡 Данные о температуре недоступны на данной материнской плате (нужен WMI/OpenHardwareMonitor)"
        except Exception as e:
            res = f"Ошибка: {e}"
        await update.message.reply_text(res, parse_mode="Markdown")
        return True

    if text == "🔋 Аккумулятор":
        from services.extra_functions import get_battery_info
        await update.message.reply_text(get_battery_info(), parse_mode="Markdown")
        return True

    if text == "🖥 Разрешение":
        from services.extra_functions import get_screen_resolution
        await update.message.reply_text(get_screen_resolution(), parse_mode="Markdown")
        return True

    if text == "🌐 IP-адреса":
        from services.extra_functions import get_local_ip, get_public_ip
        await update.message.reply_text(
            f"🌐 *IP-адреса:*\n\n🏠 Локальный: `{get_local_ip()}`\n🌍 Внешний: `{get_public_ip()}`",
            parse_mode="Markdown"
        )
        return True

    if text == "📋 Буфер обмена":
        from services.extra_functions import get_clipboard
        await update.message.reply_text(f"📋 *Буфер обмена:*\n\n```\n{get_clipboard()}\n```", parse_mode="Markdown")
        return True

    if text == "💡 Яркость +":
        from services.media_control import set_brightness
        res = set_brightness(80)
        await update.message.reply_text(f"💡 {res}")
        return True

    if text == "💡 Яркость —":
        from services.media_control import set_brightness
        res = set_brightness(30)
        await update.message.reply_text(f"💡 {res}")
        return True

    if text == "⌨ Подсветка клавы":
        from services.extra_functions import toggle_keyboard_backlight
        await update.message.reply_text(toggle_keyboard_backlight())
        return True

    if text == "🖥 Выкл. монитор":
        from services.extra_functions import turn_off_monitor
        turn_off_monitor()
        await update.message.reply_text("🖥 Монитор выключен (двигайте мышь для включения)")
        return True

    if text == "🔇 Режим Тихий час":
        from services.extra_functions import do_not_disturb_mode
        await update.message.reply_text(do_not_disturb_mode())
        return True

    if text == "🧹 Очистить %TEMP%":
        from services.system_monitor import preview_and_cleanup_temp
        count, freed_mb = preview_and_cleanup_temp()
        await update.message.reply_text(f"🧹 Очищено временных файлов: {count} (~{freed_mb} МБ)")
        return True

    if text == "🗑 Очистить корзину":
        from services.extra_functions import empty_recycle_bin
        await update.message.reply_text(empty_recycle_bin())
        return True

    if text == "🔒 Заблокировать":
        from handlers.system_commands import cmd_lock
        await cmd_lock(update, context)
        return True

    if text == "😴 Режим сна":
        from handlers.system_commands import cmd_sleep
        await cmd_sleep(update, context)
        return True

    if text == "🔁 Перезагрузка":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚠️ Да, перезагрузить!", callback_data="do_restart")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_action")]
        ])
        await update.message.reply_text("⚠️ *Вы уверены, что хотите перезагрузить компьютер?*", reply_markup=kb, parse_mode="Markdown")
        return True

    if text == "⛔ Выключить ПК":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚠️ Да, выключить ПК!", callback_data="do_shutdown")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_action")]
        ])
        await update.message.reply_text("⚠️ *Вы уверены, что хотите выключить компьютер?*", reply_markup=kb, parse_mode="Markdown")
        return True

    # ──────────────────────────────────────────────────────────
    # 3. ФУНКЦИИ МЕДИА И ЗВУКА
    # ──────────────────────────────────────────────────────────
    if text in ("⏮ Назад трек", "назад трек"):
        from services.media_control import media_prev
        media_prev()
        await update.message.reply_text("⏮ Предыдущий трек")
        return True

    if text in ("⏯ Play/Pause", "play", "pause"):
        from services.media_control import media_play_pause
        media_play_pause()
        await update.message.reply_text("⏯ Play/Pause")
        return True

    if text in ("⏭ След трек", "след трек"):
        from services.media_control import media_next
        media_next()
        await update.message.reply_text("⏭ Следующий трек")
        return True

    if text == "🔉 Тише (-10%)":
        from services.media_control import change_volume
        res = change_volume("down")
        await update.message.reply_text(res)
        return True

    if text == "🔊 Громче (+10%)":
        from services.media_control import change_volume
        res = change_volume("up")
        await update.message.reply_text(res)
        return True

    if text == "🔇 Mute":
        from services.media_control import change_volume
        res = change_volume("mute")
        await update.message.reply_text(res)
        return True

    if text.startswith("🎚 Звук "):
        lvl_str = text.replace("🎚 Звук ", "").replace("%", "")
        try:
            lvl = int(lvl_str)
            from services.media_control import set_volume_pycaw
            set_volume_pycaw(lvl)
            await update.message.reply_text(f"🎚 Громкость установлена на {lvl}%")
        except Exception as e:
            await update.message.reply_text(f"Ошибка: {e}")
        return True

    if text == "⏹ Стоп":
        from services.media_control import media_stop
        media_stop()
        await update.message.reply_text("⏹ Остановлено")
        return True

    if text == "🎬 YouTube":
        import webbrowser
        webbrowser.open("https://www.youtube.com")
        await update.message.reply_text("🎬 Открываю YouTube в браузере")
        return True

    # ──────────────────────────────────────────────────────────
    # 4. ФУНКЦИИ ФАЙЛОВ
    # ──────────────────────────────────────────────────────────
    if text == "🗂 Рабочий стол":
        from handlers.files import show_files_menu
        await show_files_menu(update, context)
        return True

    if text == "⬇️ Загрузки":
        from services.extra_functions import get_downloads_list
        await update.message.reply_text(f"⬇️ *Последние загрузки:*\n\n{get_downloads_list()}", parse_mode="Markdown")
        return True

    if text == "📂 Документы":
        from pathlib import Path as P
        docs = P.home() / "Documents"
        lines = []
        try:
            for f in sorted(docs.iterdir())[:12]:
                icon = "📁" if f.is_dir() else "📄"
                lines.append(f"{icon} {f.name}")
        except Exception as e:
            lines = [f"Ошибка: {e}"]
        await update.message.reply_text("📂 *Документы:*\n\n" + "\n".join(lines), parse_mode="Markdown")
        return True

    if text == "📦 Размер папок":
        from services.extra_functions import get_desktop_folder_sizes
        await update.message.reply_text(f"📦 *Размеры папок на рабочем столе:*\n\n{get_desktop_folder_sizes()}", parse_mode="Markdown")
        return True

    if text == "🔍 Найти файл":
        context.user_data["awaiting_file_search"] = True
        await update.message.reply_text("🔍 *Напишите имя или часть названия файла для поиска:*", parse_mode="Markdown")
        return True

    if text == "📁 Открыть Проводник":
        os.system("explorer.exe")
        await update.message.reply_text("📁 Проводник запущен")
        return True

    # ──────────────────────────────────────────────────────────
    # 5. ФУНКЦИИ СЕТИ
    # ──────────────────────────────────────────────────────────
    if text == "🌍 Внешний IP":
        from services.extra_functions import get_public_ip
        await update.message.reply_text(f"🌍 *Внешний IP:* `{get_public_ip()}`", parse_mode="Markdown")
        return True

    if text == "🏠 Локальный IP":
        from services.extra_functions import get_local_ip
        await update.message.reply_text(f"🏠 *Локальный IP:* `{get_local_ip()}`", parse_mode="Markdown")
        return True

    if text == "📡 Адаптеры сети":
        from services.extra_functions import get_network_adapters
        await update.message.reply_text(f"📡 *Сетевые адаптеры:*\n\n{get_network_adapters()}", parse_mode="Markdown")
        return True

    if text == "📶 Wi-Fi сети":
        from services.extra_functions import get_wifi_networks
        await update.message.reply_text(f"📶 *Wi-Fi сети:*\n\n{get_wifi_networks()}", parse_mode="Markdown")
        return True

    if text == "🏓 Ping 8.8.8.8":
        from services.extra_functions import ping_host
        await update.message.reply_text(f"🏓 *Ping 8.8.8.8:*\n\n```\n{ping_host('8.8.8.8')}\n```", parse_mode="Markdown")
        return True

    if text == "🏓 Ping Яндекс":
        from services.extra_functions import ping_host
        await update.message.reply_text(f"🏓 *Ping ya.ru:*\n\n```\n{ping_host('ya.ru')}\n```", parse_mode="Markdown")
        return True

    # ──────────────────────────────────────────────────────────
    # 6. БЫСТРЫЙ ЗАПУСК ПРИЛОЖЕНИЙ
    # ──────────────────────────────────────────────────────────
    APP_FAST_MAP = {
        "🌐 Chrome":         "chrome",
        "📨 Telegram":       "telegram",
        "💻 VS Code":        "vscode",
        "🧮 Калькулятор":    "calc",
        "📝 Блокнот":        "notepad",
        "🎨 Paint":          "mspaint",
        "⚙️ Панель упр.":    "control",
        "💻 CMD":            "cmd",
        "🔵 PowerShell":     "powershell",
        "📊 Диспетчер задач":"taskmgr",
        "🛡 Защитник Win":   "defender",
    }
    if text in APP_FAST_MAP:
        from services.extra_functions import quick_launch
        res = quick_launch(APP_FAST_MAP[text])
        await update.message.reply_text(f"🚀 {res}")
        return True

    # ──────────────────────────────────────────────────────────
    # 7. УПРАВЛЕНИЕ ПК И ГОРЯЧИЕ КЛАВИШИ
    # ──────────────────────────────────────────────────────────
    KEY_ACTION_MAP = {
        "⌨ Enter":   ["enter"],
        "⌨ Escape":  ["escape"],
        "⌨ Win":     ["win"],
        "⌨ Alt+Tab": ["alt", "tab"],
        "⌨ Alt+F4":  ["alt", "f4"],
        "⌨ Win+D":   ["win", "d"],
        "⌨ Ctrl+C":  ["ctrl", "c"],
        "⌨ Ctrl+V":  ["ctrl", "v"],
    }
    if text in KEY_ACTION_MAP:
        import pyautogui
        keys = KEY_ACTION_MAP[text]
        try:
            pyautogui.hotkey(*keys)
            await update.message.reply_text(f"⌨ Нажато: `{' + '.join(keys).upper()}`", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"Ошибка: {e}")
        return True

    if text == "🎛 Стол 1":
        from services.desktops_control import switch_to_desktop_number
        switch_to_desktop_number(1)
        await update.message.reply_text("🎛 Переключено на Рабочий стол 1")
        return True

    if text == "🎛 Стол 2":
        from services.desktops_control import switch_to_desktop_number
        switch_to_desktop_number(2)
        await update.message.reply_text("🎛 Переключено на Рабочий стол 2")
        return True

    if text == "➕ Новый стол":
        from services.desktops_control import create_virtual_desktop
        create_virtual_desktop()
        await update.message.reply_text("➕ Создан новый виртуальный рабочий стол")
        return True

    if text == "🖱 Пульт мыши":
        from handlers.remote_control import show_remote_control_menu
        await show_remote_control_menu(update, context)
        return True

    return False


# ═══════════════════════════════════════════════════════════
#  ЦЕНТРАЛЬНЫЙ РОУТЕР CallbackQuery (Inline кнопки)
# ═══════════════════════════════════════════════════════════

@restricted
async def menu_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает Inline кнопки подтверждений и действий."""
    query = update.callback_query
    data = query.data
    chat_id = update.effective_chat.id

    await query.answer()

    if data == "cancel_action":
        await query.edit_message_text("🚫 Действие отменено.")
        return

    if data == "do_shutdown":
        from handlers.system_commands import cmd_shutdown_execute
        await cmd_shutdown_execute(update, context)
        return

    if data == "do_restart":
        from handlers.system_commands import cmd_restart_execute
        await cmd_restart_execute(update, context)
        return

    if data.startswith("mouse_"):
        from handlers.remote_control import handle_remote_callback
        await handle_remote_callback(update, context)
        return

    if data.startswith("file_"):
        from handlers.files import show_files_menu, handle_file_callback
        if data == "file_menu":
            await show_files_menu(update, context)
        else:
            await handle_file_callback(update, context)
        return

    if data.startswith("kill_proc_"):
        from handlers.process_commands import handle_kill_callback
        await handle_kill_callback(update, context)
        return

    if data.startswith("scr_"):
        idx_str = data.replace("scr_", "")
        idx = int(idx_str) if idx_str != "all" else 0
        from handlers.system_commands import send_screenshot
        await send_screenshot(update, context, monitor_index=idx)
        return
