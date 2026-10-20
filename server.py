"""Loopback-only Jarvis HTTP service. Static content is restricted to web/."""
from __future__ import annotations
import asyncio
import json
import mimetypes
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from jarvis_core import JarvisState, ROOT, safe_config
from system_tools import capabilities, recent_events, execute, plan_voice_command, post_event
from live_info import live_query, LiveUnavailable
from runtime_health import diagnostics
from wake_service import WakeListener, startup_status, set_autostart
from offline_voice import status as whisper_status, transcribe as whisper_transcribe, MAX_AUDIO

mimetypes.add_type('application/javascript', '.js')
MAX_BODY = 12_000

class JarvisServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    def __init__(self, address, state: JarvisState):
        self.state = state
        self.wake_listener = WakeListener(state.cfg, lambda sentence: self._wake_event(sentence))
        super().__init__(address, JarvisHandler)
    def _wake_event(self, sentence):
        post_event('wake', 'صدای بیدارباش شناسایی شد: '+sentence[:180])
        try:
            import webbrowser
            webbrowser.open(f'http://127.0.0.1:{self.server_address[1]}/')
        except (OSError, RuntimeError): pass
        try:
            import winsound
            winsound.MessageBeep()
        except (ImportError, OSError): pass
        # No unattended OS action is executed from the microphone.

