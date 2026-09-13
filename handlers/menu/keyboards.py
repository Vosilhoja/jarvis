from telegram import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

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

    desk_row = []
    for i in range(1, count + 1):
        mark = "📍" if i == current else "🎛"
        desk_row.append(KeyboardButton(f"{mark} Стол {i}"))
        if len(desk_row) == 3:
            keyboard.append(desk_row)
            desk_row = []
    if desk_row:
        keyboard.append(desk_row)

    keyboard.append([KeyboardButton("➕ Новый стол"), KeyboardButton("🗑 Удалить текущий стол")])
    keyboard.append([KeyboardButton("🖱 Пульт мыши")])
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

def get_tools_reply_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("📅 Планировщик задач"), KeyboardButton("🖥 Диспетчер устройств")],
        [KeyboardButton("📋 Просмотр событий"),   KeyboardButton("🔧 Панель управления")],
        [KeyboardButton("🔐 Пароль"), KeyboardButton("📷 QR-код"), KeyboardButton("🆔 UUID")],
        [KeyboardButton("🗣 Сказать время"), KeyboardButton("🎲 Кубик"), KeyboardButton("🪙 Монета")],
        [KeyboardButton("🎯 Активное окно"), KeyboardButton("🖥 Свернуть всё")],
        [KeyboardButton("🌙 Тема Windows"), KeyboardButton("🌙 Ночной свет"), KeyboardButton("🔋 Отчет батареи")],
        [KeyboardButton("🔌 USB"), KeyboardButton("🖨 Принтеры"), KeyboardButton("🚀 Автозагрузка ПО")],
        [KeyboardButton("🛡 Firewall"), KeyboardButton("🛡 Defender"), KeyboardButton("⏱ Простой")],
        [KeyboardButton("🗑 Корзина (счёт)"), KeyboardButton("🔄 Restart Explorer")],
        [KeyboardButton("📌 Автозапуск Jarvis"), KeyboardButton("⬅️ Назад в меню")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

# Совместимость
def get_reply_keyboard() -> ReplyKeyboardMarkup:
    return get_main_reply_keyboard()

def get_main_keyboard() -> ReplyKeyboardMarkup:
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
