"""Security checks and small offline utility functions."""
from __future__ import annotations

import base64
import hashlib
import random
import secrets
import string
import uuid

from ._common import _decode, _run


def firewall_status() -> str:
    try:
        r = _run(["netsh", "advfirewall", "show", "allprofiles", "state"], timeout=10)
        return f"🛡 Брандмауэр:\n{_decode(r.stdout)[:400]}"
    except Exception as e:
        return f"Ошибка: {e}"


def defender_status() -> str:
    try:
        r = _run(["powershell", "-NoProfile", "-Command",
                  "Get-MpComputerStatus | Select-Object AMServiceEnabled,AntivirusEnabled,RealTimeProtectionEnabled | Format-List"], timeout=15)
        return "🛡 Microsoft Defender:\n" + (_decode(r.stdout).strip() or "нет данных")
    except Exception as e:
        return f"Ошибка: {e}"


def generate_password(length: int = 16) -> str:
    length = max(8, min(64, int(length or 16)))
    return f"🔐 Пароль: {''.join(secrets.choice(string.ascii_letters + string.digits + '!@#$%^&*') for _ in range(length))}"


def generate_uuid() -> str:
    return f"🆔 UUID: `{uuid.uuid4()}`"


def hash_text(text: str, algo: str = "sha256") -> str:
    algo = (algo or "sha256").lower()
    if algo not in hashlib.algorithms_available:
        algo = "sha256"
    h = hashlib.new(algo)
    h.update(text.encode("utf-8"))
    return f"#️⃣ {algo}: `{h.hexdigest()}`"


def base64_convert(text: str, mode: str = "encode") -> str:
    if (mode or "encode").lower() in ("decode", "декод", "расшифровать"):
        try:
            return "🔓 Base64 decode:\n" + base64.b64decode(text.encode("utf-8"), validate=False).decode("utf-8", errors="replace")[:1500]
        except Exception as e:
            return f"Ошибка decode: {e}"
    return f"🔒 Base64 encode:\n`{base64.b64encode(text.encode('utf-8')).decode('ascii')}`"


def random_util(kind: str = "number", min_value: int = 1, max_value: int = 100) -> str:
    k = (kind or "number").lower()
    if k in ("coin", "монета"):
        return "🪙 " + random.choice(["орёл", "решка"])
    if k in ("dice", "кубик"):
        return f"🎲 Выпало: {random.randint(1, 6)}"
    return f"🎲 Случайное число: {random.randint(int(min_value), int(max_value))}"
