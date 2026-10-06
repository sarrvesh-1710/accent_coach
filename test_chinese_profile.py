"""Software-contract tests with synthetic fixtures, not pronunciation validation."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import numpy as np

import app
import pipeline
from accent_profiles import load_profile, apply_profile
from phoneme_scoring.align_audio import load_settings
from phoneme_scoring.calibration import apply_calibration, feature_values, predict, signature
from phoneme_scoring.calibrate_scores import fit
from phoneme_scoring.speechocean_data import load_records, match_ratings, attach_word_indices

ROOT = Path(__file__).resolve().parents[1]


def evidence(margin=1.):
    return {"segment_id": "p0", "canonical_phone": "TH", "start_sec": 0., "end_sec": .2,
            "status": "scored", "raw_score": min(margin, 0.), "score_units": "natural_log_ratio_nats",
            "expected_vs_alternative_nats": margin, "evidence_frames": 3, "total_frames": 10}


def training_rows(sig="fixture"):
    rows = []
    for speaker in range(5):
        for i in range(20):
            margin = (i-10)/4
            rows.append({"utterance_id": f"{speaker}_{i}", "word_index": 0, "phone_index_in_word": 0,
                         "speaker_id": str(speaker), "split": "train", "signature": sig,
                         "match_status": "matched", "evidence": evidence(margin),
                         "human_rating": float(np.clip(1 + .3*margin, 0, 2))})
    return rows


class ChineseProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.settings = apply_profile(load_settings(ROOT / "phoneme_scoring/settings.json"), "chinese")

    def test_profile_selection_and_unknown_ids(self):
        self.assertEqual(load_profile("chinese")["learner_language"], "Mandarin Chinese")
        with self.assertRaises(ValueError):
            load_profile("../../anything")
        self.assertFalse(load_profile("general")["calibration"]["enabled"])

    def test_missing_calibration_keeps_raw_evidence(self):
        scored = {"segments": [evidence(-2.)]}
        apply_calibration(scored, self.settings, self.root)
        self.assertEqual(scored["calibration_status"], "not_trained")
        self.assertEqual(scored["segments"][0]["raw_score"], -2.)
        self.assertIsNone(scored["segments"][0]["predicted_phone_rating"])

    def test_training_speaker_split_and_test_rejection(self):
        model = fit(training_rows())
        self.assertFalse(set(model["train_speakers"]) & set(model["development_speakers"]))
        self.assertTrue(model["validation"]["beats_mean_baseline_mae"])
        rows = training_rows(); rows[0]["split"] = "test"
        with self.assertRaises(ValueError):
            fit(rows)
        with self.assertRaises(ValueError):
            fit(training_rows() + training_rows()[:1])

    def test_model_loading_compatibility_and_abstention(self):
        model = fit(training_rows(signature(self.settings)))
        path = self.root / "models/chinese_phone_calibration.json"
        path.parent.mkdir(); path.write_text(json.dumps(model))
        uncertain = evidence(); uncertain["status"] = "uncertain"
        unknown = evidence(); unknown["canonical_phone"] = "IY"
        scored = {"segments": [evidence(), uncertain, unknown]}
        apply_calibration(scored, self.settings, self.root)
        self.assertTrue(scored["calibrated"])
        self.assertEqual(scored["calibration_count"], 1)
        self.assertIsNone(scored["segments"][1]["predicted_phone_rating"])
        self.assertIsNone(scored["segments"][2]["predicted_phone_rating"])
        self.settings["scoring"]["min_winner_margin_nats"] = 99
        apply_calibration(scored, self.settings, self.root)
        self.assertEqual(scored["calibration_status"], "unavailable")
        self.assertTrue(all(r["predicted_phone_rating"] is None for r in scored["segments"]))

    def test_annotation_join_excludes_mismatch_without_shifting(self):
        segments = [dict(evidence(), canonical_phone="IH", end_sec=.1),
                    dict(evidence(), segment_id="p1", canonical_phone="T", start_sec=.1)]
        words = attach_word_indices(segments, [(0., .2, "IT")])
        record = {"utterance_id": "001", "speaker_id": "001", "split": "train",
                  "words": [{"text": "IT", "phones": ["IH0", "T"], "phones-accuracy": [1.2, 2.]}]}
        alignment = {"segments": segments, "words": words}
        rows = match_ratings(record, alignment, {"segments": segments})
        self.assertEqual([r["human_rating"] for r in rows], [1.2, 2.])
        self.assertTrue(all(r["match_status"] == "matched" for r in rows))
        segments[0]["canonical_phone"] = "IY"
        rows = match_ratings(record, alignment, {"segments": segments})
        self.assertTrue(all("evidence" not in r for r in rows))

    def test_loader_both_phone_formats_and_pipe_rejection(self):
        (self.root / "resource").mkdir(); (self.root / "train").mkdir()
        words = [{"text": "IT", "phones": "IH0 T", "phones-accuracy": [1.2, 2.]}]
        scores = {"001": {"words": words, "completeness": 10.}}
        score_path = self.root / "resource/scores.json"
        score_path.write_text(json.dumps(scores))
        for name, value in {"text": "001 IT\n", "utt2spk": "001 0001\n",
                            "wav.scp": "001 prefix/WAVE/SPEAKER0001/001.WAV\n"}.items():
            (self.root / "train" / name).write_text(value)
        record = load_records(self.root)[0]
        self.assertEqual(record["words"][0]["phones"], ["IH0", "T"])
        self.assertEqual(record["sentence_ratings"]["completeness"], 10.)
        self.assertEqual(Path(record["wav"]), self.root / "WAVE/SPEAKER0001/001.WAV")
        words[0]["phones"] = ["IH0", "T"]
        score_path.write_text(json.dumps(scores))
        self.assertEqual(load_records(self.root)[0]["words"][0]["phones"], ["IH0", "T"])
        (self.root / "train/wav.scp").write_text("001 arbitrary-command |\n")
        with self.assertRaises(ValueError):
            load_records(self.root)

    def test_pipeline_chinese_without_reference_and_switch_back(self):
        learner = self.root / "learner.wav"; learner.write_bytes(b"mock wav")
        (self.root / "phoneme_scoring").mkdir()
        for name in ("settings.json", "phoneme_map.json"):
            (self.root / "phoneme_scoring" / name).write_text((ROOT / "phoneme_scoring" / name).read_text())
        prompt = {"id": "test", "text": "TH", "reference_wav": "missing.wav",
                  "target_words": [], "target_phones": ["TH"], "lesson_links": []}
        (self.root / "prompts.json").write_text(json.dumps([prompt]))
        audio = {"status": "ok", "sample_rate_hz": 16000, "duration_sec": 1., "samples": np.zeros(16000)}
        modules = {
            "audio_io": types.SimpleNamespace(prepare_audio=lambda path, settings: deepcopy(audio) if Path(path).is_file() else {"status": "unavailable", "reason": "missing"}),
            "dsp_features": types.SimpleNamespace(extract_features=lambda *a: {"status": "ok"}),
            "compare_audio": types.SimpleNamespace(compare_audio=lambda *a: {"status": "unavailable", "reason": "reference_missing"}),
            "phoneme_scoring.align_audio": types.SimpleNamespace(align_audio=lambda *a: {"status": "available", "segments": [evidence()]}),
            "phoneme_scoring.gop_score": types.SimpleNamespace(score_phonemes=lambda *a: {"status": "available", "segments": [evidence()]}),
        }
        with patch.object(pipeline, "BASE_DIR", self.root), patch.dict("sys.modules", modules):
            result = pipeline.run_attempt(str(learner), "test", "chinese")
            self.assertEqual(result["overall_status"], "partial", result["messages"])
            self.assertEqual(result["phoneme_results"]["profile_id"], "chinese")
            self.assertEqual(result["phoneme_results"]["calibration_status"], "not_trained")
            self.assertIn("Mandarin", " ".join(result["feedback"]))
            saved = json.loads(Path(result["results_path"]).read_text())
            self.assertEqual(saved["accent_profile"]["id"], "chinese")
            self.assertEqual(len(app.evidence_rows(result)[0]), 11)
            model_path = self.root / "models/chinese_phone_calibration.json"
            model_path.parent.mkdir()
            model_path.write_text(json.dumps(fit(training_rows(signature(result["settings"])))))
            calibrated = pipeline.run_attempt(str(learner), "test", "chinese")
            self.assertTrue(calibrated["phoneme_results"]["calibrated"])
            self.assertIsNotNone(app.evidence_rows(calibrated)[0][-2])
            general = pipeline.run_attempt(str(learner), "test", "general")
            self.assertEqual(general["overall_status"], "failed")
            self.assertEqual(general["accent_profile"]["id"], "general")
            self.assertEqual(general["phoneme_results"]["segments"], [])


if __name__ == "__main__":
    unittest.main()
