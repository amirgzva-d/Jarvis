import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib import error, request
from unittest.mock import patch
from jarvis_core import JarvisState
from server import JarvisServer

class LiveEndpointTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='jarvis-live-test-')
        root=Path(self.temp.name);(root/'notes').mkdir();(root/'web').mkdir();(root/'notes'/'a.md').write_text('# Hello','utf-8')
        state=JarvisState(root,{'notes_folder':'notes','provider':'notes-only','online_tts':False,'voice':'fa-IR-FaridNeural','offline_stt_model':''})
        self.server=JarvisServer(('127.0.0.1',0),state)
        self.url=f'http://127.0.0.1:{self.server.server_address[1]}'
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join(2);self.temp.cleanup()
    def post(self,path,payload,headers=None):
        data=json.dumps(payload).encode('utf-8')
        return request.urlopen(request.Request(self.url+path,data=data,method='POST',headers={'Content-Type':'application/json',**(headers or {})}),timeout=4)
    def test_successful_live_route_uses_only_provider_output(self):
        with patch('server.live_query',return_value={'kind':'weather','answer':'دمای تأییدشده','source':'https://open-meteo.com','provider':'Open-Meteo'}):
            with self.post('/api/live',{'kind':'weather','query':'Tehran'}) as res:
                self.assertEqual(json.load(res)['answer'],'دمای تأییدشده')
    def test_unknown_kind_returns_400(self):
        with self.assertRaises(error.HTTPError) as ex:
            self.post('/api/live',{'kind':'internal_url','query':'http://127.0.0.1/'})
        self.assertEqual(ex.exception.code,400)
    def test_external_origin_cannot_control_native_microphone(self):
        with self.assertRaises(error.HTTPError) as ex:
            self.post('/api/native-wake',{'operation':'enable','enabled':True},headers={'Origin':'http://untrusted.invalid','X-Jarvis-Action':'local-ui'})
        self.assertEqual(ex.exception.code,403)
    def test_native_requires_secretless_explicit_enable(self):
        with self.assertRaises(error.HTTPError) as ex:
            self.post('/api/native-wake',{'operation':'enable','enabled':True})
        self.assertEqual(ex.exception.code,403)
    def test_disabled_native_route_requires_no_microphone(self):
        headers={'Origin':self.url,'X-Jarvis-Action':'local-ui'}
        with self.post('/api/native-wake',{'operation':'enable','enabled':False},headers=headers) as res:
            self.assertFalse(json.load(res)['nativeWake']['active'])

if __name__=='__main__':unittest.main()
