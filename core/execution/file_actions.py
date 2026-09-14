import os
import shutil
import asyncio
from typing import Tuple
from pathlib import Path
from telegram import Bot
from core.intent_schema import StepModel
from core.task_queue import UserTaskSession
from core.execution.common import resolve_path_aliases

async def handle_open_explorer_path(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    raw_p = step.params["path"]
    if raw_p.lower() in ("сюда", "эту папку", "созданную папку") and "last_created_folder" in session.context_memory:
        target_path = Path(session.context_memory["last_created_folder"])
    else:
        target_path = resolve_path_aliases(raw_p)

    if target_path.exists():
        os.startfile(target_path)
        session.context_memory["current_explorer_path"] = str(target_path)
        return True, f"✅ Открыл проводник: `{target_path}`"
    return False, f"❌ Путь `{target_path}` не существует."

async def handle_create_folder(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    name = step.params["name"]
    parent_raw = step.params.get("parent") or str(resolve_path_aliases("рабочий стол"))
    parent = resolve_path_aliases(parent_raw)
    parent.mkdir(parents=True, exist_ok=True)
    new_folder = parent / name
    new_folder.mkdir(parents=True, exist_ok=True)
    session.context_memory["last_created_folder"] = str(new_folder)
    return True, f"✅ Создал папку: `{new_folder}`"

async def handle_create_file(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    name = step.params["name"]
    parent_raw = step.params.get("parent") or session.context_memory.get("last_created_folder") or str(resolve_path_aliases("рабочий стол"))
    parent = resolve_path_aliases(parent_raw)
    content = step.params.get("content", "")
    file_path = parent / name
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return True, f"✅ Создал файл: `{file_path}`"

async def handle_move_item(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    src = resolve_path_aliases(step.params["source"])
    dst = resolve_path_aliases(step.params["destination"])
    if not src.exists():
        return False, f"❌ Нет источника: `{src}`"
    dst.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(shutil.move, str(src), str(dst))
    return True, f"✅ Перемещено: `{src}` → `{dst}`"

async def handle_copy_item(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    src = resolve_path_aliases(step.params["source"])
    dst = resolve_path_aliases(step.params["destination"])
    if not src.exists():
        return False, f"❌ Нет источника: `{src}`"
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        await asyncio.to_thread(shutil.copytree, src, dst, dirs_exist_ok=True)
    else:
        await asyncio.to_thread(shutil.copy2, src, dst)
    return True, f"✅ Скопировано: `{src}` → `{dst}`"

async def handle_rename_item(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    src = resolve_path_aliases(step.params["path"])
    if not src.exists():
        return False, f"❌ Нет файла: `{src}`"
    new_path = src.with_name(step.params["new_name"])
    src.rename(new_path)
    return True, f"✅ Переименовано в `{new_path.name}`"

async def handle_search_files(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    from services.extra_functions import search_files as _search_files
    msg = await asyncio.to_thread(_search_files, step.params["query"], step.params.get("root"))
    await bot.send_message(chat_id=session.user_id, text=msg)
    return True, "✅ Поиск файлов выполнен"

async def handle_send_file_by_name(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    from telegram import InputFile
    from adapters.windows.misc_tools import find_file_broad

    query = step.params["name"]
    MAX_SIZE = 50 * 1024 * 1024  # лимит Telegram для ботов

    matches = await asyncio.to_thread(find_file_broad, query)
    if not matches:
        return False, f"❌ Не нашёл файл по запросу «{query}» в Рабочем столе/Загрузках/Документах/Изображениях."

    best = matches[0]
    try:
        size = best.stat().st_size
    except Exception:
        size = 0

    if size > MAX_SIZE:
        return False, f"⚠️ Нашёл `{best}`, но он больше 50 МБ — Telegram-бот не может его отправить."

    with open(best, "rb") as f:
        await bot.send_document(
            chat_id=session.user_id,
            document=InputFile(f, filename=best.name),
            caption=f"📄 {best.name} ({round(size / 1024, 1)} КБ)" if size < 1024 * 1024 else f"📄 {best.name} ({round(size / (1024*1024), 2)} МБ)",
        )

    extra = ""
    if len(matches) > 1:
        others = ", ".join(m.name for m in matches[1:4])
        extra = f"\nЕщё найдено похожих: {others}"
    return True, f"✅ Отправил `{best}`{extra}"

async def handle_search_file_content(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    from services.file_search import search_file_content
    msg = await asyncio.to_thread(search_file_content, step.params["query"], step.params.get("root"))
    await bot.send_message(chat_id=session.user_id, text=msg, parse_mode="Markdown")
    return True, "✅ Полнотекстовый поиск выполнен"

async def handle_delete_item(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    # Подтверждение опасной операции теперь берёт на себя PolicyEngine
    # (delete_item помечен как RiskLevel.CONFIRM в security/risk.py) —
    # к моменту вызова этого handler'а пользователь уже подтвердил действие
    # через generic-диалог в core/executor.py / handlers/menu/callback_router.py.
    target_p = resolve_path_aliases(step.params["path"])
    if not target_p.exists():
        return False, f"❌ Путь `{target_p}` не существует."
    try:
        import send2trash
        # Отправляем в Корзину вместо безвозвратного удаления (shutil.rmtree/unlink) —
        # так операцию можно отменить, если пользователь ошибся с путём.
        await asyncio.to_thread(send2trash.send2trash, str(target_p))
    except Exception as e:
        return False, f"❌ Не удалось удалить `{target_p}`: {e}"
    return True, f"🗑️ Перемещено в Корзину: `{target_p}`"
