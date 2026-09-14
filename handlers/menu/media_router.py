"""Media and audio keyboard actions."""
from handlers.menu.input_flows import ask_for_number

async def handle_media(update, context, text: str) -> bool:
    from services import media_control as media
    actions = {
        "⏮ Назад трек": (media.media_prev, "⏮ Предыдущий трек"),
        "⏯ Play/Pause": (media.media_play_pause, "⏯ Play/Pause"),
        "⏭ След трек": (media.media_next, "⏭ Следующий трек"),
        "⏹ Стоп": (media.media_stop, "⏹ Остановлено"),
    }
    if text in actions:
        fn, reply = actions[text]; fn(); await update.message.reply_text(reply); return True
    if text in ("🔉 Тише (-10%)", "🔊 Громче (+10%)", "🔇 Mute"):
        direction = {"🔉 Тише (-10%)": "down", "🔊 Громче (+10%)": "up", "🔇 Mute": "mute"}[text]
        await update.message.reply_text(f"{text.split()[0]} {media.change_volume(direction)}"); return True
    if text == "🎙 Установить громкость":
        await ask_for_number(update, context, "awaiting_volume", "🎙 *Громкость:* введите значение от 0 до 100\n\n_Например: 50_"); return True
    if text == "🎚 Громкость приложения":
        context.user_data["awaiting_app_volume"] = True
        await update.message.reply_text("🎚 *Громкость приложения:* напишите имя процесса и процент через пробел.\n\n_Например: `chrome 30` или `spotify 80`_", parse_mode="Markdown"); return True
    if text.startswith("🎚 Звук "):
        try:
            level = int(text.replace("🎚 Звук ", "").replace("%", "").strip())
            if media.set_volume_pycaw(level):
                result = f"🎚 Громкость установлена на {level}%"
            else:
                result = f"🎚 {media.change_volume('up' if level > 50 else 'down', level=level)}"
        except Exception as exc:
            result = f"Ошибка: {exc}"
        await update.message.reply_text(result); return True
    if text == "🎬 YouTube":
        import webbrowser
        webbrowser.open("https://www.youtube.com")
        await update.message.reply_text("🎬 Открываю YouTube в браузере"); return True
    return False
