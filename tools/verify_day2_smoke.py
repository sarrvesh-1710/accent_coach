"""Offline Day 2 component smoke using an existing local demo recording.

Real Whisper/MFA/phoneme inference; trusted fixture snapshot, no real storage or
authentication. No synthetic listening example is declared a learner asset.
This recording has no independent human pronunciation label in this test.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import pipeline
from confirmed_analysis import run_confirmed_attempt
from phoneme_scoring.align_audio import load_settings
import speech_content
from tools.check_reference_free import operational_pass


def main():
    destination = ROOT / "runs/day2-phase6/real-smoke.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    source = ROOT / "data/references/think.wav"
    settings = load_settings(ROOT / "phoneme_scoring/settings.json")
    report = dict(baseline=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                  scope="Existing local demo recording; real models; no human accuracy labels; fixture snapshot only; no production authentication/storage/browser test",
                  checks=[])
    def record(name, passed, **details):
        report["checks"].append(dict(name=name, passed=passed, **details))
        destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report["checks"][-1]), flush=True)
        if not passed:
            raise RuntimeError("Smoke check failed: " + name)
    recognized = speech_content.transcribe_audio(source, settings)
    record("independent_transcription", recognized["status"] == "completed",
           model_id=recognized["model_id"], model_revision=recognized["model_revision"],
           source_audio_sha256=recognized["source_audio_sha256"], audio_sha256=recognized["audio_sha256"])
    prompt = next(p for p in pipeline.load_prompts() if p["id"] == "think")
    before = {}
    old_speech = subprocess.check_output(["git", "show", "HEAD:speech_content.py"], cwd=ROOT, text=True)
    exec(compile(old_speech, "baseline_speech_content", "exec"), before)
    before["_load_asr"] = speech_content._load_asr  # Identical cache, avoid duplicate weights.
    old_result = before["check_content"](source, prompt, settings)
    new_result = speech_content.check_content(source, prompt, settings)
    record("preset_wrapper_output_parity", old_result == new_result, status=new_result["status"])
    current = pipeline.run_attempt(source, "think", compare_reference=False)
    record("preset_real_pipeline", operational_pass(current), overall_status=current["overall_status"],
           results_path=current["results_path"], alignment=current["alignment"].get("status"),
           phoneme_model_revision=current["phoneme_results"].get("model_revision"))
    baseline = types.ModuleType("phoneme_scoring._baseline_alignment")
    baseline.__package__ = "phoneme_scoring"
    old_alignment = subprocess.check_output(["git", "show", "HEAD:phoneme_scoring/align_audio.py"], cwd=ROOT, text=True)
    exec(compile(old_alignment, "baseline_align_audio", "exec"), baseline.__dict__)
    with tempfile.TemporaryDirectory(prefix="accent_day2_smoke_") as work, patch.dict(os.environ,settings.get('mfa',{}).get('environment',{})):
        old = baseline.align_audio(source, prompt["text"], settings, work)
        aligned = current["alignment"]
        keys = ["status", "segments", "words", "audio_sha256", "duration_sec", "sample_rate_hz", "boundary_rounding_corrections"]
        record("mfa_baseline_output_parity", old["status"] == "available" and all(old.get(k) == aligned.get(k) for k in keys),
               compared_fields=keys)
    snapshot = dict(attempt_id="smoke-fixture-attempt", job_id="smoke-fixture-job", input_revision=1,
                    learner_audio_id="smoke-fixture-original-demo", learner_audio_role="learner",
                    learner_audio_path=str(source), source_audio_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    confirmed_text=prompt["text"], transcript_confirmed=True,
                    target_accent="en-US-general-american", transcription=recognized)
    confirmed = run_confirmed_attempt(snapshot, settings)
    record("confirmed_real_worker_fixture", confirmed.get("ok") is True and confirmed.get("analysis_status") == "completed",
           analysis_status=confirmed.get("analysis_status"), sound_results=confirmed.get("sound_results"),
           limitations=confirmed.get("limitations"), timings=confirmed.get("timings"), error=confirmed.get("error"))
    snapshot["learner_audio_role"] = "synthetic_example"
    rejected = run_confirmed_attempt(snapshot, settings)
    record("generated_role_rejected", rejected.get("error", {}).get("code") == "INVALID_AUDIO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
