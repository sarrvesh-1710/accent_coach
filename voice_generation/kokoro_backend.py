"""Local Kokoro CPU backend with cached model/voice and explicit timing."""
import json
import os
import importlib.util
from pathlib import Path
import time
import uuid

from .generator import DEFAULT_OUTPUT, TARGET_ACCENT, _failure

MODEL_ROOT = Path(__file__).resolve().parents[1] / "models" / "kokoro"


class KokoroGenerator:
    def __init__(self):
        started = time.perf_counter()
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        if importlib.util.find_spec("en_core_web_sm") is None:
            raise RuntimeError("Run the explicit spaCy model setup before generating audio")
        import numpy as np
        import soundfile as sf
        import torch
        from kokoro import KModel, KPipeline
        self.np, self.sf, self.torch = np, sf, torch
        self.manifest = json.loads((MODEL_ROOT / "manifest.json").read_text(encoding="utf-8"))
        torch.set_num_threads(4)
        model = KModel(repo_id=self.manifest["repo_id"], config=str(MODEL_ROOT / "config.json"),
                       model=str(MODEL_ROOT / "kokoro-v1_0.pth")).to("cpu").eval()
        self.pipeline = KPipeline(lang_code="a", repo_id=self.manifest["repo_id"], model=model)
        self.voice = torch.load(MODEL_ROOT / "voices/af_heart.pt", map_location="cpu", weights_only=True)
        self.load_ms = (time.perf_counter() - started) * 1000
        self.calls = 0

    def generate_audio(self, text, target_accent=TARGET_ACCENT, *, output_dir=None):
        if target_accent != TARGET_ACCENT:
            return _failure("UNSUPPORTED_ACCENT", "Only American English examples are available.")
        if not isinstance(text, str) or not text.strip() or len(text) > 1000:
            return _failure("UNSUPPORTED_TEXT", "Supply between 1 and 1,000 characters of confirmed text.")
        root = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT.parent / "kokoro_examples"
        root.mkdir(parents=True, exist_ok=True)
        audio_id = "synthetic-" + uuid.uuid4().hex
        path = root / (audio_id + ".wav")
        sidecar = root / (audio_id + ".json")
        cold = self.calls == 0
        started = time.perf_counter()
        try:
            chunks, spoken_chunks, phones = [], [], []
            with self.torch.inference_mode():
                for graphemes, phonemes, audio in self.pipeline(text, voice=self.voice, speed=1):
                    if audio is None:
                        raise ValueError("No waveform returned")
                    chunks.append(audio.cpu().numpy())
                    spoken_chunks.append(graphemes)
                    phones.append(phonemes)
            if not chunks:
                raise ValueError("No speech chunks")
            waveform = self.np.concatenate(chunks)
            if not self.np.isfinite(waveform).all() or not self.np.any(waveform):
                raise ValueError("Invalid waveform")
            synthesis_ms = (time.perf_counter() - started) * 1000
            self.sf.write(path, waveform, 24000, subtype="PCM_16")
            info = self.sf.info(path)
            request_ms = (time.perf_counter() - started) * 1000
            self.calls += 1
            result = {"ok": True, "status": "completed", "generated_audio_id": audio_id,
                      "type": "synthetic_example", "label": "Synthetic example", "text": text,
                      "target_accent": target_accent, "backend": "kokoro", "voice": "af_heart",
                      "model_revision": self.manifest["revision"], "device": "cpu", "torch_threads": 4,
                      "sample_rate_hz": info.samplerate, "duration_seconds": info.duration,
                      "condition": "cold" if cold else "warm",
                      "timings_ms": {"model_load": round(self.load_ms if cold else 0, 2),
                                     "synthesis": round(synthesis_ms, 2),
                                     "request": round(request_ms, 2),
                                     "total": round(request_ms + (self.load_ms if cold else 0), 2)},
                      "real_time_factor": round((request_ms / 1000) / info.duration, 4),
                      "synthesized_chunks": spoken_chunks, "phonemes": phones,
                      "review": {"words_match": None, "naturalness_1_to_5": None,
                                 "pronunciation_notes": "Listening review pending."},
                      "limitations": ["Synthetic American English voice; suitability needs listening review.",
                                       "Does not preserve the learner's voice.",
                                       "Never use generated audio as learner assessment input."], "error": None}
            sidecar.write_text(json.dumps(result, indent=2), encoding="utf-8")
            return result
        except (OSError, ValueError, RuntimeError):
            path.unlink(missing_ok=True)
            sidecar.unlink(missing_ok=True)
            return _failure("MODEL_UNAVAILABLE", "The Kokoro example could not be generated. Please retry.", True)
