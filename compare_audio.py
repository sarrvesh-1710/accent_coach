"""Compare same-prompt recordings on CPU, without assigning correctness scores.

The caller must select matching text. If both audio dictionaries include
prompt_id, mismatches are rejected. Text identity cannot be inferred from WAVs.
"""

import librosa
import numpy as np

from audio_io import _validated_samples


def _pitch_near(dsp, targets):
    """Nearest voiced observation within half a DSP hop; never bridge gaps."""
    if dsp.get("status") not in {"ok", "warning"}:
        return [None] * len(targets)
    times = np.asarray(dsp.get("time_sec", []), dtype=float)
    values = dsp.get("pitch_semitones", [])
    voiced = dsp.get("voiced_mask", [])
    if not len(times):
        return [None] * len(targets)
    if len(values) != len(times) or len(voiced) != len(times):
        raise ValueError("DSP arrays must share time_sec.")
    if not np.isfinite(times).all() or np.any(np.diff(times) <= 0):
        raise ValueError("DSP timestamps must be finite and strictly increasing.")
    tolerance = float(dsp.get("parameters", {}).get("time_step_sec", .01)) / 2 + 1e-8
    if not np.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("DSP time step must be positive and finite.")
    result = []
    for target in targets:
        right = int(np.searchsorted(times, target))
        candidates = [i for i in (right-1, right) if 0 <= i < len(times)]
        nearest = min(candidates, key=lambda i: abs(times[i]-target))
        value = values[nearest]
        valid = (abs(times[nearest]-target) <= tolerance and voiced[nearest]
                 and value is not None and np.isfinite(value))
        result.append(float(value) if valid else None)
    return result


