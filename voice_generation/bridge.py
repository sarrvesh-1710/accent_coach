"""Call Kokoro from the main app without importing its model dependencies."""
import base64
import binascii
import io
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import threading
import wave

from .generator import TARGET_ACCENT, _failure

ROOT = Path(__file__).resolve().parents[1]
MAX_REPLY = 3_000_000
ASSET = re.compile(r"synthetic-[0-9a-f]{32}\Z")


class IsolatedKokoro:
    """One persistent subprocess, serialized requests, hard response deadline."""
    def __init__(self, python=None, timeout_seconds=120):
        default = ROOT / "voice_generation/.venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        self.python = Path(python or os.environ.get("ACCENT_COACH_KOKORO_PYTHON", default))
        self.timeout = timeout_seconds
        self.process = None
        self.responses = None
        self.lock = threading.RLock()

    @staticmethod
    def _read(process, responses):
        try:
            while True:
                line = process.stdout.readline(MAX_REPLY + 1)
                if not line or len(line) > MAX_REPLY:
                    break
                responses.put(line)
        except (OSError, ValueError):
            pass
        finally:
            try:
                responses.put_nowait(None)
            except queue.Full:
                pass

    def _start(self):
        if self.process is not None and self.process.poll() is None:
            return
        self._stop()
        if not self.python.is_file():
            raise FileNotFoundError("Isolated generation Python is unavailable")
        env = os.environ.copy()
        # Do not inherit the main environment's Python search path or activation.
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
        env.pop("VIRTUAL_ENV", None)
        env["HF_HUB_OFFLINE"] = "1"
        env["TRANSFORMERS_OFFLINE"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        self.process = subprocess.Popen(
            [str(self.python), "-u", "-m", "voice_generation.stdio_worker"],
            cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, env=env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.responses = queue.Queue(maxsize=2)
        threading.Thread(target=self._read, args=(self.process, self.responses), daemon=True).start()

    def _stop(self):
        process, self.process = self.process, None
        if process is not None:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
            for stream in (process.stdin, process.stdout):
                if stream is not None:
                    stream.close()
        self.responses = None

    def __call__(self, text, target_accent=TARGET_ACCENT, *, output_dir):
        if target_accent != TARGET_ACCENT:
            return _failure("UNSUPPORTED_ACCENT", "Only American English examples are available.")
        if not isinstance(text, str) or not text.strip() or len(text) > 200 or len(re.findall(r"[A-Za-z]+(?:['\u2019][A-Za-z]+)*", text)) > 12:
            return _failure("UNSUPPORTED_TEXT", "Use at most 12 words and 200 characters.")
        with self.lock:
            path = sidecar = None
            try:
                self._start()
                self.process.stdin.write((json.dumps({"text": text, "target_accent": target_accent,
                    "work_root": str(Path(output_dir).resolve())}) + "\n").encode("utf-8"))
                self.process.stdin.flush()
                try:
                    line = self.responses.get(timeout=self.timeout)
                except queue.Empty:
                    self._stop()
                    return _failure("TIMEOUT", "Generating the example took too long. Please retry.", True)
                if line is None:
                    raise RuntimeError("Generation process stopped")
                response = json.loads(line)
                result = response["result"]
                if not result.get("ok"):
                    return result
                identity = result["generated_audio_id"]
                if not ASSET.fullmatch(identity) or result.get("type") != "synthetic_example" or result.get("backend") != "kokoro":
                    raise ValueError("Invalid generated asset metadata")
                data = base64.b64decode(response["audio_base64"], validate=True)
                if not 44 < len(data) <= 2_000_000:
                    raise ValueError("Invalid generated audio size")
                with wave.open(io.BytesIO(data), "rb") as audio:
                    if audio.getframerate() != 24000 or audio.getnchannels() != 1 or audio.getsampwidth() != 2 or audio.getnframes() == 0:
                        raise ValueError("Invalid generated WAV")
                root = Path(output_dir)
                root.mkdir(parents=True, exist_ok=True)
                path, sidecar = root / (identity + ".wav"), root / (identity + ".json")
                path.write_bytes(data)
                sidecar.write_text(json.dumps(result, indent=2), encoding="utf-8")
                return result
            except (OSError, ValueError, RuntimeError, KeyError, TypeError, binascii.Error, wave.Error, subprocess.SubprocessError):
                self._stop()
                for output in (path, sidecar):
                    if output is not None:
                        output.unlink(missing_ok=True)
                return _failure("MODEL_UNAVAILABLE", "Kokoro is unavailable. Check the isolated generation environment and retry.", True)

    def close(self):
        with self.lock:
            self._stop()


def create_generator():
    backend = os.environ.get("ACCENT_COACH_GENERATION_BACKEND", "kokoro").lower()
    if backend == "kokoro":
        return IsolatedKokoro()
    if backend == "windows":
        from .generator import generate_audio
        return generate_audio
    raise ValueError("ACCENT_COACH_GENERATION_BACKEND must be kokoro or windows")
