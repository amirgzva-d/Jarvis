"""Cross-platform launcher; PyInstaller Windows binary uses private, distinct Jarvis data."""
import json
import os
import shutil
import sys
from pathlib import Path
from server import run
from jarvis_core import CONFIG_EXAMPLE


def get_root():
    if not getattr(sys, 'frozen', False):
        return Path(__file__).resolve().parent
    # Bundled data is read-only; writable config and notes live in Jarvis-specific AppData.
    home = Path(os.getenv('LOCALAPPDATA') or Path.home())/'Jarvis'
    home.mkdir(parents=True,exist_ok=True)
    bundle = Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
    shutil.copytree(bundle/'web',home/'web',dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('data.js'))
    if not (home/'notes').exists():
        shutil.copytree(bundle/'notes',home/'notes')
    if not (home/'config.json').exists():
        (home/'config.json').write_text(json.dumps(CONFIG_EXAMPLE,ensure_ascii=False,indent=2),'utf-8')
    return home

if __name__=='__main__':
    run(get_root(),open_browser='--background' not in sys.argv)
