"""Sequential CPU integration for the twelve-file laptop prototype.

Paths in settings/prompts are relative to this file, regardless of the shell's
working directory. Missing settings use Sarrvesh's documented DSP defaults;
Lucas's optional stages still report their actual availability. No fake scores.
"""

from collections import OrderedDict
from copy import deepcopy
from datetime import datetime, timezone
import importlib
import json
import math
from pathlib import Path
import shutil
import threading
import uuid

from feedback import make_feedback

BASE_DIR = Path(__file__).resolve().parent
_LOCK = threading.Lock()
_REFERENCE_CACHE = OrderedDict()
_STAGES = ("configuration", "learner_audio", "reference_audio", "learner_dsp",
           "reference_dsp", "comparison", "alignment", "phoneme_scoring", "feedback", "save")
_USABLE = {"ok", "warning", "scored"}


def json_safe(value):
    """Convert NumPy-like values, omit waveforms, and encode missing data as null."""
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items() if k != "samples"}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "tolist"):
        return json_safe(value.tolist())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise TypeError(f"Unsupported result value: {type(value).__name__}")


def load_prompts():
    entries = json.loads((BASE_DIR / "prompts.json").read_text(encoding="utf-8"))
    if not isinstance(entries, list) or not entries:
        raise ValueError("prompts.json must contain a nonempty list.")
    ids = set()
    for entry in entries:
        for key in ("id", "text", "reference_wav"):
            if not isinstance(entry.get(key), str) or not entry[key].strip():
                raise ValueError(f"Every prompt needs a nonempty {key}.")
        if entry["id"] in ids:
            raise ValueError("Prompt IDs must be unique.")
        ids.add(entry["id"])
        for key in ("target_words", "target_phones", "lesson_links"):
            if not isinstance(entry.get(key), list):
                raise ValueError(f"Prompt {entry['id']} needs a {key} list.")
    return entries


def _path(path):
    path = Path(path).expanduser()
    return (BASE_DIR / path).resolve() if not path.is_absolute() else path.resolve()


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _validate_alignment(output, duration):
    seen, previous = set(), 0.0
    if not output.get("segments"):
        raise ValueError("Alignment returned no phoneme segments.")
    for segment in output["segments"]:
        identity = segment["segment_id"]
        start, end = segment["start_sec"], segment["end_sec"]
        if identity in seen or not isinstance(segment["canonical_phone"], str):
            raise ValueError("Invalid or duplicate alignment segment.")
        if not (_number(start) and _number(end) and previous <= start < end <= duration + 1e-6):
            raise ValueError("Alignment boundaries must be ordered and inside the recording.")
        seen.add(identity)
        previous = end


def _validate_scores(output, alignment):
    expected = {segment["segment_id"] for segment in alignment["segments"]}
    seen = set()
    for segment in output.get("segments", []):
        identity = segment["segment_id"]
        if identity not in expected or identity in seen:
            raise ValueError("Scores must join uniquely to alignment by segment_id.")
        seen.add(identity)
        if segment.get("status") not in {"scored", "uncertain", "unsupported"}:
            raise ValueError("Phoneme status must be scored, uncertain or unsupported.")
        if segment["status"] == "scored" and (
            not _number(segment.get("raw_score")) or not segment.get("score_units")
        ):
            raise ValueError("Scored segments require a finite raw_score and score_units.")
    if not seen:
        raise ValueError("No phoneme evidence was returned.")
    if seen != expected:
        output["status"] = "partial"
        output["reason"] = "Some aligned segments have no scoring result."
    elif any(s["status"] != "scored" for s in output["segments"]):
        output["status"] = "uncertain"


