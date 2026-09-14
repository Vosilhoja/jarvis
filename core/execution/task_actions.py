from typing import Tuple
from telegram import Bot
from core.intent_schema import StepModel
from core.task_queue import UserTaskSession


async def handle_create_task(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    from domain.tasks import task_manager
    task = task_manager.create(
        session.user_id, step.params["title"], step.params.get("due"), step.params["priority"]
    )
    due = f", срок: {task['due']}" if task["due"] else ""
    return True, f"✅ Задача создана [{task['id'][:6]}]: «{task['title']}» ({task['priority']}{due})"


async def handle_list_tasks(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    from domain.tasks import task_manager
    tasks = task_manager.list_for_user(session.user_id, step.params.get("status", "open"))
    if not tasks:
        return True, "📭 Задач нет."
    lines = ["📋 *Задачи:*"]
    for task in tasks[:30]:
        due = f" — срок: {task['due']}" if task.get("due") else ""
        mark = "✅" if task["status"] == "done" else "▫️"
        lines.append(f"{mark} `{task['id'][:6]}` {task['title']} [{task['priority']}]{due}")
    return True, "\n".join(lines)


async def handle_complete_task(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    from domain.tasks import task_manager
    task = task_manager.complete(session.user_id, step.params["task_id"])
    if not task:
        return False, f"❌ Открытая задача «{step.params['task_id']}» не найдена."
    return True, f"✅ Задача выполнена: «{task['title']}»"
