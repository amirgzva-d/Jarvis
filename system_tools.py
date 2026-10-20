"""Opt-in, allowlisted Windows control for Jarvis. No arbitrary shell execution."""
from __future__ import annotations
import os
import re
import sys
import subprocess
import threading
import webbrowser
from datetime import datetime, timedelta
from urllib.parse import quote_plus

APPLICATIONS = {'notepad': 'notepad.exe', 'calculator': 'calc.exe',
                'explorer': 'explorer.exe', 'paint': 'mspaint.exe',
                'settings': 'ms-settings:'}
SAFE_ACTIONS = {'open_app','google','youtube','volume_up','volume_down','mute','timer'}
ALL_ACTIONS = SAFE_ACTIONS | {'lock'}
_TIMERS = []
_EVENTS = []
_EVENT_LOCK = threading.Lock()

def capabilities():
    return {'supported':sys.platform=='win32', 'actions':sorted(ALL_ACTIONS),
            'limitations':'Windows controls only; browser wake word works only while the app is open.'}

def _key(code: int):
    import ctypes
    ctypes.windll.user32.keybd_event(code, 0, 0, 0)
    ctypes.windll.user32.keybd_event(code, 0, 2, 0)

def _timer_done(label: str):
    with _EVENT_LOCK:
        _EVENTS.append({'event':'timer','text':f'تایمر «{label}» به پایان رسید.', 'time':datetime.now().isoformat()})
    if sys.platform == 'win32':
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception: pass

def recent_events():
    with _EVENT_LOCK:
        return list(_EVENTS[-20:])

def execute(action: str, args: dict | None = None, *, approved=False):
    """Actions only have fixed implementations, and lock requires explicit approval."""
    args = args or {}
    if action not in ALL_ACTIONS: raise ValueError('این فرمان در فهرست مجاز جارویس نیست.')
    if action == 'lock' and not approved:
        raise PermissionError('قفل سیستم به تأیید صریح نیاز دارد.')
    if sys.platform != 'win32':
        raise RuntimeError('کنترل ویندوز فقط در نسخه ویندوز امکان‌پذیر است.')
    if action == 'open_app':
        app = str(args.get('app','')).lower()
        if app not in APPLICATIONS: raise ValueError('برنامه انتخابی مجاز نیست.')
        value = APPLICATIONS[app]
        if app == 'settings':os.startfile(value)
        else: subprocess.Popen([value], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        return {'ok':True,'message':f'برنامه {app} باز شد.'}
    if action in ('google','youtube'):
        query = str(args.get('query','')).strip()[:180]
        if not query: raise ValueError('عبارت جستجو را وارد کن.')
        url = ('https://www.google.com/search?q=' if action=='google' else
               'https://www.youtube.com/results?search_query=') + quote_plus(query)
        if not webbrowser.open(url): raise RuntimeError('مرورگر باز نشد.')
        return {'ok':True,'message':'جستجو در مرورگر باز شد.', 'url':url}
    if action in ('volume_up','volume_down','mute'):
        _key({'volume_up':0xAF,'volume_down':0xAE,'mute':0xAD}[action])
        return {'ok':True,'message':'فرمان صدا به ویندوز ارسال شد.'}
    if action == 'timer':
        sec = int(args.get('seconds',0))
        if not 1 <= sec <= 86400: raise ValueError('تایمر باید بین ۱ ثانیه تا ۲۴ ساعت باشد.')
        label = str(args.get('label') or 'جارویس').strip()[:60]
        t = threading.Timer(sec,_timer_done,args=(label,))
        t.daemon = True
        _TIMERS.append(t)
        t.start()
        return {'ok':True,'message':f'تایمر {sec} ثانیه‌ای فعال شد.', 'ends_at':(datetime.now()+timedelta(seconds=sec)).isoformat()}
    if action == 'lock':
        import ctypes
        if not ctypes.windll.user32.LockWorkStation(): raise RuntimeError('ویندوز قفل نشد.')
        return {'ok':True,'message':'ویندوز قفل شد.'}
    raise ValueError('فرمان پشتیبانی نمی‌شود.')


def plan_voice_command(text: str):
    """Only unambiguous Persian/English intents trigger actions, otherwise None."""
    q = str(text or '').strip()
    norm = q.lower().replace('ي','ی').replace('ك','ک')
    if not norm: return None
    if re.search(r'(?:جستجو کن|سرچ کن|بگرد)\s+(?:در\s+)?یوتیوب\s+(?:برای\s+)?(.+)',norm):
        query = re.search(r'(?:جستجو کن|سرچ کن|بگرد)\s+(?:در\s+)?یوتیوب\s+(?:برای\s+)?(.+)',norm).group(1)
        return {'action':'youtube','args':{'query':query},'needs_confirmation':False}
    if re.search(r'(?:جستجو کن|سرچ کن|بگرد)\s+(?:در\s+)?گوگل\s+(?:برای\s+)?(.+)',norm):
        query = re.search(r'(?:جستجو کن|سرچ کن|بگرد)\s+(?:در\s+)?گوگل\s+(?:برای\s+)?(.+)',norm).group(1)
        return {'action':'google','args':{'query':query},'needs_confirmation':False}
    for term, app in [('نوت پد','notepad'),('notepad','notepad'),('ماشین حساب','calculator'),('calculator','calculator'),('فایل اکسپلورر','explorer'),('اکسپلورر','explorer'),('paint','paint'),('تنظیمات ویندوز','settings')]:
        if norm.startswith(('باز کن '+term,term+' رو باز کن','اجرای '+term)):
            return {'action':'open_app','args':{'app':app},'needs_confirmation':False}
    if norm in ('صدا را زیاد کن','صدا رو زیاد کن','صدای سیستم رو زیاد کن','volume up'):
        return {'action':'volume_up','args':{},'needs_confirmation':False}
    if norm in ('صدا را کم کن','صدا رو کم کن','صدای سیستم رو کم کن','volume down'):
        return {'action':'volume_down','args':{},'needs_confirmation':False}
    if norm in ('صدا رو قطع کن','بی صدا کن','mute'):
        return {'action':'mute','args':{},'needs_confirmation':False}
    if norm in ('ویندوز را قفل کن','سیستم رو قفل کن','کامپیوتر رو قفل کن','lock computer'):
        return {'action':'lock','args':{},'needs_confirmation':True}
    tm = re.fullmatch(r'تایمر\s+([\d۰-۹٠-٩]{1,4})\s*(ثانیه|دقیقه)(?:\s+(.*))?',norm)
    if tm:
        val = tm.group(1).translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩','01234567890123456789'))
        sec = int(val)*(60 if tm.group(2)=='دقیقه' else 1)
        if 1 <= sec <= 86400:
            return {'action':'timer','args':{'seconds':sec,'label':tm.group(3) or 'جارویس'},'needs_confirmation':False}
    return None
