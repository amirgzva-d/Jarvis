"""Opt-in native wake listener while Jarvis process runs, independent of browser tabs.

Uses locally installed sounddevice and faster-whisper, a locally provisioned model,
and never executes spoken Windows actions without the visible UI confirmation path.
No audio is written to files or uploaded by this worker.
"""
from __future__ import annotations
import importlib.util
import os
import sys
import threading
import time
import re
import unicodedata
from pathlib import Path

WAKE_PHRASES = ('hey jarvis', 'hi jarvis', 'jarvis', 'هی جارویس', 'سلام جارویس', 'جارویس', 'هی جرویس')


def wake_phrase_detected(value: str) -> bool:
    text = unicodedata.normalize('NFKC',str(value or '')).lower().replace('ي','ی').replace('ك','ک')
    text = re.sub(r'[^\w\u0600-\u06ff]+',' ',text).strip()
    return any(re.search(r'(?<!\w)' + re.escape(phrase) + r'(?!\w)',text) for phrase in WAKE_PHRASES)


def load_whisper_with_cpu_fallback(model_path: str, device: str, factory):
    requested = device if device in ('auto','cpu','cuda') else 'cpu'
    try:
        return factory(model_path,device=requested,compute_type='int8',local_files_only=True), requested, False
    except Exception:
        if requested=='cpu': raise
        return factory(model_path,device='cpu',compute_type='int8',local_files_only=True), 'cpu', True

class WakeListener:
    def __init__(self, config: dict, on_wake):
        self.config=config
        self.on_wake=on_wake
        self._thread=None
        self._stop=threading.Event()
        self.state='disabled'
        self.detail=''
        self.last_wake=''
    def readiness(self):
        model=Path(str(self.config.get('offline_stt_model') or '')).expanduser()
        packages=all(importlib.util.find_spec(m) for m in ('numpy','sounddevice','faster_whisper'))
        ready=bool(str(self.config.get('offline_stt_model') or '') and (model/'model.bin').is_file() and packages)
        return {'ready':ready,'native':sys.platform=='win32','active':bool(self._thread and self._thread.is_alive()),
                'state':self.state,'detail':self.detail,'last_wake':self.last_wake,
                'privacy':'صدای میکروفون فقط در حافظه و روی همین رایانه پردازش می‌شود؛ اجرای فرمان حساس خودکار نیست.'}
    def start(self):
        if sys.platform!='win32':
            self.state='unavailable';self.detail='شنود پس‌زمینه این نسخه مخصوص ویندوز است.'
            return False
        if self._thread and self._thread.is_alive():return True
        if not self.readiness()['ready']:
            self.state='unavailable';self.detail='بسته‌های numpy، sounddevice، faster-whisper و مدل آفلاین لازم‌اند.'
            return False
        self._stop.clear()
        self._thread=threading.Thread(target=self._run,name='jarvis-native-wake',daemon=True)
        self._thread.start()
        return True
    def stop(self):
        self._stop.set();self.state='disabled'
    def _run(self):
        try:
            import numpy as np
            import sounddevice as sd
            from faster_whisper import WhisperModel
            model,actual_device,fallback=load_whisper_with_cpu_fallback(
                str(Path(self.config['offline_stt_model']).expanduser()),
                str(self.config.get('offline_stt_device') or 'cpu'),WhisperModel)
            self.state='listening'
            self.detail='میکروفون فعال است؛ پردازش روی CPU برای سازگاری با GPU انجام می‌شود.' if fallback else f'میکروفون محلی فعال است ({actual_device}).'
            sample_rate=16000
            last_trigger=0.0
            with sd.InputStream(samplerate=sample_rate,channels=1,dtype='float32',blocksize=4096) as stream:
                while not self._stop.is_set():
                    pieces=[]
                    remaining=sample_rate*4
                    while remaining>0 and not self._stop.is_set():
                        audio,_overflow=stream.read(min(4096,remaining))
                        pieces.append(audio[:,0].copy());remaining-=len(audio)
                    if self._stop.is_set():break
                    recorded=np.concatenate(pieces)
                    if float(np.sqrt(np.mean(recorded*recorded)))<0.008:
                        continue
                    segments,_=model.transcribe(recorded,language='fa',beam_size=1,condition_on_previous_text=False,
                                                vad_filter=True,without_timestamps=True)
                    detected=' '.join(s.text for s in segments).lower().strip()
                    if wake_phrase_detected(detected) and time.monotonic()-last_trigger>8:
                        last_trigger=time.monotonic()
                        self.last_wake=time.strftime('%Y-%m-%dT%H:%M:%S')
                        self.on_wake(detected[:450])
        except Exception as exc:
            self.state='error';self.detail=f'{type(exc).__name__}: {str(exc)[:160]}'
        finally:
            if self.state!='error':self.state='disabled'


def startup_status() -> dict:
    if sys.platform!='win32':return {'supported':False,'enabled':False}
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
            try:val,_=winreg.QueryValueEx(key,'JarvisNativeWake');return {'supported':True,'enabled':bool(val)}
            except FileNotFoundError:return {'supported':True,'enabled':False}
    except OSError:
        return {'supported':True,'enabled':False}

def set_autostart(enabled: bool, launcher: Path):
    """Configure current-user startup only after explicit local UI consent."""
    if sys.platform!='win32':raise RuntimeError('اجرای خودکار هنگام ورود فقط برای ویندوز است.')
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
        if enabled:
            if getattr(sys,'frozen',False):
                command=f'"{sys.executable}" --background'
            else:
                exe=sys.executable
                if exe.lower().endswith('python.exe'):
                    maybe=Path(exe).with_name('pythonw.exe')
                    if maybe.exists():exe=str(maybe)
                command=f'"{exe}" "{launcher}" --background'
            winreg.SetValueEx(key,'JarvisNativeWake',0,winreg.REG_SZ,command)
        else:
            try:winreg.DeleteValue(key,'JarvisNativeWake')
            except FileNotFoundError:pass
    return startup_status()