def _stage(result, name, module, function, *args, validator=None):
    try:
        output = getattr(importlib.import_module(module), function)(*args)
        if not isinstance(output, dict) or not isinstance(output.get("status"), str):
            raise ValueError("Stage must return a dictionary with an explicit status.")
        # Sanitize before validation, but retain audio samples only in memory.
        safe = json_safe(output)
        if output["status"] in _USABLE | {"partial", "uncertain"} and validator:
            validator(safe)
            output.update({k: v for k, v in safe.items() if k != "samples"})
        result["stage_statuses"][name] = {
            "status": output["status"], "message": output.get("reason") or output.get("error")}
        for warning in output.get("warnings", []):
            result["messages"].append(f"{name}: {warning}")
        if output["status"] not in _USABLE:
            result["messages"].append(f"{name}: {output.get('reason') or output.get('error') or output['status']}")
        return output
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        result["stage_statuses"][name] = {"status": "unavailable", "message": message}
        result["messages"].append(f"{name}: {message}")
        return {"status": "unavailable", "reason": message}


def _usable(output):
    return output.get("status") in _USABLE


def _analyze(result, learner_path, prompt_id, run_dir):
    prompts = load_prompts()
    prompt = next((p for p in prompts if p["id"] == prompt_id), None)
    if prompt is None:
        raise ValueError("Choose one of the available prompts.")
    result["prompt"] = prompt
    settings_path = BASE_DIR / "settings.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.exists() else {}
    if not isinstance(settings, dict):
        raise ValueError("settings.json must contain an object.")
    settings = {"sample_rate_hz": 16000, "max_duration_sec": 5, "device": "cpu", **settings}
    if settings["sample_rate_hz"] != 16000 or settings["device"] != "cpu":
        raise ValueError("This milestone requires 16000 Hz audio and device='cpu'.")
    limit = settings["max_duration_sec"]
    if not _number(limit) or not 0 < limit <= 5:
        raise ValueError("max_duration_sec must be positive and at most 5.")
    result["stage_statuses"]["configuration"] = {"status": "ok", "message": None}
    if not settings_path.exists():
        result["messages"].append("settings.json is missing; using documented CPU audio/DSP defaults. Add Lucas's settings for alignment and scoring.")
        result["stage_statuses"]["configuration"]["status"] = "warning"
    result["settings"] = settings
    reference = _path(prompt["reference_wav"])
    if not reference.is_file():
        result["stage_statuses"]["reference_audio"] = {"status": "unavailable", "message": f"Missing reference WAV: {reference}"}
        raise ValueError(f"Missing reference WAV: {reference}. Record exactly: {prompt['text']}")
    if not learner_path:
        raise ValueError("Upload a learner WAV before analyzing.")
    learner = Path(learner_path).resolve()
    if not learner.is_file() or learner.suffix.lower() != ".wav":
        raise ValueError("Upload an existing .wav file.")
    learner_audio = _stage(result, "learner_audio", "audio_io", "prepare_audio", str(learner), settings)
    result["learner_audio"] = json_safe(learner_audio)
    if not _usable(learner_audio):
        return
    # Retain a stable copy: Gradio's temporary upload may disappear after a session.
    saved_audio = run_dir / "learner.wav"
    shutil.copyfile(learner, saved_audio)
    result["audio_paths"]["original"] = str(saved_audio)
    learner_audio["prompt_id"] = prompt_id
    result["learner_audio"]["path"] = str(saved_audio)
    stat = reference.stat()
    cache_key = (str(reference), stat.st_mtime_ns, stat.st_size, json.dumps(settings, sort_keys=True))
    cached = _REFERENCE_CACHE.get(cache_key)
    if cached:
        reference_audio, reference_dsp = deepcopy(cached)
        _REFERENCE_CACHE.move_to_end(cache_key)
        for name, output in (("reference_audio", reference_audio), ("reference_dsp", reference_dsp)):
            result["stage_statuses"][name] = {"status": output["status"], "message": output.get("reason"), "cached": True}
            result["messages"].extend(f"{name}: {w}" for w in output.get("warnings", []))
    else:
        reference_audio = _stage(result, "reference_audio", "audio_io", "prepare_audio", str(reference), settings)
        reference_dsp = {"status": "unavailable"}
        if _usable(reference_audio):
            reference_dsp = _stage(result, "reference_dsp", "dsp_features", "extract_features", reference_audio, settings)
            if _usable(reference_dsp):
                _REFERENCE_CACHE[cache_key] = deepcopy((reference_audio, reference_dsp))
                while len(_REFERENCE_CACHE) > 3:
                    _REFERENCE_CACHE.popitem(last=False)
    result["reference_audio"] = json_safe(reference_audio)
    if not _usable(reference_audio):
        return
    reference_audio["prompt_id"] = prompt_id
    result["audio_paths"]["reference"] = str(reference)
    result["reference_dsp"] = reference_dsp
    result["learner_dsp"] = _stage(result, "learner_dsp", "dsp_features", "extract_features", learner_audio, settings)
    result["comparison"] = _stage(result, "comparison", "compare_audio", "compare_audio", learner_audio,
                                   reference_audio, result["learner_dsp"], reference_dsp, settings)
    result["alignment"] = _stage(result, "alignment", "align_audio", "align_audio", learner_audio,
                                  prompt["text"], settings, str(run_dir),
                                  validator=lambda x: _validate_alignment(x, learner_audio["duration_sec"]))
    if _usable(result["alignment"]):
        result["phoneme_results"] = _stage(result, "phoneme_scoring", "gop_score", "score_phonemes",
            learner_audio, result["alignment"], settings,
            validator=lambda x: _validate_scores(x, result["alignment"]))
    statuses = result["stage_statuses"]
    required = ("learner_dsp", "reference_dsp", "comparison", "alignment", "phoneme_scoring")
    if all(statuses[s]["status"] in _USABLE for s in required):
        result["overall_status"] = "complete"
    elif any(_usable(result.get(s, {})) for s in ("learner_dsp", "comparison", "phoneme_results")):
        result["overall_status"] = "partial"


