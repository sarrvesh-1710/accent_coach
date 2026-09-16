"""Load short WAVs without trimming or moving their annotation timestamps.

Public API: prepare_audio(path, settings=None) -> dict.
The samples array stays in memory. All other metadata is JSON-compatible.
Settings are optional: sample_rate_hz (16000), max_duration_sec (5),
silence_rms_threshold (1e-5), saturation_level (0.999).
"""

from pathlib import Path

import librosa
import numpy as np
import soundfile as sf


def prepare_audio(path, settings=None):
    """Return status 'ok', 'warning' or 'unavailable', never fabricated audio.

    Saturation is checked before mixing/resampling, which can hide clipped
    peaks. A warning is evidence of saturation, not a definitive clipping test.
    File/format failures return a reason; invalid configuration raises ValueError.
    """
    settings = settings or {}
    rate = int(settings.get("sample_rate_hz", 16000))
    limit = float(settings.get("max_duration_sec", 5.0))
    silence = float(settings.get("silence_rms_threshold", 1e-5))
    saturation = float(settings.get("saturation_level", 0.999))
    if rate != 16000:
        raise ValueError("This prototype requires sample_rate_hz = 16000.")
    if not np.isfinite(limit) or limit <= 0:
        raise ValueError("max_duration_sec must be positive and finite.")
    if not np.isfinite(silence) or silence < 0:
        raise ValueError("silence_rms_threshold must be nonnegative and finite.")
    if not np.isfinite(saturation) or not 0 < saturation <= 1:
        raise ValueError("saturation_level must be in (0, 1].")
    result = {
        "status": "unavailable", "reason": None, "warnings": [],
        "path": str(path), "samples": None, "sample_rate_hz": rate,
        "duration_sec": None, "original_sample_rate_hz": None,
        "original_channels": None, "original_duration_sec": None,
        "trim_offset_sec": 0.0,
    }
    try:
        # Check metadata before allocating memory for potentially long input.
        with sf.SoundFile(Path(path)) as source:
            if source.format not in {"WAV", "WAVEX", "RF64"}:
                result["reason"] = "unsupported_format"
                return result
            duration = source.frames / source.samplerate
            result.update(original_sample_rate_hz=source.samplerate,
                          original_channels=source.channels,
                          original_duration_sec=duration)
            if source.frames == 0:
                result["reason"] = "empty_audio"
                return result
            if duration > limit:
                result["reason"] = "audio_too_long"
                return result
            raw = source.read(dtype="float64", always_2d=True)
    except (OSError, RuntimeError, ValueError) as exc:
        result.update(reason="cannot_read_audio", error=str(exc))
        return result

    if not np.isfinite(raw).all():
        result["reason"] = "nonfinite_samples"
        return result
    result["original_peak"] = float(np.max(np.abs(raw)))
    result["saturated_sample_fraction"] = float(np.mean(np.abs(raw) >= saturation))
    if result["saturated_sample_fraction"] > 0:
        result["warnings"].append("possible_clipping")
    mono = raw.mean(axis=1)
    if raw.shape[1] > 1:
        result["warnings"].append("mixed_to_mono")
    if result["original_sample_rate_hz"] != rate:
        mono = librosa.resample(mono, orig_sr=result["original_sample_rate_hz"],
                                target_sr=rate, res_type="soxr_hq")
    # Duration may differ by at most one output sample due to resampling rounding.
    rms = float(np.sqrt(np.mean(mono ** 2)))
    result.update(duration_sec=len(mono) / rate, rms=rms)
    if rms <= silence:
        result["reason"] = "silent_audio"
        return result
    samples = mono.astype(np.float32)
    if not np.isfinite(samples).all():
        result["reason"] = "nonfinite_samples"
        return result
    result.update(samples=samples, reason=None,
                  status="warning" if result["warnings"] else "ok")
    return result


def _validated_samples(audio):
    """Shared validation for dictionaries passed to the DSP/comparison modules."""
    if audio.get("status") not in {"ok", "warning"}:
        raise ValueError("Audio preparation was not successful.")
    samples = np.asarray(audio.get("samples"), dtype=np.float64)
    rate = audio.get("sample_rate_hz")
    if rate != 16000 or samples.ndim != 1 or not len(samples):
        raise ValueError("Expected a nonempty mono array at 16000 Hz.")
    if not np.isfinite(samples).all():
        raise ValueError("Samples must be finite.")
    return samples, rate
