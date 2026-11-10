"""Controlled microphone lifecycle tests; no physical microphone access."""
from pathlib import Path
import shutil
import subprocess
import unittest
class MicrophoneTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node.js required')
    def test_capture_lifecycle(self):
        result=subprocess.run([shutil.which('node'),'--test',str(Path(__file__).with_name('test_microphone.cjs'))],capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