class JarvisHandler(BaseHTTPRequestHandler):
    server: JarvisServer
    def log_message(self, format, *args):
        # Log only method and status, not private questions or secret query parameters.
        print(f'[Jarvis HTTP] {self.command} {urlsplit(self.path).path[:80]}', file=sys.stderr)
    def _host_ok(self):
        host = self.headers.get('Host', '').split(':')[0].lower()
        return host in ('localhost','127.0.0.1')
    def _origin_ok(self):
        origin = self.headers.get('Origin')
        if origin is None:
            return True
        allowed = (f'http://127.0.0.1:{self.server.server_address[1]}',
                   f'http://localhost:{self.server.server_address[1]}')
        return origin in allowed
    def _send(self, status, body, mime='application/json; charset=utf-8'):
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; connect-src 'self'; img-src 'self' data:; media-src 'self' blob:; object-src 'none'; base-uri 'none'")
        self.send_header('Content-Length',str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def _json(self, status, data):
        self._send(status, json.dumps(data,ensure_ascii=False).encode('utf-8'))
    def _bad(self, status, message):
        self._json(status, {'error':str(message)})
    def _guard(self, write=False):
        if not self._host_ok():
            self._bad(403,'نشانی درخواست مجاز نیست.')
            return False
        if write and not self._origin_ok():
            self._bad(403,'منبع درخواست مجاز نیست.')
            return False
        return True
    def do_GET(self):
        if not self._guard():return
        path = urlsplit(self.path).path
        if path in ('/api/status','/status'):
            state = self.server.state
            self._json(200,{'name':'Jarvis','version':'1.2.0','provider':state.cfg['provider'],
                            'notes':len(state.graph['nodes']), 'links':len(state.graph['links']),
                            'onlineTTS':bool(state.cfg.get('online_tts')),
                            'voice':state.cfg.get('voice'), 'folder':str(state.notes_dir)})
            return
        if path == '/api/capabilities':
            self._json(200,{"system":capabilities(),"whisper":whisper_status(str(self.server.state.cfg.get("offline_stt_model", ""))),
                            "nativeWake":self.server.wake_listener.readiness(),"startup":startup_status()})
            return
        if path == '/api/diagnostics':
            self._json(200,diagnostics(self.server.state.cfg,self.server.wake_listener.readiness()))
            return
        if path == '/api/events':
            self._json(200,{"events":recent_events()})
            return
        if path == '/api/graph':
            self._json(200,self.server.state.graph)
            return
        if path in ('/', '/index.html'):
            path = '/index.html'
        rel = path.lstrip('/')
        # Explicit static allowlist. Prevent exposing config, Python source and note files.
        if rel not in ('index.html','style.css','app.js','data.js','favicon.svg','premium.css','premium.js','offline3d.js','live-ui.js','live-ui.css'):
            self._bad(404,'مسیر وجود ندارد.')
            return
        root = self.server.state.web_dir.resolve()
        file = (root / rel).resolve()
        if file.parent != root or not file.is_file():
            self._bad(404,'فایل وجود ندارد.')
            return
        self._send(200,file.read_bytes(),mimetypes.guess_type(str(file))[0] or 'application/octet-stream')
    def do_POST(self):
        if not self._guard(write=True):return
        path = urlsplit(self.path).path
        if path not in ('/ask','/remember','/speak','/api/reindex','/api/plan','/api/execute','/api/transcribe','/api/live','/api/native-wake'):
            self._bad(404,'مسیر وجود ندارد.')
            return
        try:
            # Privileged operations must originate in this local UI; form posts / remote sites cannot trigger them.
            privileged = path in ('/api/execute','/api/transcribe','/api/native-wake')
            if privileged and (not self.headers.get('Origin') or self.headers.get('X-Jarvis-Action') != 'local-ui'):
                self._bad(403,'این عملیات تنها از رابط محلی جارویس مجاز است.')
                return
            length = int(self.headers.get('Content-Length', '-1'))
            if not 0 <= length <= (MAX_AUDIO if path == '/api/transcribe' else MAX_BODY):
                self._bad(413,'حجم درخواست بیش از حد است.')
                return
            if path == '/api/transcribe':
                if self.headers.get('Content-Type') != 'audio/webm':
                    self._bad(415,'فرمت فایل صوتی باید audio/webm باشد.')
                    return
                audio = self.rfile.read(length)
                cfg = self.server.state.cfg
                self._json(200,{'text':whisper_transcribe(audio,str(cfg.get('offline_stt_model','')),str(cfg.get('offline_stt_device','auto')))})
                return
            if self.headers.get('Content-Type','').split(';')[0].strip() != 'application/json':
                self._bad(415,'فرمت داده باید JSON باشد.')
                return
            obj = json.loads(self.rfile.read(length))
            if not isinstance(obj,dict):
                raise ValueError('داده ارسالی باید یک شیء JSON باشد.')
            state = self.server.state
            if path == '/api/live':
                result=live_query(str(obj.get('kind','')),str(obj.get('query','')),base=str(obj.get('base','USD')),
                                  quote=str(obj.get('quote','EUR')),amount=float(obj.get('amount',1)))
                self._json(200,result)
            elif path == '/api/native-wake':
                operation=obj.get('operation')
                if operation=='enable':
                    enabled=obj.get('enabled')
                    if not isinstance(enabled,bool):raise ValueError('وضعیت فعال‌سازی باید درست یا نادرست باشد.')
                    listener=self.server.wake_listener
                    if enabled and not listener.start():raise RuntimeError(listener.detail)
                    if not enabled:listener.stop()
                    state.cfg['native_wake_enabled']=enabled
                    cfg_file=state.root/'config.json'
                    from jarvis_core import CONFIG_EXAMPLE
                    saved={k:state.cfg.get(k, v) for k,v in CONFIG_EXAMPLE.items()}
                    temp=cfg_file.with_suffix('.tmp')
                    temp.write_text(json.dumps(saved,ensure_ascii=False,indent=2),'utf-8');temp.replace(cfg_file)
                    self._json(200,{'nativeWake':listener.readiness(),'startup':startup_status()})
                elif operation=='startup':
                    enabled=obj.get('enabled')
                    if not isinstance(enabled,bool):raise ValueError('وضعیت اجرای خودکار نامعتبر است.')
                    if enabled and not self.server.wake_listener.readiness()['ready']:
                        raise RuntimeError('برای اجرای خودکار ابتدا مدل و موتور شنود آفلاین را نصب کن.')
                    from jarvis_core import ROOT
                    self._json(200,{'startup':set_autostart(enabled,ROOT/'start_jarvis.py')})
                else:raise ValueError('عملیات تنظیم بیدارباش ناشناخته است.')
            elif path == '/api/plan':
                self._json(200,{'plan':plan_voice_command(obj.get('text',''))})
            elif path == '/api/execute':
                approved = obj.get('approved') is True
                result = execute(str(obj.get('action','')),obj.get('args',{}),approved=approved)
                self._json(200,result)
            elif path == '/ask':
                res = state.ask(obj.get('question',''))
                if res.get('created'): res['graph'] = state.graph
                self._json(200,res)
            elif path == '/remember':
                note = state.remember(obj.get('text',''))
                self._json(200,{'note':note, 'graph':state.graph,
                                'answer':'ثبت شد، قربان! ستارهٔ تازه‌ات روشن شد. ✨'})
            elif path == '/api/reindex':
                self._json(200,{'graph':state.refresh()})
            elif path == '/speak':
                if not state.cfg.get('online_tts'):
                    self._bad(403,'صدای آنلاین در تنظیمات غیرفعال است.')
                    return
                content = str(obj.get('text','')).strip()[:650]
                if not content:
                    raise ValueError('متن خواندن خالی است.')
                try:
                    import edge_tts
                except ImportError:
                    self._bad(503,'edge-tts نصب نشده است. دستور pip install edge-tts را اجرا کن.')
                    return
                async def synth():
                    stream = edge_tts.Communicate(content, str(state.cfg.get('voice') or 'fa-IR-FaridNeural'))
                    out = bytearray()
                    async for item in stream.stream():
                        if item['type']=='audio':
                            out.extend(item['data'])
                            if len(out)>6_000_000:
                                raise ValueError('فایل صوتی بیش از حد بزرگ است.')
                    return bytes(out)
                try:
                    mp3 = asyncio.run(asyncio.wait_for(synth(),timeout=28))
                    if not mp3: raise RuntimeError('صدای خالی دریافت شد.')
                    self._send(200,mp3,'audio/mpeg')
                except Exception:
                    self._bad(503,'ساخت صدای طبیعی در دسترس نیست؛ از صدای مرورگر استفاده کن.')
        except PermissionError as exc:
            self._bad(403,str(exc))
        except LiveUnavailable as exc:
            self._bad(503,str(exc))
        except RuntimeError as exc:
            self._bad(503,str(exc))
        except (ValueError,TypeError,UnicodeDecodeError,json.JSONDecodeError) as exc:
            self._bad(400,str(exc))
        except (BrokenPipeError,ConnectionResetError):
            pass
        except Exception as exc:
            print('[Jarvis error]',type(exc).__name__,str(exc)[:180],file=sys.stderr)
            self._bad(500,'در انجام درخواست مشکلی رخ داد.')

def run(root: Path = ROOT, port: int | None = None, open_browser=False):
    cfg = safe_config(root/'config.json')
    state = JarvisState(root,cfg)
    host='127.0.0.1'
    port=int(port if port is not None else cfg.get('port',8800))
    if not 1 <= port <= 65535: raise ValueError('Invalid port')
    web = JarvisServer((host,port),state)
    if cfg.get('native_wake_enabled'):web.wake_listener.start()
    url=f'http://{host}:{port}'
    print(f'JARVIS READY: {url} | {len(state.graph["nodes"])} notes | provider={cfg["provider"]}',flush=True)
    if open_browser:
        import webbrowser
        threading.Timer(1.2,lambda:webbrowser.open(url)).start()
    try: web.serve_forever(poll_interval=.2)
    except KeyboardInterrupt: pass
    finally:
        web.wake_listener.stop()
        web.server_close()

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=None)
    parser.add_argument('--open',action='store_true',help='Open the UI in your browser')
    args=parser.parse_args()
    run(ROOT,args.port,args.open)
