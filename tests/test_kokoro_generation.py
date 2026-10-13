import contextlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import numpy as np
import soundfile as sf

from voice_generation.kokoro_backend import KokoroGenerator


class KokoroGenerationTests(unittest.TestCase):
    def generator(self, pipeline):
        generator = KokoroGenerator.__new__(KokoroGenerator)
        generator.np, generator.sf = np, sf
        generator.torch = SimpleNamespace(inference_mode=contextlib.nullcontext)
        generator.pipeline = pipeline
        generator.voice = object()
        generator.manifest = {"revision": "test-revision"}
        generator.load_ms = 100
        generator.calls = 0
        return generator

    def test_all_chunks_saved_and_model_load_only_counted_once(self):
        def pipeline(*args, **kwargs):
            for size, word in ((2400, "Hello"), (4800, "world")):
                yield word, word, SimpleNamespace(cpu=lambda: SimpleNamespace(numpy=lambda: np.full(size, 0.1)))
        generator = self.generator(pipeline)
        root = Path(__file__).resolve().parents[1] / "runs"
        root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            cold = generator.generate_audio("Hello world", output_dir=folder)
            warm = generator.generate_audio("Hello world", output_dir=folder)
            self.assertTrue(cold["ok"])
            self.assertAlmostEqual(cold["duration_seconds"], 0.3)
            self.assertEqual(cold["timings_ms"]["model_load"], 100)
            self.assertEqual(warm["timings_ms"]["model_load"], 0)
            self.assertEqual(warm["condition"], "warm")
            self.assertEqual(cold["type"], "synthetic_example")
            path = Path(folder) / (cold["generated_audio_id"] + ".json")
            self.assertIsNone(json.loads(path.read_text())["review"]["words_match"])

    def test_invalid_text_and_accent_do_not_call_pipeline(self):
        def forbidden(*args, **kwargs):
            self.fail("Invalid input reached synthesis")
        generator = self.generator(forbidden)
        self.assertEqual(generator.generate_audio("")["error"]["code"], "UNSUPPORTED_TEXT")
        self.assertEqual(generator.generate_audio("Hi", "en-GB")["error"]["code"], "UNSUPPORTED_ACCENT")

    def test_empty_output_is_failure_without_assets(self):
        generator = self.generator(lambda *args, **kwargs: iter(()))
        root = Path(__file__).resolve().parents[1] / "runs"
        root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            self.assertFalse(generator.generate_audio("Hello", output_dir=folder)["ok"])
            self.assertEqual(list(Path(folder).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
