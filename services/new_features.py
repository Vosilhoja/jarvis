"""
New features utilities: small non-destructive helpers added as requested.
"""
from __future__ import annotations

import platform
import psutil
from typing import Dict


def generate_system_health_summary() -> Dict[str, str]:
    """Return a small summary of system health (safe, read-only).
    Includes CPU load, memory usage, disk free for C:\ and OS info.
    """
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('C:\\' if platform.system() == 'Windows' else '/')
        return {
            'os': platform.platform(),
            'cpu_percent': f"{cpu}%",
            'memory': f"{mem.percent}% used ({mem.available // (1024*1024)} MB free)",
            'disk_c': f"{disk.percent}% used ({disk.free // (1024*1024)} MB free)"
        }
    except Exception as e:
        return {'error': str(e)}


def suggest_improvements() -> Dict[str, str]:
    """Simple heuristic suggestions based on system health."""
    try:
        summary = generate_system_health_summary()
        if 'error' in summary:
            return {'note': 'Cannot run checks', 'detail': summary.get('error')}
        suggestions = []
        try:
            cpu = float(summary['cpu_percent'].rstrip('%'))
            if cpu > 80:
                suggestions.append('High CPU load detected — consider closing heavy apps')
        except Exception:
            pass
        try:
            mem_percent = float(summary['memory'].split('%')[0])
            if mem_percent > 85:
                suggestions.append('Low available memory — consider restarting memory-heavy apps or system')
        except Exception:
            pass
        if not suggestions:
            suggestions = ['No immediate suggestions; system looks healthy']
        return {'suggestions': '\n'.join(suggestions)}
    except Exception as e:
        return {'error': str(e)}
