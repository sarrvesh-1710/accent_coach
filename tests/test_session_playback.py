"""Run production JavaScript rendering tests with Node's built-in test runner."""
from pathlib import Path
import shutil
import subprocess
import unittest


class SessionPlaybackTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node.js is needed for rendering tests')
    def test_account_playback_rendering(self):
        result = subprocess.run(
            [shutil.which('node'), '--test', str(Path(__file__).with_name('session_playback.cjs'))],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
