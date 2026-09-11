import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types

from config import (
    GOOGLE_API_KEY,
    AI_MODEL_NAME,
    AI_FALLBACK_MODEL_NAME,
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
3. Если запрос не связан с управлением ПК или поиском — верни ОДИН шаг `chat_reply` с твоим вежливым и полезным ответом.
4. Ответ ДОЛЖЕН БЫТЬ СТРОГИМ JSON объектом следующего формата без markdown кавычек или лишнего текста:
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

    model_to_use = AI_MODEL_NAME
    raw_response_text = ""

    for attempt in range(2):
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=AI_TEMPERATURE,
                response_mime_type="application/json"
            )

            response = client.models.generate_content(
                model=model_to_use,
                contents=[user_text],
                config=config
            )
            raw_response_text = response.text.strip() if response.text else ""
            break
        except Exception as e:
            logger.warning(f"Ошибка модели {model_to_use} (попытка {attempt+1}): {e}")
            model_to_use = AI_FALLBACK_MODEL_NAME

    if not raw_response_text:
        # Fallback: обычный разговор
        return [StepModel(intent="chat_reply", params={"message": "Извините, не удалось связаться с сервером ИИ."})]

    # Парсинг JSON
    try:
        # Очистка если модель добавила ```json
        cleaned = raw_response_text
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("\n", 1)[0]
        data = json.loads(cleaned)
    except Exception as e:
        logger.error(f"Не удалось распарсить JSON от LLM: {raw_response_text} ({e})")
        return [StepModel(intent="chat_reply", params={"message": raw_response_text})]

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
