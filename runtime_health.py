"""Privacy-preserving, read-only readiness checks for the Jarvis dashboard."""
from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from pathlib import Path


def _has_module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def provider_readiness(cfg: dict) -> dict:
    provider = str(cfg.get('provider') or 'notes-only').strip().lower()
    if provider == 'codex-cli':
        present = bool(shutil.which('codex'))
        return {'provider': provider, 'configured': present,
                'verified': False, 'detail': 'Codex نصب است؛ ورود حساب هنوز باید با پرسش واقعی آزموده شود.' if present
                else 'Codex نصب نیست. npm install -g @openai/codex و سپس codex login را اجرا کن.'}
    if provider == 'claude-cli':
        present = bool(shutil.which('claude'))
        return {'provider': provider, 'configured': present,
                'verified': False, 'detail': 'Claude Code پیدا شد؛ ورود حساب با پرسش واقعی بررسی شود.' if present
                else 'ابتدا Claude Code را نصب و در حساب خود وارد شو.'}
    if provider in ('openai-api', 'anthropic-api'):
        env = 'OPENAI_API_KEY' if provider == 'openai-api' else 'ANTHROPIC_API_KEY'
        present = bool(str(cfg.get('api_key') or os.environ.get(env) or '').strip())
        return {'provider': provider, 'configured': present,
                'verified': False, 'detail': 'کلید تنظیم شده است؛ اتصال هنوز آزمایش نشده.' if present
                else 'کلید API تنظیم نشده است. هرگز کلید را در چت یا GitHub نگذار.'}
    if provider in ('notes-only', 'offline'):
        return {'provider': provider, 'configured': True, 'verified': True,
                'detail': 'حالت یادداشت‌ها فعال است؛ پاسخ هوش مصنوعی مولد نیست.'}
    return {'provider': provider, 'configured': False, 'verified': False,
            'detail': 'ارائه‌دهنده مدل در تنظیمات شناخته‌شده نیست.'}


def diagnostics(cfg: dict, native_wake: dict | None = None) -> dict:
    brain = provider_readiness(cfg)
    model = Path(str(cfg.get('offline_stt_model') or '')).expanduser()
    model_ready = bool(str(cfg.get('offline_stt_model') or '') and model.is_dir()
                       and (model / 'model.bin').is_file())
    whisper_installed = _has_module('faster_whisper')
    microphone_engine = _has_module('sounddevice')
    natural_voice = _has_module('edge_tts') and bool(cfg.get('online_tts', True))
    return {
        'brain': brain,
        'persian_voice': {
            'configured': natural_voice, 'verified': False,
            'detail': 'موتور Edge TTS در دسترس است؛ صحت صدای آنلاین با پخش واقعی سنجیده شود.' if natural_voice
            else 'edge-tts نصب یا در تنظیمات غیرفعال است؛ صدای فارسی مرورگر می‌تواند جایگزین باشد.'},
        'local_speech': {
            'configured': model_ready and whisper_installed, 'model_ready': model_ready,
            'engine_installed': whisper_installed, 'microphone_engine': microphone_engine,
            'verified': False,
            'detail': 'مدل و موتور محلی آماده‌اند؛ دقت تشخیص باید با گفتار واقعی آزموده شود.'
                      if model_ready and whisper_installed else
                      'برای Whisper آفلاین، faster-whisper و پوشه مدل محلی حاوی model.bin لازم‌اند.'},
        'native_wake': native_wake or {},
        'windows_control': {'supported': sys.platform == 'win32',
                            'detail': 'فرمان‌های حساس فقط با تأیید UI اجرا می‌شوند.'},
        'live_information': {'implemented': True, 'verified': False,
                             'detail': 'هواشناسی، RSS اخبار و نرخ مرجع ارز نیازمند اتصال شبکه و آزمون منبع‌اند.'}
    }
