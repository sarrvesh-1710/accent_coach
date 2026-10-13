"""Transcript preflight tests; dictionary coverage is not assessment accuracy."""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from transcript_input import prepare_transcript, sound_occurrences


class TranscriptInputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "test.dict"
        self.path.write_text("i\tAY1\nthink\t0.9\t0.2\t1.0\t1.0\tTH IH1 NG K\nso\tS OW1\n"
                             "don't\tD OW1 N T\nthat\tDH AE1 T\nthat\tDH AH0 T\n", encoding="utf-8")
        self.settings = {"mfa": {"dictionary": str(self.path)}}

    def prepare(self, text):
        return prepare_transcript(text, self.settings)

    def test_valid_and_dictionary_provenance(self):
        r = self.prepare("I think so.")
        self.assertTrue(r["ok"])
        self.assertEqual(r["normalized_text"], "i think so")
        self.assertEqual(r["dictionary"]["sha256"], hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertEqual(r["tokens"][1]["pronunciations"], [["TH", "IH1", "NG", "K"]])
        self.assertNotIn("outcome", r)

    def test_empty_and_invalid_type(self):
        for text in ["", " \t\n", None, 2, [], {}]:
            with self.subTest(text=text):
                r = self.prepare(text)
                self.assertFalse(r["ok"])
                self.assertEqual(r["error"]["code"], "UNSUPPORTED_TEXT")
                self.assertTrue(r["error"]["user_message"])
                self.assertFalse(r["error"]["retryable"])

    def test_punctuation_capitalization_offsets_contraction(self):
        text = '  “I,”\nDON’T (think); so?! '
        r = self.prepare(text)
        self.assertTrue(r["ok"])
        self.assertEqual(r["original_text"], text)
        self.assertEqual(r["normalized_text"], "i don't think so")
        self.assertEqual(r["word_count"], 4)
        for i, t in enumerate(r["tokens"]):
            self.assertEqual(t["word_index"], i)
            self.assertEqual(text[t["source_start"]:t["source_end"]], t["original_token"])

    def test_repeated_words_and_sounds_stable(self):
        r = self.prepare("Think think think.")
        self.assertEqual(r, self.prepare("Think think think."))
        ids = [t["occurrence_id"] for t in r["tokens"]]
        self.assertEqual(len(set(ids)), 3)
        rows = [row for t in r["tokens"] for row in sound_occurrences(t, ["TH", "TH", "IH1"])]
        self.assertEqual(len({row["occurrence_id"] for row in rows}), 9)
        self.assertEqual([x["phone_index"] for x in rows[:3]], [0, 1, 2])
        self.assertEqual(rows[2]["expected_phone"], "IH")
        self.assertNotEqual(ids[0], self.prepare("think think think.")["tokens"][0]["occurrence_id"])
        self.assertNotEqual(sound_occurrences(r["tokens"][0], ["TH"])[0]["occurrence_id"],
                            sound_occurrences(r["tokens"][0], ["S"])[0]["occurrence_id"])

    def test_variants_are_not_silently_selected(self):
        self.assertEqual(len(self.prepare("that")["tokens"][0]["pronunciations"]), 2)

    def test_missing_words_preserve_each_occurrence(self):
        r = self.prepare("I Zzunknown, zzunknown.")
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"]["code"], "UNSUPPORTED_TEXT")
        self.assertEqual([m["word_index"] for m in r["missing_words"]], [1, 2])
        self.assertEqual(r["missing_words"][0]["original_token"], "Zzunknown")
        self.assertEqual(r["missing_words"][0]["source_start"], 2)
        self.assertNotIn("mispronounced", str(r))

    def test_word_limit(self):
        self.assertTrue(self.prepare(" ".join(["don't"] * 12))["ok"])
        r = self.prepare(" ".join(["don't"] * 13))
        self.assertEqual(r["word_count"], 13)
        self.assertEqual(r["reason_code"], "WORD_LIMIT")

    def test_character_limit_on_original_input(self):
        text = "I" + " " * 199
        self.assertTrue(self.prepare(text)["ok"])
        self.assertEqual(self.prepare(text)["character_count"], 200)
        self.assertEqual(self.prepare(text + " ")["reason_code"], "TOO_MANY_CHARACTERS")

    def test_unsupported_characters_not_silently_dropped(self):
        for text in ["I 2", "café", "think-so", "<think>", "I🙂", "I/think", "don't'", "I\x00", "I\u00a0think"]:
            with self.subTest(text=text):
                r = self.prepare(text)
                self.assertEqual(r["reason_code"], "UNSUPPORTED_CHARACTER")
                position = r["invalid_character"]["source_start"]
                self.assertEqual(text[position], r["invalid_character"]["character"])
        self.assertEqual(self.prepare("...")["reason_code"], "WORD_LIMIT")

    def test_dictionary_failure_not_missing_words(self):
        for content in [None, "", "think\t0.5\n", b"\xff"]:
            if content is None:
                self.path.unlink()
            elif isinstance(content, bytes):
                self.path.write_bytes(content)
            else:
                self.path.write_text(content)
            r = self.prepare("think")
            self.assertEqual(r["error"]["code"], "MODEL_UNAVAILABLE")
            self.assertEqual(r["missing_words"], [])
            self.assertNotIn(str(self.path), r["error"]["user_message"])
        self.assertEqual(prepare_transcript("think", {})["error"]["code"], "MODEL_UNAVAILABLE")

    def test_configured_named_dictionary_and_changes(self):
        root = Path(self.temp.name)
        named = root / "pretrained_models/dictionary/fixture.dict"
        named.parent.mkdir(parents=True)
        named.write_bytes(self.path.read_bytes())
        cfg = {"mfa": {"dictionary": "fixture"}}
        with patch.dict(os.environ, {"MFA_ROOT_DIR": str(root)}):
            first = prepare_transcript("think", cfg)
            self.assertTrue(first["ok"])
            named.write_text("i\tAY1\n")
            second = prepare_transcript("think", cfg)
            self.assertEqual(second["reason_code"], "MISSING_DICTIONARY_WORDS")
            self.assertNotEqual(first["dictionary"]["sha256"], second["dictionary"]["sha256"])

    def test_settings_file_and_invalid_phone_input(self):
        import json
        cfg = Path(self.temp.name) / "settings.json"
        cfg.write_text(json.dumps(self.settings))
        self.assertTrue(prepare_transcript("think", cfg)["ok"])
        token = self.prepare("think")["tokens"][0]
        with self.assertRaises(ValueError):
            sound_occurrences(token, [])


if __name__ == "__main__":
    unittest.main()
