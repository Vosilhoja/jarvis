"""File and folder utilities."""
from __future__ import annotations

import os
import shutil
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from ._common import _decode, _run


def _recycle_bin_item_count() -> int:
    try:
        r = _run(["powershell", "-NoProfile", "-Command",
                  "(New-Object -ComObject Shell.Application).NameSpace(10).Items().Count"], timeout=15)
        return int(_decode(r.stdout).strip())
    except Exception:
        return -1


def empty_recycle_bin() -> str:
    try:
        count_before = _recycle_bin_item_count()
        r = _run(["powershell", "-NoProfile", "-Command",
                  "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"], timeout=20)
        if r.returncode == 0:
            return "🗑 Корзина очищена."
        if count_before == 0:
            return "🗑 Корзина уже была пуста."
        return f"⚠️ Не удалось очистить корзину (элементов было: {count_before}). {_decode(r.stderr).strip() or 'Ошибка PowerShell.'}"
    except Exception as e:
        return f"Ошибка очистки корзины: {e}"


def recycle_bin_info() -> str:
    try:
        r = _run(["powershell", "-NoProfile", "-Command",
                  "(New-Object -ComObject Shell.Application).NameSpace(10).Items() | Measure-Object | Select-Object -ExpandProperty Count"], timeout=15)
        return f"🗑 В корзине элементов: {_decode(r.stdout).strip() or '?'}"
    except Exception as e:
        return f"Ошибка: {e}"


def get_desktop_folder_sizes() -> str:
    desktop = Path.home() / "Desktop"
    if not desktop.exists():
        return "Рабочий стол не найден"
    lines = []
    try:
        for item in sorted(desktop.iterdir())[:15]:
            try:
                if item.is_dir():
                    size = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
                    lines.append(f"📁 {item.name}: {size / (1024**2):.1f} МБ")
                else:
                    lines.append(f"📄 {item.name}: {item.stat().st_size / 1024:.0f} КБ")
            except Exception:
                if item.is_dir():
                    lines.append(f"📁 {item.name}: (нет доступа)")
    except Exception as e:
        return f"Ошибка: {e}"
    return "\n".join(lines) if lines else "Рабочий стол пуст"


def search_files(query: str, search_dir: Optional[str] = None) -> str:
    base = Path(search_dir) if search_dir else Path.home() / "Desktop"
    results = []
    try:
        for p in base.rglob(f"*{query}*"):
            results.append(str(p))
            if len(results) >= 12:
                break
    except Exception as e:
        return f"Ошибка поиска: {e}"
    return (f"🔍 По запросу «{query}» ничего не найдено в {base}" if not results
            else "🔍 Найдено:\n" + "\n".join(results))


def find_file_broad(query: str, max_results: int = 8, timeout_sec: float = 6.0) -> list[Path]:
    roots = [Path.home() / x for x in ("Desktop", "Downloads", "Documents", "Pictures")]
    q, matches, start = query.strip().lower(), [], time.time()
    for root in roots:
        if not root.exists():
            continue
        try:
            for p in root.rglob("*"):
                if time.time() - start > timeout_sec:
                    break
                if p.is_file() and q in p.name.lower():
                    matches.append(p)
        except Exception:
            continue
        if time.time() - start > timeout_sec:
            break
    matches.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    return matches[:max_results]


def get_downloads_list() -> str:
    downloads = Path.home() / "Downloads"
    if not downloads.exists():
        return "Папка Загрузки не найдена"
    try:
        lines = [f"{'📁' if f.is_dir() else '📄'} {f.name} ({f.stat().st_size // 1024} КБ)"
                 for f in sorted(downloads.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:10]]
        return "\n".join(lines) if lines else "Папка Загрузки пуста"
    except Exception as e:
        return f"Ошибка: {e}"


def get_file_info(path: str) -> str:
    p = Path(os.path.expandvars(path))
    if not p.exists():
        return f"❌ Не найдено: {p}"
    st, kind = p.stat(), "папка" if p.is_dir() else "файл"
    return (f"📄 {p.name}\nТип: {kind}\nПуть: {p}\nРазмер: {st.st_size} байт "
            f"({st.st_size/1024:.1f} КБ)\nИзменён: {datetime.fromtimestamp(st.st_mtime):%Y-%m-%d %H:%M}")


def zip_path(source: str, destination: Optional[str] = None) -> str:
    src = Path(os.path.expandvars(source))
    if not src.exists():
        return f"❌ Нет такого пути: {src}"
    dest = Path(os.path.expandvars(destination)) if destination else src.with_suffix(".zip")
    if src.is_dir():
        archive = shutil.make_archive(str(dest.with_suffix("")), "zip", root_dir=src)
        return f"📦 Архив создан: {archive}"
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(src, src.name)
    return f"📦 Архив создан: {dest}"


def unzip_path(source: str, destination: Optional[str] = None) -> str:
    src = Path(os.path.expandvars(source))
    if not src.exists():
        return f"❌ Архив не найден: {src}"
    dest = Path(os.path.expandvars(destination)) if destination else src.with_suffix("")
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src, "r") as zf:
        zf.extractall(dest)
    return f"📂 Распаковано в: {dest}"


def get_folder_changes_today(path: str) -> str:
    import humanize
    from core.execution.common import resolve_path_aliases
    try:
        folder = resolve_path_aliases(path)
        if not folder.exists() or not folder.is_dir():
            return f"❌ Папка не найдена: `{folder}`"
        today, changed, checked, max_check = datetime.now().date(), [], 0, 20000
        hit_limit = False
        for item in folder.rglob("*"):
            checked += 1
            if checked > max_check:
                hit_limit = True
                break
            if item.is_file():
                try:
                    mtime = datetime.fromtimestamp(item.stat().st_mtime)
                    if mtime.date() == today:
                        changed.append((mtime, item))
                except Exception:
                    continue
        warning = (f"\n\n⚠️ _Папка большая — просмотрены только первые {max_check} объектов, "
                   "возможно, есть ещё изменения глубже в дереве. Уточните запрос подпапкой поменьше._"
                   if hit_limit else "")
        if not changed:
            return f"📂 За сегодня в «{folder.name}» изменений не найдено.{warning}"
        changed.sort(key=lambda x: x[0], reverse=True)
        lines = [f"• {m:%H:%M} — {p.name} ({humanize.naturalsize(p.stat().st_size, binary=True)})"
                 for m, p in changed[:30]]
        extra = f"\n\n…и ещё {len(changed) - 30} файл(ов)" if len(changed) > 30 else ""
        return f"📂 *Изменено сегодня в «{folder.name}»* ({len(changed)}):\n\n" + "\n".join(lines) + extra + warning
    except Exception as e:
        return f"Ошибка: {e}"
