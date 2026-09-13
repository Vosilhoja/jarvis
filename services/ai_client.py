import json
import time
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types

from config import (
    GOOGLE_API_KEY,
    AI_MODEL_NAME,
    AI_FALLBACK_MODEL_NAME,
    AI_MODEL_CHAIN,
    AI_TEMPERATURE,
    AI_MAX_STEPS_PER_MESSAGE
)
from core.intent_schema import generate_intents_documentation, PlanModel, StepModel, validate_step
from services.system_info import get_system_metrics

logger = logging.getLogger("jarvis")

_client = None

def get_genai_client() -> genai.Client:
    global _client
    if _client is None:
        if not GOOGLE_API_KEY:
            raise RuntimeError("GOOGLE_API_KEY не установлен в конфигурации.")
        _client = genai.Client(api_key=GOOGLE_API_KEY)
    return _client

def friendly_ai_error(exc: Exception) -> str:
    """Короткое сообщение пользователю без сырого JSON API."""
    err = str(exc)
    if "429" in err or "RESOURCE_EXHAUSTED" in err or "quota" in err.lower():
        return (
            "⚠️ Лимит запросов к ИИ исчерпан.\n"
            "Подождите 1–2 минуты и напишите снова.\n"
            "Если это повторяется каждый день — в `.env` поставьте "
            "`AI_MODEL_NAME=gemini-2.0-flash` (больше бесплатных запросов)."
        )
    if "API_KEY" in err or "401" in err or "403" in err or "UNAUTHENTICATED" in err:
        return "⚠️ Ключ Gemini API не принят. Проверьте GOOGLE_API_KEY в файле .env."
    if "404" in err or "NOT_FOUND" in err:
        return "⚠️ Модель ИИ не найдена. Смените AI_MODEL_NAME в .env на gemini-2.0-flash."
    logger.error("Ошибка Gemini (скрыта от пользователя): %s", exc)
    return "⚠️ ИИ временно недоступен. Попробуйте ещё раз через минуту."


def ask_gemini(prompt: str, history: Optional[List[Dict[str, Any]]] = None) -> str:
    """Диалог с Gemini: перебор моделей без блокирующего sleep."""
    last_err: Optional[Exception] = None
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

    for model_name in AI_MODEL_CHAIN:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents
            )
            text = (response.text or "").strip()
            if text:
                return text
        except Exception as e:
            last_err = e
            logger.warning("ask_gemini модель %s: %s", model_name, e)
            continue

    return friendly_ai_error(last_err or RuntimeError("пустой ответ ИИ"))

def build_system_prompt(recent_actions: Optional[List[str]] = None) -> str:
    """Динамически формирует системный промпт с реестром интентов и контекстом системы."""
    metrics = get_system_metrics()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    recent_act_str = "\n".join([f"- {a}" for a in recent_actions]) if recent_actions else "(нет недавних действий)"
    
    intents_doc = generate_intents_documentation()

    prompt = f"""Ты — Jarvis, персональный резидентный ИИ-ассистент и полноправный оператор компьютера на Windows 10/11.
Текущее системное время: {now_str}

Сводка состояния ПК:
- Загрузка CPU: {metrics['cpu_percent']}%
- Оперативная память: {metrics['ram_percent']}% (свободно {metrics['ram_total_mb'] - metrics['ram_used_mb']} MB)
- Uptime: {metrics['uptime']}

Последние действия сессии:
{recent_act_str}

ТВОЯ ЗАДАЧА:
Проанализировать сообщение пользователя (текст или расшифрованный голос), понять его намерения и разбить запрос на строгую последовательность шагов (intent'ов).
Пользователь может отдавать как одиночные, так и сложные многошаговые команды («перейди в 1 рабочий стол, открой яндекс музыку, сделай скриншот»).
Также пользователь может просто общаться («расскажи шутку», «что такое квантовый компьютер») — для этого используй intent `chat_reply`.

РЕЕСТР ДОСТУПНЫХ INTENT'ОВ И ИХ ПАРАМЕТРОВ:
{intents_doc}

ВАЖНЫЕ ПРАВИЛА:
1. Если пользователь называет приложение неточно, сленгом, опечаткой или сокращением (например 'яндекс музыка', 'янд музыка', 'ymusic', 'хром', 'стим', 'vs code') — ВСЕГДА используй `open_application` с параметром `app_query`, равным тому, что сказал пользователь. Внутренний модуль app_resolver сам найдет нужное приложение.
2. Если в сообщении несколько действий подряд — верни их в поле `steps` строго в порядке их выполнения.
3. Если пользователь присылает только номера (например `4,9,5` или `1 3 5`) — это номера виртуальных рабочих столов для скриншота. Верни шаги `take_screenshot` с `desktop_number` для каждого номера. Не задавай уточняющих вопросов.
4. Не предлагай создавать сайты или веб-приложения. Jarvis — Telegram-бот для управления ПК.
5. Если запрос не связан с управлением ПК — верни ОДИН шаг `chat_reply` с коротким ответом.
6. Ответ ДОЛЖЕН БЫТЬ СТРОГИМ JSON объектом следующего формата без markdown кавычек или лишнего текста:
{{
  "steps": [
    {{"intent": "имя_интента", "params": {{"параметр1": "значение"}}}},
    ...
  ]
}}
"""
    return prompt

