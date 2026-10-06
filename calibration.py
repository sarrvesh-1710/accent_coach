"""Small, inspectable JSON ridge calibrator; never converts missing evidence to zero."""
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from .align_audio import config_path

FEATURES = ["expected_vs_alternative_nats", "duration_sec", "log1p_evidence_frames"]


def signature(settings):
    mapping = json.loads(config_path(settings["scoring"]["map_path"], settings).read_text(encoding="utf-8"))
    return hashlib.sha256(json.dumps({"model": {k: settings["model"][k] for k in ("id", "revision")},
        "scoring": settings["scoring"], "mapping": mapping, "mfa": {k: settings["mfa"][k] for k in ("dictionary", "acoustic_model")},
        "feature_schema": FEATURES, "implementation": "chinese-profile-v1"}, sort_keys=True).encode()).hexdigest()


def feature_values(row):
    if row.get("status") != "scored":
        return None
    try:
        margin = float(row["expected_vs_alternative_nats"])
        duration = float(row["end_sec"]) - float(row["start_sec"])
        frames = int(row["evidence_frames"])
        if duration <= 0 or frames < 2 or not math.isfinite(margin + duration):
            return None
        return [margin, duration, math.log1p(frames)]
    except (KeyError, TypeError, ValueError, OverflowError):
        return None


def predict(row, model):
    values = feature_values(row)
    phone = row.get("canonical_phone", "").upper()
    if values is None or phone not in model["phones"]:
        return None
    x = (np.asarray(values) - model["mean"]) / model["scale"]
    onehot = [float(phone == p) for p in model["phones"]]
    value = float(np.dot(np.r_[1., x, onehot], model["coefficients"]))
    return float(np.clip(value, 0., 2.)) if math.isfinite(value) else None


def validate_model(model):
    if model.get("schema_version") != 1 or model.get("kind") != "ridge_phone_rating" or model.get("profile_id") != "chinese":
        raise ValueError("Unsupported calibration model")
    if model.get("features") != FEATURES or not model.get("phones"):
        raise ValueError("Invalid calibration feature schema")
    if len(model["mean"]) != 3 or len(model["scale"]) != 3 or len(model["coefficients"]) != 4 + len(model["phones"]):
        raise ValueError("Invalid calibration dimensions")
    if not all(math.isfinite(v) for v in model["mean"] + model["scale"] + model["coefficients"]) or min(model["scale"]) <= 0:
        raise ValueError("Nonfinite or invalid calibration parameters")


def apply_calibration(evidence, settings, project_root):
    """Mutate only added estimate fields, preserving raw evidence and its status."""
    profile = settings.get("accent_profile", {})
    cfg = profile.get("calibration", {})
    evidence["profile_id"] = profile.get("id", "general")
    evidence["calibrated"] = False
    for row in evidence.get("segments", []):
        row["predicted_phone_rating"] = None
    evidence["calibration_status"] = "disabled"
    if not cfg.get("enabled"):
        return evidence
    path = Path(project_root) / cfg["model_path"]
    if not path.is_file():
        evidence["calibration_status"] = "not_trained"
        return evidence
    try:
        model = json.loads(path.read_text(encoding="utf-8"))
        validate_model(model)
        if model["signature"] != signature(settings):
            raise ValueError("Model, mapping, MFA configuration, or evidence settings changed; recalibrate")
        evidence["calibration_status"] = "loaded"
        evidence["calibration_id"] = model["calibration_id"]
        evidence["calibration_validation"] = model["validation"]
        evidence["calibration_count"] = 0
        for row in evidence.get("segments", []):
            row["predicted_phone_rating"] = predict(row, model)
            evidence["calibration_count"] += int(row["predicted_phone_rating"] is not None)
        evidence["calibrated"] = evidence["calibration_count"] > 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        for row in evidence.get("segments", []):
            row["predicted_phone_rating"] = None
        evidence.update(calibrated=False, calibration_status="unavailable", calibration_reason=str(exc))
    return evidence


def metrics(expected, predicted):
    y, p = np.asarray(expected, float), np.asarray(predicted, float)
    if not len(y):
        return {"count": 0, "mae": None, "rmse": None, "pearson_r": None}
    return {"count": len(y), "mae": float(np.mean(np.abs(y-p))),
            "rmse": float(np.sqrt(np.mean((y-p)**2))),
            "pearson_r": float(np.corrcoef(y, p)[0, 1]) if len(y) > 1 and np.std(y) > 1e-10 and np.std(p) > 1e-10 else None}
