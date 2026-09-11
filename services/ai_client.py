import logging
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from config import GOOGLE_API_KEY

logger = logging.getLogger("jarvis")

_client: Optional[genai.Client] = None

def get_genai_client() -> genai.Client:
    global _client
    if _client is None:
        if not GOOGLE_API_KEY:
            raise RuntimeError("GOOGLE_API_KEY не установлен в конфигурации.")
        _client = genai.Client(api_key=GOOGLE_API_KEY)
    return _client

SYSTEM_INSTRUCTION = """Ты — Jarvis, персональный голосовой и текстовый ассистент, управляющий рабочим компьютером на Windows.
Отвечай точно, вежливо, информативно и по делу. Ты можешь советовать команды Windows, помогать с программированием и отвечать на любые общие вопросы."""

def ask_gemini(prompt: str, history: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    Отправляет запрос модели Gemini с сохранением истории диалога.
    """
    try:
        client = get_genai_client()
        contents = []
        if history:
            for item in history:
                contents.append(types.Content(
                    role=item.get("role", "user"),
                    parts=[types.Part.from_text(text=p.get("text", "")) for p in item.get("parts", [])]
                ))

        contents.append(types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)]
        ))

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.7,
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=config
        )

        if response.text:
            return response.text
        return "Ответ от Gemini пуст или заблокирован фильтрами безопасности."

    except Exception as e:
        logger.error(f"Ошибка при вызове Gemini API: {e}", exc_info=True)
        return f"⚠️ Ошибка вызова Gemini API: {e}"