def run_attempt(learner_path, prompt_id) -> dict:
    """Analyze one attempt; always return a fresh result and try to save its JSON."""
    with _LOCK:  # Also protects reference cache and model calls across UI sessions.
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "_" + uuid.uuid4().hex[:12]
        run_dir = BASE_DIR / "runs" / run_id
        result = {"run_id": run_id, "prompt_id": prompt_id, "overall_status": "failed",
                  "stage_statuses": {s: {"status": "skipped", "message": "Prerequisite unavailable."} for s in _STAGES},
                  "audio_paths": {"original": None, "reference": None}, "learner_dsp": {},
                  "reference_dsp": {}, "comparison": {}, "alignment": {},
                  "phoneme_results": {"status": "unavailable", "segments": []},
                  "messages": [], "feedback": [], "results_path": None}
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
            _analyze(result, learner_path, prompt_id, run_dir)
        except Exception as exc:
            result["messages"].append(str(exc))
            if result["stage_statuses"]["configuration"]["status"] == "skipped":
                result["stage_statuses"]["configuration"] = {"status": "unavailable", "message": str(exc)}
        try:
            result["feedback"] = make_feedback(result, result.get("prompt", {}))
            result["stage_statuses"]["feedback"] = {"status": "ok", "message": None}
        except Exception as exc:
            result["stage_statuses"]["feedback"] = {"status": "unavailable", "message": str(exc)}
            result["messages"].append(f"Feedback unavailable: {exc}")
            if result["overall_status"] == "complete":
                result["overall_status"] = "partial"
        try:
            destination = run_dir / "results.json"
            result["results_path"] = str(destination)
            result["stage_statuses"]["save"] = {"status": "ok", "message": None}
            result = json_safe(result)
            temporary = run_dir / "results.tmp"
            temporary.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
            temporary.replace(destination)
        except Exception as exc:
            result["results_path"] = None
            result["overall_status"] = "failed"
            result["stage_statuses"]["save"] = {"status": "unavailable", "message": str(exc)}
            result["messages"].append(f"Could not save this attempt: {exc}")
        return result
