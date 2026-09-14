"""
Диагностика качества Wi-Fi во времени — в отличие от get_wifi_networks() /
get_mac_and_hostname() (разовый снимок), этот модуль периодически (из
scheduler.py::background_monitoring_loop) сэмплирует уровень сигнала ТЕКУЩЕГО
подключения и копит историю, чтобы можно было ответить на вопрос
"а сеть вообще стабильная или скачет весь день?".
"""
from __future__ import annotations

import re
import subprocess
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

import msgspec

from config import WIFI_HISTORY_PATH

logger = logging.getLogger("jarvis")

_MAX_HISTORY_SAMPLES = 4000  # ~2 недели при сэмплировании раз в 2 минуты


def sample_wifi_signal() -> Optional[dict]:
    """
    Блокирующая функция — вызывать через asyncio.to_thread/run_in_executor.
    Возвращает {"ts": unix_time, "ssid": str, "signal_percent": int, "connected": bool}
    или None, если Wi-Fi адаптер не используется (например, работаете по Ethernet).
    """
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True, timeout=8,
        )
        out = result.stdout.decode("cp866", errors="ignore") or result.stdout.decode("utf-8", errors="ignore")
    except Exception as e:
        logger.debug(f"sample_wifi_signal: не удалось выполнить netsh: {e}")
        return None

    if "There is no wireless interface" in out or not out.strip():
        return None

    ssid_m = re.search(r"^\s*SSID\s*:\s*(.+)$", out, re.MULTILINE)
    signal_m = re.search(r"^\s*Signal\s*:\s*(\d+)%", out, re.MULTILINE)
    state_m = re.search(r"^\s*State\s*:\s*(\S+)", out, re.MULTILINE)

    if not signal_m:
        return None

    return {
        "ts": time.time(),
        "ssid": (ssid_m.group(1).strip() if ssid_m else "?"),
        "signal_percent": int(signal_m.group(1)),
        "connected": bool(state_m and "connected" in state_m.group(1).lower()),
    }


def record_wifi_sample() -> None:
    """Сэмплирует текущий сигнал и добавляет в историю (с ротацией по размеру)."""
    sample = sample_wifi_signal()
    if sample is None:
        return

    history = []
    try:
        if WIFI_HISTORY_PATH.exists():
            raw = WIFI_HISTORY_PATH.read_bytes()
            if raw.strip():
                history = msgspec.json.decode(raw)
    except Exception as e:
        logger.warning(f"Не удалось прочитать историю Wi-Fi: {e}")
        history = []

    history.append(sample)
    if len(history) > _MAX_HISTORY_SAMPLES:
        history = history[-_MAX_HISTORY_SAMPLES:]

    try:
        WIFI_HISTORY_PATH.write_bytes(msgspec.json.encode(history))
    except Exception as e:
        logger.warning(f"Не удалось сохранить историю Wi-Fi: {e}")


def get_wifi_diagnostics_report(hours: int = 24) -> str:
    """Отчёт по стабильности Wi-Fi за последние `hours` часов (не разовый снимок)."""
    if not WIFI_HISTORY_PATH.exists():
        return (
            "📶 История сигнала пока не накоплена — сбор идёт в фоне каждые "
            "несколько минут. Загляните сюда чуть позже."
        )

    try:
        raw = WIFI_HISTORY_PATH.read_bytes()
        history = msgspec.json.decode(raw) if raw.strip() else []
    except Exception as e:
        return f"Ошибка чтения истории Wi-Fi: {e}"

    cutoff = time.time() - hours * 3600
    recent = [s for s in history if s.get("ts", 0) >= cutoff]

    if not recent:
        return f"📶 За последние {hours} ч нет данных (возможно, Wi-Fi не использовался — работали по Ethernet)."

    signals = [s["signal_percent"] for s in recent if s.get("signal_percent") is not None]
    disconnects = sum(1 for s in recent if not s.get("connected", True))
    ssids = sorted(set(s.get("ssid", "?") for s in recent))

    if not signals:
        return f"📶 За последние {hours} ч данных о сигнале нет."

    avg_signal = sum(signals) / len(signals)
    min_signal = min(signals)
    max_signal = max(signals)

    first_ts = datetime.fromtimestamp(recent[0]["ts"]).strftime("%H:%M")
    last_ts = datetime.fromtimestamp(recent[-1]["ts"]).strftime("%H:%M")

    quality = "🟢 стабильный" if min_signal >= 60 else ("🟡 нестабильный местами" if min_signal >= 30 else "🔴 часто слабый")

    return (
        f"📶 *Диагностика Wi-Fi за {hours} ч* ({first_ts}–{last_ts}, {len(recent)} замеров):\n\n"
        f"Сеть: {', '.join(ssids)}\n"
        f"Сигнал: сейчас нельзя судить по одной точке — в среднем *{avg_signal:.0f}%*, "
        f"разброс {min_signal}%–{max_signal}%\n"
        f"Качество: {quality}\n"
        f"Разрывов соединения зафиксировано: {disconnects}"
    )
