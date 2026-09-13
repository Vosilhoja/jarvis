"""Network diagnostic and inspection tools."""
from __future__ import annotations

import logging
import re
import socket
import subprocess
import time

logger = logging.getLogger("jarvis")

CREATE_NO_WINDOW = 0x08000000


def _run(cmd: list[str] | str, timeout: int = 20, shell: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        timeout=timeout,
        shell=shell,
        creationflags=CREATE_NO_WINDOW,
    )


def _decode(data: bytes) -> str:
    for enc in ("utf-8", "cp866", "cp1251"):
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode("utf-8", errors="replace")


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "Не удалось определить"


def get_public_ip() -> str:
    try:
        import urllib.request
        with urllib.request.urlopen("https://api.ipify.org", timeout=5) as r:
            return r.read().decode().strip()
    except Exception as e:
        return f"Ошибка: {e}"


def ping_host(host: str = "8.8.8.8") -> str:
    try:
        result = _run(["ping", "-n", "3", host], timeout=12)
        out = _decode(result.stdout)
        times = re.findall(r"(?:среднее|средняя|average|avg)\s*[=:]\s*(\d+)\s*(?:мс|ms)?", out, re.IGNORECASE)
        loss = re.findall(r"(\d+)%\s*(?:потерь|loss)", out, re.IGNORECASE)
        loss_val = f"{loss[0]}% потерь" if loss else "0% потерь"
        if times:
            return f"✅ Ответ от {host}: среднее {times[0]} мс ({loss_val})"
        times_all = re.findall(r"время[=\s]*(\d+)\s*мс|time[=<]\s*(\d+)\s*ms", out, re.IGNORECASE)
        nums = [int(a or b) for a, b in times_all if a or b]
        if nums:
            avg = sum(nums) // len(nums)
            return f"✅ Ответ от {host}: ~{avg} мс ({loss_val})"
        return f"Ответ от {host}:\n{out[-800:]}"
    except Exception as e:
        return f"Ошибка ping: {e}"


def traceroute_host(host: str = "8.8.8.8") -> str:
    try:
        result = _run(["tracert", "-d", "-h", "12", host], timeout=45)
        out = _decode(result.stdout)
        lines = [ln for ln in out.splitlines() if ln.strip()][:18]
        return "🛤 Трассировка:\n" + "\n".join(lines) if lines else "Нет данных traceroute"
    except Exception as e:
        return f"Ошибка traceroute: {e}"


def get_network_adapters() -> str:
    try:
        import psutil
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        lines = []
        for iface, addr_list in addrs.items():
            st = stats.get(iface)
            status = "🟢" if (st and st.isup) else "🔴"
            for addr in addr_list:
                if addr.family == socket.AF_INET:
                    lines.append(f"{status} {iface}: {addr.address}")
                    break
        return "\n".join(lines) if lines else "Нет адаптеров"
    except Exception as e:
        return f"Ошибка: {e}"


def get_wifi_networks() -> str:
    try:
        result = _run(["netsh", "wlan", "show", "networks"], timeout=10)
        out = _decode(result.stdout)
        ssids = []
        for line in out.splitlines():
            m = re.search(r"SSID\s+\d+\s*:\s*(.+)", line)
            if m:
                name = m.group(1).strip()
                if name:
                    ssids.append(f"📶 {name}")
        return "\n".join(ssids[:12]) if ssids else "Wi-Fi сети в радиусе не найдены"
    except Exception as e:
        return f"Ошибка: {e}"


def get_mac_and_hostname() -> str:
    host = socket.gethostname()
    mac = "н/д"
    try:
        import uuid as _uuid
        mac = ":".join(f"{(_uuid.getnode() >> ele) & 0xff:02x}" for ele in range(40, -8, -8))
    except Exception:
        pass
    return f"🖥 Имя ПК: `{host}`\n🔗 MAC: `{mac}`\n🏠 Локальный IP: `{get_local_ip()}`"


def flush_dns() -> str:
    try:
        r = _run(["ipconfig", "/flushdns"], timeout=10)
        return "✅ Кэш DNS очищен" if r.returncode == 0 else f"⚠️ flushdns: {_decode(r.stdout)[-300:]}"
    except Exception as e:
        return f"Ошибка: {e}"


def ipconfig_summary() -> str:
    try:
        r = _run(["ipconfig"], timeout=10)
        out = _decode(r.stdout)
        keep = []
        for ln in out.splitlines():
            if any(k in ln.lower() for k in ("адаптер", "adapter", "ipv4", "ipv6", "шлюз", "gateway", "маска", "subnet", "dns")):
                keep.append(ln.rstrip())
        return "🌐 ipconfig:\n" + "\n".join(keep[:40]) if keep else out[-1200:]
    except Exception as e:
        return f"Ошибка: {e}"


def speed_test() -> str:
    url = "https://speed.cloudflare.com/__down?bytes=2000000"
    try:
        import urllib.request
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) JarvisBot/1.0"}
        )
        t0 = time.perf_counter()
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
        dt = max(time.perf_counter() - t0, 0.001)
        mb = len(data) / (1024 * 1024)
        mbps = (len(data) * 8 / dt) / 1_000_000
        return f"⚡ Тест загрузки: {mb:.2f} МБ за {dt:.2f} с ≈ {mbps:.1f} Мбит/с (Cloudflare)"
    except Exception as e:
        return f"Не удалось измерить скорость: {e}"
