"""
Статистика использования: запуски приложений и простой ПК.
Хранится в плоском JSON, события старше 30 дней автоматически подчищаются
(чтобы файл не рос бесконечно при постоянно работающем боте).
"""
import json
import logging
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List

logger = logging.getLogger("jarvis")

STATS_DB_PATH = Path(__file__).resolve().parent.parent / "usage_stats.json"
RETENTION_DAYS = 30


def _load() -> Dict[str, Any]:
    if not STATS_DB_PATH.exists():
        return {"app_launches": [], "idle_samples": []}
    try:
        with open(STATS_DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            data.setdefault("app_launches", [])
            data.setdefault("idle_samples", [])
            return data
    except Exception as e:
        logger.error(f"usage_stats: ошибка загрузки {e}")
        return {"app_launches": [], "idle_samples": []}


def _save(data: Dict[str, Any]):
    try:
        with open(STATS_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        logger.error(f"usage_stats: ошибка сохранения {e}")


def _prune(data: Dict[str, Any]) -> Dict[str, Any]:
    cutoff = time.time() - RETENTION_DAYS * 86400
    data["app_launches"] = [e for e in data["app_launches"] if e.get("ts", 0) >= cutoff]
    data["idle_samples"] = [e for e in data["idle_samples"] if e.get("ts", 0) >= cutoff]
    return data


def record_app_launch(app_name: str):
    """Вызывается при каждом успешном запуске приложения через Jarvis."""
    try:
        data = _load()
        data["app_launches"].append({"ts": time.time(), "name": app_name})
        data = _prune(data)
        _save(data)
    except Exception as e:
        logger.debug(f"record_app_launch: {e}")


def record_idle_sample(idle_seconds: float, sample_interval_sec: float):
    """
    Вызывается периодически фоновым циклом. Если пользователь простаивал
    ВСЁ время с прошлой проверки (idle >= interval), считаем этот интервал простоем.
    Это грубая, но дешёвая оценка без необходимости в низкоуровневых хуках ввода.
    """
    try:
        is_idle = idle_seconds >= sample_interval_sec
        data = _load()
        data["idle_samples"].append({"ts": time.time(), "idle": is_idle, "span": sample_interval_sec})
        data = _prune(data)
        _save(data)
    except Exception as e:
        logger.debug(f"record_idle_sample: {e}")


def get_top_visited_sites(days: int = 7, limit: int = 15) -> str:
    """
    Читает историю посещений из Chrome/Edge (SQLite-файл History).
    Файл блокируется работающим браузером на запись, поэтому читаем через
    копию (SQLite в режиме read-only с URI ?mode=ro тоже работает с залоченным файлом).
    """
    import os
    import shutil
    import sqlite3
    import tempfile
    from urllib.parse import urlparse
    from collections import defaultdict

    local_appdata = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        Path(local_appdata) / "Google" / "Chrome" / "User Data" / "Default" / "History",
        Path(local_appdata) / "Microsoft" / "Edge" / "User Data" / "Default" / "History",
    ]

    domain_counts = defaultdict(int)
    domain_titles = {}
    found_any = False
    # Chrome хранит время как микросекунды с 1601-01-01 (Windows FILETIME epoch)
    chrome_epoch_offset = 11644473600  # секунд между 1601 и 1970
    cutoff_chrome_ts = int((time.time() - days * 86400 + chrome_epoch_offset) * 1_000_000)

    for hist_path in candidates:
        if not hist_path.exists():
            continue
        found_any = True
        tmp_copy = None
        try:
            tmp_copy = tempfile.mktemp(suffix="_history_copy.db")
            shutil.copy2(hist_path, tmp_copy)
            conn = sqlite3.connect(tmp_copy)
            cur = conn.cursor()
            cur.execute(
                "SELECT url, title, visit_count FROM urls WHERE last_visit_time >= ? ORDER BY visit_count DESC LIMIT 500",
                (cutoff_chrome_ts,)
            )
            for url, title, visit_count in cur.fetchall():
                try:
                    domain = urlparse(url).netloc.replace("www.", "")
                except Exception:
                    continue
                if not domain:
                    continue
                domain_counts[domain] += visit_count
                domain_titles.setdefault(domain, title or domain)
            conn.close()
        except Exception as e:
            logger.warning(f"get_top_visited_sites: не удалось прочитать {hist_path}: {e}")
        finally:
            if tmp_copy and os.path.exists(tmp_copy):
                try:
                    os.unlink(tmp_copy)
                except Exception:
                    pass

    if not found_any:
        return "🌐 История браузера не найдена (проверьте, что установлен Chrome или Edge)."
    if not domain_counts:
        return f"🌐 За последние {days} дн. посещений не найдено (или браузер использует другой профиль)."

    top = sorted(domain_counts.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    lines = [f"🌐 *Топ посещаемых сайтов за {days} дн.:*\n"]
    for domain, count in top:
        lines.append(f"• {domain} — {count} посещ.")
    lines.append("\n_Данные из истории Chrome/Edge (профиль Default). Если используете другой профиль или браузер — не учтётся._")
    return "\n".join(lines)


def get_weekly_report() -> str:
    """Формирует читаемую еженедельную сводку: топ приложений и простой ПК."""
    data = _load()
    cutoff = time.time() - 7 * 86400

    launches = [e for e in data["app_launches"] if e.get("ts", 0) >= cutoff]
    counts: Dict[str, int] = {}
    for e in launches:
        counts[e["name"]] = counts.get(e["name"], 0) + 1
    top_apps = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:10]

    idle_samples = [e for e in data["idle_samples"] if e.get("ts", 0) >= cutoff]
    idle_seconds = sum(e["span"] for e in idle_samples if e.get("idle"))
    total_tracked_seconds = sum(e["span"] for e in idle_samples)
    idle_hours = idle_seconds / 3600
    active_hours = (total_tracked_seconds - idle_seconds) / 3600

    lines = ["📊 *Статистика за последние 7 дней:*\n"]
    if top_apps:
        lines.append("🚀 *Топ запускаемых приложений:*")
        for name, cnt in top_apps:
            lines.append(f"  • {name}: {cnt}x")
    else:
        lines.append("🚀 Запусков приложений через Jarvis за неделю не зафиксировано.")

    lines.append("")
    if total_tracked_seconds > 0:
        lines.append(f"🖥 *Активность ПК (пока бот работал):*")
        lines.append(f"  • Активно: ~{active_hours:.1f} ч")
        lines.append(f"  • Простой: ~{idle_hours:.1f} ч")
    else:
        lines.append("🖥 Недостаточно данных о простое ПК (бот недавно запущен).")

    lines.append("\n_Учитываются только запуски приложений ЧЕРЕЗ Jarvis (голосом/кнопками), не все запуски в системе. Простой считается только за время, пока бот был запущен._")

    lines.append("")
    try:
        sites_report = get_top_visited_sites(days=7, limit=8)
        # get_top_visited_sites уже содержит свой заголовок "🌐 Топ..." — используем как есть.
        lines.append(sites_report)
    except Exception as e:
        logger.debug(f"get_weekly_report: не удалось получить топ сайтов: {e}")
        lines.append("🌐 Топ сайтов недоступен (не удалось прочитать историю браузера).")

    return "\n".join(lines)
