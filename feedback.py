"""Plain-language observations and explicitly labeled practice suggestions."""

import math


def make_feedback(result, prompt) -> list[str]:
    messages = []
    state = result.get("overall_status", "failed")
    if state == "failed":
        messages.append("Analysis unavailable. Check the stage messages and try again.")
    elif state == "partial":
        messages.append("Some evidence is limited or unavailable. This is not a pronunciation failure.")
    profile = result.get("accent_profile", {})
    if profile.get("id") == "chinese":
        messages.append("Chinese accent profile: Mandarin-speaking learner; target is General American English.")
        messages.append(profile["feedback"]["note"])
        calibrated = result.get("phoneme_results", {})
        if calibrated.get("calibration_status") == "not_trained":
            messages.append("SpeechOcean calibration has not been trained yet. Raw model evidence is available where supported; expert ratings are unavailable.")
        elif calibrated.get("calibrated"):
            messages.append("Estimated expert phone ratings use the SpeechOcean 0–2 scale. They are model estimates, not pass/fail judgments.")
            if not calibrated.get("calibration_validation", {}).get("beats_mean_baseline_mae", False):
                messages.append("This calibrator did not outperform the mean-rating baseline on development speakers. Treat its estimates as experimental.")
        elif calibrated.get("calibration_status") == "unavailable":
            messages.append("SpeechOcean calibration unavailable: " + calibrated.get("calibration_reason", "Unknown reason"))
    messages.append("Pronunciation pass/fail unavailable: decision rules have not been validated.")
    comparison = result.get("comparison", {})
    ratio = comparison.get("duration_ratio")
    if (comparison.get("status") in {"ok", "warning"}
            and isinstance(ratio, (int, float)) and math.isfinite(ratio) and ratio > 0):
        relation = "longer than" if ratio > 1 else "shorter than" if ratio < 1 else "the same duration as"
        messages.append(f"Your recording is {relation} the reference (duration ratio {ratio:.2f}). Timing alone does not establish a pronunciation error.")
    for who, key in (("Your recording", "learner_dsp"), ("The reference", "reference_dsp")):
        dsp = result.get(key, {})
        if dsp.get("status") not in {"ok", "warning"}:
            messages.append(f"{who}: acoustic measurements unavailable.")
        elif not any(dsp.get("voiced_mask", [])):
            messages.append(f"{who}: reliable voiced pitch unavailable.")
        if dsp.get("pitch_rejected_frames", 0):
            messages.append(f"{who}: {dsp['pitch_rejected_frames']} pitch estimate(s) were omitted by quality checks; gaps do not indicate pronunciation errors.")
    evidence = result.get("phoneme_results", {})
    segments = evidence.get("segments", [])
    if evidence.get("status") == "unavailable" or not segments:
        messages.append("Phoneme evidence is unavailable. Pronunciation errors could not be assessed for this attempt.")
    else:
        uncertain = sum(s.get("status") == "uncertain" for s in segments)
        diagnostic = sum(isinstance(s.get("expected_vs_alternative_nats"), (int, float)) and math.isfinite(s["expected_vs_alternative_nats"]) for s in segments)
        sparse = sum(s.get("evidence_quality") == "sparse" for s in segments)
        messages.append(f"{diagnostic} sound(s) have diagnostic model comparisons; {sparse} use a single CTC frame. {uncertain} sound(s) remain uncertain. These counts are not pronunciation grades.")
        if any(s.get("status") in {"uncertain", "unsupported"} for s in segments):
            messages.append("Some sounds are uncertain or unsupported; no error judgment is made for those segments.")
    cues = {
        "TH": "Practice cue: for th in think, let air flow continuously with the tongue tip lightly between the teeth.",
        "IH": "Practice cue: alternate ship and sheep slowly, listening for two distinct vowel sounds before repeating the prompt.",
        "AE": "Practice cue: alternate bad and bed, allowing a little more jaw opening for the vowel in bad.",
    }
    for phone in prompt.get("target_phones", []):
        if phone in cues:
            messages.append(cues[phone])
    if prompt:
        messages.append("Practice cues follow the selected prompt; they are not detected errors or measurements of tongue position.")
        messages.append("A team demo reference supports comparison but is not automatically a validated General American target.")
    return messages
