"""Jarvis advanced modules: permission boundary, planner and local model safety."""
import sys
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib import request,error
from unittest.mock import patch
from server import JarvisServer
from jarvis_core import JarvisState
from offline_voice import status
from system_tools import plan_voice_command, execute, capabilities

class VoicePlannerTest(unittest.TestCase):
    def test_open_apps_allowlisted(self):
        self.assertEqual(plan_voice_command('باز کن نوت پد')['args']['app'],'notepad')
        self.assertEqual(plan_voice_command('ماشین حساب رو باز کن')['args']['app'],'calculator')
        self.assertIsNone(plan_voice_command('باز کن برنامه ناشناس'))
        self.assertIsNone(plan_voice_command('باز کن cmd.exe'))
    def test_web_search_queries(self):
        self.assertEqual(plan_voice_command('جستجو کن یوتیوب آموزش پایتون')['args']['query'],'آموزش پایتون')
        self.assertEqual(plan_voice_command('سرچ کن گوگل آب و هوا')['action'],'google')
    def test_timer_minute_and_limits(self):
        self.assertEqual(plan_voice_command('تایمر ۳ دقیقه')['args']['seconds'],180)
        self.assertEqual(plan_voice_command('تایمر 20 ثانیه')['args']['seconds'],20)
        self.assertIsNone(plan_voice_command('تایمر 99999 دقیقه'))
    def test_lock_always_requires_approval(self):
        p=plan_voice_command('سیستم رو قفل کن')
        self.assertTrue(p['needs_confirmation'])
        with self.assertRaises(PermissionError):execute('lock',approved=False)
    def test_no_arbitrary_program(self):
        with self.assertRaises(ValueError):execute('shell',{'command':'powershell'})
    def test_offline_stt_does_not_download(self):
        with tempfile.TemporaryDirectory() as d:
            state=status(d)
            self.assertFalse(state['model_ready'])
    def test_platform_capability_real(self):
        self.assertEqual(capabilities()['supported'],sys.platform=='win32')

class AdvancedHttpTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='jarvis-advanced-')
        root=Path(self.tmp.name)
        (root/'notes').mkdir();(root/'web').mkdir()
        (root/'web'/'index.html').write_text('<h1>Jarvis</h1>','utf-8')
        (root/'notes'/'one.md').write_text('# One\n\nTest','utf-8')
        state=JarvisState(root,{'notes_folder':'notes','provider':'notes-only','online_tts':False,'voice':'fa-IR-FaridNeural'})
        self.server=JarvisServer(('127.0.0.1',0),state)
        self.port=self.server.server_address[1]
        self.t=threading.Thread(target=self.server.serve_forever,daemon=True);self.t.start()
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.t.join(timeout=2);self.tmp.cleanup()
    def url(self,path):return f'http://127.0.0.1:{self.port}{path}'
    def post(self,path,body,headers=None):
        h={'Content-Type':'application/json',**(headers or {})}
        r=request.Request(self.url(path),json.dumps(body).encode('utf-8'),headers=h,method='POST')
        return request.urlopen(r,timeout=3)
    def test_safe_plan_and_capabilities(self):
        with self.post('/api/plan',{'text':'تایمر 5 دقیقه'}) as r:
            self.assertEqual(json.load(r)['plan']['args']['seconds'],300)
        with request.urlopen(self.url('/api/capabilities')) as r:
            self.assertIn('whisper',json.load(r))
    def test_privileged_origin_mandatory(self):
        with self.assertRaises(error.HTTPError) as c:
            self.post('/api/execute',{'action':'volume_up'})
        self.assertEqual(c.exception.code,403)
        with self.assertRaises(error.HTTPError) as c:
            self.post('/api/execute',{'action':'volume_up'},{'Origin':'http://evil.test','X-Jarvis-Action':'local-ui'})
        self.assertEqual(c.exception.code,403)
    def test_approved_own_origin_cannot_run_unknown_commands(self):
        with self.assertRaises(error.HTTPError) as c:
            self.post('/api/execute',{'action':'start_shell','args':{'command':'rm -rf /'}},{'Origin':f'http://127.0.0.1:{self.port}','X-Jarvis-Action':'local-ui'})
        self.assertEqual(c.exception.code,400)
    def test_transcribe_rejects_invalid_mime(self):
        req=request.Request(self.url('/api/transcribe'),b'xxxx',headers={
            'Content-Type':'application/octet-stream','Origin':f'http://127.0.0.1:{self.port}',
            'X-Jarvis-Action':'local-ui'},method='POST')
        with self.assertRaises(error.HTTPError) as c:request.urlopen(req,timeout=3)
        self.assertEqual(c.exception.code,415)

if __name__=='__main__': unittest.main()
