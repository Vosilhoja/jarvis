import os
import shutil
import asyncio
from typing import Tuple
from pathlib import Path
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
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
    from services.misc_tools import find_file_broad
    query = step.params["query"]
    matches = await asyncio.to_thread(find_file_broad, query)
    if not matches:
        return True, f"🔍 Файл по запросу «{query}» не найден в Рабочем столе/Загрузках/Документах/Изображениях."

    top = matches[0]
    try:
        with open(top, "rb") as f:
            await bot.send_document(chat_id=session.user_id, document=f, filename=top.name)
    except Exception as e:
        return False, f"❌ Не удалось отправить файл {top.name}: {e}"

    extra = ""
    if len(matches) > 1:
        others = "\n".join(f"• {p}" for p in matches[1:])
        extra = f"\n\nЕщё найдено похожих (не отправлены):\n{others}"
    return True, f"📎 Отправлен файл: *{top.name}*{extra}"

async def handle_delete_item(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    target_p = resolve_path_aliases(step.params["path"])
    session.pending_confirmation = {"action": "delete", "path": str(target_p)}
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"⚠️ Да, удалить {target_p.name}", callback_data="confirm_delete_yes")],
        [InlineKeyboardButton("❌ Отмена", callback_data="confirm_delete_no")]
    ])
    await bot.send_message(
        chat_id=session.user_id,
        text=f"⚠️ *Подтверждение удаления!*\nВы уверены, что хотите безвозвратно удалить:\n`{target_p}`?",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    return True, "⏳ Запрошено подтверждение удаления"
