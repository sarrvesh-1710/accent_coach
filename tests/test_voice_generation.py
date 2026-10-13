"""Safety boundaries for the isolated generator; no shared speech dependencies."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from voice_generation import generate_audio

TEST_ROOT = Path(__file__).resolve().parents[1] / "runs"
TEST_ROOT.mkdir(exist_ok=True)

class GenerationTests(unittest.TestCase):
    def test_invalid_text_creates_no_assets(self):
        with tempfile.TemporaryDirectory(dir=TEST_ROOT) as folder:
            for text in (None, "", "   ", "a" * 1001):
                result = generate_audio(text, output_dir=folder)
                self.assertEqual(result["error"]["code"], "UNSUPPORTED_TEXT")
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_unsupported_accent_does_not_synthesize(self):
        with patch("voice_generation.generator.subprocess.run") as backend:
            result = generate_audio("Hello", "en-GB")
            self.assertEqual(result["error"]["code"], "UNSUPPORTED_ACCENT")
            backend.assert_not_called()

    @unittest.skipUnless(__import__("os").name == "nt", "Windows backend")
    def test_backend_failure_cleans_partial_audio_and_hides_logs(self):
        with tempfile.TemporaryDirectory(dir=TEST_ROOT) as folder:
            def fail(*args, **kwargs):
                request = Path(args[0][-1])
                import json
                path = Path(json.loads(request.read_text(encoding="utf-8"))["output_path"])
                path.write_bytes(b"partial")
                return __import__("subprocess").CompletedProcess(args[0], 1, "", "private backend logs")
            with patch("voice_generation.generator.subprocess.run", side_effect=fail):
                result = generate_audio("Hello", output_dir=folder)
            self.assertFalse(result["ok"])
            self.assertTrue(result["error"]["retryable"])
            self.assertNotIn("private", str(result))
            self.assertEqual(list(Path(folder).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
