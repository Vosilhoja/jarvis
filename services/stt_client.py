import io
import logging
from google import genai
from google.genai import types
from config import GOOGLE_API_KEY, STT_LANGUAGE

logger = logging.getLogger("jarvis")

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=GOOGLE_API_KEY)
    return _client

def transcribe_audio_bytes(audio_bytes: bytes, mime_type: str = "audio/ogg") -> str:
    """
    Распознает голосовое аудиосообщение (OGG/OGA/MP3/WAV) напрямую с помощью Google Gemini Multimodal.
    Не требует стороннего ffmpeg или локальных тяжелых моделей.
    """
    client = _get_client()
    logger.info(f"Отправка аудиофайла ({len(audio_bytes)} байт) в Gemini STT...")

    prompt = (
        f"Ты — модуль транскрибации речи для голосового ассистента Jarvis. "
        f"Твоя задача — точно транскрибировать данную аудиозапись в текст. "
        f"Основной язык речи: {STT_LANGUAGE}, однако пользователь может употреблять технические термины и английские названия приложений "
        f"(например 'Яндекс Музыка', 'Chrome', 'Visual Studio Code', 'Steam'). "
        f"Не добавляй от себя никаких комментариев, приветствий или знаков в кавычках. "
        f"Верни ТОЛЬКО чистый расшифрованный текст пользователя."
    )

    try:
        audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[audio_part, prompt]
        )
        text = response.text.strip() if response.text else ""
        logger.info(f"Результат STT: '{text}'")
        return text
    except Exception as e:
        logger.error(f"Ошибка при распознавании голоса через Gemini: {e}", exc_info=True)
        # Fallback на gemini-2.0-flash
        try:
            audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[audio_part, prompt]
            )
            return response.text.strip() if response.text else ""
        except Exception as ex:
            raise RuntimeError(f"Не удалось распознать голос: {ex}")
