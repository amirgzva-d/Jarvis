import sys
import unittest
from unittest.mock import patch
from wake_service import WakeListener, startup_status, set_autostart

class WakeTests(unittest.TestCase):
    def test_opt_in_default_off(self):
        wake=WakeListener({'offline_stt_model':''},lambda s:None)
        self.assertFalse(wake.start());self.assertFalse(wake.readiness()['ready'])
        self.assertEqual(wake.state,'unavailable')
    def test_unavailable_nonwindows(self):
        if sys.platform!='win32':
            self.assertFalse(startup_status()['supported'])
            with self.assertRaises(RuntimeError):set_autostart(True, __import__('pathlib').Path('start_jarvis.py'))
    def test_worker_does_not_execute_tool(self):
        self.assertFalse(hasattr(WakeListener, 'execute'))

if __name__=='__main__':unittest.main()
