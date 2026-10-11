"""Software tests with synthetic audio/model evidence; not pronunciation accuracy."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from scipy.io import wavfile

import phoneme_practice as practice
from phoneme_scoring.align_audio import prepare_audio, split_phone
from phoneme_scoring.gop_score import _score_logprobs


def fixture(sentence, root, offset=.75):
    """Distinct word/phone intervals with leading silence and internal pauses."""
    words, phones, segments = [], [(0., offset, "sil")], []
    now = offset
    for word in sentence["words"]:
        begin = now
        for phone in word["variants"][0]:
            phones.append((now, now + .12, phone))
            now += .12
        words.append((begin, now, word["text"]))
        phones.append((now, now + .2, "sil"))
        now += .2
    duration = now + .4
    phones[-1] = (phones[-1][0], duration, "sil")
    word_intervals = [(0., offset, "")]
    for i, word in enumerate(words):
        word_intervals.append(word)
        word_intervals.append((word[1], words[i+1][0] if i+1 < len(words) else duration, ""))
    text = f'File type = "ooTextFile short"\n"TextGrid"\n0\n{duration}\n<exists>\n2\n'
    for name, entries in (("words", word_intervals), ("phones", phones)):
        text += f'"IntervalTier"\n"{name}"\n0\n{duration}\n{len(entries)}\n'
        text += "".join(f'{start}\n{end}\n"{label}"\n' for start, end, label in entries)
    path = Path(root) / "fixture.TextGrid"
    path.write_text(text, encoding="utf-8")
    for i, (start, end, phone) in enumerate(phones):
        base, stress = split_phone(phone)
        segments.append(dict(segment_id=f"p{i:04d}", canonical_phone=base,
                             original_phone=phone, stress=stress, start_sec=start, end_sec=end))
    return dict(status="available", duration_sec=duration, textgrid_path=str(path), segments=segments)


class PracticeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.sentence = practice.select_target("general_american", "think")[1]

    def tearDown(self):
        self.tmp.cleanup()

    def test_exact_prompts_and_manual_targets(self):
        sentences = practice.load_targets()["general_american"]["sentences"]
        self.assertEqual([s["text"] for s in sentences],
                         ["I think so.", "The bed is bad.", "The ship is here."])
        for sentence in sentences:
            alignment = fixture(sentence, self.root)
            words = practice.aligned_words(alignment, sentence)
            rows, onset, end = practice.bind_targets(alignment, words, sentence)
            self.assertEqual(len(rows), sum(len(w["variants"][0]) for w in sentence["words"]))
            self.assertTrue(all(r["manual_target_supported"] for r in rows))
            self.assertAlmostEqual(onset, .75)
            self.assertAlmostEqual(rows[0]["sentence_start_sec"], 0.)
            self.assertAlmostEqual(end, words[-1]["end_sec"])

    def test_leading_silence_does_not_shift_relative_times_or_close_pauses(self):
        groups = []
        for offset in (.75, 2.):
            alignment = fixture(self.sentence, self.root, offset=offset)
            words = practice.aligned_words(alignment, self.sentence)
            rows, _, _ = practice.bind_targets(alignment, words, self.sentence)
            groups.append(rows)
            self.assertAlmostEqual(rows[1]["sentence_start_sec"] - rows[0]["sentence_end_sec"], .2)
        for a, b in zip(*groups):
            self.assertAlmostEqual(a["sentence_start_sec"], b["sentence_start_sec"])
            self.assertAlmostEqual(b["start_sec"] - a["start_sec"], 1.25)

    def test_missing_or_wrong_words_and_crossing_boundaries_rejected(self):
        alignment = fixture(self.sentence, self.root)
        wrong = deepcopy(self.sentence)
        wrong["words"][0]["text"] = "you"
        with self.assertRaisesRegex(ValueError, "word labels"):
            practice.aligned_words(alignment, wrong)
        words = practice.aligned_words(alignment, self.sentence)
        alignment["segments"][1]["start_sec"] = .74
        alignment["segments"][0]["end_sec"] = .74
        with self.assertRaisesRegex(ValueError, "boundaries"):
            practice.bind_targets(alignment, words, self.sentence)
        path = Path(alignment["textgrid_path"])
        path.write_text(path.read_text().replace('"words"', '"other"'))
        with self.assertRaisesRegex(ValueError, "word timing"):
            practice.aligned_words(alignment, self.sentence)

    def test_unsupported_dictionary_variant_is_not_silently_accepted(self):
        alignment = fixture(self.sentence, self.root)
        alignment["segments"][3].update(canonical_phone="IY", original_phone="IY1", stress=1)
        words = practice.aligned_words(alignment, self.sentence)
        rows, _, _ = practice.bind_targets(alignment, words, self.sentence)
        self.assertTrue(all(not r["manual_target_supported"] for r in rows if r["word"] == "think"))

    def test_decisions_need_multiple_frames_and_strong_evidence(self):
        row = dict(manual_target_supported=True, status="scored", evidence_frames=2,
                   target_token="θ", winning_phone="θ", expected_vs_alternative_nats=2.)
        self.assertEqual(practice.classify(row)[0], "Correct")
        self.assertEqual(practice.classify({**row, "winning_phone": None, "target_token": None})[0], "Uncertain")
        row.update(winning_phone="s", expected_vs_alternative_nats=-2.)
        self.assertEqual(practice.classify(row)[0], "Incorrect")
        for changes in ({"evidence_frames": 1}, {"status": "uncertain"},
                        {"expected_vs_alternative_nats": -.5}, {"expected_vs_alternative_nats": float("nan")},
                        {"manual_target_supported": False}, {"winning_phone": None}):
            self.assertEqual(practice.classify({**row, **changes})[0], "Uncertain")

    def test_accepted_reduction_compared_against_nonaccepted_alternatives(self):
        settings = practice.load_settings(practice.BASE / "phoneme_scoring" / "settings.json")
        mapping = json.loads((practice.BASE / "phoneme_scoring" / "phoneme_map.json").read_text())
        vocab = {"<pad>": 0, "ə": 1, "iː": 2, "s": 3}
        segment = dict(segment_id="vowel", canonical_phone="AH", original_phone="AH0", stress=0,
                       start_sec=0., end_sec=.1, accepted_target_tokens=["ə", "iː"], manual_target_supported=True)
        # Strong evidence for the other accepted realization must not become red.
        logits = np.array([[0., 1., 7., 0.], [0., 1., 7., 0.]])
        logp = logits - np.logaddexp.reduce(logits, axis=1)[:, None]
        row = _score_logprobs(logp, np.array([.03, .05]), [segment], mapping, vocab, {0}, settings["scoring"])[0]
        self.assertEqual(row["target_token"], "iː")
        self.assertEqual(row["competing_phone"], "s")
        self.assertEqual(practice.classify(row)[0], "Correct")
        # Legacy callers without an accepted-set override keep their old result.
        segment.pop("accepted_target_tokens")
        legacy = _score_logprobs(logp, np.array([.03, .05]), [segment], mapping, vocab, {0}, settings["scoring"])[0]
        self.assertEqual(legacy["target_token"], "ə")
        self.assertLess(legacy["expected_vs_alternative_nats"], 0)

    def test_score_join_uses_ids_and_preserves_timing(self):
        alignment = fixture(self.sentence, self.root)
        rows, _, _ = practice.bind_targets(alignment, practice.aligned_words(alignment, self.sentence), self.sentence)
        score = dict(segment_id=rows[0]["segment_id"], status="scored", target_token="aɪ", winning_phone="aɪ",
                     evidence_frames=2, expected_vs_alternative_nats=3., start_sec=999.)
        joined = practice.join_results(rows, {"segments": [score]}, 1.)
        self.assertEqual(joined[0]["judgment"], "Correct")
        self.assertEqual(joined[0]["start_sec"], .75)
        self.assertEqual(joined[1]["judgment"], "Uncertain")
        with self.assertRaisesRegex(ValueError, "uniquely"):
            practice.join_results(rows, {"segments": [score, score]}, 1.)

    def test_reference_free_pipeline_saves_audio_timing_and_judgments(self):
        alignment = fixture(self.sentence, self.root)
        sr = 16000
        samples = (.1 * np.sin(np.arange(round(alignment["duration_sec"] * sr)) * .1)).astype(np.float32)
        audio = self.root / "learner.wav"
        wavfile.write(audio, sr, samples)

        def fake_align(audio, transcript, settings, run_dir):
            self.assertEqual(transcript, self.sentence["text"])
            _, _, digest = prepare_audio(audio, settings)
            return {**alignment, "audio_sha256": digest}

        def fake_score(audio, aligned, settings):
            self.assertGreaterEqual(settings["scoring"]["min_evidence_frames"], 2)
            output = []
            for i, seg in enumerate(aligned["segments"]):
                target = seg["accepted_target_tokens"][0]
                output.append(dict(segment_id=seg["segment_id"], status="scored", target_token=target,
                                   winning_phone="s" if i == 1 else target, evidence_frames=2,
                                   expected_vs_alternative_nats=-3. if i == 1 else 3.))
            return {"status": "available", "segments": output[::-1]}

        with patch.object(practice, "align_audio", side_effect=fake_align), patch.object(practice, "score_phonemes", side_effect=fake_score):
            result = practice.run_practice(str(audio), "general_american", "think", self.root / "runs")
        self.assertEqual(result["status"], "complete", result["messages"])
        self.assertEqual(result["rows"][1]["judgment"], "Incorrect")
        self.assertEqual(result["sentence_onset_sec"], .75)
        saved = json.loads(Path(result["results_path"]).read_text())
        self.assertFalse(saved["calibrated"])
        _, cropped = wavfile.read(result["sentence_audio"])
        self.assertEqual(len(cropped), round(result["sentence_offset_sec"] * sr) - round(.75 * sr))
        self.assertEqual(Path(result["original_audio"]).read_bytes(), audio.read_bytes())
        self.assertTrue(all(Path(r["audio_path"]).is_file() for r in result["rows"]))
        self.assertIn("Incorrect", practice.highlights(result))

    def test_bad_audio_has_no_fabricated_judgments(self):
        result = practice.run_practice(None, "general_american", "think", self.root)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["rows"], [])
        self.assertTrue(Path(result["results_path"]).is_file())

    def test_gradio_controls_and_callbacks(self):
        demo = practice.build_app()
        try:
            controls = {getattr(c, "label", None): c for c in demo.blocks.values()}
            self.assertEqual(controls["Target accent"].value, "general_american")
            self.assertEqual(len(controls["Practice sentence"].choices), 3)
            callback = next(f.fn for f in demo.fns.values() if f.fn and f.fn.__name__ == "analyze_attempt")
            with patch.object(practice, "run_practice", side_effect=RuntimeError("model missing")):
                generator = callback(None, "general_american", "think")
                initial, final = next(generator), next(generator)
            self.assertEqual(len(initial), 13)
            self.assertFalse(initial[-1]["interactive"])
            self.assertTrue(final[-1]["interactive"])
            self.assertIn("model missing", final[0])
            self.assertEqual(final[2], [])
            self.assertIsNone(final[8])
        finally:
            demo.close()


if __name__ == "__main__":
    unittest.main()
