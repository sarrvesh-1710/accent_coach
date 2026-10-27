"""Extraction/validation regressions; mocked inference is not accuracy evidence."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np
import soundfile as sf
import torch

import audio_io
import speech_content as speech
from phoneme_scoring.align_audio import prepare_audio


class TranscriptionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "learner.wav"
        self.samples = .1 * np.sin(2 * np.pi * 180 * np.arange(16000) / 16000)
        sf.write(self.path, self.samples, 16000, subtype="PCM_16")
        self.settings = json.loads((Path(__file__).parents[1] / "phoneme_scoring/settings.json").read_text())
        self.processor = Mock()
        self.tensor = torch.zeros((1, 80, 4))
        self.processor.return_value = {"input_features": self.tensor}
        self.processor.batch_decode.return_value = [" I think so. "]
        self.model = Mock()
        self.model.generate.side_effect = self.generate
        self.loader = self.enterContext(patch.object(speech, "_load_asr", return_value=(self.processor, self.model)))

    def generate(self, **kwargs):
        self.assertTrue(torch.is_inference_mode_enabled())
        return torch.tensor([[1, 2]])

    def test_independent_text_identity_and_provenance(self):
        result = speech.transcribe_audio(self.path, self.settings)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["transcription_status"], "completed")
        self.assertEqual(result["recognized_text"], "I think so.")
        self.assertIsNone(result["learner_audio_id"])
        self.assertEqual(result["source_audio_sha256"], hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertEqual(result["audio_sha256"], prepare_audio(self.path, self.settings)[2])
        self.assertEqual(result["model_id"], self.settings["content_check"]["model_id"])
        self.assertEqual(result["model_revision"], self.settings["content_check"]["revision"])
        self.assertNotIn("expected_text", result)
        self.assertIsNone(result["error"])

    def test_preprocessing_and_generation_arguments_unchanged(self):
        # Resampling and stereo mixing must use scoring preparation, not DSP output.
        stereo = np.column_stack([self.samples, self.samples / 2])
        sf.write(self.path, stereo, 22050, subtype="PCM_16")
        settings_before = deepcopy(self.settings)
        speech.transcribe_audio(self.path, self.settings)
        expected, sr, _ = prepare_audio(self.path, self.settings)
        args, kwargs = self.processor.call_args
        np.testing.assert_array_equal(args[0], expected)
        self.assertEqual(kwargs, dict(sampling_rate=sr, return_tensors="pt", return_attention_mask=True))
        generated = self.model.generate.call_args.kwargs
        self.assertEqual(set(generated), {"input_features", "max_new_tokens", "do_sample", "num_beams"})
        self.assertEqual((generated["max_new_tokens"], generated["do_sample"], generated["num_beams"]), (64, False, 1))
        self.assertEqual(generated["input_features"].device.type, "cpu")
        self.assertTrue(self.processor.batch_decode.call_args.kwargs["skip_special_tokens"])
        self.assertEqual(self.settings, settings_before)
        cfg = self.settings["content_check"]
        self.assertEqual(self.loader.call_args.args, (cfg["model_id"], cfg["revision"],
                         str(speech.config_path(cfg["cache_dir"], self.settings)), True, 2))

    def test_preset_wrapper_fields_and_outcomes(self):
        prompt = dict(text="I think so", content_alternatives={"think": ["sink"]})
        for text, state in [("I think so.", "match"), ("I sink so", "target_variant"), ("Something else", "mismatch")]:
            with self.subTest(text=text):
                self.processor.batch_decode.return_value = [text]
                result = speech.check_content(self.path, prompt, self.settings)
                expected = speech.compare_transcript(text, prompt)
                expected.update(model_id=self.settings["content_check"]["model_id"],
                                model_revision=self.settings["content_check"]["revision"],
                                audio_sha256=prepare_audio(self.path, self.settings)[2], limitation=speech.LIMITATION)
                self.assertEqual(result, expected)
                self.assertEqual(result["status"], state)

    def test_disabled_and_empty_are_not_success(self):
        disabled = deepcopy(self.settings)
        disabled["content_check"]["enabled"] = False
        self.assertEqual(speech.check_content(self.path, {}, disabled),
                         dict(status="unavailable", reason="Independent sentence check is disabled."))
        self.loader.assert_not_called()
        for text in ["", "  "]:
            self.processor.batch_decode.return_value = [text]
            r = speech.transcribe_audio(self.path, self.settings)
            self.assertEqual(r["status"], "failed")
            self.assertIsNone(r["recognized_text"])
            self.assertEqual(r["error"]["code"], "TRANSCRIPTION_EMPTY")
            self.assertEqual(speech.check_content(self.path, {"text": "I think so"}, self.settings)["status"], "unavailable")

    def test_model_and_inference_failure(self):
        self.loader.side_effect = RuntimeError("model unavailable")
        r = speech.transcribe_audio(self.path, self.settings)
        self.assertEqual(r["error"]["code"], "MODEL_UNAVAILABLE")
        self.assertIsNone(r["recognized_text"])
        self.assertIsNotNone(r["audio_sha256"])
        self.loader.side_effect = None
        self.model.generate.side_effect = RuntimeError("inference failed")
        r = speech.transcribe_audio(self.path, self.settings)
        self.assertEqual(r["error"]["code"], "TRANSCRIPTION_FAILED")
        self.assertIsNone(r["recognized_text"])

    def assert_invalid(self, path, reason=None, settings=None):
        self.loader.reset_mock()
        r = speech.transcribe_audio(path, settings or self.settings)
        self.assertEqual(r["status"], "failed")
        self.assertEqual(r["error"]["code"], "INVALID_AUDIO")
        self.assertIsNone(r["recognized_text"])
        if reason:
            self.assertEqual(r["reason"], reason)
        self.loader.assert_not_called()

    def test_duration_rejected_even_when_settings_allow_longer(self):
        sf.write(self.path, np.tile(self.samples, 6), 16000)
        cfg = deepcopy(self.settings)
        cfg["max_duration_sec"] = 30
        self.assert_invalid(self.path, "audio_too_long", cfg)
        self.assertEqual(audio_io.prepare_audio(self.path, cfg)["reason"], "audio_too_long")

    def test_exact_five_seconds_is_accepted(self):
        sf.write(self.path, np.tile(self.samples, 5), 16000)
        self.assertEqual(speech.transcribe_audio(self.path, self.settings)["status"], "completed")

    def test_file_size_boundaries_before_decoding(self):
        with self.path.open("ab") as f:
            f.truncate(audio_io.MAX_AUDIO_BYTES)
        self.assertEqual(audio_io.inspect_audio_file(self.path)["status"], "ok")
        with self.path.open("ab") as f:
            f.write(b"x")
        self.assert_invalid(self.path, "file_too_large")
        self.assertEqual(audio_io.prepare_audio(self.path)["reason"], "file_too_large")

    def test_missing_malformed_empty_and_silent_audio(self):
        self.assert_invalid(self.path.with_name("missing.wav"), "cannot_read_audio")
        self.path.write_bytes(b"not audio")
        self.assert_invalid(self.path, "cannot_read_audio")
        sf.write(self.path, np.zeros(0), 16000)
        self.assert_invalid(self.path, "empty_audio")
        sf.write(self.path, np.zeros(16000), 16000)
        self.assert_invalid(self.path)

    def test_changed_audio_rejected_and_array_identity_is_not_file_hash(self):
        with patch.object(speech, "prepare_audio", wraps=prepare_audio) as prep:
            def change(*args):
                out = prepare_audio(*args)
                self.path.write_bytes(self.path.read_bytes() + b"change")
                return out
            prep.side_effect = change
            self.assert_invalid(self.path, "audio_changed")
        r = speech.transcribe_audio((self.samples, 16000), self.settings)
        self.assertEqual(r["status"], "completed")
        self.assertIsNone(r["source_audio_sha256"])
        self.assertIsNotNone(r["audio_sha256"])


class ModelCacheTests(unittest.TestCase):
    def test_loader_cache_keys_and_cpu_configuration(self):
        speech._load_asr.cache_clear()
        self.addCleanup(speech._load_asr.cache_clear)
        with patch("transformers.WhisperProcessor.from_pretrained") as processor, \
             patch("transformers.WhisperForConditionalGeneration.from_pretrained") as model, \
             patch("torch.set_num_threads") as threads:
            first = speech._load_asr("model", "revision", "cache", True, 2)
            self.assertIs(first, speech._load_asr("model", "revision", "cache", True, 2))
            processor.assert_called_once_with("model", revision="revision", cache_dir="cache", local_files_only=True, trust_remote_code=False)
            model.return_value.to.assert_called_once_with("cpu")
            model.return_value.to.return_value.eval.assert_called_once_with()
            threads.assert_called_once_with(2)
            speech._load_asr("model", "new-revision", "cache", True, 2)
            self.assertEqual(processor.call_count, 2)
            self.assertEqual(speech._load_asr.cache_info().maxsize, 1)


if __name__ == "__main__":
    unittest.main()
