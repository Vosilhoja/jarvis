"""
Главный модуль меню Jarvis.
Архитектура: ReplyKeyboardMarkup (нижняя клавиатура).
- Нажал категорию → клавиатура меняется
- Нажал функцию → выполняется или бот просит ввод
- Нажал "⬅️ Назад" → возврат в главное меню
"""
import os
import re
import logging
import subprocess
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import ContextTypes

from handlers.auth import restricted

logger = logging.getLogger("jarvis")


# ═══════════════════════════════════════════════════════════
#  УТИЛИТЫ БЕЗОПАСНОЙ ОТПРАВКИ
# ═══════════════════════════════════════════════════════════

def _escape_md(text: str) -> str:
    """Экранирует спецсимволы Markdown v1 в пользовательских данных."""
    # Экранируем только символы вне *bold*, _italic_, `code` блоков
    return re.sub(r'([_\*\[\]\(\)~`>#+\-=|{}.!])', r'\\\1', str(text))


async def safe_reply(update: Update, text: str, reply_markup=None, parse_mode: str = "Markdown") -> None:
    """Отправляет сообщение с Markdown. При ошибке парсинга — повторяет без форматирования."""
    msg = update.message or (update.callback_query and update.callback_query.message if update.callback_query else None)
    if not msg:
        return
    try:
        await msg.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except Exception as e:
        if "parse" in str(e).lower() or "entity" in str(e).lower():
            # Убираем Markdown-форматирование и повторяем
            plain = re.sub(r'[*_`]', '', text)
            try:
                await msg.reply_text(plain, reply_markup=reply_markup)
            except Exception as e2:
                logger.error(f"safe_reply: не смогли отправить сообщение: {e2}")
        else:
            raise


async def safe_edit(update: Update, text: str, reply_markup=None, parse_mode: str = "Markdown") -> None:
    """Редактирует сообщение с Markdown. При ошибке — без форматирования."""
    cq = update.callback_query
    if not cq:
        return
    try:
        await cq.edit_message_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except Exception as e:
        if "parse" in str(e).lower() or "entity" in str(e).lower():
            plain = re.sub(r'[*_`]', '', text)
            try:
                await cq.edit_message_text(plain, reply_markup=reply_markup)
            except Exception as e2:
                logger.error(f"safe_edit: не смогли отредактировать: {e2}")
        else:
            raise


# ═══════════════════════════════════════════════════════════
#  КЛАВИАТУРЫ (ReplyKeyboardMarkup)
# ═══════════════════════════════════════════════════════════

