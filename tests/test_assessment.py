"""Validate sequence arithmetic and abstention, not pronunciation accuracy."""
import itertools
import math
import unittest
from unittest.mock import patch

import numpy as np

from assessment import summarize_assessment
from app_2 import assessment_notice
from phoneme_scoring.gop_score import _resolve
from phoneme_scoring.sequence_evidence import ctc_log_probability, compare_targets
from speech_content import compare_transcript, check_content


def collapse(path):
    return [token for i, token in enumerate(path) if token != 0 and (i == 0 or path[i - 1] != token)]


class SequenceTests(unittest.TestCase):
    def test_forward_matches_exhaustive_paths_including_repeated_phones(self):
        probs = np.array([[.6, .3, .1], [.3, .5, .2], [.5, .1, .4], [.2, .6, .2]])
        for labels in ([], [1], [2], [1, 2], [1, 1], [2, 1, 2]):
            total = sum(math.prod(probs[t, token] for t, token in enumerate(path))
                        for path in itertools.product(range(3), repeat=4) if collapse(path) == labels)
            self.assertAlmostEqual(math.exp(ctc_log_probability(np.log(probs), labels, 0)), total, places=12)

    def test_impossible_repeats_remain_impossible(self):
        self.assertEqual(ctc_log_probability(np.log([[.2, .8], [.2, .8]]), [1, 1], 0), -math.inf)

    def test_invalid_scores_and_target_ids_rejected(self):
        for lp, target in (([[float('nan'), 0]], [1]), ([[0, 0]], [0]), ([[0, 0]], [2])):
            with self.assertRaises(ValueError):
                ctc_log_probability(lp, target, 0)

    def setUp(self):
        self.mapping = dict(silence=["sil"], unsupported=["unk"], phones={"TH": "th", "S": "s"}, stress_overrides={})
        self.segments = [dict(segment_id="p1", word="think", canonical_phone="TH", start_sec=0, end_sec=.2)]
        self.local = [dict(segment_id="p1", target_token="th", winning_phone="th", evidence_frames=1, total_frames=3)]
        self.targets = [dict(word="think", phone="TH", alternatives=["S"])]

    def compare(self, probs, local=None, segments=None):
        return compare_targets(np.log(probs), segments or self.segments, self.local if local is None else local,
            self.mapping, {"blank": 0, "th": 1, "s": 2}, {0}, 0, self.targets,
            {"decision_margin_nats": 1}, _resolve)["targets"][0]

    def test_sequence_expected_and_alternative_have_opposite_margins(self):
        expected = self.compare([[.98,.01,.01], [.05,.9,.05], [.98,.01,.01]])
        alternative = self.compare([[.98,.01,.01], [.05,.05,.9], [.98,.01,.01]],
                                   [dict(self.local[0], winning_phone="s")])
        self.assertEqual(expected["status"], "expected_supported")
        self.assertEqual(alternative["status"], "alternative_favored")
        self.assertAlmostEqual(expected["margin_nats"], -alternative["margin_nats"])

    def test_ties_blank_only_and_outside_contrast_abstain(self):
        self.assertEqual(self.compare([[.2,.4,.4]])["status"], "insufficient_evidence")
        probs = [[.9,.08,.02]]
        for change in ({"evidence_frames": 0}, {"winning_phone": "unknown"}):
            row = self.compare(probs, [dict(self.local[0], **change)])
            self.assertEqual(row["status"], "insufficient_evidence")

    def test_target_word_must_match_not_other_instance_of_same_phone(self):
        row = self.compare([[.1,.85,.05]], segments=[dict(self.segments[0], word="other")])
        self.assertEqual(row["status"], "insufficient_evidence")
        self.assertNotIn("margin_nats", row)


class ContentAndSafeguardTests(unittest.TestCase):
    def setUp(self):
        self.prompt = dict(text="I think so", assessment_targets=[dict(word="think", phone="TH", alternatives=["S"])],
                           content_alternatives={"think": ["sink", "tink", "fink"]})

    def test_content_check_normalizes_punctuation_but_not_missing_words(self):
        self.assertEqual(compare_transcript(" I THINK so!", self.prompt)["status"], "match")
        self.assertEqual(compare_transcript("I sink so", self.prompt)["status"], "target_variant")
        for utterance in ("think so", "I think", "the ship is here", "I really think so", ""):
            self.assertEqual(compare_transcript(utterance, self.prompt)["status"], "mismatch")

    def test_asr_failure_is_unavailable_not_a_bad_grade(self):
        with patch("speech_content.prepare_audio", side_effect=RuntimeError("missing model")):
            actual = check_content("clip.wav", self.prompt, {"content_check": {"enabled": True}})
        self.assertEqual(actual["status"], "unavailable")

    def result(self):
        return dict(prompt=self.prompt, prompt_id="think", learner_audio={"status": "ok"},
                    spoken_words_verification={"status": "match", "transcript": "I think so"},
                    phoneme_results={"sequence_evidence": {"status": "available", "targets": [
                        dict(word="think", expected_phone="TH", alternative_phone="S", status="expected_supported", margin_nats=3)]}})

    def test_content_failure_or_clipping_blocks_positive_sound_feedback(self):
        for content in ("unavailable", "mismatch"):
            r = self.result()
            r["spoken_words_verification"]["status"] = content
            self.assertEqual(summarize_assessment(r)["targets"][0]["status"], "insufficient_evidence")
        r = self.result()
        r["learner_audio"]["warnings"] = ["possible_clipping"]
        self.assertEqual(summarize_assessment(r)["targets"][0]["status"], "insufficient_evidence")

    def test_supported_evidence_keeps_grade_null_and_does_not_mutate_raw_result(self):
        r = self.result()
        out = summarize_assessment(r)
        self.assertIsNone(out["grade"])
        self.assertFalse(out["calibrated"])
        out["targets"][0]["status"] = "changed"
        self.assertEqual(r["phoneme_results"]["sequence_evidence"]["targets"][0]["status"], "expected_supported")

    def test_ui_explains_model_evidence_and_escapes_transcript(self):
        r = self.result()
        r["target_assessment"] = summarize_assessment(r)
        self.assertIn("sounded closer to the expected sound", assessment_notice(r))
        self.assertIn("not a final grade", assessment_notice(r))
        self.assertIn("Recognized:</strong>", assessment_notice(r))
        r["spoken_words_verification"].update(status="mismatch", transcript="<script>bad</script>")
        self.assertNotIn("<script>", assessment_notice(r))
        self.assertIn("may have misheard", assessment_notice(r))


if __name__ == "__main__":
    unittest.main()

