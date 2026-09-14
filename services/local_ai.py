"""
Local AI coordinator: lightweight rule-based planner for low-latency, local control of the PC.

This module implements:
- is_control_query(text): heuristic deciding whether a query is a control/PC command
- parse_user_instruction_to_plan_local(text, recent_actions, user_id): returns List[StepModel]

The goal: avoid cloud calls for deterministic PC control tasks and provide a fast, local fallback.
"""
from typing import List, Dict, Any, Optional
import re
import logging

from core.intent_schema import validate_step, StepModel

logger = logging.getLogger("jarvis.local_ai")

_CONTROL_KEYWORDS = [
    "откри", "запуст", "запусти", "открыть", "open", "run",
    "перейди", "переключись", "рабочий стол", "виртуальн",
    "выключи", "выключить", "перезагруз", "перезагрузи", "перезагрузка", "restart",
    "скриншот", "снимок", "скрин", "screenshot",
    "громк", "громкость", "volume", "mute", "звук",
    "ярк", "яркость", "подсветк", "подсветка", "подсветить",
    "нажми", "клик", "нажать", "нажатие", "мышь", "клавиш", "hotkey",
    "закрой", "закрыть", "убить процесс", "kill", "taskkill",
    "напомни", "напоминан", "напомнить",
    "очисти", "удали", "удалить", "создай", "создать", "скопируй", "перемести",
]