def compare_audio(learner_audio, reference_audio, learner_dsp, reference_dsp, settings=None):
    """Return duration ratio, mean path MFCC distance and paired pitch contours.

    DTW distance = accumulated Euclidean MFCC cost / warping-path length.
    Values depend on recording conditions and MFCC settings, and are not
    pronunciation scores. Settings: mfcc_n_fft=512, mfcc_hop_length=160,
    mfcc_n_mfcc=13, dtw_band_rad=.25, max_duration_sec=5.
    """
    settings = settings or {}
    result = {"status": "unavailable", "reason": None, "warnings": [],
              "duration_ratio": None, "dtw_distance": None,
              "distance_units": "mean_euclidean_mfcc_cost_per_path_step",
              "warping_path": [], "pitch_comparison": {
                  "learner_time_sec": [], "reference_time_sec": [],
                  "learner_semitones": [], "reference_semitones": [],
                  "delta_semitones": []}}
    a_id, b_id = learner_audio.get("prompt_id"), reference_audio.get("prompt_id")
    if a_id is not None and b_id is not None and a_id != b_id:
        result["reason"] = "prompt_mismatch"
        return result
    if a_id is None or b_id is None:
        result["warnings"].append("caller_must_verify_matching_text")
    try:
        a, rate = _validated_samples(learner_audio)
        b, _ = _validated_samples(reference_audio)
    except (ValueError, TypeError) as exc:
        result.update(reason="invalid_audio", error=str(exc))
        return result
    limit = float(settings.get("max_duration_sec", 5))
    if not np.isfinite(limit) or limit <= 0:
        raise ValueError("max_duration_sec must be positive and finite.")
    if max(len(a), len(b)) > round(limit * rate):
        result["reason"] = "audio_too_long"
        return result
    if min(np.sqrt(np.mean(a*a)), np.sqrt(np.mean(b*b))) <= 1e-5:
        result["reason"] = "silent_audio"
        return result
    n_fft = int(settings.get("mfcc_n_fft", 512))
    hop = int(settings.get("mfcc_hop_length", 160))
    n_mfcc = int(settings.get("mfcc_n_mfcc", 13))
    band = float(settings.get("dtw_band_rad", .25))
    if n_fft < 32 or not 1 <= hop <= n_fft or not 1 <= n_mfcc <= 40:
        raise ValueError("Invalid MFCC FFT, hop or coefficient count.")
    if not np.isfinite(band) or not 0 < band <= 1:
        raise ValueError("dtw_band_rad must be in (0, 1].")
    if min(len(a), len(b)) < n_fft:
        result["reason"] = "audio_too_short_for_comparison"
        return result
    frames_a = 1 + (len(a) - n_fft) // hop
    frames_b = 1 + (len(b) - n_fft) // hop
    if frames_a * frames_b > 1_000_000:
        result["reason"] = "dtw_matrix_too_large"
        return result

    def mfcc(samples):
        return librosa.feature.mfcc(y=samples, sr=rate, n_mfcc=n_mfcc,
                                    n_fft=n_fft, hop_length=hop, n_mels=40, center=False)
    try:
        costs, backward_path = librosa.sequence.dtw(
            X=mfcc(a), Y=mfcc(b), metric="euclidean", global_constraints=True, band_rad=band)
    except librosa.util.exceptions.ParameterError as exc:
        result.update(reason="dtw_failed", error=str(exc))
        return result
    path = backward_path[::-1]
    distance = float(costs[-1, -1] / len(path))
    if not np.isfinite(distance):
        result["reason"] = "no_finite_alignment"
        return result
    # center=False means timestamps refer to each window's center, not its start.
    time_a = (path[:, 0] * hop + n_fft / 2) / rate
    time_b = (path[:, 1] * hop + n_fft / 2) / rate
    result.update(duration_ratio=float(len(a)/len(b)), dtw_distance=distance,
                  warping_path=path.tolist(), status="ok",
                  mfcc_settings={"n_fft": n_fft, "hop_length": hop, "n_mfcc": n_mfcc,
                                 "n_mels": 40, "center": False, "band_rad": band})
    try:
        pitch_a = _pitch_near(learner_dsp, time_a)
        pitch_b = _pitch_near(reference_dsp, time_b)
    except (ValueError, TypeError) as exc:
        pitch_a, pitch_b = [None]*len(path), [None]*len(path)
        result["warnings"].append("invalid_pitch_features")
        result["pitch_error"] = str(exc)
    delta = [float(x-y) if x is not None and y is not None else None
             for x, y in zip(pitch_a, pitch_b)]
    result["pitch_comparison"] = {
        "learner_time_sec": time_a.tolist(), "reference_time_sec": time_b.tolist(),
        "learner_semitones": pitch_a, "reference_semitones": pitch_b,
        "delta_semitones": delta}
    if all(v is None for v in delta):
        result["warnings"].append("no_paired_voiced_pitch")
    if result["warnings"]:
        result["status"] = "warning"
    return result


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path
    from audio_io import prepare_audio
    from dsp_features import extract_features

    parser = argparse.ArgumentParser(description="Compare two WAVs of the same spoken text (up to 5 seconds each).")
    parser.add_argument("learner")
    parser.add_argument("reference")
    parser.add_argument("--output", help="Optional JSON output path")
    args = parser.parse_args()
    learner = prepare_audio(args.learner)
    reference = prepare_audio(args.reference)
    learner_dsp = extract_features(learner)
    reference_dsp = extract_features(reference)
    comparison = compare_audio(learner, reference, learner_dsp, reference_dsp)
    report = {"learner_audio": {k: v for k, v in learner.items() if k != "samples"},
              "reference_audio": {k: v for k, v in reference.items() if k != "samples"},
              "learner_dsp": learner_dsp, "reference_dsp": reference_dsp,
              "comparison": comparison}
    payload = json.dumps(report, indent=2, allow_nan=False)
    if args.output:
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(payload + "\n", encoding="utf-8")
        print(f"{comparison['status']}: {destination}")
    else:
        print(payload)
    raise SystemExit(1 if comparison["status"] == "unavailable" else 0)

