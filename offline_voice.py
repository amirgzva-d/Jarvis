"""Optional local speech recognition. No hidden downloads; local model must be present."""
from __future__ import annotations
from pathlib import Path
import importlib.util
import tempfile

MAX_AUDIO = 8 * 1024 * 1024

def status(model_path: str) -> dict:
    path = Path(model_path).expanduser() if model_path else None
    return {'installed':importlib.util.find_spec('faster_whisper') is not None,
            'model_ready':bool(path and path.is_dir() and (path/'model.bin').is_file()),
            'engine':'faster-whisper',
            'note':'Offline STT requires installed faster-whisper and a local model folder.'}

def transcribe(audio: bytes, model_path: str, device: str = 'auto') -> str:
    s = status(model_path)
    if not s['installed'] or not s['model_ready']:
        raise RuntimeError('مدل Whisper محلی آماده نیست. ابتدا بسته و مدل را روی سیستم نصب کن.')
    if not 100 < len(audio) <= MAX_AUDIO:
        raise ValueError('حجم صدا نامعتبر است.')
    from faster_whisper import WhisperModel
    model = WhisperModel(str(Path(model_path).expanduser()),device=device,compute_type='auto',local_files_only=True)
    with tempfile.TemporaryDirectory(prefix='jarvis-whisper-') as td:
        filepath = Path(td)/'recording.webm'
        filepath.write_bytes(audio)
        segments, _ = model.transcribe(str(filepath), language='fa', beam_size=3, vad_filter=True)
        return ' '.join(seg.text.strip() for seg in segments).strip()[:2000]