def is_control_query(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    # If query contains typical web/chat words: 'википедия', 'что такое', 'расскажи', prefer cloud
    if any(k in t for k in ("википедия", "что такое", "расскажи", "почему", "объясни", "кто такой", "как работает", "документация")):
        return False

    # Heuristic: if any control keyword present → it's a control query
    for kw in _CONTROL_KEYWORDS:
        if kw in t:
            return True
    return False


def _has_fast_rule_match(text: str) -> bool:
    """Return True for commands handled deterministically without an LLM."""
    return bool(re.search(
        r"(?:откри|запуст|open|run)\s+.+|"
        r"скриншот|снимок|скрин|"
        r"громк.*?\d{1,3}|ярк.*?\d{1,3}|"
        r"перезагр|restart|выключи|выключить|shutdown|"
        r"(?:перейди|переключись|переключи).{0,30}\d+.*рабоч|"
        r"(?:добавь|создай)\s+задачу\s+.+|"
        r"(?:покажи|список)\s+(?:мои\s+)?задач|"
        r"(?:выполни|закрой|заверши)\s+задачу\s+.+|"
        r"напомни",
        text,
        re.IGNORECASE,
    ))


def parse_user_instruction_to_plan_local(
    text: str,
    recent_actions: Optional[List[str]] = None,
    user_id: Optional[int] = None,
) -> List[StepModel]:
    """Локальный парсер планов. Сначала пытаемся задействовать локальную LLM (llama/ollama/HTTP),
    если она доступна — просим вернуть JSON-массив шагов. Если LLM недоступна или ответ некорректен,
    откатываемся к rule-based разбору (как раньше).
    """
    t = (text or "").strip()
    steps: List[StepModel] = []

    # Exact learned shortcuts are validated again before execution. PolicyEngine
    # still runs later, so memory can never bypass safety confirmation.
    if user_id is not None:
        try:
            from domain.memory import user_memory
            learned = user_memory.match_phrase(user_id, t)
            if learned:
                return [validate_step(learned["intent"], learned.get("params", {}))]
        except Exception:
            logger.debug("local_ai: learned shortcut ignored", exc_info=True)

    # Простые команды разбираются сразу. Это не только быстрее, но и надёжнее:
    # недоступная Ollama не должна добавлять к каждой команде таймаут в несколько секунд.
    use_local_llm = not _has_fast_rule_match(t)

    # 1) Попробовать локальную LLM только для сложных команд
    try:
        if not use_local_llm:
            raise RuntimeError("fast rule match")
        from services.local_llm import ask_local_llm
        prompt = (
            "STRICT_JSON_ONLY:\n"
            "You are a local planner for PC control. Given the user instruction in Russian, produce ONLY a JSON array (no text, no explanation) describing the plan.\n"
            "Each array element must be an object with exactly two keys: 'intent' (string) and 'params' (object).\n"
            "If you cannot map the instruction to any actionable PC control step, return an empty array [].\n"
            "Allowed intents (examples):\n"
            " - open_application: {\"app_query\":\"chrome\"}\n"
            " - take_screenshot: {\"target\":\"full_screen\"}\n"
            " - set_volume: {\"level\":50}\n"
            " - set_brightness: {\"level\":70}\n"
            " - restart_pc: {\"delay_min\":0}\n"
            " - shutdown_pc: {\"delay_min\":0}\n"
            " - set_reminder: {\"text\":\"Позвонить маме\", \"when\":\"через 20 минут\"}\n"
            "Only output valid JSON array. Do not emit any surrounding commentary or explanation.\n\n"
            f"User instruction: {t}\n"
        )
        logger.info("local_ai: ask_local_llm prompt prepared; invoking local LLM")
        raw = ask_local_llm(prompt, timeout=6)
        logger.info("local_ai: local LLM responded (len=%d)", len(raw) if raw else 0)
        if raw:
            # Попробуем распарсить JSON
            import json
            try:
                parsed = json.loads(raw)
            except Exception:
                # Попытка 2: извлечь первый JSON-массив между '[' и ']' — модели иногда оборачивают JSON в текст
                try:
                    start = raw.find('[')
                    end = raw.rfind(']')
                    if start != -1 and end != -1 and end > start:
                        candidate = raw[start:end+1]
                        parsed = json.loads(candidate)
                    else:
                        raise
                except Exception:
                    parsed = None

            if isinstance(parsed, list):
                for item in parsed:
                    if not isinstance(item, dict):
                        continue
                    intent = item.get("intent")
                    params = item.get("params", {}) or {}
                    try:
                        s = validate_step(intent, params)
                        steps.append(s)
                    except Exception:
                        # Пропускаем шаги, которые не валидируются
                        logger.debug(f"Local LLM returned invalid step for intent={intent}")
                if steps:
                    return steps
            else:
                logger.debug("Local LLM returned non-JSON or unparsable output; falling back to rule-based parsing")
    except Exception as e:
        logger.debug(f"Local LLM not available or failed: {e}")

    # 2) Fallback: rule-based parsing (previous implementation)
    try:
        # Открыть приложение: "открой chrome" / "запусти яндекс музыку"
        m = re.search(r"(?:откри|запуст|open|run)\s+(.+)", t, re.IGNORECASE)
        if m:
            app_q = m.group(1).strip()
            try:
                s = validate_step("open_application", {"app_query": app_q})
                steps.append(s)
                return steps
            except Exception:
                pass

        # Скриншот
        if re.search(r"скриншот|снимок|скрин", t, re.IGNORECASE):
            try:
                s = validate_step("take_screenshot", {"target": "full_screen"})
                steps.append(s)
                return steps
            except Exception:
                pass

        # Громкость: 'громкость 50' или 'установи громкость на 30%'
        m = re.search(r"громк.*?(\d{1,3})", t, re.IGNORECASE)
        if m:
            level = max(0, min(100, int(m.group(1))))
            try:
                s = validate_step("set_volume", {"level": level})
                steps.append(s)
                return steps
            except Exception:
                pass

        # Яркость
        m = re.search(r"ярк.*?(\d{1,3})", t, re.IGNORECASE)
        if m:
            level = max(0, min(100, int(m.group(1))))
            try:
                s = validate_step("set_brightness", {"level": level})
                steps.append(s)
                return steps
            except Exception:
                pass

        # Рестарт / выключение
        if re.search(r"перезагр|restart", t, re.IGNORECASE):
            try:
                s = validate_step("restart_pc", {"delay_min": 0})
                steps.append(s)
                return steps
            except Exception:
                pass
        if re.search(r"выключи|выключить|shutdown", t, re.IGNORECASE):
            try:
                s = validate_step("shutdown_pc", {"delay_min": 0})
                steps.append(s)
                return steps
            except Exception:
                pass

        m_desktop = re.search(
            r"(?:перейди|переключись|переключи)[^0-9]{0,20}"
            r"(?:на|в)?\s*(\d+)\s*(?:-й|-ый|-ой)?\s*рабоч",
            t,
            re.IGNORECASE,
        )
        if m_desktop:
            steps.append(validate_step("switch_virtual_desktop", {
                "desktop_number": int(m_desktop.group(1))
            }))
            return steps

        # Личные задачи: эти команды должны работать даже без Gemini.
        m_task = re.search(r"(?:добавь|создай)\s+задачу\s+(.+)", t, re.IGNORECASE)
        if m_task:
            title = m_task.group(1).strip()
            m_due = re.search(
                r"\s+(через\s+\d+\s*(?:минут\w*|м|час\w*|ч)|"
                r"(?:сегодня|завтра)\s+в\s+\d{1,2}[:.]\d{2})",
                title,
                re.IGNORECASE,
            )
            due = m_due.group(1) if m_due else None
            if m_due:
                title = (title[:m_due.start()] + title[m_due.end():]).strip(" ,")
            steps.append(validate_step("create_task", {"title": title, "due": due}))
            return steps
        if re.search(r"(?:покажи|список)\s+(?:мои\s+)?задач", t, re.IGNORECASE):
            steps.append(validate_step("list_tasks", {}))
            return steps
        m_done = re.search(r"(?:выполни|закрой|заверши)\s+задачу\s+(.+)", t, re.IGNORECASE)
        if m_done:
            steps.append(validate_step("complete_task", {"task_id": m_done.group(1).strip()}))
            return steps

        # Напоминание
        m = re.search(r"напомни(?: меня|)", t)
        if m or "напомни" in t:
            # Попробуем вытащить время 'через 20 минут' и текст
            # Простейший подход: 'напомни через 20 минут позвонить маме'
            m2 = re.search(r"напомни(?:\s+меня)?\s*(.*)", t, re.IGNORECASE)
            message = t
            when = ""
            if m2:
                rest = m2.group(1).strip()
                m_time = re.search(
                    r"((?:через\s+\d+\s*(?:секунд\w*|с|минут\w*|м|час\w*|ч)"
                    r"(?:\s+\d+\s*(?:минут\w*|м))?)|"
                    r"(?:(?:сегодня|завтра|послезавтра)\s+в\s+\d{1,2}[:.]\d{2}|"
                    r"в\s+\d{1,2}[:.]\d{2}))",
                    rest,
                    re.IGNORECASE,
                )
                if m_time:
                    when = m_time.group(1).strip()
                    message = (rest[:m_time.start()] + rest[m_time.end():]).strip(" ,")
                elif rest:
                    message = rest
            if not when:
                return []
            try:
                s = validate_step("set_reminder", {"text": message, "when": when})
                steps.append(s)
                return steps
            except Exception:
                pass

    except Exception as e:
        logger.exception("local_ai parse failed: %s", e)

    return steps
