"""PDF prompt #1 indexer (Python standard library only)."""
import argparse
from pathlib import Path
from jarvis_core import ROOT, export_galaxy, get_notes_path, safe_config

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Index all Markdown notes into Jarvis galaxy')
    parser.add_argument('--notes', type=Path, help='Override configured notes folder')
    args = parser.parse_args()
    folder = args.notes or get_notes_path(safe_config(), ROOT)
    result = export_galaxy(folder, ROOT / 'web' / 'data.js')
    print(f'Indexed {len(result["nodes"])} notes and {len(result["links"])} links -> web/data.js')
