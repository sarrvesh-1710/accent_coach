"""Regression checks for honest evidence labels and pitch quality, not accuracy."""
import unittest
import json
from pathlib import Path

import numpy as np

import app
from dsp_features import extract_features
from phoneme_scoring.gop_score import _score_logprobs, _mapping


class EvidenceQualityTests(unittest.TestCase):
    def score(self, retained, total=4, expected=8., alternative=1.):
        folder = Path(__file__).resolve().parents[1] / "phoneme_scoring"
        settings = json.loads((folder / "settings.json").read_text(encoding="utf-8"))
        settings["_settings_dir"] = str(folder)
        vocab = {"<pad>": 0, "θ": 1, "s": 2}
        logits = np.array([[0., expected, alternative]] * retained + [[8., 0., 0.]] * (total-retained))
        logp = logits - np.logaddexp.reduce(logits, axis=1)[:, None]
        segment = dict(segment_id="test", canonical_phone="TH", start_sec=0, end_sec=total*.02)
        row = _score_logprobs(logp, .01 + np.arange(total)*.02, [segment],
                             _mapping(settings), vocab, {0}, settings["scoring"])[0]
        return segment, row

    def test_short_and_long_segments_keep_sparse_diagnostics(self):
        for total in (2, 40):
            with self.subTest(total=total):
                _, row = self.score(1, total)
                self.assertEqual(row["status"], "uncertain")
                self.assertEqual(row["raw_score"], 0.)
                self.assertEqual(row["reason"], "single_ctc_frame")
                self.assertEqual(row["evidence_quality"], "sparse")
                self.assertAlmostEqual(row["expected_vs_alternative_nats"], 7.)

    def test_blank_only_never_gets_a_score(self):
        _, row = self.score(0)
        self.assertIsNone(row["raw_score"])
        self.assertNotIn("expected_vs_alternative_nats", row)
        self.assertEqual(row["status"], "uncertain")

    def test_alternative_and_ambiguous_winners_are_not_hidden(self):
        _, row = self.score(1, expected=1, alternative=8)
        self.assertAlmostEqual(row["expected_vs_alternative_nats"], -7.)
        self.assertEqual(row["winning_phone"], "s")
        _, row = self.score(2, expected=8, alternative=7.9)
        self.assertEqual(row["status"], "uncertain")
        self.assertEqual(row["reason"], "ambiguous_acoustic_winner")

    def test_three_strong_frames_allow_raw_comparison(self):
        _, row = self.score(3)
        self.assertEqual(row["status"], "scored")
        self.assertEqual(row["raw_score"], 0.)

    def test_table_distinguishes_sparse_diagnostic_from_missing_score(self):
        segment, row = self.score(1)
        result = {"alignment": {"segments": [segment]}, "phoneme_results": {"segments": [row]}}
        displayed = app.evidence_rows(result)[0]
        self.assertAlmostEqual(displayed[4], 7.)
        self.assertEqual(displayed[7], "1/4")
        self.assertIn("Single CTC frame", displayed[8])
        self.assertEqual(displayed[9], "limited evidence")
        result["phoneme_results"]["segments"] = [self.score(3)[1]]
        self.assertEqual(app.evidence_rows(result)[0][-1], "evidence available")
        result["phoneme_results"]["segments"] = [self.score(0)[1]]
        self.assertIsNone(app.evidence_rows(result)[0][4])

    def test_background_hum_is_masked_without_removing_low_voice(self):
        t = np.arange(48000)/16000
        x = .02*np.sin(2*np.pi*55*t)
        speech = (t >= 1) & (t < 2)
        x[speech] += .2*np.sin(2*np.pi*80*t[speech])
        for gain in (1., .01):
            with self.subTest(gain=gain):
                result = extract_features({"status": "ok", "samples": x*gain, "sample_rate_hz": 16000})
                times = np.asarray(result["time_sec"])
                mask = np.asarray(result["voiced_mask"])
                self.assertFalse(mask[(times < .8) | (times > 2.2)].any())
                self.assertGreater(mask[(times > 1.2) & (times < 1.8)].mean(), .8)
                self.assertAlmostEqual(result["pitch_median_hz"], 80, delta=2)
                self.assertIn("background_level_energy", result["pitch_invalid_reason"])

    def test_stable_low_and_high_pitch_survive_filter(self):
        for hz in (65, 180, 450):
            with self.subTest(hz=hz):
                samples = .2 * np.sin(2*np.pi*hz*np.arange(16000)/16000)
                original = samples.copy()
                result = extract_features({"status": "ok", "samples": samples, "sample_rate_hz": 16000})
                np.testing.assert_array_equal(samples, original)
                self.assertGreater(result["voiced_fraction"], .8)
                self.assertAlmostEqual(result["pitch_median_hz"], hz, delta=2)
                for key in ("pitch_hz", "voiced_mask", "pitch_semitones", "pitch_strength", "pitch_invalid_reason"):
                    self.assertEqual(len(result[key]), len(result["time_sec"]))
                for valid, pitch, reason in zip(result["voiced_mask"], result["pitch_hz"], result["pitch_invalid_reason"]):
                    self.assertEqual(valid, pitch is not None)
                    self.assertEqual(valid, reason is None)

    def test_invalid_pitch_quality_parameters_rejected(self):
        audio = {"status": "ok", "samples": np.ones(16000)*.1, "sample_rate_hz": 16000}
        for settings in ({"pitch_filter_attenuation": 0}, {"pitch_min_run_frames": True},
                         {"pitch_min_strength": 2}, {"pitch_max_jump_semitones": -1}):
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                extract_features(audio, settings)


if __name__ == "__main__":
    unittest.main()
