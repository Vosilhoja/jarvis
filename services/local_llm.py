"""
Local LLM adapter for llama/ollama/text-generation-webui-like local models.

Behavior:
- If env LOCAL_LLM_API is set, send an HTTP POST {prompt} to that endpoint and return the text.
- Else use the local Ollama HTTP API when it is available.
- The CLI is only a last-resort fallback.

This is intentionally conservative: it prefers an explicit HTTP endpoint, then Ollama HTTP.
"""
import logging
import os
import shutil
import subprocess
import time

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger("jarvis.local_llm")

LOCAL_LLM_API = os.getenv("LOCAL_LLM_API", "").strip()  # e.g. http://127.0.0.1:5000/api/generate
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
_OLLAMA_DISABLED_UNTIL = 0.0
_OLLAMA_FAILURE_COOLDOWN_SEC = 60.0
_OLLAMA_MODEL_CACHE = ""
_OLLAMA_MODEL_CACHE_AT = 0.0
_OLLAMA_MODEL_CACHE_TTL_SEC = 600.0


def _ollama_is_temporarily_disabled() -> bool:
    return time.monotonic() < _OLLAMA_DISABLED_UNTIL


def _disable_ollama() -> None:
    global _OLLAMA_DISABLED_UNTIL
    _OLLAMA_DISABLED_UNTIL = time.monotonic() + _OLLAMA_FAILURE_COOLDOWN_SEC


def _get_ollama_model() -> str:
    global _OLLAMA_MODEL_CACHE, _OLLAMA_MODEL_CACHE_AT
    explicit_model = OLLAMA_MODEL or LOCAL_LLM_MODEL
    if explicit_model:
        return explicit_model
    now = time.monotonic()
    if _OLLAMA_MODEL_CACHE and now - _OLLAMA_MODEL_CACHE_AT < _OLLAMA_MODEL_CACHE_TTL_SEC:
        return _OLLAMA_MODEL_CACHE
    try:
        proc = subprocess.run(
            ["ollama", "list"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=3,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        for line in proc.stdout.decode("utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line and not line.lower().startswith(("name", "id")):
                _OLLAMA_MODEL_CACHE = line.split()[0]
                _OLLAMA_MODEL_CACHE_AT = now
                return _OLLAMA_MODEL_CACHE
    except Exception:
        pass
    return ""


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=0.4, min=0.4, max=2),
    retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    reraise=True,
)
def _post_json(url: str, payload: dict, timeout: int):
    import requests
    response = requests.post(url, json=payload, timeout=timeout)
    response.raise_for_status()
    return response


def ask_local_llm(prompt: str, timeout: int = 30) -> str:
    """Query a local LLM via HTTP endpoint or Ollama HTTP API.

    Returns raw text response. Raises RuntimeError if no local LLM is available or call fails.
    """
    if LOCAL_LLM_API:
        try:
            payload = {"prompt": prompt, "max_tokens": 1024}
            resp = _post_json(LOCAL_LLM_API, payload, timeout)
            # Try common response shapes
            j = resp.json()
            if isinstance(j, dict):
                for k in ("text", "result", "response", "output", "generated_text"):
                    if k in j and isinstance(j[k], str):
                        return j[k]
                # If 'choices' present (OpenAI style)
                if "choices" in j and isinstance(j["choices"], list) and j["choices"]:
                    c = j["choices"][0]
                    if isinstance(c, dict) and "text" in c:
                        return c["text"]
                    if isinstance(c, str):
                        return c
            # Fallback to raw text
            return resp.text
        except Exception as e:
            logger.exception("LOCAL_LLM_API request failed: %s", e)
            raise RuntimeError(f"LOCAL_LLM_API request failed: {e}")

    if _ollama_is_temporarily_disabled():
        raise RuntimeError("Локальная модель временно отключена после неудачного запроса")

    # Prefer Ollama's local HTTP API: it avoids process startup overhead and
    # supports structured, non-interactive requests.
    if shutil.which("ollama"):
        model = _get_ollama_model()
        if not model:
            raise RuntimeError("Ollama не содержит ни одной установленной модели")
        try:
            response = _post_json(
                f"{OLLAMA_HOST}/api/generate",
                {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "keep_alive": "30s",
                    "options": {"num_predict": 256},
                },
                timeout,
            )
            result = response.json()
            out = result.get("response", "") if isinstance(result, dict) else ""
            if out:
                return str(out).strip()
            raise RuntimeError("Ollama вернула пустой ответ")
        except Exception as e:
            _disable_ollama()
            logger.warning("Ollama HTTP API недоступен: %s", e)
            raise RuntimeError(f"Ollama недоступна: {e}")

    # No supported interface found
    raise RuntimeError("No local LLM configured: set LOCAL_LLM_API or install ollama CLI")
