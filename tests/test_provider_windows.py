import subprocess
import unittest
from unittest.mock import patch
from jarvis_core import ask_provider, ProviderError

SCORED=[(3.0,{'id':0,'title':'آزمون امن','summary':'یادداشت نمونه‌ای برای پاسخ کوتاه.'})]


class WindowsCodexTests(unittest.TestCase):
    def test_uses_absolute_resolved_cmd_and_no_shell(self):
        fake=subprocess.CompletedProcess(args=[],returncode=0,stdout='پاسخ کوتاه فارسی',stderr='')
        with patch('shutil.which',return_value=r'C:\Users\demo\AppData\Roaming\npm\codex.CMD'), \
             patch('jarvis_core.subprocess.run',return_value=fake) as called:
            answer=ask_provider('موضوع آزمون چیست؟',SCORED,{'provider':'codex-cli'},[])
        self.assertEqual(answer,'پاسخ کوتاه فارسی')
        args,kwargs=called.call_args
        self.assertTrue(args[0][0].endswith('codex.CMD'))
        self.assertFalse(kwargs['shell'])
        self.assertIn('read-only',args[0])

    def test_provider_error_does_not_expose_invalid_key(self):
        fake=subprocess.CompletedProcess(args=[],returncode=1,stdout='',stderr='401 Incorrect API key: secret-example-token')
        with patch('shutil.which',return_value=r'C:\demo\codex.CMD'), \
             patch('jarvis_core.subprocess.run',return_value=fake):
            with self.assertRaises(ProviderError) as ctx:
                ask_provider('موضوع آزمون',SCORED,{'provider':'codex-cli'},[])
        self.assertIn('نامعتبر',str(ctx.exception))
        self.assertNotIn('secret-example-token',str(ctx.exception))


if __name__=='__main__':
    unittest.main()
