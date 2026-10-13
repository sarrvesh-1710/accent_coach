"""Real audio/text preparation; fake MFA/scorer and explicitly fake storage.

These tests do not establish production authentication or pronunciation accuracy.
"""
from copy import deepcopy
import hashlib
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import numpy as np
import soundfile as sf

import confirmed_analysis as backend
from phoneme_scoring.align_audio import load_settings, prepare_audio
from phoneme_scoring.sequence_evidence import compare_targets
from phoneme_scoring.gop_score import _resolve


class FakeStore:
    """Test double only: opaque auth identity and locked compare-and-set."""
    def __init__(self, snapshot):
        self.auth = object()
        self.snapshot = deepcopy(snapshot)
        self.active = True
        self.lock = threading.Lock()
        self.published = None

    def resolve_analysis_snapshot(self, auth, attempt_id, job_id, input_revision):
        with self.lock:
            if auth is not self.auth or not self.active or attempt_id != self.snapshot["attempt_id"]:
                raise PermissionError()
            return deepcopy(self.snapshot)

    def publish_analysis_if_current(self, auth, snapshot, result):
        with self.lock:
            if auth is not self.auth or not self.active or snapshot != self.snapshot:
                return False
            self.published = deepcopy(result)
            return True


class ConfirmedAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "input.wav"
        sf.write(self.path, .1*np.sin(2*np.pi*180*np.arange(16000)/16000), 16000)
        dictionary = Path(self.temp.name) / "fixture.dict"
        dictionary.write_text("think TH IH1 NG K\nso S OW1\n")
        self.settings = load_settings(Path(__file__).parents[1] / "phoneme_scoring/settings.json")
        self.settings["mfa"]["dictionary"] = str(dictionary)
        digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.fingerprint = prepare_audio(self.path, self.settings)[2]
        self.snapshot = dict(attempt_id="attempt-1", job_id="job-1", input_revision=2,
            learner_audio_id="asset-1", learner_audio_role="learner", learner_audio_path=str(self.path),
            source_audio_sha256=digest, confirmed_text="Think think.", transcript_confirmed=True,
            target_accent="en-US-general-american", transcription=dict(status="completed", recognized_text="Think think.",
            source_audio_sha256=digest, audio_sha256=self.fingerprint, model_id="fixture", model_revision="fixture-rev"))
        self.alignment = dict(status="available", audio_sha256=self.fingerprint,
            words=[dict(segment_id=f"w{i}", word="think", start_sec=i*.3, end_sec=i*.3+.2) for i in range(2)],
            segments=[dict(segment_id=f"p{i}", word_id=f"w{i}", word="think", canonical_phone="TH",
                           original_phone="TH", start_sec=i*.3, end_sec=i*.3+.2) for i in range(2)])
        self.align = self.enterContext(patch.object(backend, "align_audio", return_value=self.alignment))
        self.score = self.enterContext(patch.object(backend, "score_phonemes", side_effect=self.scorer))
        self.enterContext(patch("pipeline.load_prompts", side_effect=AssertionError("No preset lookup allowed")))

    def scorer(self, path, alignment, settings):
        self.assertEqual(hashlib.sha256(Path(path).read_bytes()).hexdigest(), self.snapshot["source_audio_sha256"])
        return dict(status="available", audio_sha256=self.fingerprint,
            segments=[dict(segment_id=s["segment_id"], status="scored", raw_score=0, score_units="nats") for s in alignment["segments"]],
            sequence_evidence=dict(status="available", targets=[dict(segment_id=t["segment_id"],
                status="expected_supported", reason="Experimental evidence", alternative_phone="S") for t in settings["_assessment_targets"]]))

    def run_worker(self):
        return backend.run_confirmed_attempt(self.snapshot, self.settings)

    def execute(self, store):
        return backend.execute_confirmed_analysis(store.auth, "attempt-1", "job-1", 2, store=store, settings=self.settings)

    def test_independent_confirmed_text_and_identities(self):
        before = deepcopy(self.settings)
        r = self.run_worker()
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["analysis_status"], "completed")
        self.assertEqual(self.align.call_args.args[1], "think think")
        self.assertEqual(r["confirmed_text"], "Think think.")
        for k in ("attempt_id", "job_id", "input_revision", "learner_audio_id", "source_audio_sha256"):
            self.assertEqual(r[k], self.snapshot[k])
        self.assertEqual([x["word_index"] for x in r["sound_results"]], [0, 1])
        self.assertEqual(len({x["occurrence_id"] for x in r["sound_results"]}), 2)
        self.assertEqual({x["outcome"] for x in r["sound_results"]}, {"supported"})
        self.assertEqual(self.settings, before)
        self.assertFalse(Path(self.align.call_args.args[0]).exists())

    def test_atomic_publication_and_stale_mutations(self):
        store = FakeStore(self.snapshot)
        self.assertTrue(self.execute(store)["ok"])
        self.assertIsNotNone(store.published)
        for mutation in (lambda s: s.snapshot.update(input_revision=3), lambda s: s.snapshot.update(job_id="retry"),
                         lambda s: s.snapshot.update(confirmed_text="so"), lambda s: s.snapshot.update(learner_audio_id="new"),
                         lambda s: setattr(s, "active", False), lambda s: setattr(s, "auth", object())):
            store = FakeStore(self.snapshot)
            def changing_score(*args):
                value = self.scorer(*args)
                mutation(store)
                return value
            self.score.side_effect = changing_score
            result = self.execute(store)
            self.assertEqual(result["error"]["code"], "REVISION_CONFLICT")
            self.assertNotIn("sound_results", result)
            self.assertIsNone(store.published)

    def test_untrusted_user_id_is_not_authorization(self):
        store = FakeStore(self.snapshot)
        r = backend.execute_confirmed_analysis({"user_id": "owner"}, "attempt-1", "job-1", 2, store=store, settings=self.settings)
        self.assertEqual(r["error"]["code"], "ATTEMPT_UNAVAILABLE")
        self.align.assert_not_called()

    def test_stale_before_work(self):
        store = FakeStore(self.snapshot)
        store.snapshot["input_revision"] = 3
        self.assertEqual(self.execute(store)["error"]["code"], "REVISION_CONFLICT")
        self.align.assert_not_called()

    def test_generated_audio_and_changed_hash_rejected(self):
        for role in ("synthetic_example", "voice_converted", "generated", None):
            self.snapshot["learner_audio_role"] = role
            self.assertEqual(self.run_worker()["error"]["code"], "INVALID_AUDIO")
        self.snapshot["learner_audio_role"] = "learner"
        self.snapshot["source_audio_sha256"] = "wrong"
        self.assertEqual(self.run_worker()["error"]["code"], "INVALID_AUDIO")
        self.align.assert_not_called()

    def test_confirmation_and_preflight(self):
        self.snapshot["transcript_confirmed"] = False
        self.assertEqual(self.run_worker()["error"]["code"], "TRANSCRIPT_CONFIRMATION_REQUIRED")
        self.snapshot["transcript_confirmed"] = True
        self.snapshot["confirmed_text"] = "unknownword"
        self.assertEqual(self.run_worker()["error"]["code"], "UNSUPPORTED_TEXT")
        self.align.assert_not_called()

    def test_asr_disagreement_and_missing_provenance_abstain(self):
        for change in ({"recognized_text": "so"}, {"status": "failed"}, {"audio_sha256": "wrong"}, {"model_revision": None}):
            original = deepcopy(self.snapshot["transcription"])
            self.snapshot["transcription"].update(change)
            r = self.run_worker()
            self.assertTrue(r["ok"])
            self.assertEqual({x["outcome"] for x in r["sound_results"]}, {"inconclusive"})
            self.snapshot["transcription"] = original

    def test_unsupported_uncertain_and_practice(self):
        for state, expected in (("unsupported", "inconclusive"), ("uncertain", "inconclusive"), ("scored", "practice")):
            def fake(*args):
                value = self.scorer(*args)
                for row in value["segments"]:
                    row["status"] = state
                for row in value["sequence_evidence"]["targets"]:
                    row["status"] = "insufficient_evidence" if state == "uncertain" else "alternative_favored"
                return value
            self.score.side_effect = fake
            r = self.run_worker()
            self.assertTrue(r["ok"])
            self.assertEqual({x["outcome"] for x in r["sound_results"]}, {expected})

    def test_alignment_and_model_failures(self):
        self.align.return_value = dict(status="unavailable")
        self.assertEqual(self.run_worker()["analysis_status"], "failed")
        self.score.assert_not_called()
        self.align.return_value = self.alignment
        self.score.side_effect = None
        self.score.return_value = dict(status="unavailable")
        self.assertEqual(self.run_worker()["reason_code"], "PHONEME_ANALYSIS_FAILED")

    def test_clipping_guard_and_no_eligible_targets(self):
        original = backend.audio_io.prepare_audio
        def clipped(*args):
            value = original(*args)
            value["warnings"] = ["possible_clipping"]
            return value
        with patch.object(backend.audio_io, "prepare_audio", side_effect=clipped):
            self.assertEqual({r["outcome"] for r in self.run_worker()["sound_results"]}, {"inconclusive"})
        for s in self.alignment["segments"]:
            s.update(canonical_phone="S", original_phone="S")
        r = self.run_worker()
        self.assertTrue(r["ok"])
        self.assertEqual(r["sound_results"], [])
        self.assertIn("NO_SUPPORTED_TARGETS", r["limitations"])

    def test_timeout_and_exception_are_operational_failures(self):
        self.align.return_value = dict(status="unavailable", reason="TimeoutExpired: process expired")
        self.assertEqual(self.run_worker()["error"]["code"], "TIMEOUT")
        self.align.side_effect = RuntimeError("private/path")
        r = self.run_worker()
        self.assertEqual(r["analysis_status"], "failed")
        self.assertNotIn("private/path", str(r))
        self.score.assert_not_called()

    def test_ambiguous_word_mapping_abstains(self):
        self.alignment["words"][0]["word"] = "other"
        r = self.run_worker()
        self.assertTrue(r["ok"])
        self.assertEqual(r["sound_results"], [])
        self.assertIn("ALIGNMENT_WORD_MISMATCH", r["limitations"])

    def test_real_sequence_selector_repeated_targets_preserves_legacy(self):
        segments = self.alignment["segments"]
        mapping = dict(silence=["sil"], unsupported=["unk"], phones={"TH": "th", "S": "s"}, stress_overrides={})
        rows = [dict(segment_id=s["segment_id"], target_token="th", winning_phone="th", evidence_frames=1) for s in segments]
        spec = dict(word="think", phone="TH", alternatives=["S"])
        args = (np.log([[.01,.98,.01],[.98,.01,.01],[.01,.98,.01]]), segments, rows, mapping, {"blank":0,"th":1,"s":2}, {0}, 0)
        legacy = compare_targets(*args, [spec], {}, _resolve)
        self.assertEqual(legacy["targets"][0]["status"], "insufficient_evidence")
        explicit = compare_targets(*args, [dict(spec, segment_id="p0"), dict(spec, segment_id="p1")], {}, _resolve)
        self.assertEqual([r["segment_id"] for r in explicit["targets"]], ["p0", "p1"])
        self.assertEqual({r["status"] for r in explicit["targets"]}, {"expected_supported"})


if __name__ == "__main__":
    unittest.main()
