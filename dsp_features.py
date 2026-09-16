"""Measure pitch and exploratory formants with Praat/Parselmouth on CPU.

extract_features(audio, settings=None) returns only JSON-compatible values.
Every feature array uses time_sec. Unvoiced/unreliable values are None (JSON
null). Formant flags are signal-quality checks, NOT vowel correctness labels.
No cross-speaker vowel normalization or pronunciation classification is done.
"""

import numpy as np
import parselmouth

from audio_io import _validated_samples


def extract_features(audio, settings=None):
    """Extract raw-autocorrelation pitch and Burg formants on the pitch grid.

    Optional flat settings: time_step_sec=.01, pitch_floor_hz=75,
    pitch_ceiling_hz=500, formant_ceiling_hz=5000,
    formant_window_sec=.025, max_formant_bandwidth_hz=700,
    silence_rms_threshold=1e-5. These are starting parameters, not universal
    physiological thresholds; adjust with actual recordings.
    """
    settings = settings or {}
    result = {"status": "unavailable", "reason": None, "warnings": [],
              "time_sec": [], "pitch_hz": [], "voiced_mask": [],
              "pitch_semitones": [], "pitch_median_hz": None,
              "voiced_fraction": 0.0,
              "formants_hz": {"f1": [], "f2": [], "f3": []},
              "formant_valid_mask": [], "formant_invalid_reason": [],
              "normalization_status": "not_speaker_normalized"}
    try:
        samples, rate = _validated_samples(audio)
    except (TypeError, ValueError) as exc:
        result.update(reason="invalid_audio", error=str(exc))
        return result
    step = float(settings.get("time_step_sec", .01))
    floor = float(settings.get("pitch_floor_hz", 75))
    ceiling = float(settings.get("pitch_ceiling_hz", 500))
    formant_ceiling = float(settings.get("formant_ceiling_hz", 5000))
    window = float(settings.get("formant_window_sec", .025))
    bandwidth_limit = float(settings.get("max_formant_bandwidth_hz", 700))
    silence = float(settings.get("silence_rms_threshold", 1e-5))
    parameters = [step, floor, ceiling, formant_ceiling, window, bandwidth_limit]
    if not all(np.isfinite(x) and x > 0 for x in parameters):
        raise ValueError("DSP parameters must be positive and finite.")
    if not floor < ceiling < rate / 2 or formant_ceiling >= rate / 2:
        raise ValueError("Pitch bounds/formant ceiling must be below Nyquist.")
    if not np.isfinite(silence) or silence < 0:
        raise ValueError("silence_rms_threshold must be finite and nonnegative.")
    if np.sqrt(np.mean(samples ** 2)) <= silence:
        result["reason"] = "silent_audio"
        return result
    if len(samples) / rate < max(3 / floor, 2 * window):
        result["reason"] = "audio_too_short_for_analysis"
        return result
    sound = parselmouth.Sound(samples, sampling_frequency=rate)
    try:
        pitch = sound.to_pitch_ac(time_step=step, pitch_floor=floor,
                                  pitch_ceiling=ceiling)
    except parselmouth.PraatError as exc:
        result.update(reason="pitch_extraction_failed", error=str(exc))
        return result
    times = pitch.xs()
    frequencies = pitch.selected_array["frequency"]
    voiced = np.isfinite(frequencies) & (frequencies > 0)
    # Reject low-energy windows even if a tracker assigns a candidate pitch.
    half_window = max(1, round(1.5 * rate / floor))
    for i, time in enumerate(times):
        center = round(time * rate)
        frame = samples[max(0, center-half_window):min(len(samples), center+half_window)]
        if not len(frame) or np.sqrt(np.mean(frame ** 2)) <= silence:
            voiced[i] = False
    median = float(np.median(frequencies[voiced])) if voiced.any() else None
    result.update(time_sec=times.tolist(), voiced_mask=voiced.tolist(),
                  pitch_hz=[float(f) if v else None for f, v in zip(frequencies, voiced)],
                  pitch_semitones=[float(12*np.log2(f/median)) if v else None
                                   for f, v in zip(frequencies, voiced)],
                  pitch_median_hz=median, voiced_fraction=float(np.mean(voiced)),
                  status="ok", parameters={"time_step_sec": step,
                  "pitch_floor_hz": floor, "pitch_ceiling_hz": ceiling,
                  "formant_ceiling_hz": formant_ceiling,
                  "formant_window_sec": window,
                  "max_formant_bandwidth_hz": bandwidth_limit})
    if not voiced.any():
        result["warnings"].append("no_reliable_voiced_frames")
    try:
        formants = sound.to_formant_burg(time_step=step, maximum_formant=formant_ceiling,
                                         max_number_of_formants=5, window_length=window)
    except parselmouth.PraatError:
        formants = None
        result["warnings"].append("formant_extraction_failed")
    for time, is_voiced in zip(times, voiced):
        reason = "unvoiced" if not is_voiced else None
        values = None
        if reason is None and formants is None:
            reason = "extraction_failed"
        if reason is None:
            values = [formants.get_value_at_time(n, float(time)) for n in (1, 2, 3)]
            bandwidths = [formants.get_bandwidth_at_time(n, float(time)) for n in (1, 2, 3)]
            if not all(np.isfinite(v) for v in values + bandwidths):
                reason = "missing_estimate"
            elif not 0 < values[0] < values[1] < values[2] < formant_ceiling:
                reason = "unordered_or_out_of_range"
            elif not all(0 < b <= bandwidth_limit for b in bandwidths):
                reason = "broad_or_invalid_bandwidth"
        valid = reason is None
        for j, key in enumerate(("f1", "f2", "f3")):
            result["formants_hz"][key].append(float(values[j]) if valid else None)
        result["formant_valid_mask"].append(valid)
        result["formant_invalid_reason"].append(reason)
    if not any(result["formant_valid_mask"]):
        result["warnings"].append("no_reliable_formant_frames")
    if result["warnings"]:
        result["status"] = "warning"
    return result
