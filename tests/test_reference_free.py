import unittest
from unittest.mock import patch

import app_2
from phoneme_scoring.align_audio import attach_words
from tools.evaluate_recordings import template, summarize
from tools.check_reference_free import operational_pass


class ReferenceFreeTests(unittest.TestCase):
    def test_operational_check_distinguishes_uncertainty_from_model_failure(self):
        r = dict(stage_statuses={
            "alignment": {"status": "available"}, "learner_dsp": {"status": "ok"}, "save": {"status": "ok"},
            **{s: {"status": "skipped"} for s in ("reference_audio", "reference_dsp", "comparison")}},
            audio_paths={"reference": None}, phoneme_results=dict(status="uncertain", timing={"stride_samples": 320},
            model_revision="pinned", segments=[{"status": "uncertain"}]))
        self.assertTrue(operational_pass(r))
        r["phoneme_results"].pop("timing")
        self.assertFalse(operational_pass(r))

    def test_phone_word_association_requires_containment(self):
        segments = [dict(start_sec=0.1, end_sec=0.2), dict(start_sec=0.9, end_sec=1.1)]
        words = attach_words(segments, {"words": [(0, 1, "ship"), (1, 2, "is")]}, 2)
        self.assertEqual(segments[0]["word"], "ship")
        self.assertNotIn("word", segments[1])
        self.assertEqual(len(words), 2)
        self.assertEqual(attach_words(segments, {"phones": []}, 2), [])

    def test_invalid_word_boundaries_are_rejected(self):
        with self.assertRaises(ValueError):
            attach_words([], {"words": [(0, 3, "ship")]}, 2)

    def test_reference_free_ui_builds_without_example_paths(self):
        with patch.object(app_2, "load_prompts", return_value=[dict(id="think", text="I think so")]):
            demo = app_2.build_app()
        self.assertIsNone(app_2.reference_file(dict(id="think")))
        components = demo.get_config_file()["components"]
        checkboxes = [c for c in components if c["type"] == "checkbox"]
        self.assertTrue(all('delete' in c['props']['label'].lower() for c in checkboxes))
        demo.close()

    def test_evaluation_does_not_treat_requested_conditions_as_labels(self):
        rows = [dict(r, outcome="missing_recording") for r in template()["records"]]
        report = summarize(rows)
        self.assertEqual(report["planned"], 36)
        self.assertEqual(len({r["pair_id"] for r in rows}), 18)
        self.assertEqual(sum(r["split"] == "held_out" for r in rows), 12)
        self.assertEqual(report["human_reviewed"], 0)
        self.assertEqual(report["analyzed"], 0)
        self.assertIsNone(report["pronunciation_accuracy"])


if __name__ == "__main__":
    unittest.main()
