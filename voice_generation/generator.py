"""Synchronous internal Day 1 proof. Not an authenticated web endpoint."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import uuid
import wave

TARGET_ACCENT = "en-US-general-american"
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "runs" / "synthetic_examples"


def _failure(code, message, retryable=False):
    return {"ok": False, "status": "failed", "error": {
        "code": code, "user_message": message, "retryable": retryable}}


def generate_audio(text, target_accent=TARGET_ACCENT, *, output_dir=None):
    """Return a local synthetic asset ID and measured timings, or a safe error.

    output_dir is trusted local configuration. No browser-supplied disk paths.
    The eventual session adapter must load confirmed text from authorized storage.
    """
    if target_accent != TARGET_ACCENT:
        return _failure("UNSUPPORTED_ACCENT", "Only the American English example voice is available.")
    if not isinstance(text, str) or not text.strip() or len(text) > 1000:
        return _failure("UNSUPPORTED_TEXT", "Supply between 1 and 1,000 characters of confirmed text.")
    if os.name != "nt":
        return _failure("MODEL_UNAVAILABLE", "This starter requires a Windows American English desktop voice.")
    root = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT
    audio_id = "synthetic-" + uuid.uuid4().hex
    wav_path = root / (audio_id + ".wav")
    metadata_path = root / (audio_id + ".json")
    started = time.perf_counter()
    try:
        root.mkdir(parents=True, exist_ok=True)
        # A request file avoids shell interpolation of text and paths.
        with tempfile.NamedTemporaryFile(prefix=".request-", suffix=".json", dir=root, delete=False) as handle:
            request = Path(handle.name)
        try:
            request.write_text(json.dumps({"text": text, "output_path": str(wav_path.resolve())}), encoding="utf-8")
            powershell = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
            completed = subprocess.run(
                [str(powershell), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File",
                 str(Path(__file__).with_name("synthesize.ps1")), "-RequestPath", str(request)],
                capture_output=True, text=True, timeout=60,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if completed.returncode != 0:
                raise RuntimeError("Speech backend failed")
            backend = json.loads(completed.stdout)
        finally:
            request.unlink(missing_ok=True)
        with wave.open(str(wav_path), "rb") as audio:
            frames = audio.getnframes()
            rate = audio.getframerate()
            if frames <= 0 or rate <= 0:
                raise ValueError("Empty audio")
            duration = frames / rate
        result = {
            "ok": True, "status": "completed", "generated_audio_id": audio_id,
            "type": "synthetic_example", "label": "Synthetic example",
            "text": text, "target_accent": target_accent,
            "backend": "windows-system-speech", "voice": backend["voice"],
            "sample_rate_hz": rate, "duration_seconds": round(duration, 3),
            "timings_ms": {"total": round((time.perf_counter() - started) * 1000, 2),
                           "synthesis": round(backend["synthesis_ms"], 2)},
            "review": {"words_match": None, "pronunciation_notes": "Listening review pending."},
            "limitations": ["American English desktop voice; General American suitability needs listening review.",
                            "Does not preserve the learner's voice.",
                            "Never use this generated asset as learner assessment input."],
            "error": None,
        }
        metadata_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
        for path in (wav_path, metadata_path):
            path.unlink(missing_ok=True)
        return _failure("MODEL_UNAVAILABLE", "The synthetic example could not be generated. Check the installed Windows voice and try again.", True)
