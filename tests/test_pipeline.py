"""Integration and failure contracts; synthetic tones are not speech validation."""

from copy import deepcopy
from contextlib import contextmanager
import json
from pathlib import Path
import tempfile
import sys
import types
import unittest
from unittest.mock import patch

import numpy as np
import soundfile as sf

import app
import pipeline
from phoneme_scoring.align_audio import prepare_audio as prepare_scoring_audio, config_path
from phoneme_scoring.gop_score import score_phonemes

SCORING_DIR = Path(pipeline.__file__).parent / "phoneme_scoring"


@contextmanager
def substitute_modules(replacements):
    # Restore only our two test doubles. Restoring the entire sys.modules mapping
    # would unload lazily imported native audio extensions and crash on reimport.
    absent = object()
    previous = {name: sys.modules.get(name, absent) for name in replacements}
    sys.modules.update(replacements)
    try:
        yield
    finally:
        for name, module in previous.items():
            if module is absent:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "phoneme_scoring").mkdir()
        for name in ("settings.json", "phoneme_map.json"):
            (self.root / "phoneme_scoring" / name).write_text(
                (SCORING_DIR / name).read_text(encoding="utf-8"), encoding="utf-8")
        self.patch = patch.object(pipeline, "BASE_DIR", self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        pipeline._REFERENCE_CACHE.clear()
        self.prompt = {"id": "test", "text": "I think so", "reference_wav": "reference.wav",
                       "target_words": ["think"], "target_phones": ["TH"], "lesson_links": []}
        (self.root / "prompts.json").write_text(json.dumps([self.prompt]), encoding="utf-8")
        t = np.arange(32000) / 16000
        self.tone = .15 * np.sin(2 * np.pi * 180 * t)
        self.learner = self.root / "learner.wav"
        sf.write(self.learner, self.tone, 16000)
        sf.write(self.root / "reference.wav", self.tone, 16000)
        self.alignment = {"status": "available", "segments": [
            {"segment_id": "first", "canonical_phone": "TH", "start_sec": 0.1, "end_sec": .4},
            {"segment_id": "second", "canonical_phone": "IH", "start_sec": .5, "end_sec": .8}]}
        self.scores = {"status": "available", "segments": [
            {"segment_id": "second", "raw_score": np.float32(-2), "score_units": "natural_log", "competing_phone": "IY", "status": "scored"},
            {"segment_id": "first", "raw_score": -1.0, "score_units": "natural_log", "competing_phone": "S", "status": "scored"}]}

    def modules(self, score=None, alignment=None):
        captured = {}
        def align(audio, transcript, settings, run_dir):
            self.assertIsInstance(audio, str)
            self.assertEqual(Path(audio).parent, Path(run_dir))
            self.assertEqual(transcript, self.prompt["text"])
            self.assertTrue(config_path(settings["scoring"]["map_path"], settings).is_file())
            _, _, fingerprint = prepare_scoring_audio(audio, settings)
            captured.update(audio=audio, settings=deepcopy(settings), fingerprint=fingerprint)
            output = deepcopy(self.alignment if alignment is None else alignment)
            output["audio_sha256"] = fingerprint
            return output
        def scoring(audio, aligned, settings):
            self.assertEqual(audio, captured["audio"])
            self.assertEqual(settings, captured["settings"])
            self.assertEqual(prepare_scoring_audio(audio, settings)[2], aligned["audio_sha256"])
            if isinstance(score, Exception):
                raise score
            return deepcopy(self.scores if score is None else score)
        return substitute_modules({
            "phoneme_scoring.align_audio": types.SimpleNamespace(align_audio=align),
            "phoneme_scoring.gop_score": types.SimpleNamespace(score_phonemes=scoring)})

    def attempt(self):
        result = pipeline.run_attempt(str(self.learner), "test")
        self.assertIsNotNone(result["results_path"], result["messages"])
        saved = json.loads(Path(result["results_path"]).read_text(encoding="utf-8"))
        self.assertEqual(saved, result)
        self.assertNotIn('"samples"', json.dumps(saved))
        return result

    def test_real_dsp_and_mocked_scoring_complete_then_cached(self):
        with self.modules():
            first = self.attempt()
            second = self.attempt()
        self.assertEqual(first["overall_status"], "complete", first["messages"])
        self.assertEqual(second["overall_status"], "complete")
        self.assertNotEqual(first["run_id"], second["run_id"])
        self.assertTrue(second["stage_statuses"]["reference_dsp"]["cached"])
        self.assertAlmostEqual(first["comparison"]["duration_ratio"], 1)
        self.assertAlmostEqual(first["comparison"]["dtw_distance"], 0)
        self.assertEqual(app.evidence_rows(first)[0][4], -1)
        self.assertIn("<svg", app.pitch_html(first))

    def test_gop_failure_preserves_acoustics(self):
        with self.modules(score=RuntimeError("model unavailable")):
            result = self.attempt()
        self.assertEqual(result["overall_status"], "partial")
        self.assertIn(result["comparison"]["status"], {"ok", "warning"})
        self.assertIn("model unavailable", " ".join(result["messages"]))
        self.assertTrue(all(row[-1] == "unavailable" for row in app.evidence_rows(result)))

    def test_missing_alignment_module_is_partial(self):
        with substitute_modules({"phoneme_scoring.align_audio": None}):
            result = self.attempt()
        self.assertEqual(result["overall_status"], "partial")
        self.assertEqual(result["stage_statuses"]["phoneme_scoring"]["status"], "skipped")

    def test_missing_reference_rejected(self):
        (self.root / "reference.wav").unlink()
        result = self.attempt()
        self.assertEqual(result["overall_status"], "failed")
        self.assertIn("Missing reference", " ".join(result["messages"]))

    def test_silence_rejected_and_retry_has_no_stale_results(self):
        with self.modules():
            self.assertEqual(self.attempt()["overall_status"], "complete")
            sf.write(self.learner, np.zeros(32000), 16000)
            result = self.attempt()
        self.assertEqual(result["overall_status"], "failed")
        self.assertEqual(result["comparison"], {})
        self.assertIsNone(result["audio_paths"]["original"])
        self.assertIn("silent_audio", " ".join(result["messages"]))

    def test_overlong_and_invalid_wav_rejected(self):
        sf.write(self.learner, np.tile(self.tone, 3), 16000)
        self.assertEqual(self.attempt()["overall_status"], "failed")
        self.learner.write_bytes(b"not a wav")
        self.assertEqual(self.attempt()["overall_status"], "failed")

    def test_alignment_outside_audio_is_unavailable(self):
        alignment = deepcopy(self.alignment)
        alignment["segments"][0]["end_sec"] = 99
        with self.modules(alignment=alignment):
            result = self.attempt()
        self.assertEqual(result["overall_status"], "partial")
        self.assertEqual(result["stage_statuses"]["alignment"]["status"], "unavailable")
        self.assertEqual(app.evidence_rows(result), [])

    def test_uncertain_or_incomplete_scores_never_complete(self):
        uncertain = deepcopy(self.scores)
        uncertain["segments"][0]["status"] = "uncertain"
        for scores in (uncertain, {"status": "available", "segments": self.scores["segments"][:1]}):
            with self.subTest(scores=scores), self.modules(score=scores):
                self.assertEqual(self.attempt()["overall_status"], "partial")

    def test_nonfinite_scores_rejected_and_json_null(self):
        scores = deepcopy(self.scores)
        scores["segments"][0]["raw_score"] = float("nan")
        with self.modules(score=scores):
            self.assertEqual(self.attempt()["stage_statuses"]["phoneme_scoring"]["status"], "unavailable")
        self.assertEqual(pipeline.json_safe({"array": np.array([np.nan, np.inf, 3]), "samples": self.tone}), {"array": [None, None, 3.0]})

    def test_settings_and_reference_change_invalidate_cache(self):
        with self.modules():
            self.attempt()
            settings_path = self.root / "phoneme_scoring" / "settings.json"
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            settings["pitch_floor_hz"] = 80
            settings_path.write_text(json.dumps(settings), encoding="utf-8")
            changed = self.attempt()
            self.assertNotIn("cached", changed["stage_statuses"]["reference_dsp"])
            sf.write(self.root / "reference.wav", self.tone[:16000], 16000)
            replaced = self.attempt()
            self.assertNotIn("cached", replaced["stage_statuses"]["reference_dsp"])

    def test_bad_settings_and_unknown_prompt_save_failure(self):
        (self.root / "phoneme_scoring" / "settings.json").write_text('{"device": "cuda"}', encoding="utf-8")
        self.assertEqual(self.attempt()["overall_status"], "failed")
        result = pipeline.run_attempt(str(self.learner), "unknown")
        self.assertEqual(result["overall_status"], "failed")
        self.assertTrue(Path(result["results_path"]).is_file())

    def test_write_failure_never_claims_saved(self):
        with patch.object(Path, "mkdir", side_effect=PermissionError("read only")):
            result = pipeline.run_attempt(str(self.learner), "test")
        self.assertIsNone(result["results_path"])
        self.assertEqual(result["stage_statuses"]["save"]["status"], "unavailable")

    def test_gradio_builds_and_callbacks_clear_outputs(self):
        demo = app.build_app()
        callback = next(fn.fn for fn in demo.fns.values() if getattr(fn.fn, "__name__", "") == "analyze_attempt")
        with self.modules():
            generator = callback(str(self.learner), "test")
            first = next(generator)
            self.assertEqual(first[2], [])
            self.assertIsNone(first[4])
            self.assertFalse(first[-1]["interactive"])
            last = next(generator)
            self.assertIn("Analysis complete", last[0])
            self.assertTrue(last[-1]["interactive"])
        demo.close()


if __name__ == "__main__":
    unittest.main()
