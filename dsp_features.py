"""Measure pitch and exploratory formants with Praat/Parselmouth on CPU.

extract_features(audio, settings=None) returns only JSON-compatible values.
Every feature array uses time_sec. Unvoiced/unreliable values are None (JSON
null). Formant flags are signal-quality checks, NOT vowel correctness labels.
No cross-speaker vowel normalization or pronunciation classification is done.
"""

import numpy as np
import parselmouth
from scipy.ndimage import gaussian_filter1d

from audio_io import _validated_samples


def extract_features(audio, settings=None):
    """Extract pitch from a Gaussian-filtered analysis copy and Burg formants.

    Optional flat settings: time_step_sec=.01, pitch_floor_hz=50,
    pitch_ceiling_hz=500, formant_ceiling_hz=5000,
    formant_window_sec=.025, max_formant_bandwidth_hz=700,
    silence_rms_threshold=1e-5. These are starting parameters, not universal
    physiological thresholds; adjust with actual recordings.
    """
    settings = settings or {}
    result = {"status": "unavailable", "reason": None, "warnings": [],
              "time_sec": [], "pitch_hz": [], "voiced_mask": [],
              "pitch_semitones": [], "pitch_median_hz": None,
              "voiced_fraction": 0.0, "pitch_strength": [],
              "pitch_invalid_reason": [], "pitch_rejected_frames": 0,
              "formants_hz": {"f1": [], "f2": [], "f3": []},
              "formant_valid_mask": [], "formant_invalid_reason": [],
              "normalization_status": "not_speaker_normalized"}
    try:
        samples, rate = _validated_samples(audio)
    except (TypeError, ValueError) as exc:
        result.update(reason="invalid_audio", error=str(exc))
        return result
    step = float(settings.get("time_step_sec", .01))
    floor = float(settings.get("pitch_floor_hz", 50))
    ceiling = float(settings.get("pitch_ceiling_hz", 500))
    formant_ceiling = float(settings.get("formant_ceiling_hz", 5000))
    window = float(settings.get("formant_window_sec", .025))
    bandwidth_limit = float(settings.get("max_formant_bandwidth_hz", 700))
    silence = float(settings.get("silence_rms_threshold", 1e-5))
    filter_top = float(settings.get("pitch_filter_top_hz", 800))
    attenuation = float(settings.get("pitch_filter_attenuation", .03))
    strength_min = float(settings.get("pitch_min_strength", .6))
    jump_max = float(settings.get("pitch_max_jump_semitones", 12))
    min_run = settings.get("pitch_min_run_frames", 3)
    relative_db = float(settings.get("pitch_relative_energy_db", -20))
    parameters = [step, floor, ceiling, formant_ceiling, window, bandwidth_limit]
    if not all(np.isfinite(x) and x > 0 for x in parameters):
        raise ValueError("DSP parameters must be positive and finite.")
    if not floor < ceiling < rate / 2 or formant_ceiling >= rate / 2:
        raise ValueError("Pitch bounds/formant ceiling must be below Nyquist.")
    if not np.isfinite(silence) or silence < 0:
        raise ValueError("silence_rms_threshold must be finite and nonnegative.")
    if not (np.isfinite(filter_top) and 0 < filter_top < rate / 2
            and np.isfinite(attenuation) and 0 < attenuation < 1
            and np.isfinite(strength_min) and 0 < strength_min <= 1
            and np.isfinite(jump_max) and jump_max > 0
            and isinstance(min_run, int) and not isinstance(min_run, bool) and min_run >= 1
            and np.isfinite(relative_db) and -80 <= relative_db < 0):
        raise ValueError("Invalid pitch quality parameters.")
    if np.sqrt(np.mean(samples ** 2)) <= silence:
        result["reason"] = "silent_audio"
        return result
    if len(samples) / rate < max(3 / floor, 2 * window):
        result["reason"] = "audio_too_short_for_analysis"
        return result
    sound = parselmouth.Sound(samples, sampling_frequency=rate)
    # Gaussian low-pass response: attenuation ** ((frequency / filter_top) ** 2).
    # This symmetric filter changes only the pitch-analysis copy. Saved audio,
    # MFA/model inputs, original sample times, and formant input stay untouched.
    sigma = rate * np.sqrt(-2 * np.log(attenuation)) / (2 * np.pi * filter_top)
    pitch_sound = parselmouth.Sound(
        gaussian_filter1d(samples, sigma, mode="reflect"), sampling_frequency=rate)
    try:
        pitch = pitch_sound.to_pitch_ac(time_step=step, pitch_floor=floor,
                                        pitch_ceiling=ceiling, voicing_threshold=.5,
                                        octave_cost=.055)
    except parselmouth.PraatError as exc:
        result.update(reason="pitch_extraction_failed", error=str(exc))
        return result
    times = pitch.xs()
    frequencies = pitch.selected_array["frequency"]
    strengths = pitch.selected_array["strength"]
    voiced = np.isfinite(frequencies) & (frequencies > 0)
    candidates = voiced.copy()
    reasons = [None if v else "unvoiced" for v in voiced]
    # Reject low-energy windows even if a tracker assigns a candidate pitch.
    half_window = max(1, round(1.5 * rate / floor))
    frame_rms = []
    for time in times:
        center = round(time * rate)
        frame = samples[max(0, center-half_window):min(len(samples), center+half_window)]
        frame_rms.append(float(np.sqrt(np.mean(frame ** 2))) if len(frame) else 0.)
    frame_rms = np.asarray(frame_rms)
    quiet, active = np.percentile(frame_rms, [10, 90])
    # Treat the quiet decile as background only when the clip has a distinct
    # louder region. Otherwise a steady soft voice must remain analyzable.
    background_floor = 2 * quiet if active >= 3 * max(quiet, silence) else 0.
    energy_floor = max(silence, active * 10 ** (relative_db / 20), background_floor)
    for i, time in enumerate(times):
        if not voiced[i]:
            continue
        if frame_rms[i] <= silence:
            reasons[i] = "low_energy"
        elif frame_rms[i] <= energy_floor:
            reasons[i] = "background_level_energy"
        elif not np.isfinite(strengths[i]) or strengths[i] < strength_min:
            reasons[i] = "weak_periodicity"
        elif frequencies[i] <= floor * 1.01 or frequencies[i] >= ceiling * .99:
            reasons[i] = "near_pitch_boundary"
        if reasons[i] is not None:
            voiced[i] = False
    # A very large change between adjacent 10 ms frames has ambiguous tracking.
    # Mask both sides rather than guessing which octave belongs to the speaker.
    for i in range(1, len(times)):
        if voiced[i-1] and voiced[i] and abs(12 * np.log2(frequencies[i] / frequencies[i-1])) > jump_max:
            reasons[i-1] = reasons[i] = "abrupt_pitch_change"
    voiced &= np.array([reason is None for reason in reasons])
    starts = np.flatnonzero(voiced & ~np.r_[False, voiced[:-1]])
    ends = np.flatnonzero(voiced & ~np.r_[voiced[1:], False]) + 1
    for start, end in zip(starts, ends):
        if end - start < min_run:
            voiced[start:end] = False
            reasons[start:end] = ["short_voiced_run"] * (end-start)
    rejected = int(np.sum(candidates & ~voiced))
    median = float(np.median(frequencies[voiced])) if voiced.any() else None
    result.update(time_sec=times.tolist(), voiced_mask=voiced.tolist(),
                  pitch_hz=[float(f) if v else None for f, v in zip(frequencies, voiced)],
                  pitch_semitones=[float(12*np.log2(f/median)) if v else None
                                   for f, v in zip(frequencies, voiced)],
                  pitch_median_hz=median, voiced_fraction=float(np.mean(voiced)),
                  pitch_strength=[float(s) if np.isfinite(s) else None for s in strengths],
                  pitch_invalid_reason=reasons, pitch_rejected_frames=rejected,
                  pitch_frame_rms=frame_rms.tolist(),
                  status="ok", parameters={"time_step_sec": step,
                  "pitch_method": "gaussian_filtered_autocorrelation",
                  "pitch_filter_top_hz": filter_top,
                  "pitch_filter_attenuation": attenuation,
                  "pitch_min_strength": strength_min,
                  "pitch_max_jump_semitones": jump_max,
                  "pitch_min_run_frames": min_run,
                  "pitch_relative_energy_db": relative_db,
                  "pitch_effective_energy_floor": float(energy_floor),
                  "pitch_background_rms_estimate": float(quiet),
                  "pitch_floor_hz": floor, "pitch_ceiling_hz": ceiling,
                  "formant_ceiling_hz": formant_ceiling,
                  "formant_window_sec": window,
                  "max_formant_bandwidth_hz": bandwidth_limit})
    if rejected:
        result["warnings"].append("unreliable_pitch_frames_omitted")
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
