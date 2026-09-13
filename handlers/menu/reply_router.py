import os
import re
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from handlers.menu.common import safe_reply
from handlers.menu.keyboards import (
    get_main_reply_keyboard, get_system_reply_keyboard, get_media_reply_keyboard,
    get_files_reply_keyboard, get_network_reply_keyboard, get_apps_reply_keyboard,
    get_control_reply_keyboard, get_screenshot_reply_keyboard, get_tools_reply_keyboard
)

logger = logging.getLogger("jarvis")

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
                        "🔌", "🖨", "🛡", "⏱", "🗑", "🔄", "📌", "📦", "🔍",
                        "📅", "🔧")):
        return True
    return False

def parse_desktop_selection(text: str):
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

async def _ask_for_number(update: Update, context: ContextTypes.DEFAULT_TYPE, state_key: str, prompt: str):
    context.user_data[state_key] = True
    await update.message.reply_text(prompt, parse_mode="Markdown")

async def handle_reply_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Обрабатывает нажатия ВСЕХ кнопок клавиатуры."""
    text = (update.message.text or "").strip()
    chat_id = update.effective_chat.id

    # 0. КНОПКА ВОЗВРАТА
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

    # 0.5 ПРИОРИТЕТ: ожидание числового/текстового ввода
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

    if context.user_data.get("awaiting_file_search"):
        context.user_data.pop("awaiting_file_search")
        from services.extra_functions import search_files
        result = search_files(text)
        await update.message.reply_text(result, parse_mode="Markdown")
        return True

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
        if _looks_like_keyboard_button(text):
            context.user_data.pop("ai_mode", None)
        else:
            from handlers.ai_chat import handle_ai_message
            await handle_ai_message(update, context)
            return True

    # 1. ПЕРЕКЛЮЧЕНИЕ КАТЕГОРИЙ
    CATEGORY_MAP = {
        "🖥 Система":     (get_system_reply_keyboard,   "🖥 *Меню системы:*"),
        "🎵 Медиа / Звук":(get_media_reply_keyboard,    "🎵 *Меню звука и медиа:*"),
        "📁 Файлы":       (get_files_reply_keyboard,    "📁 *Меню файлов и папок:*"),
        "🌐 Сеть":        (get_network_reply_keyboard,  "🌐 *Меню сети и интернета:*"),
        "🚀 Приложения":  (get_apps_reply_keyboard,     "🚀 *Быстрый запуск приложений:*"),
        "🖱 Управление ПК":(get_control_reply_keyboard, "🖱 *Управление окнами, клавишами и ПК:*"),
        "📸 Скриншот":    (get_screenshot_reply_keyboard,"📸 *Выберите рабочий стол для скриншота:*"),
        "🧰 Инструменты": (get_tools_reply_keyboard,     "🧰 *Инструменты:*"),
    }

    if text in CATEGORY_MAP:
        context.user_data.pop("ai_mode", None)
        keyboard_fn, title = CATEGORY_MAP[text]
        await update.message.reply_text(
            title,
            reply_markup=keyboard_fn(),
            parse_mode="Markdown"
        )
        return True

    # 2. СКРИНШОТ
    if text == "📸 Весь экран":
        from handlers.system_commands import send_screenshot
        await send_screenshot(update, context, monitor_index=0, reply_markup=get_screenshot_reply_keyboard())
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

    m_desk = re.search(r"Стола?\s+(\d+)", text)
    if m_desk and ("Снимок" in text or "Стол" in text) and not text.startswith("🎛") and not text.startswith("📍 Стол"):
        desk_num = int(m_desk.group(1))
        from handlers.system_commands import send_screenshot
        await send_screenshot(update, context, monitor_index=0, desktop_num=desk_num, reply_markup=get_screenshot_reply_keyboard())
        return True

    # 3. ПРОЦЕССЫ, ИИ-ЧАТ, НАПОМИНАНИЯ
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

    # 4. ФУНКЦИИ СИСТЕМЫ
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
        await update.message.reply_text(f"📋 Буфер обмена:\n\n{content}")
        return True

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
        from services.security_guard import security_guard, make_guard_alert_callback

        on_guard_triggered = make_guard_alert_callback(
            context.bot, chat_id, loop=context.application.loop
        )
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

    # 5. ФУНКЦИИ МЕДИА И ЗВУКА
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

    if text == "🎙 Установить громкость":
        await _ask_for_number(
            update, context,
            "awaiting_volume",
            "🎙 *Громкость:* введите значение от 0 до 100\n\n_Например: 50_"
        )
        return True

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

    # 6. ФУНКЦИИ ФАЙЛОВ
    if text == "🗂 Рабочий стол":
        from handlers.files import show_files_menu
        await show_files_menu(update, context)
        return True

    if text == "⬇️ Загрузки":
        from services.extra_functions import get_downloads_list
        raw = get_downloads_list()
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

    # 7. ФУНКЦИИ СЕТИ
    if text == "🌍 Внешний IP":
        from services.extra_functions import get_public_ip
        await update.message.reply_text(f"🌍 *Внешний IP:* `{get_public_ip()}`", parse_mode="Markdown")
        return True

    if text == "🏠 Локальный IP":
        from services.extra_functions import get_local_ip
        await update.message.reply_text(f"🏠 *Локальный IP:* `{get_local_ip()}`", parse_mode="Markdown")
        return True

    if text == "📡 Адаптеры сети":
        import asyncio
        from services.extra_functions import get_network_adapters
        result = await asyncio.to_thread(get_network_adapters)
        await safe_reply(update, f"📡 *Сетевые адаптеры:*\n\n{result}")
        return True

    if text == "📶 Wi-Fi сети":
        import asyncio
        from services.extra_functions import get_wifi_networks
        result = await asyncio.to_thread(get_wifi_networks)
        await safe_reply(update, f"📶 *Wi-Fi сети:*\n\n{result}")
        return True

    if text == "🏓 Ping 8.8.8.8":
        import asyncio
        from services.extra_functions import ping_host
        result = await asyncio.to_thread(ping_host, "8.8.8.8")
        await safe_reply(update, f"🏓 *Ping 8.8.8.8:*\n\n```\n{result}\n```")
        return True

    if text == "🏓 Ping Яндекс":
        import asyncio
        from services.extra_functions import ping_host
        result = await asyncio.to_thread(ping_host, "ya.ru")
        await safe_reply(update, f"🏓 *Ping ya.ru:*\n\n```\n{result}\n```")
        return True

    # 8. БЫСТРЫЙ ЗАПУСК ПРИЛОЖЕНИЙ
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

    # 9. УПРАВЛЕНИЕ ПК И ГОРЯЧИЕ КЛАВИШИ
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

    m_switch = re.search(r"Стол\s+(\d+)", text)
    if m_switch and ("🎛" in text or "📍" in text or "стол" in text.lower()) and "снимок" not in text.lower() and "новый" not in text.lower():
        desk_num = int(m_switch.group(1))
        import asyncio
        from services.desktops_control import switch_to_desktop_number
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, switch_to_desktop_number, desk_num)
            # Отправляем подтверждение с обновлённой клавиатурой (метка активного стола 📍 переместится)
            await update.message.reply_text(
                f"🎛 Переключено на *Рабочий стол {desk_num}*",
                reply_markup=get_control_reply_keyboard(),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка переключения стола {desk_num}: {e}", exc_info=True)
            await update.message.reply_text(f"⚠️ Не удалось переключиться на стол {desk_num}: {e}")
        return True

    if text == "➕ Новый стол":
        import asyncio
        from services.desktops_control import create_virtual_desktop
        try:
            loop = asyncio.get_running_loop()
            new_total = await loop.run_in_executor(None, create_virtual_desktop)
            # Отправляем подтверждение с обновлённой клавиатурой (новая кнопка стола сразу появится в меню)
            await update.message.reply_text(
                f"➕ Создан новый виртуальный рабочий стол! (Всего столов: *{new_total}*)",
                reply_markup=get_control_reply_keyboard(),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка создания стола: {e}", exc_info=True)
            await update.message.reply_text(f"⚠️ Не удалось создать рабочий стол: {e}")
        return True

    if text == "🗑 Удалить текущий стол":
        from services.desktops_control import get_current_desktop_number, get_desktop_count
        current = get_current_desktop_number()
        total = get_desktop_count()
        if total <= 1:
            await update.message.reply_text("⚠️ Нельзя удалить единственный оставшийся рабочий стол.")
            return True
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"⚠️ Да, удалить Стол {current}!", callback_data=f"do_delete_desktop_{current}")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_action")]
        ])
        await update.message.reply_text(
            f"⚠️ *Удалить рабочий стол {current}?* Все открытые на нём окна свернутся на соседний стол.",
            reply_markup=kb, parse_mode="Markdown"
        )
        return True

    if text == "🖱 Пульт мыши":
        from handlers.remote_control import show_remote_control_menu
        await show_remote_control_menu(update, context)
        return True

    # ═══════════════════════════════════════════════════════
    # 🧰 ИНСТРУМЕНТЫ — прямые обработчики (без похода в облачный ИИ)
    # ═══════════════════════════════════════════════════════
    import asyncio as _asyncio

    if text == "🔐 Пароль":
        from services.misc_tools import generate_password
        res = await _asyncio.to_thread(generate_password, 16)
        await update.message.reply_text(res, parse_mode="Markdown")
        return True

    if text == "📷 QR-код":
        context.user_data["awaiting_qr"] = True
        await update.message.reply_text("📷 Отправьте текст или ссылку, которую закодировать в QR:")
        return True

    if text == "🗣 Сказать время":
        from services.misc_tools import speak_text
        from datetime import datetime
        now_str = datetime.now().strftime("%H:%M")
        res = await _asyncio.to_thread(speak_text, f"Сейчас {now_str}")
        await update.message.reply_text(res)
        return True

    if text == "🎲 Кубик":
        from services.misc_tools import random_util
        res = await _asyncio.to_thread(random_util, "dice")
        await update.message.reply_text(res)
        return True

    if text == "🪙 Монета":
        from services.misc_tools import random_util
        res = await _asyncio.to_thread(random_util, "coin")
        await update.message.reply_text(res)
        return True

    if text == "🎯 Активное окно":
        from services.misc_tools import get_active_window
        res = await _asyncio.to_thread(get_active_window)
        await update.message.reply_text(res)
        return True

    if text == "🖥 Свернуть всё":
        from services.misc_tools import minimize_all_windows
        res = await _asyncio.to_thread(minimize_all_windows)
        await update.message.reply_text(res)
        return True

    if text == "🌙 Тема Windows":
        from services.misc_tools import toggle_dark_mode
        res = await _asyncio.to_thread(toggle_dark_mode)
        await update.message.reply_text(res)
        return True

    if text == "🌙 Ночной свет":
        from services.misc_tools import open_night_light
        res = await _asyncio.to_thread(open_night_light)
        await update.message.reply_text(res)
        return True

    if text == "🔋 Отчет батареи":
        from services.power_tools import get_battery_report
        res = await _asyncio.to_thread(get_battery_report)
        await update.message.reply_text(res[:3000])
        return True

    if text == "🔌 USB":
        from services.misc_tools import list_usb_devices
        res = await _asyncio.to_thread(list_usb_devices)
        await update.message.reply_text(res[:3000])
        return True

    if text == "🖨 Принтеры":
        from services.misc_tools import list_printers
        res = await _asyncio.to_thread(list_printers)
        await update.message.reply_text(res[:3000])
        return True

    if text == "🚀 Автозагрузка ПО":
        from services.misc_tools import list_startup_apps
        res = await _asyncio.to_thread(list_startup_apps)
        await update.message.reply_text(res[:3000])
        return True

    if text == "🛡 Firewall":
        from services.misc_tools import firewall_status
        res = await _asyncio.to_thread(firewall_status)
        await update.message.reply_text(res)
        return True

    if text == "🛡 Defender":
        from services.misc_tools import defender_status
        res = await _asyncio.to_thread(defender_status)
        await update.message.reply_text(res)
        return True

    if text == "⏱ Простой":
        from services.power_tools import get_idle_time
        res = await _asyncio.to_thread(get_idle_time)
        await update.message.reply_text(res)
        return True

    if text == "🗑 Корзина (счёт)":
        from services.misc_tools import recycle_bin_info
        res = await _asyncio.to_thread(recycle_bin_info)
        await update.message.reply_text(res)
        return True

    if text == "🔄 Restart Explorer":
        from services.misc_tools import restart_explorer
        res = await _asyncio.to_thread(restart_explorer)
        await update.message.reply_text(res)
        return True

    if text == "📌 Автозапуск Jarvis":
        from services.autostart import ensure_autostart, autostart_status
        res = await _asyncio.to_thread(lambda: ensure_autostart() + "\n\n" + autostart_status())
        await update.message.reply_text(res)
        return True

    return False
