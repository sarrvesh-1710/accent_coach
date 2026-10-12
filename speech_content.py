"""Independent local transcription, never a pronunciation correctness score."""
from functools import lru_cache
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


def check_content(audio, prompt, settings):
    cfg = settings.get("content_check", {})
    if not cfg.get("enabled", False):
        return dict(status="unavailable", reason="Independent sentence check is disabled.")
    try:
        x, sr, fingerprint = prepare_audio(audio, settings)
        cache = str(config_path(cfg["cache_dir"], settings)) if cfg.get("cache_dir") else None
        processor, model = _load_asr(cfg["model_id"], cfg["revision"], cache,
                                     cfg.get("local_files_only", True), cfg.get("cpu_threads", 2))
        import torch
        batch = processor(x, sampling_rate=sr, return_tensors="pt", return_attention_mask=True)
        # No sentence prompt/forced word IDs: transcription must be independent.
        with torch.inference_mode():
            generated = model.generate(**{k: v.to("cpu") for k, v in batch.items()},
                                       max_new_tokens=64, do_sample=False, num_beams=1)
        transcript = processor.batch_decode(generated, skip_special_tokens=True)[0]
        result = compare_transcript(transcript, prompt)
        result.update(model_id=cfg["model_id"], model_revision=cfg["revision"], audio_sha256=fingerprint,
                      limitation="ASR may misrecognize or hallucinate words; a match is not proof of correct pronunciation.")
        return result
    except Exception as exc:
        return dict(status="unavailable", reason=f"{type(exc).__name__}: {exc}")
