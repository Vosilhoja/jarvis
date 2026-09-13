from pathlib import Path
import tempfile
p = Path(tempfile.gettempdir())
files = list(p.glob('jarvis_live_smoke_*.png'))
if files:
    files_sorted = sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)
    print('Latest screenshot:', files_sorted[0])
    print('Size (KB):', files_sorted[0].stat().st_size//1024)
else:
    print('No live smoke screenshot found')