def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Главная нижняя клавиатура со всеми категориями."""
    keyboard = [
        [KeyboardButton("🖥 Система"),       KeyboardButton("🎵 Медиа / Звук")],
        [KeyboardButton("📁 Файлы"),          KeyboardButton("🌐 Сеть")],
        [KeyboardButton("🚀 Приложения"),     KeyboardButton("🖱 Управление ПК")],
        [KeyboardButton("📸 Скриншот"),       KeyboardButton("📋 Процессы")],
        [KeyboardButton("🧰 Инструменты"),    KeyboardButton("⏰ Напоминания")],
        [KeyboardButton("🤖 ИИ-чат")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)


def get_system_reply_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура управления системой."""
    keyboard = [
        [KeyboardButton("📊 Инфо о системе"),  KeyboardButton("🌡 Температура")],
        [KeyboardButton("🔋 Аккумулятор"),      KeyboardButton("🖥 Разрешение")],
        [KeyboardButton("🌐 IP-адреса"),        KeyboardButton("📋 Буфер обмена")],
        [KeyboardButton("💾 Диски"),            KeyboardButton("🧠 Железо")],
        [KeyboardButton("💡 Яркость"),          KeyboardButton("⌨ Подсветка клавы")],
        [KeyboardButton("🔇 Режим Тихий час"), KeyboardButton("🧹 Очистить %TEMP%")],
        [KeyboardButton("🛡 Включить охрану"), KeyboardButton("🛑 Снять с охраны")],
        [KeyboardButton("🗑 Очистить корзину"),KeyboardButton("🔒 Заблокировать")],
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
        [KeyboardButton("🎙 Установить громкость"),                             KeyboardButton("⏹ Стоп")],
        [KeyboardButton("⬅️ Назад в меню")],
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
        [KeyboardButton("🛤 Трассировка"),    KeyboardButton("⚡ Скорость сети")],
        [KeyboardButton("🧹 Flush DNS"),      KeyboardButton("🌐 ipconfig")],
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
        [KeyboardButton("📦 Все программы ПК"),KeyboardButton("🔍 Найти программу")],
        [KeyboardButton("⬅️ Назад в меню")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)


def get_control_reply_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура клавиш и окон ПК с динамическими столами."""
    from services.desktops_control import get_desktop_count, get_current_desktop_number
    count = get_desktop_count()
    current = get_current_desktop_number()

    keyboard = [
        [KeyboardButton("⌨ Enter"),           KeyboardButton("⌨ Escape"),    KeyboardButton("⌨ Win")],
        [KeyboardButton("⌨ Alt+Tab"),         KeyboardButton("⌨ Alt+F4"),    KeyboardButton("⌨ Win+D")],
        [KeyboardButton("⌨ Ctrl+C"),          KeyboardButton("⌨ Ctrl+V")],
    ]

    # Динамические кнопки переключения столов с отметкой текущего активного
    desk_row = []
    for i in range(1, count + 1):
        mark = "📍" if i == current else "🎛"
        desk_row.append(KeyboardButton(f"{mark} Стол {i}"))
        if len(desk_row) == 3:
            keyboard.append(desk_row)
            desk_row = []
    if desk_row:
        keyboard.append(desk_row)

    keyboard.append([KeyboardButton("➕ Новый стол"), KeyboardButton("🖱 Пульт мыши")])
    keyboard.append([KeyboardButton("🛡 Включить охрану"), KeyboardButton("🛑 Снять с охраны")])
    keyboard.append([KeyboardButton("⬅️ Назад в меню")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)


def get_screenshot_reply_keyboard() -> ReplyKeyboardMarkup:
    """
    Клавиатура скриншота — динамически считывает реальное кол-во столов из реестра
    и выводит кнопки для каждого из них.
    """
    from services.desktops_control import get_desktop_count, get_current_desktop_number
    desktop_count = get_desktop_count()
    current = get_current_desktop_number()

    keyboard = [
        [KeyboardButton("📸 Весь экран"), KeyboardButton("📸 Все столы подряд")],
    ]

    row = []
    for i in range(1, desktop_count + 1):
        mark = "📍" if i == current else "🖥"
        row.append(KeyboardButton(f"{mark} Снимок Стола {i}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([KeyboardButton("📝 Выбрать столы вручную")])
    keyboard.append([KeyboardButton("⬅️ Назад в меню")])

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)


def _get_virtual_desktop_count() -> int:
    """Читает кол-во виртуальных рабочих столов из реестра Windows."""
    from services.desktops_control import get_desktop_count
    return get_desktop_count()


def get_tools_reply_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("🔐 Пароль"), KeyboardButton("📷 QR-код"), KeyboardButton("🆔 UUID")],
        [KeyboardButton("🗣 Сказать время"), KeyboardButton("🎲 Кубик"), KeyboardButton("🪙 Монета")],
        [KeyboardButton("🪟 Окна"), KeyboardButton("🎯 Активное окно"), KeyboardButton("🖥 Свернуть всё")],
        [KeyboardButton("🌙 Тема Windows"), KeyboardButton("🌙 Ночной свет"), KeyboardButton("🔋 Отчет батареи")],
        [KeyboardButton("🔌 USB"), KeyboardButton("🖨 Принтеры"), KeyboardButton("🚀 Автозагрузка ПО")],
        [KeyboardButton("🛡 Firewall"), KeyboardButton("🛡 Defender"), KeyboardButton("⏱ Простой")],
        [KeyboardButton("🗑 Корзина (счёт)"), KeyboardButton("🔄 Restart Explorer")],
        [KeyboardButton("📌 Автозапуск Jarvis"), KeyboardButton("⬅️ Назад в меню")],
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
    logger.info(f"Вызов /start от пользователя id={user.id}")
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
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════

async def _ask_for_number(update, context, state_key: str, prompt: str):
    """Универсальная функция: устанавливает ожидание числового ввода и просит пользователя."""
    context.user_data[state_key] = True
    await update.message.reply_text(prompt, parse_mode="Markdown")


_AWAITING_INPUT_KEYS = (
    "awaiting_screenshot_choice", "awaiting_brightness",
    "awaiting_volume", "awaiting_file_search", "awaiting_app_search",
    "awaiting_qr",
)


def _clear_awaiting(context: ContextTypes.DEFAULT_TYPE) -> None:
    for key in _AWAITING_INPUT_KEYS:
        context.user_data.pop(key, None)


def _looks_like_keyboard_button(text: str) -> bool:
    if text.startswith(("📸", "🖥", "🎛", "📍", "⬅️", "🚀", "🧰", "🤖", "📋", "⏰",
                        "🖱", "🌐", "📁", "🎵", "🔑", "⌨", "🧹", "🛤", "⚡", "🏓",
                        "🔐", "📷", "🆔", "🗣", "🎲", "🪙", "🪟", "🎯", "🌙", "🔋",
                        "🔌", "🖨", "🛡", "⏱", "🗑", "🔄", "📌", "📦", "🔍")):
        return True
    return False


def parse_desktop_selection(text: str):
    """
    Разбирает ввод номеров столов.
    Возвращает 'all', список int, или None если это не выбор столов.
    """
    raw = (text or "").strip().lower()
    if raw in ("все", "all", "*", "всё"):
        return "all"
    if _looks_like_keyboard_button(text):
        return None
    parts = [p.strip() for p in re.split(r"[,;]+", raw) if p.strip()]
    if not parts:
        return None
    nums = []
    for p in parts:
        if p.isdigit():
            nums.append(int(p))
        else:
            return None
    return nums or None


async def send_desktop_screenshots(update: Update, context: ContextTypes.DEFAULT_TYPE, selection) -> None:
    from services.desktops_control import get_desktop_count
    from handlers.system_commands import send_screenshot
    from services.screenshot import take_multiple_desktops_screenshots

    count = get_desktop_count()
    if selection == "all":
        desks = list(range(1, count + 1))
    else:
        valid = [n for n in selection if 1 <= n <= count]
        invalid = [n for n in selection if n not in valid]
        if invalid:
            await update.message.reply_text(
                f"⚠️ Столов {', '.join(map(str, invalid))} нет (сейчас 1–{count})."
            )
        desks = valid

    if not desks:
        await update.message.reply_text(f"⚠️ Нет подходящих номеров. Сейчас рабочих столов: {count}.")
        return

    if len(desks) == 1:
        await send_screenshot(update, context, monitor_index=0, desktop_num=desks[0])
        return

    await update.message.reply_text(f"📸 Делаю скриншоты столов: {', '.join(map(str, desks))}...")
    try:
        results = take_multiple_desktops_screenshots(desks, monitor_index=0)
        for desk_num, buf in results:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=buf,
                caption=f"📸 Снимок: Рабочий стол {desk_num}",
            )
        await update.message.reply_text("✅ Скриншоты готовы, вы на исходном рабочем столе.")
    except Exception as e:
        logger.error("Ошибка пакетного скриншота: %s", e, exc_info=True)
        await update.message.reply_text(f"⚠️ Ошибка скриншота: {e}")


# ═══════════════════════════════════════════════════════════
#  ОБРАБОТЧИК НАЖАТИЙ НИЖНЕЙ КЛАВИАТУРЫ (ReplyKeyboard)
# ═══════════════════════════════════════════════════════════

async def handle_reply_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Обрабатывает нажатия ВСЕХ кнопок клавиатуры.
    Меняет саму клавиатуру при выборе категории или выполняет действие.
    Возвращает True если кнопка была обработана.
    """
    text = (update.message.text or "").strip()
    chat_id = update.effective_chat.id

    # ──────────────────────────────────────────────────────────
    # 0. КНОПКА ВОЗВРАТА (всегда перехватываем, даже в ИИ-режиме)
    # ──────────────────────────────────────────────────────────
    if text in ("⬅️ Назад в меню", "назад в меню", "главное меню", "/menu"):
        context.user_data.pop("ai_mode", None)
        context.user_data.pop("menu_section", None)
        _clear_awaiting(context)
        await update.message.reply_text(
            "🏠 *Главное меню:* выберите категорию",
            reply_markup=get_main_reply_keyboard(),
            parse_mode="Markdown"
        )
        return True

    # ──────────────────────────────────────────────────────────
    # 0.5 ПРИОРИТЕТ: ожидание числового/текстового ввода
    # (проверяется ДО ai_mode, чтобы ИИ не перехватывал ввод)
    # ──────────────────────────────────────────────────────────

    # Ожидание выбора рабочих столов для скриншота
    if context.user_data.get("awaiting_screenshot_choice"):
        selection = parse_desktop_selection(text)
        if selection is not None:
            context.user_data.pop("awaiting_screenshot_choice", None)
            await send_desktop_screenshots(update, context, selection)
            return True
        if _looks_like_keyboard_button(text):
            context.user_data.pop("awaiting_screenshot_choice", None)
        else:
            await update.message.reply_text(
                "⚠️ Неверный формат. Введите числа через запятую или напишите `все`\n"
                "_Пример: `1,3` или `2`_",
                parse_mode="Markdown"
            )
            return True

    # Ожидание ввода яркости
    if context.user_data.get("awaiting_brightness"):
        context.user_data.pop("awaiting_brightness")
        try:
            level = int(text.replace("%", "").strip())
            if not (0 <= level <= 100):
                raise ValueError("out of range")
            from services.media_control import set_brightness
            res = set_brightness(level)
            await update.message.reply_text(f"💡 {res}")
        except ValueError:
            await update.message.reply_text(
                "⚠️ Введите число от 0 до 100. Например: `70`", parse_mode="Markdown"
            )
        return True

    # Ожидание ввода громкости
    if context.user_data.get("awaiting_volume"):
        context.user_data.pop("awaiting_volume")
        try:
            level = int(text.replace("%", "").strip())
            if not (0 <= level <= 100):
                raise ValueError("out of range")
            from services.media_control import set_volume_pycaw, change_volume
            ok = set_volume_pycaw(level)
            if ok:
                await update.message.reply_text(f"🎙 Громкость установлена на {level}%")
            else:
                res = change_volume("up" if level > 50 else "down", level=level)
                await update.message.reply_text(f"🎙 {res}")
        except ValueError:
            await update.message.reply_text(
                "⚠️ Введите число от 0 до 100. Например: `50`", parse_mode="Markdown"
            )
        return True

    # Ожидание поиска файла
    if context.user_data.get("awaiting_file_search"):
        context.user_data.pop("awaiting_file_search")
        from services.extra_functions import search_files
        result = search_files(text)
        await update.message.reply_text(result, parse_mode="Markdown")
        return True

    # Ожидание поиска и запуска программы
    if context.user_data.get("awaiting_app_search"):
        context.user_data.pop("awaiting_app_search")
        from core.app_resolver import app_resolver
        candidates = app_resolver.find_candidates(text, top_k=3)
        if candidates:
            best_app, score = candidates[0]
            ok = app_resolver.launch_app(best_app)
            if ok:
                await update.message.reply_text(f"🚀 Запущено: *{best_app['display_name']}* (найдено по «{text}»)", parse_mode="Markdown")
            else:
                await update.message.reply_text(f"❌ Ошибка запуска {best_app['display_name']}")
        else:
            await update.message.reply_text(f"⚠️ Программа по запросу «{text}» не найдена.")
        return True

    # Ожидание текста для QR
    if context.user_data.get("awaiting_qr"):
        if _looks_like_keyboard_button(text):
            context.user_data.pop("awaiting_qr", None)
        else:
            context.user_data.pop("awaiting_qr", None)
            from services.extra_functions import generate_qr_png
            extra = generate_qr_png(text)
            if extra.photo_bytes:
                from telegram import InputFile
                import io
                await update.message.reply_photo(
                    photo=InputFile(io.BytesIO(extra.photo_bytes), extra.photo_name or "qr.png"),
                    caption=extra.text[:900],
                )
            else:
                await update.message.reply_text(extra.text)
            return True

    if context.user_data.get("ai_mode"):
        # Если сообщение похоже на нажатие клавиаторной кнопки — рассматриваем его как навигацию
        # и выходим из режима ИИ, чтобы пользователь мог переключать меню.
        if _looks_like_keyboard_button(text):
            context.user_data.pop("ai_mode", None)
        else:
            from handlers.ai_chat import handle_ai_message
            await handle_ai_message(update, context)
            return True

    # ──────────────────────────────────────────────────────────
    # 1. ПЕРЕКЛЮЧЕНИЕ КАТЕГОРИЙ (Смена нижней клавиатуры)
    # ──────────────────────────────────────────────────────────
    CATEGORY_MAP = {
        "🖥 Система":     (get_system_reply_keyboard,   "🖥 *Меню системы:*"),
        "🎵 Медиа / Звук":(get_media_reply_keyboard,    "🎵 *Меню звука и медиа:*"),
        "📁 Файлы":       (get_files_reply_keyboard,    "📁 *Меню файлов и папок:*"),
        "🌐 Сеть":        (get_network_reply_keyboard,  "🌐 *Меню сети и интернета:*"),
        "🚀 Приложения":  (get_apps_reply_keyboard,     "🚀 *Быстрый запуск приложений:*"),
        "🖱 Управление ПК":(get_control_reply_keyboard, "🖱 *Управление окнами, клавишами и ПК:*"),
        "📸 Скриншот":    (get_screenshot_reply_keyboard,"📸 *Выберите рабочий стол для скриншота:*"),
    }

    if text in CATEGORY_MAP:
        # При переключении категории явно выход из режима ИИ, чтобы ИИ не перехватывал дальнейший ввод
        context.user_data.pop("ai_mode", None)
        keyboard_fn, title = CATEGORY_MAP[text]
        await update.message.reply_text(
            title,
            reply_markup=keyboard_fn(),
            parse_mode="Markdown"
        )
        return True

    # ──────────────────────────────────────────────────────────
    # 2. СКРИНШОТ
    # ──────────────────────────────────────────────────────────
    if text == "📸 Весь экран":
        from handlers.system_commands import send_screenshot
        await send_screenshot(update, context, monitor_index=0)
        return True

    if text == "📝 Выбрать столы вручную":
        context.user_data["awaiting_screenshot_choice"] = True
        await update.message.reply_text(
            "📝 *Введите номера рабочих столов:*\n\n"
            "• Один: `1`\n"
            "• Несколько: `1,3,5`\n"
            "• Все: `все`",
            parse_mode="Markdown"
        )
        return True

    if text == "📸 Все столы подряд":
        from services.desktops_control import get_desktop_count
        from services.screenshot import take_multiple_desktops_screenshots
        count = get_desktop_count()
        await update.message.reply_text(f"📸 Делаю скриншоты всех {count} виртуальных столов...")
        try:
            results = take_multiple_desktops_screenshots(list(range(1, count + 1)), monitor_index=0)
            for desk_num, buf in results:
                caption = f"📸 Снимок: *Рабочий стол {desk_num}*"
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=buf,
                    caption=caption,
                    parse_mode="Markdown"
                )
        except Exception as e:
            logger.error(f"Ошибка пакетного скриншота: {e}", exc_info=True)
            await update.message.reply_text(f"⚠️ Ошибка: {e}")
        await update.message.reply_text("✅ Все скриншоты сделаны, вы вернулись на свой исходный рабочий стол.")
        return True

    # Кнопки "Снимок Стола N" (с иконками 🖥 или 📍)
    m_desk = re.search(r"Стола?\s+(\d+)", text)
    if m_desk and ("Снимок" in text or "Стол" in text) and not text.startswith("🎛") and not text.startswith("📍 Стол"):
        desk_num = int(m_desk.group(1))
        from handlers.system_commands import send_screenshot
        await send_screenshot(update, context, monitor_index=0, desktop_num=desk_num)
        return True

    # ──────────────────────────────────────────────────────────
    # 3. ПРОЦЕССЫ, ИИ-ЧАТ, НАПОМИНАНИЯ
    # ──────────────────────────────────────────────────────────
    if text == "📋 Процессы":
        from handlers.process_commands import show_processes
        await show_processes(update, context, sort_by="memory")
        return True

    if text == "🤖 ИИ-чат":
        context.user_data["ai_mode"] = True
        ai_kb = ReplyKeyboardMarkup(
            [[KeyboardButton("⬅️ Назад в меню")]],
            resize_keyboard=True,
            is_persistent=True
        )
        await update.message.reply_text(
            "🤖 *Режим ИИ-диалога:*\n\n"
            "Вы можете просто писать текст или отправлять голосовые сообщения. Jarvis поймет любую задачу!\n\n"
            "_Для выхода нажмите_ ⬅️ *Назад в меню*",
            reply_markup=ai_kb,
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
    # 4. ФУНКЦИИ СИСТЕМЫ
    # ──────────────────────────────────────────────────────────
    if text == "📊 Инфо о системе":
        from handlers.system_commands import cmd_sysinfo
        await cmd_sysinfo(update, context)
        return True

    if text == "🌡 Температура":
        from services.system_info import get_cpu_temperature
        temp = get_cpu_temperature()
        if temp is not None:
            res = f"🌡 *Температура процессора:* `{temp}°C`\n\nСтатус: " + ("🟢 В норме" if temp < 75 else ("🟡 Повышенная" if temp < 85 else "🔴 Высокая!"))
        else:
            res = "🌡 Датчик температуры не вернул значение (WMI ThermalZone не передает данные на этой конфигурации)."
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
        content = get_clipboard() or "(пусто)"
        # Не используем Markdown — в буфере могут быть спецсимволы
        await update.message.reply_text(f"📋 Буфер обмена:\n\n{content}")
        return True


    # Яркость — одна кнопка → просим ввод числа
    if text == "💡 Яркость":
        await _ask_for_number(
            update, context,
            "awaiting_brightness",
            "💡 *Яркость:* введите уровень от 0 до 100\n\n_Например: 70_"
        )
        return True

    if text == "⌨ Подсветка клавы":
        from services.extra_functions import toggle_keyboard_backlight
        await update.message.reply_text(toggle_keyboard_backlight())
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

    if text in ("🛡 Включить охрану", "включить охрану"):
        from services.security_guard import security_guard
        import asyncio

        def on_guard_triggered(sx, sy, cx, cy):
            alert_text = (
                f"🚨 *ТРЕВОГА! РЕЖИМ ОХРАНЫ СРАБОТАЛ!*\n\n"
                f"Зафиксировано движение мыши!\n"
                f"📍 Исходные координаты: `({sx}, {sy})`\n"
                f"📍 Новые координаты: `({cx}, {cy})`\n\n"
                f"🔒 *Компьютер немедленно заблокирован!*"
            )
            try:
                asyncio.run_coroutine_threadsafe(
                    context.bot.send_message(chat_id=chat_id, text=alert_text, parse_mode="Markdown"),
                    context.application.loop
                )
            except Exception as e:
                logger.error(f"Не удалось отправить тревожное сообщение: {e}")

        msg = security_guard.start_guard(on_trigger_callback=on_guard_triggered, delay_sec=5)
        await update.message.reply_text(msg, parse_mode="Markdown")
        return True

    if text in ("🛑 Снять с охраны", "снять с охраны", "выключить охрану"):
        from services.security_guard import security_guard
        msg = security_guard.stop_guard()
        await update.message.reply_text(msg, parse_mode="Markdown")
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
    # 5. ФУНКЦИИ МЕДИА И ЗВУКА
    # ──────────────────────────────────────────────────────────
    if text in ("⏮ Назад трек",):
        from services.media_control import media_prev
        media_prev()
        await update.message.reply_text("⏮ Предыдущий трек")
        return True

    if text in ("⏯ Play/Pause",):
        from services.media_control import media_play_pause
        media_play_pause()
        await update.message.reply_text("⏯ Play/Pause")
        return True

    if text in ("⏭ След трек",):
        from services.media_control import media_next
        media_next()
        await update.message.reply_text("⏭ Следующий трек")
        return True

    if text == "⏹ Стоп":
        from services.media_control import media_stop
        media_stop()
        await update.message.reply_text("⏹ Остановлено")
        return True

    if text == "🔉 Тише (-10%)":
        from services.media_control import change_volume
        res = change_volume("down")
        await update.message.reply_text(f"🔉 {res}")
        return True

    if text == "🔊 Громче (+10%)":
        from services.media_control import change_volume
        res = change_volume("up")
        await update.message.reply_text(f"🔊 {res}")
        return True

    if text == "🔇 Mute":
        from services.media_control import change_volume
        res = change_volume("mute")
        await update.message.reply_text(f"🔇 {res}")
        return True

    # Адаптивный ввод громкости — одна кнопка
    if text == "🎙 Установить громкость":
        await _ask_for_number(
            update, context,
            "awaiting_volume",
            "🎙 *Громкость:* введите значение от 0 до 100\n\n_Например: 50_"
        )
        return True

    # Пресеты громкости (🎚 Звук X%)
    if text.startswith("🎚 Звук "):
        lvl_str = text.replace("🎚 Звук ", "").replace("%", "").strip()
        try:
            lvl = int(lvl_str)
            from services.media_control import set_volume_pycaw, change_volume
            ok = set_volume_pycaw(lvl)
            if ok:
                await update.message.reply_text(f"🎚 Громкость установлена на {lvl}%")
            else:
                res = change_volume("up" if lvl > 50 else "down", level=lvl)
                await update.message.reply_text(f"🎚 {res}")
        except Exception as e:
            await update.message.reply_text(f"Ошибка: {e}")
        return True

    if text == "🎬 YouTube":
        import webbrowser
        webbrowser.open("https://www.youtube.com")
        await update.message.reply_text("🎬 Открываю YouTube в браузере")
        return True

    # ──────────────────────────────────────────────────────────
    # 6. ФУНКЦИИ ФАЙЛОВ
    # ──────────────────────────────────────────────────────────
    if text == "🗂 Рабочий стол":
        from handlers.files import show_files_menu
        await show_files_menu(update, context)
        return True

    if text == "⬇️ Загрузки":
        from services.extra_functions import get_downloads_list
        raw = get_downloads_list()
        # Экранируем имена файлов (могут содержать [ ] _ * и т.д.)
        safe_list = re.sub(r'([_\*\[\]])', r'\\\1', raw)
        await safe_reply(update, f"⬇️ *Последние загрузки:*\n\n{safe_list}")
        return True

    if text == "📂 Документы":
        from pathlib import Path as P
        docs = P.home() / "Documents"
        lines = []
        try:
            for f in sorted(docs.iterdir())[:12]:
                icon = "📁" if f.is_dir() else "📄"
                safe_name = re.sub(r'([_\*\[\]])', r'\\\1', f.name)
                lines.append(f"{icon} {safe_name}")
        except Exception as e:
            lines = [f"Ошибка: {e}"]
        await safe_reply(update, "📂 *Документы:*\n\n" + "\n".join(lines))
        return True

    if text == "📦 Размер папок":
        from services.extra_functions import get_desktop_folder_sizes
        raw = get_desktop_folder_sizes()
        safe_sizes = re.sub(r'([_\*\[\]])', r'\\\1', raw)
        await safe_reply(update, f"📦 *Размеры папок на рабочем столе:*\n\n{safe_sizes}")
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
    # 7. ФУНКЦИИ СЕТИ
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
        await safe_reply(update, f"📡 *Сетевые адаптеры:*\n\n{get_network_adapters()}")
        return True

    if text == "📶 Wi-Fi сети":
        from services.extra_functions import get_wifi_networks
        await safe_reply(update, f"📶 *Wi-Fi сети:*\n\n{get_wifi_networks()}")
        return True

    if text == "🏓 Ping 8.8.8.8":
        from services.extra_functions import ping_host
        await safe_reply(update, f"🏓 *Ping 8.8.8.8:*\n\n```\n{ping_host('8.8.8.8')}\n```")
        return True

    if text == "🏓 Ping Яндекс":
        from services.extra_functions import ping_host
        await safe_reply(update, f"🏓 *Ping ya.ru:*\n\n```\n{ping_host('ya.ru')}\n```")
        return True

    # ──────────────────────────────────────────────────────────
    # 8. БЫСТРЫЙ ЗАПУСК ПРИЛОЖЕНИЙ
    # ──────────────────────────────────────────────────────────
    APP_FAST_MAP = {
        "🌐 Chrome":          "chrome",
        "📨 Telegram":        "telegram",
        "💻 VS Code":         "vscode",
        "🧮 Калькулятор":     "calc",
        "📝 Блокнот":         "notepad",
        "🎨 Paint":           "mspaint",
        "⚙️ Панель упр.":     "control",
        "💻 CMD":             "cmd",
        "🔵 PowerShell":      "powershell",
        "📊 Диспетчер задач": "taskmgr",
        "🛡 Защитник Win":    "defender",
        "📁 Проводник":       "explorer",
    }
    if text in APP_FAST_MAP:
        from services.extra_functions import quick_launch
        res = quick_launch(APP_FAST_MAP[text])
        await update.message.reply_text(f"🚀 {res}")
        return True

    if text == "📦 Все программы ПК":
        from core.app_resolver import app_resolver
        apps = app_resolver.apps_index
        total = len(apps)
        names = sorted({a.get("display_name", "") for a in apps if a.get("display_name")})
        preview = names[:35]
        text_msg = (
            f"📦 *Установленные программы на ПК (всего найдено: {total}):*\n\n"
            + "\n".join(f"• {n}" for n in preview)
            + f"\n\n_Показаны первые 35 из {total}. Чтобы запустить любую: просто напишите ее название или воспользуйтесь кнопкой «🔍 Найти программу»._"
        )
        await safe_reply(update, text_msg)
        return True

    if text == "🔍 Найти программу":
        context.user_data["awaiting_app_search"] = True
        await update.message.reply_text("🔍 *Введите название или часть имени программы для запуска:*", parse_mode="Markdown")
        return True

    # ──────────────────────────────────────────────────────────
    # 9. УПРАВЛЕНИЕ ПК И ГОРЯЧИЕ КЛАВИШИ
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

    # Динамическое переключение на любой рабочий стол (🎛 Стол N / 📍 Стол N)
    m_switch = re.search(r"Стол\s+(\d+)", text)
    if m_switch and ("🎛" in text or "📍" in text or "стол" in text.lower()) and "снимок" not in text.lower() and "новый" not in text.lower():
        desk_num = int(m_switch.group(1))
        from services.desktops_control import switch_to_desktop_number
        switch_to_desktop_number(desk_num)
        await update.message.reply_text(f"🎛 Переключено на Рабочий стол {desk_num}")
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

    if data == "main_menu":
        await query.edit_message_text(
            "🏠 *Главное меню:* выберите категорию",
            reply_markup=None,
            parse_mode="Markdown"
        )
        await query.message.reply_text(
            "🏠 Вы в главном меню",
            reply_markup=get_main_reply_keyboard()
        )
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
        os.system("shutdown /a")
        await query.edit_message_text("✅ Выключение/перезагрузка отменена!")
        return

    if data == "sys_info":
        from handlers.system_commands import cmd_sysinfo
        await cmd_sysinfo(update, context)
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

    if data in ("procs_sort_ram", "procs_sort_cpu") or data.startswith("procs_refresh_"):
        from handlers.process_commands import show_processes
        sort_by = "cpu" if "cpu" in data else "memory"
        await show_processes(update, context, sort_by=sort_by)
        return

    if data.startswith("scr_"):
        idx_str = data.replace("scr_", "")
        idx = int(idx_str) if idx_str != "all" else 0
        from handlers.system_commands import send_screenshot
        await send_screenshot(update, context, monitor_index=idx)
        return
