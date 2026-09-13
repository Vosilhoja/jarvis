import os
import io
import asyncio
import logging
from typing import Tuple
import psutil
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from core.intent_schema import StepModel
from core.task_queue import UserTaskSession
from services.desktops_control import switch_to_desktop_number, switch_desktop_direction, create_virtual_desktop
from services.media_control import change_volume, set_brightness, media_play_pause, media_next, media_prev, media_stop
from services.system_info import get_system_metrics, get_top_processes, kill_process_by_pid
from services.system_monitor import preview_and_cleanup_temp

logger = logging.getLogger("jarvis")

async def handle_switch_virtual_desktop(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    num = step.params.get("desktop_number")
    direction = step.params.get("direction")
    if num:
        switch_to_desktop_number(int(num))
        return True, f"✅ Переключился на рабочий стол *{num}*"
    elif direction:
        switch_desktop_direction(direction)
        return True, f"✅ Переключился на рабочий стол ({direction})"
    return False, "Не указан номер стола или направление"

async def handle_create_virtual_desktop(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    create_virtual_desktop()
    return True, "✅ Создан новый виртуальный рабочий стол"

async def handle_list_running_processes(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    procs = get_top_processes(limit=8, sort_by="memory")
    text = "📋 *Топ процессов по RAM:*\n"
    for p in procs:
        text += f"• `{p['name']}` (PID: {p['pid']}, {p['memory_mb']} MB)\n"
    await bot.send_message(chat_id=session.user_id, text=text, parse_mode="Markdown")
    return True, "✅ Список процессов получен"

async def handle_kill_process(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    target = step.params["name_or_pid"]
    if target.isdigit():
        success = kill_process_by_pid(int(target))
        return success, f"{'✅' if success else '❌'} Завершение процесса PID {target}"
    else:
        def _kill_by_name():
            killed = 0
            for p in psutil.process_iter(['pid', 'name']):
                try:
                    if target.lower() in p.info['name'].lower():
                        p.kill()
                        killed += 1
                except Exception:
                    pass
            return killed

        killed = await asyncio.to_thread(_kill_by_name)
        return (killed > 0), f"Завершено {killed} процессов с именем «{target}»"

async def handle_get_disk_space(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    m = get_system_metrics()
    drive = (step.params.get("drive") or "").upper().replace(":", "")
    lines = []
    for d in m.get("disks", []):
        if drive and not d["device"].upper().startswith(drive):
            continue
        lines.append(
            f"• {d['device']} свободно {d['free_gb']} ГБ из {d['total_gb']} ГБ ({d['percent']}%)"
        )
    text = "💾 Диски:\n" + ("\n".join(lines) if lines else "Нет данных")
    await bot.send_message(chat_id=session.user_id, text=text)
    return True, "✅ Место на дисках отправлено"

async def handle_set_volume(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    msg = change_volume(step.params.get("direction", ""), step.params.get("level"))
    return True, f"🔊 {msg}"

async def handle_set_brightness(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    msg = set_brightness(step.params["level"])
    return True, f"☀️ {msg}"

async def handle_media_control(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    action = step.params["action"]
    if action == "play_pause":
        media_play_pause()
    elif action == "next":
        media_next()
    elif action == "prev":
        media_prev()
    elif action == "stop":
        media_stop()
    return True, f"⏯ Медиа: {action}"

async def handle_get_system_status(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    m = get_system_metrics()
    text = (
        f"🖥 *Состояние ПК*\n"
        f"CPU: {m['cpu_percent']}%\n"
        f"RAM: {m['ram_percent']}% ({m['ram_used_mb']}/{m['ram_total_mb']} MB)\n"
        f"Uptime: {m['uptime']}"
    )
    await bot.send_message(chat_id=session.user_id, text=text, parse_mode="Markdown")
    return True, "✅ Статус системы отправлен"

async def handle_lock_pc(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    import ctypes
    ctypes.windll.user32.LockWorkStation()
    return True, "🔒 Рабочая станция заблокирована"

async def handle_start_guard(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    from services.security_guard import security_guard
    delay = step.params.get("delay_sec", 5)
    chat_id = session.user_id
    loop = asyncio.get_running_loop()

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
                bot.send_message(chat_id=chat_id, text=alert_text, parse_mode="Markdown"),
                loop
            )
        except Exception as e:
            logger.error(f"Не удалось отправить тревогу: {e}")

    msg = security_guard.start_guard(on_trigger_callback=on_guard_triggered, delay_sec=delay)
    return True, msg

async def handle_stop_guard(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    from services.security_guard import security_guard
    msg = security_guard.stop_guard()
    return True, msg

async def handle_sleep_pc(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
    return True, "😴 ПК переведен в спящий режим"

async def handle_shutdown_pc(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    act = "shutdown"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚠️ Да, выключить!", callback_data="do_shutdown")],
        [InlineKeyboardButton("❌ Отмена", callback_data="main_menu")]
    ])
    await bot.send_message(
        chat_id=session.user_id,
        text="⚠️ *Подтвердите действие: SHUTDOWN ПК?*",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    return True, "⏳ Запрошено подтверждение выключения"

async def handle_restart_pc(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    act = "restart"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚠️ Да, перезагрузить!", callback_data="do_restart")],
        [InlineKeyboardButton("❌ Отмена", callback_data="main_menu")]
    ])
    await bot.send_message(
        chat_id=session.user_id,
        text="⚠️ *Подтвердите действие: RESTART ПК?*",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    return True, "⏳ Запрошено подтверждение перезагрузки"

async def handle_cleanup_temp(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    count, freed_mb = preview_and_cleanup_temp()
    return True, f"🧹 Очищено временных файлов: {count} (освобождено ~{freed_mb} МБ)"

async def handle_watch_process(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    pname = step.params["process_name"]
    chat_id = session.user_id

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

async def handle_chat_reply(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    await bot.send_message(chat_id=session.user_id, text=step.params["message"])
    return True, "✅ Ответ отправлен"

async def handle_clarify(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    await bot.send_message(chat_id=session.user_id, text=f"❓ {step.params['question']}")
    return True, "✅ Задан уточняющий вопрос"
