"""Experimental CTC substitution evidence; not calibrated GOP or a grade.

For each target, sum all CTC paths for the complete MFA-derived phone sequence
and compare with sequences replacing that target with configured alternatives.
Keep all frames including blank. No reference waveform, frame mean, sigmoid,
or percentage is used. This assesses selected substitutions, not deletions,
insertions, stress, accent identity, or comprehensive pronunciation quality.
"""
import math
import numpy as np


def ctc_log_probability(logp, tokens, blank):
    """Exact log-space forward sum; repeated tokens require intervening blank."""
    logp = np.asarray(logp, dtype=np.float64)
    if logp.ndim != 2 or not len(logp) or np.isnan(logp).any() or np.isposinf(logp).any():
        raise ValueError("Invalid CTC log probabilities")
    if not 0 <= blank < logp.shape[1] or any(t == blank or not 0 <= t < logp.shape[1] for t in tokens):
        raise ValueError("Invalid CTC token/blank IDs")
    if not tokens:
        return float(logp[:, blank].sum())
    expanded = np.full(2 * len(tokens) + 1, blank, dtype=int)
    expanded[1::2] = tokens
    alpha = np.full(len(expanded), -np.inf)
    alpha[0], alpha[1] = logp[0, blank], logp[0, tokens[0]]
    skip = np.zeros(len(expanded), dtype=bool)
    skip[2:] = (expanded[2:] != blank) & (expanded[2:] != expanded[:-2])
    for frame in logp[1:]:
        one = np.r_[-np.inf, alpha[:-1]]
        two = np.r_[-np.inf, -np.inf, alpha[:-2]]
        two[~skip] = -np.inf
        alpha = np.logaddexp(np.logaddexp(alpha, one), two) + frame[expanded]
    return float(np.logaddexp(alpha[-1], alpha[-2]))


def compare_targets(logp, segments, segment_rows, mapping, vocab, special_ids, blank, targets, cfg, resolve):
    result = dict(status="available", method="full_sequence_ctc_substitution_v1", calibrated=False,
                  units="log_likelihood_ratio_nats", targets=[],
                  limitation="Selected substitutions only. Conditional on MFA transcript/phone variants; no pronunciation grade.")
    sequence, active = [], []
    for seg in segments:
        label, reason = resolve(seg, mapping)
        if reason == "silence":
            continue
        if reason or label not in vocab or vocab[label] in special_ids:
            return dict(result, status="unavailable", reason="Unsupported phone in sentence context.")
        sequence.append(vocab[label])
        active.append(seg)
    if not sequence:
        return dict(result, status="unavailable", reason="No supported sentence phones.")
    expected_logp = ctc_log_probability(logp, sequence, blank)
    threshold = float(cfg.get("decision_margin_nats", 1.0))
    if not math.isfinite(threshold) or threshold <= 0:
        raise ValueError("decision_margin_nats must be positive and finite")
    result.update(expected_sequence=[vocab_id for vocab_id in sequence],
                  decision_margin_nats=threshold, threshold_validated=False,
                  expected_sequence_logp=expected_logp if math.isfinite(expected_logp) else None)
    by_id = {row["segment_id"]: row for row in segment_rows}
    for spec in targets:
        row = dict(word=spec["word"], expected_phone=spec["phone"], status="insufficient_evidence", reason=None)
        result["targets"].append(row)
        matches = [(i, s) for i, s in enumerate(active)
                   if s.get("word", "").lower() == spec["word"].lower() and s["canonical_phone"] == spec["phone"]
                   and ("segment_id" not in spec or s["segment_id"] == spec["segment_id"])]
        if len(matches) != 1 or not math.isfinite(expected_logp):
            row["reason"] = "Target not uniquely aligned or sequence has no valid CTC path."
            continue
        index, seg = matches[0]
        row.update(segment_id=seg["segment_id"], start_sec=seg["start_sec"], end_sec=seg["end_sec"])
        alternatives = []
        for phone in spec["alternatives"]:
            label = mapping["phones"].get(phone)
            if label not in vocab or vocab[label] in special_ids or vocab[label] == sequence[index]:
                continue
            alternative = sequence.copy()
            alternative[index] = vocab[label]
            value = ctc_log_probability(logp, alternative, blank)
            if math.isfinite(value):
                alternatives.append(dict(phone=phone, token=label, sequence_logp=value))
        if not alternatives:
            row["reason"] = "No supported alternative sequence."
            continue
        best = max(alternatives, key=lambda a: a["sequence_logp"])
        margin = expected_logp - best["sequence_logp"]
        local = by_id.get(seg["segment_id"], {})
        row.update(margin_nats=margin, alternative_phone=best["phone"], alternatives=alternatives,
                   evidence_frames=local.get("evidence_frames", 0), total_frames=local.get("total_frames", 0))
        plausible = {vocab_label for vocab_label in [local.get("target_token"), *[a["token"] for a in alternatives]] if vocab_label}
        if not local.get("evidence_frames"):
            row["reason"] = "No qualified phonetic evidence in the target interval."
        elif local.get("winning_phone") not in plausible:
            row["reason"] = "Strongest local sound lies outside the tested contrast."
        elif abs(margin) < threshold:
            row["reason"] = "Sequence comparison is too close under the experimental rule."
        else:
            row["status"] = "expected_supported" if margin > 0 else "alternative_favored"
            row["reason"] = "Experimental model evidence; not a confirmed pronunciation judgment."
    return result
