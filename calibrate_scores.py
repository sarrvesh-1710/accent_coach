"""Fit only official training rows; development speakers never enter the fit."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random

import numpy as np

from .calibration import FEATURES, feature_values, metrics, predict


def fit(rows, seed=762, alpha=1.0):
    if not np.isfinite(alpha) or alpha <= 0:
        raise ValueError("alpha must be positive and finite")
    if any(r.get("split") != "train" for r in rows):
        raise ValueError("Calibration accepts only official train rows; test must stay held out")
    usable = [r for r in rows if r.get("match_status") == "matched" and feature_values(r.get("evidence", {})) is not None]
    if len(usable) < 30:
        raise ValueError("Need at least 30 usable phones for a smoke-test fit; realistic validation needs many more")
    signatures = {r["signature"] for r in usable}
    if len(signatures) != 1:
        raise ValueError("Rows have different model/evidence signatures")
    keys = [(r["utterance_id"], r["word_index"], r["phone_index_in_word"]) for r in usable]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate phone records; do not concatenate overlapping runs")
    speakers = sorted({r["speaker_id"] for r in usable})
    if len(speakers) < 3:
        raise ValueError("Need at least three speakers to separate training and development")
    random.Random(seed).shuffle(speakers)
    dev_ids = set(speakers[:max(1, round(len(speakers)*.2))])
    train = [r for r in usable if r["speaker_id"] not in dev_ids]
    dev = [r for r in usable if r["speaker_id"] in dev_ids]
    phones = sorted({r["evidence"]["canonical_phone"].upper() for r in train})
    values = np.asarray([feature_values(r["evidence"]) for r in train])
    mean, scale = values.mean(axis=0), values.std(axis=0)
    scale[scale < 1e-8] = 1.
    x = np.column_stack([np.ones(len(train)), (values - mean) / scale,
                         [[float(r["evidence"]["canonical_phone"].upper() == p) for p in phones] for r in train]])
    y = np.asarray([r["human_rating"] for r in train], dtype=float)
    if not np.isfinite(y).all() or np.any((y < 0) | (y > 2)):
        raise ValueError("Human ratings must be finite and in 0..2")
    penalty = alpha * np.eye(x.shape[1]); penalty[0, 0] = 0.
    coefficients = np.linalg.solve(x.T @ x + penalty, x.T @ y)
    model = {"schema_version": 1, "kind": "ridge_phone_rating", "profile_id": "chinese",
             "features": FEATURES, "phones": phones, "mean": mean.tolist(), "scale": scale.tolist(),
             "coefficients": coefficients.tolist(), "signature": next(iter(signatures)),
             "alpha": alpha, "seed": seed, "train_speakers": sorted(set(speakers)-dev_ids),
             "development_speakers": sorted(dev_ids), "train_count": len(train),
             "created_at": datetime.now(timezone.utc).isoformat(),
             "note": "Predicts aggregated SpeechOcean phone ratings. No pass/fail threshold; no validation for other learner populations."}
    pairs = [(r["human_rating"], predict(r["evidence"], model)) for r in dev]
    pairs = [(y, p) for y, p in pairs if p is not None]
    if not pairs:
        raise ValueError("No development phones supported by training phone inventory")
    ys, ps = zip(*pairs)
    model["validation"] = {"development": metrics(ys, ps),
        "constant_train_mean_baseline": metrics(ys, [float(y.mean())]*len(ys)),
        "development_total_usable": len(dev), "development_scored": len(pairs),
        "official_test_evaluated": False}
    model["validation"]["beats_mean_baseline_mae"] = model["validation"]["development"]["mae"] < model["validation"]["constant_train_mean_baseline"]["mae"]
    model["calibration_id"] = hashlib.sha256(json.dumps(model, sort_keys=True).encode()).hexdigest()[:16]
    return model


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rows", type=Path)
    parser.add_argument("--output", type=Path, default=Path("models/chinese_phone_calibration.json"))
    parser.add_argument("--seed", type=int, default=762)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.rows.read_text(encoding="utf-8").splitlines() if line.strip()]
    model = fit(rows, seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(model, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps(model["validation"], indent=2))
    print(f"Saved {args.output}. Review development results before relying on ratings.")


if __name__ == "__main__":
    main()
