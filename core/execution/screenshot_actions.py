import asyncio
from typing import Tuple
from telegram import Bot, InputFile
from core.intent_schema import StepModel
from core.task_queue import UserTaskSession
from services.screenshot import take_screenshot

async def handle_take_screenshot(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    mon_idx = step.params.get("monitor_index", 0)
    desk_num = step.params.get("desktop_number")
    
    def _capture():
        if desk_num:
            from services.screenshot import take_desktop_screenshot
            buf = take_desktop_screenshot(desk_num, mon_idx)
            name = f"Рабочий стол {desk_num}"
        else:
            buf = take_screenshot(mon_idx)
            name = "Все мониторы" if mon_idx == 0 else f"Монитор {mon_idx}"
        return buf, name

    buf, name = await asyncio.to_thread(_capture)
    await bot.send_photo(
        chat_id=session.user_id,
        photo=InputFile(buf, "screenshot.png"),
        caption=f"📸 Снимок: {name}"
    )
    return True, f"✅ Скриншот ({name}) отправлен"
