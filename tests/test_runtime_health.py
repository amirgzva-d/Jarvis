import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib import request
from unittest.mock import patch

from jarvis_core import JarvisState
from runtime_health import diagnostics, provider_readiness
from server import JarvisServer
from wake_service import load_whisper_with_cpu_fallback, wake_phrase_detected


class RuntimeHealthTests(unittest.TestCase):
    def test_provider_status_no_api_secret_in_response(self):
        with patch.dict('os.environ', {'OPENAI_API_KEY':'highly_private_test_secret'}):
            data = provider_readiness({'provider':'openai-api'})
        self.assertTrue(data['configured'])
        self.assertFalse(data['verified'])
        self.assertNotIn('highly_private_test_secret', json.dumps(data))

    def test_unconfigured_cli_cannot_be_marked_verified(self):
        with patch('runtime_health.shutil.which',return_value=None):
            data = diagnostics({'provider':'codex-cli','offline_stt_model':'','online_tts':False})
        self.assertFalse(data['brain']['configured'])
        self.assertFalse(data['brain']['verified'])

    def test_keyword_tolerates_case_and_punctuation_without_substrings(self):
        for text in ['Hey Jarvis!', 'هی، جارویس!', 'سلام جارویس', 'Hi Jarvis']:
            self.assertTrue(wake_phrase_detected(text), text)
        for text in ['notjarvisok', '', 'سلام امروز هوا خوب است']:
            self.assertFalse(wake_phrase_detected(text), text)

    def test_gpu_failure_falls_back_to_cpu(self):
        attempts=[]
        def factory(path,**kwargs):
            attempts.append(kwargs['device'])
            if kwargs['device'] != 'cpu':
                raise RuntimeError('unsupported gpu')
            return {'path':path}
        model,device,fallback=load_whisper_with_cpu_fallback('local','cuda',factory)
        self.assertEqual(model,{'path':'local'})
        self.assertEqual(attempts,['cuda','cpu'])
        self.assertEqual(device,'cpu')
        self.assertTrue(fallback)

    def test_cpu_failure_does_not_loop(self):
        with self.assertRaises(RuntimeError):
            load_whisper_with_cpu_fallback('local','cpu',lambda *a,**kw: (_ for _ in ()).throw(RuntimeError('missing model')))

    def test_http_diagnostics_never_exposes_key_or_private_model_path(self):
        with tempfile.TemporaryDirectory(prefix='jarvis-runtime-health-') as temp:
            root=Path(temp)
            (root/'notes').mkdir()
            (root/'web').mkdir()
            (root/'notes'/'test.md').write_text('# سلام\nمحتوا','utf-8')
            cfg={'notes_folder':'notes','provider':'openai-api','api_key':'secret-not-for-browser',
                 'online_tts':False,'offline_stt_model':str(root/'secret-model-location')}
            state=JarvisState(root,cfg)
            service=JarvisServer(('127.0.0.1',0),state)
            worker=threading.Thread(target=service.serve_forever,daemon=True)
            worker.start()
            try:
                port=service.server_address[1]
                with request.urlopen(f'http://127.0.0.1:{port}/api/diagnostics',timeout=4) as resp:
                    body=resp.read().decode('utf-8')
                self.assertNotIn('secret-not-for-browser',body)
                self.assertNotIn('secret-model-location',body)
                self.assertTrue(json.loads(body)['brain']['configured'])
            finally:
                service.shutdown()
                service.server_close()
                worker.join(2)


if __name__=='__main__':
    unittest.main()
