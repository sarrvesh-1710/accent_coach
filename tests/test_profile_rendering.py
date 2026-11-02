"""Run the dedicated production profile renderer with controlled browser state."""
from pathlib import Path
import shutil
import subprocess
import unittest


class ProfileRenderingTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node.js is needed for rendering tests')
    def test_profile_renderer(self):
        result = subprocess.run([shutil.which('node'), '--test', str(Path(__file__).with_name('profile_rendering.cjs'))],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__': unittest.main()
