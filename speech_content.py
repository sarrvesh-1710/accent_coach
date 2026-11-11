"""Independent local transcription, never a pronunciation correctness score."""
from functools import lru_cache
import hashlib
from pathlib import Path
import re
from difflib import SequenceMatcher

from phoneme_scoring.align_audio import config_path, prepare_audio


def words(text):
    return re.findall(r"[a-z]+(?:'[a-z]+)?", text.lower())


def compare_transcript(transcript, prompt):
    expected, heard = words(prompt["text"]), words(transcript)
    if heard == expected:
        status = "match"
    elif len(heard) == len(expected) and all(
        a == b or b in prompt.get("content_alternatives", {}).get(a, [])
        for a, b in zip(expected, heard)
    ):
        status = "target_variant"
    else:
        status = "mismatch"
    differences = [dict(kind=tag, expected=expected[i:j], recognized=heard[k:l])
                   for tag, i, j, k, l in SequenceMatcher(a=expected, b=heard, autojunk=False).get_opcodes() if tag != 'equal']
    return dict(status=status, transcript=transcript.strip(), expected_text=prompt["text"], word_differences=differences,
                reason=None if status == "match" else "Recognizer text differs; this may be a speech or recognition difference.",
                is_pronunciation_grade=False, independently_transcribed=True)


@lru_cache(maxsize=1)
def _load_asr(model_id, revision, cache_dir, local_only, threads):
    import torch
    from transformers import WhisperProcessor, WhisperForConditionalGeneration
    torch.set_num_threads(threads)
    kwargs = dict(revision=revision, cache_dir=cache_dir, local_files_only=local_only, trust_remote_code=False)
    processor = WhisperProcessor.from_pretrained(model_id, **kwargs)
    model = WhisperForConditionalGeneration.from_pretrained(model_id, **kwargs).to("cpu").eval()
    return processor, model


LIMITATION = "ASR may misrecognize or hallucinate words; a match is not proof of correct pronunciation."


def transcribe_audio(audio, settings):
    """Transcribe trusted learner input without a lesson or expected sentence.

    Internal result, not a full session or authorized job endpoint. The session
    adapter must resolve ownership/asset roles and fill learner_audio_id; hashes
    are content identity, never authentication. audio_sha256 is prepared PCM16;
    source_audio_sha256 identifies original file bytes (null for array input).
    """
    cfg = settings.get("content_check", {})
    result = dict(status="failed", transcription_status="failed", recognized_text=None,
                  learner_audio_id=None, audio_sha256=None, source_audio_sha256=None,
                  model_id=cfg.get("model_id"), model_revision=cfg.get("revision"),
                  independently_transcribed=True, is_pronunciation_grade=False,
                  limitation=LIMITATION, reason=None, error=None)
    def failed(code, reason, user_message, retryable=False):
        return dict(result, reason=reason, error=dict(code=code, user_message=user_message, retryable=retryable))
    if not cfg.get("enabled", False):
        return failed("MODEL_UNAVAILABLE", "Independent sentence check is disabled.", "Transcription is disabled.")
    # Reuse the file validation boundary, not its DSP output: Whisper must still
    # receive the exact same scoring prepare_audio samples as before extraction.
    try:
        from audio_io import inspect_audio_file, MAX_AUDIO_BYTES, MAX_DURATION_SEC
        if isinstance(audio, (str, Path)):
            inspected = inspect_audio_file(audio, settings["max_duration_sec"])
            if inspected["status"] != "ok":
                return failed("INVALID_AUDIO", inspected["reason"], "Use a readable WAV within five seconds and 10 MB.")
            result["source_audio_sha256"] = hashlib.sha256(Path(audio).read_bytes()).hexdigest()
        else:
            # Retain the existing low-level (samples, rate) input convention.
            import numpy as np
            samples, rate = audio
            samples = np.asarray(samples)
            if samples.nbytes > MAX_AUDIO_BYTES or rate <= 0 or len(samples) / rate > MAX_DURATION_SEC:
                return failed("INVALID_AUDIO", "audio_limits_exceeded", "Use audio within five seconds and 10 MB.")
        x, sr, fingerprint = prepare_audio(audio, settings)
        if isinstance(audio, (str, Path)) and hashlib.sha256(Path(audio).read_bytes()).hexdigest() != result["source_audio_sha256"]:
            return failed("INVALID_AUDIO", "audio_changed", "The recording changed; submit it again.", True)
        result["audio_sha256"] = fingerprint
    except Exception as exc:
        return failed("INVALID_AUDIO", f"{type(exc).__name__}: {exc}", "The recording could not be prepared.")
    try:
        cache = str(config_path(cfg["cache_dir"], settings)) if cfg.get("cache_dir") else None
        processor, model = _load_asr(cfg["model_id"], cfg["revision"], cache,
                                     cfg.get("local_files_only", True), cfg.get("cpu_threads", 2))
    except Exception as exc:
        return failed("MODEL_UNAVAILABLE", f"{type(exc).__name__}: {exc}", "The transcription model could not be loaded.", True)
    try:
        import torch
        batch = processor(x, sampling_rate=sr, return_tensors="pt", return_attention_mask=True)
        # No sentence prompt/forced word IDs: transcription must be independent.
        with torch.inference_mode():
            generated = model.generate(**{k: v.to("cpu") for k, v in batch.items()},
                                       max_new_tokens=64, do_sample=False, num_beams=1)
        transcript = processor.batch_decode(generated, skip_special_tokens=True)[0]
        if not isinstance(transcript, str) or not transcript.strip():
            return failed("TRANSCRIPTION_EMPTY", "Recognizer returned no text.", "No words were recognized. Please record again.", True)
        return dict(result, status="completed", transcription_status="completed", recognized_text=transcript.strip())
    except Exception as exc:
        return failed("TRANSCRIPTION_FAILED", f"{type(exc).__name__}: {exc}", "Transcription could not finish. Please retry.", True)


def check_content(audio, prompt, settings):
    """Legacy preset wrapper: preserve comparison statuses and result fields."""
    transcription = transcribe_audio(audio, settings)
    if transcription["status"] != "completed":
        return dict(status="unavailable", reason=transcription["reason"])
    try:
        result = compare_transcript(transcription["recognized_text"], prompt)
        result.update({key: transcription[key] for key in
                       ("model_id", "model_revision", "audio_sha256", "limitation")})
        return result
    except Exception as exc:
        return dict(status="unavailable", reason=f"{type(exc).__name__}: {exc}")
