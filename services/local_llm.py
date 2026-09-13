"""
Local LLM adapter for llama/ollama/text-generation-webui-like local models.

Behavior:
- If env LOCAL_LLM_API is set, send an HTTP POST {prompt} to that endpoint and return the text.
- Else if `ollama` CLI is available, use `ollama query <model> --prompt '<prompt>'` to get output.
- Else raise RuntimeError("No local LLM interface found").

This is intentionally conservative: it prefers an explicit HTTP endpoint, then ollama CLI.
"""
import os
import shutil
import subprocess
import logging
import json
from typing import Optional

logger = logging.getLogger("jarvis.local_llm")

LOCAL_LLM_API = os.getenv("LOCAL_LLM_API", "").strip()  # e.g. http://127.0.0.1:5000/api/generate
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "")


def ask_local_llm(prompt: str, timeout: int = 30) -> str:
    """Query a local LLM via HTTP endpoint or ollama CLI.

    Returns raw text response. Raises RuntimeError if no local LLM is available or call fails.
    """
    if LOCAL_LLM_API:
        try:
            import requests
            payload = {"prompt": prompt, "max_tokens": 1024}
            resp = requests.post(LOCAL_LLM_API, json=payload, timeout=timeout)
            resp.raise_for_status()
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

    # Try ollama CLI
    if shutil.which("ollama"):
        # Prefer explicit env vars, else try to auto-detect the first available model from `ollama list`.
        model = OLLAMA_MODEL or LOCAL_LLM_MODEL or ""
        if not model:
            try:
                proc = subprocess.run(["ollama", "list"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
                txt = proc.stdout.decode("utf-8", errors="ignore").strip()
                # Parse the first non-empty, non-header line. Output typically has a header like "NAME    ID    SIZE    MODIFIED"
                for line in txt.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    if line.lower().startswith("name") or line.lower().startswith("id"):
                        # header line — skip
                        continue
                    # data line — first token is the model name
                    parts = line.split()
                    if parts:
                        model = parts[0]
                        logger.info("Auto-detected ollama model: %s", model)
                        break
            except Exception:
                # ignore auto-detection failures and fall back to no-model behavior
                model = model or ""

        cmd = ["ollama", "query"]
        if model:
            cmd.append(model)
        # Use prompt via stdin and capture stdout/stderr
        try:
            proc = subprocess.run(cmd, input=prompt.encode("utf-8"), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
            out = proc.stdout.decode("utf-8", errors="ignore").strip()
            if out:
                return out
            err = proc.stderr.decode("utf-8", errors="ignore").strip()
            raise RuntimeError(f"ollama returned no output, stderr={err}")
        except Exception as e:
            logger.exception("ollama query failed: %s", e)
            raise RuntimeError(f"ollama query failed: {e}")

    # No supported interface found
    raise RuntimeError("No local LLM configured: set LOCAL_LLM_API or install ollama CLI")
