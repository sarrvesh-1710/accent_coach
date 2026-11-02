"""Opt-in isolated Kokoro transport. Default desktop synthesis is unchanged."""
import os
from pathlib import Path
import queue
import re
import subprocess
import threading
import json
import wave

from .generator import generate_audio, TARGET_ACCENT, _failure

ROOT = Path(__file__).resolve().parents[1]


def generation_capabilities():
    backend = os.environ.get('ACCENT_COACH_EXAMPLE_BACKEND', 'windows')
    if backend == 'windows':
        return dict(backend='windows', optional=False,
                    message='Listening examples use the local desktop voice. Neural examples are optional.')
    python = Path(os.environ.get('ACCENT_COACH_KOKORO_PYTHON', ''))
    ready = backend == 'kokoro' and python.is_absolute() and python.is_file() and all(
        (ROOT / 'models/kokoro' / p).is_file() for p in ('manifest.json', 'config.json', 'kokoro-v1_0.pth', 'voices/af_heart.pt'))
    return dict(backend=backend if backend in {'windows', 'kokoro'} else 'unavailable', optional=True,
                assets_present=ready,
                message='Optional neural listening examples are configured; first generation loads its separate model.' if ready else
                        'Optional neural examples need a separate runtime and model setup. Pronunciation analysis is still available.')


def valid_text(text):
    return (isinstance(text, str) and 0 < len(text.strip()) and len(text) <= 200
            and 1 <= len(re.findall(r"[A-Za-z]+(?:['\u2019][A-Za-z]+)*", text)) <= 12)


class ExternalKokoro:
    """One owned, lazy child interpreter. No neural imports in the web process."""
    def __init__(self, python, *, timeout=120, command=None):
        self.python = Path(python)
        self.timeout = timeout
        self.command = command  # Trusted dependency injection for transport tests.
        self.process = None
        self.lock = threading.RLock()

    def _stop(self):
        process, self.process = self.process, None
        if process is None: return
        if process.poll() is None:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5,
                               creationflags=subprocess.CREATE_NO_WINDOW, check=False)
            else:
                process.kill()
        process.wait(timeout=5)
        for stream in (process.stdin, process.stdout):
            if stream: stream.close()

    def _start(self):
        if self.process is not None and self.process.poll() is None: return
        self._stop()
        if not self.command and (not self.python.is_absolute() or not self.python.is_file()):
            raise OSError('Missing isolated interpreter')
        env = dict(os.environ, HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', PYTHONUNBUFFERED='1')
        self.process = subprocess.Popen(self.command or [str(self.python), '-u', '-m', 'voice_generation.external_worker'],
            cwd=ROOT, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

    def __call__(self, text, target_accent=TARGET_ACCENT, *, output_dir):
        if target_accent != TARGET_ACCENT:
            return _failure('UNSUPPORTED_ACCENT', 'Only General American examples are available.')
        if not valid_text(text):
            return _failure('UNSUPPORTED_TEXT', 'Use 1–12 words and at most 200 characters.')
        root = Path(output_dir).resolve()
        root.mkdir(parents=True, exist_ok=True)
        with self.lock:
            before = set(root.glob('synthetic-*'))
            failed = True
            try:
                self._start()
                self.process.stdin.write(json.dumps(dict(text=text, target_accent=target_accent, output_dir=str(root))) + '\n')
                self.process.stdin.flush()
                answer = queue.Queue(maxsize=1)
                stream = self.process.stdout
                def read():
                    try: answer.put(stream.readline(2_000_001))
                    except (OSError, ValueError): answer.put('')
                thread = threading.Thread(target=read, daemon=True)
                thread.start()
                line = answer.get(timeout=self.timeout)
                if len(line) > 2_000_000: raise ValueError('Oversized result')
                result = json.loads(line)
                if not isinstance(result, dict): raise ValueError('Invalid result')
                if result.get('ok'):
                    asset = result.get('generated_audio_id', '')
                    if (not isinstance(asset, str) or not re.fullmatch(r'synthetic-[0-9a-f]{32}', asset)
                            or result.get('type') != 'synthetic_example'
                            or not (root / (asset + '.wav')).is_file()):
                        raise ValueError('Invalid synthetic output')
                    with wave.open(str(root / (asset + '.wav')), 'rb') as audio:
                        if audio.getnframes() <= 0 or audio.getframerate() <= 0:
                            raise ValueError('Empty synthetic output')
                failed = not result.get('ok')
                return result
            except queue.Empty:
                self._stop()
                return _failure('TIMEOUT', 'Neural example generation timed out. You can retry; your analysis is saved.', True)
            except (OSError, ValueError, EOFError, wave.Error, subprocess.SubprocessError):
                self._stop()
                return _failure('MODEL_UNAVAILABLE', 'The optional neural voice is unavailable. Check its separate setup or use the desktop backend.', True)
            finally:
                if failed:
                    for path in set(root.glob('synthetic-*')) - before:
                        if path.suffix in {'.wav', '.json'}: path.unlink(missing_ok=True)

    def close(self):
        with self.lock: self._stop()


def configured_generator():
    backend = os.environ.get('ACCENT_COACH_EXAMPLE_BACKEND', 'windows')
    if backend == 'windows': return generate_audio
    if backend == 'kokoro': return ExternalKokoro(os.environ.get('ACCENT_COACH_KOKORO_PYTHON', ''))
    return lambda *args, **kwargs: _failure('MODEL_UNAVAILABLE', 'The configured example backend is unavailable.', True)