def parse_user_instruction_to_plan(user_text: str, recent_actions: Optional[List[str]] = None) -> List[StepModel]:
    """
    Отправляет сообщение пользователя в Gemini и возвращает валидированный список StepModel.
    """
    client = get_genai_client()
    system_prompt = build_system_prompt(recent_actions)
    raw_response_text = ""
    last_err: Optional[Exception] = None
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=AI_TEMPERATURE,
        response_mime_type="application/json"
    )

    for model_to_use in AI_MODEL_CHAIN:
        try:
            response = client.models.generate_content(
                model=model_to_use,
                contents=[user_text],
                config=config
            )
            raw_response_text = response.text.strip() if response.text else ""
            if raw_response_text:
                break
        except Exception as e:
            last_err = e
            logger.warning("Планировщик, модель %s: %s", model_to_use, e)

    if not raw_response_text:
        return [StepModel(intent="chat_reply", params={
            "message": friendly_ai_error(last_err or RuntimeError("пустой ответ ИИ"))
        })]

    # Парсинг JSON
    try:
        # Очистка если модель добавила ```json
        cleaned = raw_response_text
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("\n", 1)[0]
        data = json.loads(cleaned)
    except Exception as e:
        logger.error("Не удалось распарсить JSON от LLM: %s (%s)", raw_response_text[:500], e)
        return [StepModel(intent="chat_reply", params={
            "message": "Не понял команду. Напишите иначе или используйте кнопки меню."
        })]

    steps_raw = data.get("steps", [])
    validated_steps: List[StepModel] = []

    for s in steps_raw[:AI_MAX_STEPS_PER_MESSAGE]:
        intent = s.get("intent", "")
        params = s.get("params", {})
        try:
            step_obj = validate_step(intent, params)
            validated_steps.append(step_obj)
        except Exception as err:
            logger.warning(f"Ошибка валидации шага {intent}: {err}")

    if not validated_steps:
        validated_steps.append(StepModel(intent="chat_reply", params={"message": "Я не смог определить команду. Попробуйте сформулировать иначе."}))

    return validated_steps

def ask_gemini_app_choice(query: str, candidates: List[Dict[str, Any]]) -> Optional[int]:
    """
    ИИ-этап разрешения приложения: модель выбирает правильного кандидата из найденных.
    Возвращает индекс лучшего кандидата (0..N) или None.
    """
    client = get_genai_client()
    options_text = ""
    for idx, c in enumerate(candidates):
        options_text += f"[{idx}] {c['display_name']} (путь: {c['exec_path']})\n"

    prompt = (
        f"Пользователь запросил запуск приложения: «{query}».\n"
        f"Вот кандидаты, найденные на компьютере:\n{options_text}\n"
        f"Какое приложение больше всего соответствует запросу пользователя?\n"
        f"Верни строгий JSON: {{\"choice_index\": <номер от 0 до {len(candidates)-1} или null>, \"confidence\": <число от 0.0 до 1.0>}}"
    )

    try:
        resp = client.models.generate_content(
            model=AI_MODEL_NAME,
            contents=[prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.0)
        )
        data = json.loads(resp.text)
        idx = data.get("choice_index")
        conf = float(data.get("confidence", 0.0))
        if idx is not None and 0 <= idx < len(candidates) and conf >= 0.5:
            return idx
    except Exception as e:
        logger.warning(f"Ошибка в ask_gemini_app_choice: {e}")

    return None
