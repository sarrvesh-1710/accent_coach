"""Deterministic elapsed-clock tests; no real MFA inference here."""
from contextlib import contextmanager
import importlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

mfa = importlib.import_module("phoneme_scoring.align_audio")


class MFATimingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.now = 0.0
        self.events = []
        self.enterContext(patch.object(mfa.time, "monotonic", side_effect=lambda: self.now))
        self.enterContext(patch.object(mfa, "prepare_audio", side_effect=self.prepare))
        self.enterContext(patch.object(mfa, "alignment_lock", side_effect=self.lock))
        self.process = self.enterContext(patch.object(mfa, "run_mfa", side_effect=self.fake_subprocess))
        self.enterContext(patch.object(mfa, "parse_textgrid", side_effect=self.parse))
        self.settings = {"mfa": {"executable": "mfa", "dictionary": "dict", "acoustic_model": "model",
                                  "phone_tiers": ["phones"], "timeout_sec": 120}}

    def prepare(self, *args):
        self.now += 2
        return np.ones(16000)*.1, 16000, "fingerprint"

    @contextmanager
    def lock(self, path):
        self.now += 3
        self.events.append("locked")
        try:
            yield
        finally:
            self.events.append("released")

    def fake_subprocess(self, args, **kwargs):
        self.assertEqual(self.events[-1], "locked")
        self.now += 7
        Path(args[6]).write_text("fixture")
        self.assertEqual(args[1], "align_one")
        self.assertEqual(args[4:6], ["dict", "model"])
        self.assertEqual(args[7:10], ["--output_format", "long_textgrid", "--no_use_mp"])
        self.assertEqual(kwargs["timeout"], 120)
        self.assertFalse(kwargs["check"])
        return subprocess.CompletedProcess(args, 0)

    def parse(self, path):
        self.now += 5
        return {"phones": [(0.0, 1.0, "TH")], "words": [(0.0, 1.0, "think")]}

    def call(self):
        return mfa.align_audio("fixture.wav", "think", self.settings, self.temp.name)

    def test_distinct_boundaries_and_monotonic_total(self):
        result = self.call()
        self.assertEqual(result["status"], "available", result)
        self.assertEqual(result["timings_sec"], dict(input_preparation=2, lock_wait=3,
                         subprocess_execution=7, output_processing=5, total=17))
        self.assertEqual(self.events, ["locked", "released"])

    def test_lock_failure_has_no_subprocess_measurement(self):
        @contextmanager
        def fail_lock(path):
            self.now += 120
            raise TimeoutError("lock timeout")
            yield
        with patch.object(mfa, "alignment_lock", side_effect=fail_lock):
            result = self.call()
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["timings_sec"]["lock_wait"], 120)
        self.assertEqual(result["timings_sec"]["total"], 122)
        self.assertNotIn("subprocess_execution", result["timings_sec"])
        self.process.assert_not_called()

    def test_process_timeout_includes_cleanup_releases_lock(self):
        def expired(*args, **kwargs):
            self.now += 125  # Simulated wait plus owned-process cleanup.
            raise subprocess.TimeoutExpired("fixture", 120)
        self.process.side_effect = expired
        result = self.call()
        self.assertEqual(result["status"], "unavailable")
        self.assertIn("TimeoutExpired", result["reason"])
        self.assertEqual(result["timings_sec"]["subprocess_execution"], 125)
        self.assertEqual(result["timings_sec"]["total"], 130)
        self.assertEqual(self.events[-1], "released")

    def test_missing_executable_and_early_failure(self):
        self.process.side_effect = FileNotFoundError("fixture")
        r = self.call()
        self.assertIn("MFA could not start", r["reason"])
        self.assertIn("subprocess_execution", r["timings_sec"])
        r = mfa.align_audio("fixture.wav", "", self.settings, self.temp.name)
        self.assertEqual(r["timings_sec"], {"total": 2})


if __name__ == "__main__":
    unittest.main()
