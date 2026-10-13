"""Persistent model process: reuse weights; bound inference lifetime on failure."""
import contextlib
import multiprocessing
import sys
import threading

from .service import failure


def _worker(pipe):
    generator = None
    try:
        while True:
            request = pipe.recv()
            if request is None:
                break
            try:
                with contextlib.redirect_stdout(sys.stderr):
                    if generator is None:
                        from .kokoro_backend import KokoroGenerator
                        generator = KokoroGenerator()
                    result = generator.generate_audio(**request)
                pipe.send(result)
            except Exception:
                generator = None
                pipe.send(failure("MODEL_UNAVAILABLE", "Kokoro is unavailable. Check the local model setup and retry.", True))
    except (EOFError, BrokenPipeError):
        pass
    finally:
        pipe.close()


class ModelWorker:
    def __init__(self, timeout_seconds=120):
        self.timeout = timeout_seconds
        self.process = self.pipe = None
        self.lock = threading.RLock()

    def _stop(self):
        if self.process is not None:
            if self.process.is_alive():
                self.process.terminate()
            self.process.join(timeout=3)
            if self.process.is_alive():
                self.process.kill()
                self.process.join(timeout=3)
            self.process.close()
        if self.pipe is not None:
            self.pipe.close()
        self.process = self.pipe = None

    def generate_audio(self, text, target_accent, *, output_dir):
        with self.lock:
            existing_files = set(output_dir.glob("synthetic-*"))
            if self.process is None or not self.process.is_alive():
                self._stop()
                ctx = multiprocessing.get_context("spawn")
                self.pipe, child = ctx.Pipe()
                self.process = ctx.Process(target=_worker, args=(child,), daemon=True)
                self.process.start()
                child.close()
            try:
                self.pipe.send({"text": text, "target_accent": target_accent, "output_dir": str(output_dir)})
                if not self.pipe.poll(self.timeout):
                    self._stop()
                    # Remove only files created by this interrupted job.
                    for path in set(output_dir.glob("synthetic-*")) - existing_files:
                        if path.suffix in (".wav", ".json"):
                            path.unlink(missing_ok=True)
                    return failure("TIMEOUT", "Generation took too long. Please retry.", True)
                return self.pipe.recv()
            except (EOFError, BrokenPipeError, OSError):
                self._stop()
                return failure("MODEL_UNAVAILABLE", "The generation worker stopped. Please retry.", True)

    def close(self):
        with self.lock:
            self._stop()
