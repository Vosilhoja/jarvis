import json
from typing import Tuple
from telegram import Bot
from core.intent_schema import StepModel
from core.task_queue import UserTaskSession

async def handle_set_reminder(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    from scheduler import reminder_manager
    try:
        rem = reminder_manager.add_reminder(session.user_id, step.params["text"], step.params["when"])
    except ValueError as exc:
        return False, f"❌ Напоминание не создано: {exc}"
    return True, f"⏰ Напоминание установлено: «{rem['text']}» на {rem['next_trigger_at']}"

async def handle_list_reminders(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    from scheduler import reminder_manager
    active = reminder_manager.get_active_reminders(session.user_id)
    if not active:
        await bot.send_message(chat_id=session.user_id, text="📭 Активных напоминаний нет.")
    else:
        text = "⏰ *Активные напоминания:*\n"
        for r in active:
            text += f"• `{r['id'][:6]}`: «{r['text']}» — {r['next_trigger_at']}\n"
        await bot.send_message(chat_id=session.user_id, text=text, parse_mode="Markdown")
    return True, "✅ Список напоминаний отправлен"

async def handle_cancel_reminder(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    from scheduler import reminder_manager
    ok = reminder_manager.cancel_reminder(step.params["reminder_id"], session.user_id)
    return ok, "✅ Напоминание отменено" if ok else "❌ Напоминание не найдено"

async def handle_create_scenario(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    from config import SCENARIOS_PATH
    name = step.params["scenario_name"]
    steps = session.context_memory.get("last_plan_steps") or []
    data = {}
    if SCENARIOS_PATH.exists():
        try:
            data = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data[name] = {
        "description": step.params.get("steps_description", ""),
        "steps": steps,
    }
    SCENARIOS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return True, f"✅ Сценарий «{name}» сохранён ({len(steps)} шагов из последней цепочки)"

async def handle_run_scenario(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    from config import SCENARIOS_PATH
    from core.intent_schema import validate_step
    name = step.params["scenario_name"]
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

async def handle_focus_mode(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    from services.extra_functions import do_not_disturb_mode
    mins = int(step.params.get("duration_minutes") or 60)
    do_not_disturb_mode()
    from scheduler import reminder_manager
    reminder_manager.add_reminder(session.user_id, "Режим фокуса закончился", f"через {mins} минут")
    return True, f"🎯 Режим фокуса на {mins} мин: уведомления переключены, напоминание поставлено"
