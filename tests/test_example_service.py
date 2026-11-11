from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading
import unittest
import uuid
import wave

from voice_generation.service import DevelopmentStore, GenerationService, AttemptUnavailable, development_fixture
from voice_generation.generator import TARGET_ACCENT

ROOT = Path(__file__).resolve().parents[1]


class Backend:
    def __init__(self, gate=None, fail=False):
        self.calls = 0
        self.gate, self.fail = gate, fail
        self.started = threading.Event()

    def generate_audio(self, text, target_accent, *, output_dir):
        self.calls += 1
        self.started.set()
        if self.gate:
            if not self.gate.wait(5):
                raise RuntimeError("Test release timed out")
        if self.fail:
            raise RuntimeError("Private backend details")
        identity = "synthetic-" + uuid.uuid4().hex
        with wave.open(str(output_dir / (identity + ".wav")), "wb") as audio:
            audio.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
            audio.writeframes(b"\x01\x00" * 240)
        return {"ok": True, "generated_audio_id": identity, "timings_ms": {"total": 1}, "error": None}


class ExampleServiceTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "runs").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "runs")
        self.output = Path(self.temp.name)
        self.store = DevelopmentStore()
        fixture = development_fixture(json.loads((ROOT / "contracts/examples/session.json").read_text()))
        fixture["sound_results"] = [{"message": "Existing analysis"}]
        fixture["jobs"]["analysis"]["status"] = "completed"
        self.session = self.store.create("user-a", fixture)
        self.identity = self.session["attempt_id"]
        self.backend = Backend()
        self.service = GenerationService(self.store, self.backend, self.output)
        self.gate = None

    def tearDown(self):
        if self.gate:
            self.gate.set()
        self.service.close()
        self.temp.cleanup()

    def confirm(self, text="I think so."):
        revision = self.store.get_attempt("user-a", self.identity)["input_revision"]
        result = self.service.confirm_text("user-a", self.identity, text, TARGET_ACCENT, revision)
        self.assertTrue(result["ok"])
        return result["session"]["input_revision"]

    def submit(self):
        revision = self.store.get_attempt("user-a", self.identity)["input_revision"]
        return self.service.generate_example("user-a", self.identity, revision)

    def wait(self):
        self.assertTrue(self.service.idle.wait(3))

    def test_confirmation_required(self):
        result = self.submit()
        self.assertEqual(result["error"]["code"], "TRANSCRIPT_CONFIRMATION_REQUIRED")
        self.assertEqual(self.backend.calls, 0)

    def test_success_envelope_playback_and_backend_reuse(self):
        self.confirm()
        for _ in range(2):
            response = self.submit()
            self.assertEqual(response["status"], "queued")
            self.wait()
            snapshot = self.store.get_attempt("user-a", self.identity)
            self.assertEqual(snapshot["jobs"]["example_generation"]["status"], "completed")
            asset = snapshot["generated_assets"][0]
            self.assertEqual(asset["type"], "synthetic_example")
            self.assertTrue(self.service.audio_path("user-a", self.identity, asset["audio_id"]).exists())
        self.assertEqual(self.backend.calls, 2)
        self.assertEqual(len(list(self.output.glob("*.wav"))), 1)

    def test_failure_preserves_completed_analysis_and_allows_retry(self):
        revision = self.confirm()
        with self.store.lock:
            attempt = self.store.attempts[self.identity]
            attempt["jobs"]["analysis"]["status"] = "completed"
            attempt["sound_results"] = [{"message": "Assessment stays visible"}]
        self.backend.fail = True
        self.submit()
        self.wait()
        snapshot = self.store.get_attempt("user-a", self.identity)
        self.assertEqual(snapshot["jobs"]["analysis"]["status"], "completed")
        self.assertEqual(snapshot["sound_results"][0]["message"], "Assessment stays visible")
        self.assertNotIn("Private", str(snapshot["jobs"]["example_generation"]["error"]))
        self.backend.fail = False
        self.assertTrue(self.submit()["ok"])
        self.wait()
        self.assertEqual(self.store.get_attempt("user-a", self.identity)["jobs"]["example_generation"]["status"], "completed")

    def test_edit_during_generation_rejects_and_cleans_late_output(self):
        self.confirm()
        self.gate = threading.Event()
        self.backend.gate = self.gate
        self.submit()
        self.assertTrue(self.backend.started.wait(2))
        self.confirm("The ship is here.")
        self.gate.set()
        self.wait()
        snapshot = self.store.get_attempt("user-a", self.identity)
        self.assertEqual(snapshot["confirmed_text"], "The ship is here.")
        self.assertEqual(snapshot["generated_assets"], [])
        self.assertEqual(list(self.output.iterdir()), [])

    def test_delete_during_generation_cannot_recreate_session(self):
        self.confirm()
        self.gate = threading.Event()
        self.backend.gate = self.gate
        self.submit()
        self.assertTrue(self.backend.started.wait(2))
        self.service.delete_attempt("user-a", self.identity)
        self.gate.set()
        self.wait()
        with self.assertRaises(AttemptUnavailable):
            self.store.get_attempt("user-a", self.identity)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_cross_user_generation_playback_and_deletion_denied(self):
        revision = self.confirm()
        self.submit()
        self.wait()
        snapshot = self.store.get_attempt("user-a", self.identity)
        audio_id = snapshot["generated_assets"][0]["audio_id"]
        self.assertEqual(self.service.generate_example("user-b", self.identity, revision)["error"]["code"], "ATTEMPT_UNAVAILABLE")
        with self.assertRaises(AttemptUnavailable):
            self.service.audio_path("user-b", self.identity, audio_id)
        with self.assertRaises(AttemptUnavailable):
            self.service.delete_attempt("user-b", self.identity)

    def test_busy_revision_conflict_and_unsupported_accent(self):
        revision = self.confirm()
        self.assertEqual(self.service.generate_example("user-a", self.identity, revision-1)["error"]["code"], "REVISION_CONFLICT")
        self.assertEqual(self.service.confirm_text("user-a", self.identity, "Hi", "en-GB", revision)["error"]["code"], "UNSUPPORTED_ACCENT")
        self.gate = threading.Event()
        self.backend.gate = self.gate
        self.submit()
        self.assertTrue(self.backend.started.wait(2))
        self.assertEqual(self.submit()["error"]["code"], "BUSY")
        self.gate.set()
        self.wait()

    def test_text_change_removes_old_playback(self):
        self.confirm()
        self.submit()
        self.wait()
        old_asset = self.store.get_attempt("user-a", self.identity)["generated_assets"][0]["audio_id"]
        self.confirm("That is a bad bed.")
        with self.assertRaises(AttemptUnavailable):
            self.service.audio_path("user-a", self.identity, old_asset)
        self.assertFalse((self.output / (old_asset + ".wav")).exists())


if __name__ == "__main__":
    unittest.main()
