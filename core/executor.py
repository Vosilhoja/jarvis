import os
import io
import re
import uuid
import json
import time
import shutil
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

import psutil
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton

from core.intent_schema import StepModel
from core.app_resolver import app_resolver
from core.task_queue import UserTaskSession, task_queue_manager
from services.ai_client import ask_gemini_app_choice
from services.desktops_control import switch_to_desktop_number, switch_desktop_direction, create_virtual_desktop
from services.media_control import change_volume, set_brightness, media_play_pause, media_next, media_prev, media_stop
from services.screenshot import take_screenshot
from services.system_info import get_system_metrics, get_top_processes, kill_process_by_pid
from services.system_monitor import preview_and_cleanup_temp
from services.web_client import open_url_or_search, search_web_summary, download_wikipedia_article, download_file_by_url, get_weather_forecast, get_exchange_rates

logger = logging.getLogger("jarvis")

def resolve_path_aliases(raw_path: str) -> Path:
    """Разворачивает алиасы путей и переменные окружения в реальный путь.

    Поддерживает привычные алиасы (рабочий стол, downloads, documents), а также
    Windows- и Unix-форматы путей. Если пользователь передал относительный путь,
    он резолвится относительно домашней директории пользователя, а не C:\Users\Default.
    """
    if raw_path is None:
        return Path.home()

    value = str(raw_path).strip()
    if not value:
        return Path.home()

    user_home = Path.home()
    userprofile = os.environ.get("USERPROFILE")
    if userprofile:
        user_home = Path(userprofile)

    aliases = {
        "рабочий стол": user_home / "Desktop",
        "десктоп": user_home / "Desktop",
        "desktop": user_home / "Desktop",
        "загрузки": user_home / "Downloads",
        "скачанные": user_home / "Downloads",
        "downloads": user_home / "Downloads",
        "документы": user_home / "Documents",
        "мои документы": user_home / "Documents",
        "documents": user_home / "Documents",
        "изображения": user_home / "Pictures",
        "картинки": user_home / "Pictures",
        "pictures": user_home / "Pictures",
        "видео": user_home / "Videos",
        "videos": user_home / "Videos",
        "музыка": user_home / "Music",
        "music": user_home / "Music",
        "home": user_home,
        "~": user_home,
    }

    cleaned = value.lower()
    if cleaned in aliases:
        return aliases[cleaned]

    expanded = os.path.expandvars(os.path.expanduser(value))
    path = Path(expanded)
    if not path.is_absolute():
        path = user_home / path
    return path

