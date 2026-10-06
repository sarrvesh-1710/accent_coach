"""Allowlisted learner profiles; paths in profile JSON are project-relative."""
from copy import deepcopy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
_FILES = {"chinese": "chinese.json"}


def load_profile(profile_id="general"):
    if profile_id == "general":
        return {"schema_version": 1, "id": "general", "label": "General practice",
                "target_accent": "General American English",
                "calibration": {"enabled": False}, "feedback": {}}
    if profile_id not in _FILES:
        raise ValueError(f"Unknown learner profile: {profile_id}")
    profile = json.loads((ROOT / "accent_profiles" / _FILES[profile_id]).read_text(encoding="utf-8"))
    if profile.get("schema_version") != 1 or profile.get("id") != profile_id:
        raise ValueError("Invalid profile schema or identity")
    return profile


def list_profiles():
    return [load_profile(key) for key in ("general", *_FILES)]


def apply_profile(settings, profile_id):
    result = deepcopy(settings)
    result["accent_profile"] = load_profile(profile_id)
    return result