class StepExecutor:
    """Исполняет шаги интентов, отправляет отчеты и управляет контекстом сессии."""

    async def execute_step(self, step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
        intent = step.intent
        params = step.params
        chat_id = session.user_id

        try:
            # 1. Запуск приложения
            if intent == "open_application":
                query = params["app_query"]
                candidates = app_resolver.find_candidates(query, top_k=5)
                if not candidates:
                    return False, f"❌ Не нашел приложения по запросу «{query}»."

                # Если первый кандидат имеет высокий скор (>= 75)
                best_app, score = candidates[0]
                if score >= 75.0:
                    success = app_resolver.launch_app(best_app)
                    if success:
                        return True, f"✅ Запустил *{best_app['display_name']}* (найдено по «{query}»)"
                    return False, f"❌ Ошибка запуска {best_app['display_name']}"

                # Если скор ниже, вызываем ИИ для разрешения неоднозначности
                choice_idx = ask_gemini_app_choice(query, [c[0] for c in candidates])
                if choice_idx is not None:
                    chosen_app = candidates[choice_idx][0]
                    app_resolver.add_user_alias(chosen_app["display_name"], query)
                    success = app_resolver.launch_app(chosen_app)
                    if success:
                        return True, f"✅ Запустил *{chosen_app['display_name']}* (выбор ИИ по «{query}»)"

                # Если ИИ не уверен, предлагаем кнопки пользователю
                kb_buttons = []
                for c_app, _ in candidates[:3]:
                    kb_buttons.append([InlineKeyboardButton(f"Запустить {c_app['display_name']}", callback_data=f"launch_app_{c_app['display_name'][:25]}")])
                kb_buttons.append([InlineKeyboardButton("❌ Отмена", callback_data="main_menu")])

                await bot.send_message(
                    chat_id=chat_id,
                    text=f"🤔 Найдено несколько похожих приложений для «{query}». Выберите нужное:",
                    reply_markup=InlineKeyboardMarkup(kb_buttons)
                )
                return True, f"⏳ Предложен выбор приложений для «{query}»"

            # 2. Закрытие приложения
            elif intent == "close_application":
                query = params["app_query"].lower()
                killed = 0
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        if query in proc.info['name'].lower():
                            proc.terminate()
                            killed += 1
                    except Exception:
                        continue
                if killed > 0:
                    return True, f"✅ Закрыто процессов: {killed} (по запросу «{query}»)"
                return False, f"⚠️ Запущенных процессов по запросу «{query}» не найдено."

            # 3. Рабочие столы
            elif intent == "switch_virtual_desktop":
                num = params.get("desktop_number")
                direction = params.get("direction")
                if num:
                    switch_to_desktop_number(int(num))
                    return True, f"✅ Переключился на рабочий стол *{num}*"
                elif direction:
                    switch_desktop_direction(direction)
                    return True, f"✅ Переключился на рабочий стол ({direction})"
                return False, "Не указан номер стола или направление"

            elif intent == "create_virtual_desktop":
                create_virtual_desktop()
                return True, "✅ Создан новый виртуальный рабочий стол"

            # 4. Процессы
            elif intent == "list_running_processes":
                procs = get_top_processes(limit=8, sort_by="memory")
                text = "📋 *Топ процессов по RAM:*\n"
                for p in procs:
                    text += f"• `{p['name']}` (PID: {p['pid']}, {p['memory_mb']} MB)\n"
                await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
                return True, "✅ Список процессов получен"

            elif intent == "kill_process":
                target = params["name_or_pid"]
                if target.isdigit():
                    success = kill_process_by_pid(int(target))
                    return success, f"{'✅' if success else '❌'} Завершение процесса PID {target}"
                else:
                    # По имени
                    killed = 0
                    for p in psutil.process_iter(['pid', 'name']):
                        try:
                            if target.lower() in p.info['name'].lower():
                                p.kill()
                                killed += 1
                        except Exception:
                            pass
                    return (killed > 0), f"Завершено {killed} процессов с именем «{target}»"

            # 5. Скриншот
            elif intent == "take_screenshot":
                mon_idx = params.get("monitor_index", 0)
                desk_num = params.get("desktop_number")
                if desk_num:
                    from services.screenshot import take_desktop_screenshot
                    buf = take_desktop_screenshot(desk_num, mon_idx)
                    name = f"Рабочий стол {desk_num}"
                else:
                    buf = take_screenshot(mon_idx)
                    name = "Все мониторы" if mon_idx == 0 else f"Монитор {mon_idx}"
                from telegram import InputFile
                await bot.send_photo(chat_id=chat_id, photo=InputFile(buf, "screenshot.png"), caption=f"📸 Снимок: {name}")
                return True, f"✅ Скриншот ({name}) отправлен"

            # 6. Файлы и проводник
            elif intent == "open_explorer_path":
                raw_p = params["path"]
                # Проверяем, не ссылается ли пользователь на созданную в прошлом шаге папку
                if raw_p.lower() in ("сюда", "эту папку", "созданную папку") and "last_created_folder" in session.context_memory:
                    target_path = Path(session.context_memory["last_created_folder"])
                else:
                    target_path = resolve_path_aliases(raw_p)

                if target_path.exists():
                    os.startfile(target_path)
                    session.context_memory["current_explorer_path"] = str(target_path)
                    return True, f"✅ Открыл проводник: `{target_path}`"
                return False, f"❌ Путь `{target_path}` не существует."

            elif intent == "create_folder":
                name = params["name"]
                parent_raw = params.get("parent") or str(resolve_path_aliases("рабочий стол"))
                parent = resolve_path_aliases(parent_raw)
                parent.mkdir(parents=True, exist_ok=True)
                new_folder = parent / name
                new_folder.mkdir(parents=True, exist_ok=True)
                session.context_memory["last_created_folder"] = str(new_folder)
                return True, f"✅ Создал папку: `{new_folder}`"

            elif intent == "create_file":
                name = params["name"]
                parent_raw = params.get("parent") or session.context_memory.get("last_created_folder") or str(resolve_path_aliases("рабочий стол"))
                parent = resolve_path_aliases(parent_raw)
                content = params.get("content", "")
                file_path = parent / name
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return True, f"✅ Создал файл: `{file_path}`"

            elif intent == "move_item":
                src = resolve_path_aliases(params["source"])
                dst = resolve_path_aliases(params["destination"])
                if not src.exists():
                    return False, f"❌ Нет источника: `{src}`"
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
                return True, f"✅ Перемещено: `{src}` → `{dst}`"

            elif intent == "copy_item":
                src = resolve_path_aliases(params["source"])
                dst = resolve_path_aliases(params["destination"])
                if not src.exists():
                    return False, f"❌ Нет источника: `{src}`"
                dst.parent.mkdir(parents=True, exist_ok=True)
                if src.is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
                return True, f"✅ Скопировано: `{src}` → `{dst}`"

            elif intent == "rename_item":
                src = resolve_path_aliases(params["path"])
                if not src.exists():
                    return False, f"❌ Нет файла: `{src}`"
                new_path = src.with_name(params["new_name"])
                src.rename(new_path)
                return True, f"✅ Переименовано в `{new_path.name}`"

            elif intent == "search_files":
                from services.extra_functions import search_files as _search_files
                msg = _search_files(params["query"], params.get("root"))
                await bot.send_message(chat_id=chat_id, text=msg)
                return True, "✅ Поиск файлов выполнен"

            elif intent == "list_installed_apps":
                q = (params.get("query") or "").strip()
                apps = app_resolver.apps_index
                if q:
                    from rapidfuzz import process, fuzz
                    names = [a.get("display_name", "") for a in apps]
                    hits = process.extract(q, names, scorer=fuzz.WRatio, limit=12)
                    lines = [f"• {n} ({s:.0f}%)" for n, s, _ in hits]
                else:
                    lines = [f"• {a.get('display_name')}" for a in apps[:20]]
                await bot.send_message(chat_id=chat_id, text="📦 Программы:\n" + "\n".join(lines))
                return True, "✅ Список приложений отправлен"

            elif intent == "get_disk_space":
                m = get_system_metrics()
                drive = (params.get("drive") or "").upper().replace(":", "")
                lines = []
                for d in m.get("disks", []):
                    if drive and not d["device"].upper().startswith(drive):
                        continue
                    lines.append(
                        f"• {d['device']} свободно {d['free_gb']} ГБ из {d['total_gb']} ГБ ({d['percent']}%)"
                    )
                text = "💾 Диски:\n" + ("\n".join(lines) if lines else "Нет данных")
                await bot.send_message(chat_id=chat_id, text=text)
                return True, "✅ Место на дисках отправлено"

            elif intent == "delete_item":
                target_p = resolve_path_aliases(params["path"])
                # Защита: опасная операция!
                session.pending_confirmation = {"action": "delete", "path": str(target_p)}
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"⚠️ Да, удалить {target_p.name}", callback_data="confirm_delete_yes")],
                    [InlineKeyboardButton("❌ Отмена", callback_data="confirm_delete_no")]
                ])
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ *Подтверждение удаления!*\nВы уверены, что хотите безвозвратно удалить:\n`{target_p}`?",
                    reply_markup=kb,
                    parse_mode="Markdown"
                )
                return True, "⏳ Запрошено подтверждение удаления"

            # 7. Веб и Wikipedia
            elif intent == "open_website":
                url = open_url_or_search(params["url_or_query"])
                return True, f"✅ Открыл сайт в браузере: {url}"

            elif intent == "web_search":
                summary = search_web_summary(params["query"])
                await bot.send_message(chat_id=chat_id, text=f"🌐 *Результат поиска:*\n\n{summary}", parse_mode="Markdown")
                return True, "✅ Поиск в интернете завершен"

            elif intent == "download_from_wikipedia":
                query = params["query"]
                dest = params.get("destination") or session.context_memory.get("last_created_folder") or str(resolve_path_aliases("рабочий стол"))
                dest_path = str(resolve_path_aliases(dest))
                msg = download_wikipedia_article(query, dest_path)
                return True, f"✅ {msg}"

            elif intent == "download_file":
                url = params["url"]
                dest = params.get("destination") or session.context_memory.get("last_created_folder")
                msg = download_file_by_url(url, dest)
                return True, f"✅ {msg}"

            # 8. Медиа и звук
            elif intent == "set_volume":
                msg = change_volume(params.get("direction", ""), params.get("level"))
                return True, f"🔊 {msg}"

            elif intent == "set_brightness":
                msg = set_brightness(params["level"])
                return True, f"☀️ {msg}"

            elif intent == "media_control":
                action = params["action"]
                if action == "play_pause":
                    media_play_pause()
                elif action == "next":
                    media_next()
                elif action == "prev":
                    media_prev()
                elif action == "stop":
                    media_stop()
                return True, f"⏯ Медиа: {action}"

            # 9. Система
            elif intent == "get_system_status":
                m = get_system_metrics()
                text = (
                    f"🖥 *Состояние ПК*\n"
                    f"CPU: {m['cpu_percent']}%\n"
                    f"RAM: {m['ram_percent']}% ({m['ram_used_mb']}/{m['ram_total_mb']} MB)\n"
                    f"Uptime: {m['uptime']}"
                )
                await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
                return True, "✅ Статус системы отправлен"

            elif intent == "lock_pc":
                import ctypes
                ctypes.windll.user32.LockWorkStation()
                return True, "🔒 Рабочая станция заблокирована"

            elif intent == "start_guard":
                from services.security_guard import security_guard
                delay = params.get("delay_sec", 5)
                
                def on_guard_triggered(sx, sy, cx, cy):
                    import asyncio
                    alert_text = (
                        f"🚨 *ТРЕВОГА! РЕЖИМ ОХРАНЫ СРАБОТАЛ!*\n\n"
                        f"Зафиксировано движение мыши!\n"
                        f"📍 Исходные координаты: `({sx}, {sy})`\n"
                        f"📍 Новые координаты: `({cx}, {cy})`\n\n"
                        f"🔒 *Компьютер немедленно заблокирован!*"
                    )
                    try:
                        asyncio.run_coroutine_threadsafe(
                            bot.send_message(chat_id=chat_id, text=alert_text, parse_mode="Markdown"),
                            asyncio.get_event_loop()
                        )
                    except Exception as e:
                        logger.error(f"Не удалось отправить тревогу: {e}")

                msg = security_guard.start_guard(on_trigger_callback=on_guard_triggered, delay_sec=delay)
                return True, msg

            elif intent == "stop_guard":
                from services.security_guard import security_guard
                msg = security_guard.stop_guard()
                return True, msg

            elif intent == "sleep_pc":
                os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
                return True, "😴 ПК переведен в спящий режим"

            elif intent in ("shutdown_pc", "restart_pc"):
                act = "shutdown" if intent == "shutdown_pc" else "restart"
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"⚠️ Да, {act}!", callback_data=f"do_{act}")],
                    [InlineKeyboardButton("❌ Отмена", callback_data="main_menu")]
                ])
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ *Подтвердите действие: {act.upper()} ПК?*",
                    reply_markup=kb,
                    parse_mode="Markdown"
                )
                return True, f"⏳ Запрошено подтверждение {act}"

            # 10. Напоминания
            elif intent == "set_reminder":
                from scheduler import reminder_manager
                rem = reminder_manager.add_reminder(chat_id, params["text"], params["when"])
                return True, f"⏰ Напоминание установлено: «{rem['text']}» на {rem['next_trigger_at']}"

            elif intent == "list_reminders":
                from scheduler import reminder_manager
                active = reminder_manager.get_active_reminders(chat_id)
                if not active:
                    await bot.send_message(chat_id=chat_id, text="📭 Активных напоминаний нет.")
                else:
                    text = "⏰ *Активные напоминания:*\n"
                    for r in active:
                        text += f"• `{r['id'][:6]}`: «{r['text']}» — {r['next_trigger_at']}\n"
                    await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
                return True, "✅ Список напоминаний отправлен"

            elif intent == "cancel_reminder":
                from scheduler import reminder_manager
                ok = reminder_manager.cancel_reminder(params["reminder_id"], chat_id)
                return ok, "✅ Напоминание отменено" if ok else "❌ Напоминание не найдено"

            elif intent == "create_scenario":
                from config import SCENARIOS_PATH
                name = params["scenario_name"]
                steps = session.context_memory.get("last_plan_steps") or []
                data = {}
                if SCENARIOS_PATH.exists():
                    try:
                        data = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
                    except Exception:
                        data = {}
                data[name] = {
                    "description": params.get("steps_description", ""),
                    "steps": steps,
                }
                SCENARIOS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                return True, f"✅ Сценарий «{name}» сохранён ({len(steps)} шагов из последней цепочки)"

            elif intent == "run_scenario":
                from config import SCENARIOS_PATH
                from core.intent_schema import validate_step
                name = params["scenario_name"]
                if not SCENARIOS_PATH.exists():
                    return False, "Нет сохранённых сценариев"
                data = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
                sc = data.get(name)
                if not sc:
                    return False, f"Сценарий «{name}» не найден. Есть: {', '.join(data.keys()) or '—'}"
                added = 0
                for s in sc.get("steps") or []:
                    try:
                        session.add_steps([validate_step(s["intent"], s.get("params") or {})])
                        added += 1
                    except Exception:
                        continue
                return True, f"▶ Сценарий «{name}»: в очередь добавлено {added} шагов"

            elif intent == "focus_mode":
                from services.extra_functions import do_not_disturb_mode
                mins = int(params.get("duration_minutes") or 60)
                do_not_disturb_mode()
                from scheduler import reminder_manager
                reminder_manager.add_reminder(chat_id, "Режим фокуса закончился", f"через {mins} минут")
                return True, f"🎯 Режим фокуса на {mins} мин: уведомления переключены, напоминание поставлено"

            elif intent == "watch_process":
                import asyncio
                pname = params["process_name"]

                async def _watch():
                    while True:
                        found = False
                        for p in psutil.process_iter(["name"]):
                            try:
                                if pname.lower() in (p.info.get("name") or "").lower():
                                    found = True
                                    break
                            except Exception:
                                continue
                        if not found:
                            await bot.send_message(chat_id=chat_id, text=f"✅ Процесс «{pname}» завершился")
                            return
                        await asyncio.sleep(5)

                asyncio.create_task(_watch())
                return True, f"👁 Слежу за процессом «{pname}» — напишу, когда завершится"

            # 11. Дополнительные фичи (погода, валюта, очистка, фокус)
            elif intent == "get_weather":
                msg = get_weather_forecast(params.get("city"))
                await bot.send_message(chat_id=chat_id, text=msg)
                return True, "✅ Погода получена"

            elif intent == "get_exchange_rate":
                msg = get_exchange_rates(params.get("currency", "USD"))
                await bot.send_message(chat_id=chat_id, text=msg)
                return True, "✅ Курсы валют получены"

            elif intent == "cleanup_temp":
                count, freed_mb = preview_and_cleanup_temp()
                return True, f"🧹 Очищено временных файлов: {count} (освобождено ~{freed_mb} МБ)"

            # 12. Разговор и общее
            elif intent == "chat_reply":
                await bot.send_message(chat_id=chat_id, text=params["message"])
                return True, "✅ Ответ отправлен"

            elif intent == "clarify":
                await bot.send_message(chat_id=chat_id, text=f"❓ {params['question']}")
                return True, "✅ Задан уточняющий вопрос"

            from services.extra_functions import dispatch_extra
            extra = dispatch_extra(intent, params, session)
            if extra is not None:
                if extra.photo_bytes:
                    from telegram import InputFile
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=InputFile(io.BytesIO(extra.photo_bytes), extra.photo_name),
                        caption=extra.text[:900],
                    )
                return extra.success, extra.text

            return False, f"Неизвестный intent: {intent}"

        except Exception as e:
            logger.error(f"Ошибка выполнения шага {intent}: {e}", exc_info=True)
            return False, f"❌ Ошибка в шаге «{intent}»: {e}"

class TaskExecutorService:
    def __init__(self):
        self.executor = StepExecutor()

    async def process_user_queue(self, session: UserTaskSession, bot: Bot):
        """Обрабатывает очередь шагов пользователя по очереди (FIFO)."""
        if session.is_running:
            return

        session.is_running = True
        try:
            while not session.queue.empty():
                step = await session.queue.get()
                session.current_step = step

                success, report = await self.executor.execute_step(step, session, bot)
                session.history.append({"intent": step.intent, "success": success, "time": time.time()})
                session.context_memory.setdefault("last_plan_steps", [])
                session.context_memory["last_plan_steps"].append({"intent": step.intent, "params": step.params})
                session.context_memory["last_plan_steps"] = session.context_memory["last_plan_steps"][-30:]

                if step.intent != "chat_reply":
                    try:
                        await bot.send_message(chat_id=session.user_id, text=report, parse_mode="Markdown")
                    except Exception:
                        await bot.send_message(chat_id=session.user_id, text=str(report))

                session.queue.task_done()
        finally:
            session.is_running = False
            session.current_step = None

task_executor = TaskExecutorService()
