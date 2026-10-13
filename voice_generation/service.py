"""Generation boundary; DevelopmentStore is a localhost-only integration fixture."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import re
from pathlib import Path
import threading
import time
import uuid

from .generator import TARGET_ACCENT

ASSET = re.compile(r"synthetic-[0-9a-f]{32}\Z")


class AttemptUnavailable(Exception):
    pass


def failure(code, message, retryable=False, **ids):
    return {"ok": False, **ids, "error": {"code": code, "user_message": message, "retryable": retryable}}


class DevelopmentStore:
    """Replace with Lucas's authorized, atomic persistent storage adapter at integration.

    auth_context here is a server-issued user identifier, never a browser owner ID.
    The lock covers every owner/revision/job check and its associated mutation.
    """
    def __init__(self):
        self.lock = threading.RLock()
        self.attempts = {}

    def _get(self, auth_context, attempt_id):
        attempt = self.attempts.get(attempt_id)
        if attempt is None or attempt["user_id"] != auth_context:
            raise AttemptUnavailable()
        return attempt

    def create(self, auth_context, fixture):
        with self.lock:
            attempt = deepcopy(fixture)
            attempt.update(attempt_id=uuid.uuid4().hex, user_id=auth_context,
                           confirmed_text=None, transcript_confirmed=False, input_revision=1,
                           generated_assets=[])
            attempt["jobs"]["example_generation"] = self.job(1)
            self.attempts[attempt["attempt_id"]] = attempt
            return deepcopy(attempt)

    @staticmethod
    def job(revision, job_id=None, status="not_requested", timings=None, error=None):
        return {"job_id": job_id, "input_revision": revision, "status": status,
                "timings_ms": timings or {}, "error": error}

    def get_attempt(self, auth_context, attempt_id):
        with self.lock:
            return deepcopy(self._get(auth_context, attempt_id))

    def confirm(self, auth_context, attempt_id, text, accent, expected_revision):
        with self.lock:
            attempt = self._get(auth_context, attempt_id)
            if attempt["input_revision"] != expected_revision:
                return None
            old_assets = deepcopy(attempt["generated_assets"])
            attempt["input_revision"] += 1
            attempt.update(confirmed_text=text, transcript_confirmed=True, target_accent=accent,
                           generated_assets=[], sound_results=[])
            revision = attempt["input_revision"]
            attempt["jobs"]["example_generation"] = self.job(revision)
            # Input edits invalidate all dependent findings, not recognition/original audio.
            for name in ("analysis", "accent_conversion"):
                attempt["jobs"][name] = self.job(revision)
            return deepcopy(attempt), old_assets

    def begin(self, auth_context, attempt_id, revision, job_id):
        with self.lock:
            attempt = self._get(auth_context, attempt_id)
            if attempt["input_revision"] != revision:
                return failure("REVISION_CONFLICT", "The text changed. Generate again from the current text.")
            if not attempt["transcript_confirmed"] or not attempt.get("confirmed_text"):
                return failure("TRANSCRIPT_CONFIRMATION_REQUIRED", "Confirm your text before generating an example.")
            if attempt["target_accent"] != TARGET_ACCENT:
                return failure("UNSUPPORTED_ACCENT", "Only American English examples are available.")
            if len(attempt["confirmed_text"]) > 1000:
                return failure("UNSUPPORTED_TEXT", "Use at most 1,000 characters.")
            previous = deepcopy(attempt["generated_assets"])
            attempt["generated_assets"] = []
            attempt["jobs"]["example_generation"] = self.job(revision, job_id, "queued")
            return {"ok": True, "snapshot": deepcopy(attempt), "previous_assets": previous}

    def update_job(self, auth_context, attempt_id, revision, job_id, status, result=None):
        with self.lock:
            try:
                attempt = self._get(auth_context, attempt_id)
            except AttemptUnavailable:
                return False
            job = attempt["jobs"]["example_generation"]
            if attempt["input_revision"] != revision or job["job_id"] != job_id:
                return False
            attempt["jobs"]["example_generation"] = self.job(
                revision, job_id, status, (result or {}).get("timings_ms"), (result or {}).get("error"))
            if status == "completed":
                attempt["generated_assets"] = [{"audio_id": result["generated_audio_id"],
                    "type": "synthetic_example", "input_revision": revision}]
            return True

    def delete(self, auth_context, attempt_id):
        with self.lock:
            attempt = self._get(auth_context, attempt_id)
            del self.attempts[attempt_id]
            return deepcopy(attempt["generated_assets"])


class GenerationService:
    def __init__(self, store, backend, output_dir):
        self.store, self.backend = store, backend
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="synthetic-example")
        self.lock = threading.Lock()
        self.busy = False
        self.idle = threading.Event()
        self.idle.set()

    def _cleanup(self, assets):
        for asset in assets:
            audio_id = asset.get("audio_id", "")
            if ASSET.fullmatch(audio_id):
                for extension in (".wav", ".json"):
                    (self.output_dir / (audio_id + extension)).unlink(missing_ok=True)

    def confirm_text(self, auth_context, attempt_id, text, accent, expected_revision):
        if not isinstance(text, str) or not text.strip() or len(text) > 1000:
            return failure("UNSUPPORTED_TEXT", "Enter between 1 and 1,000 characters.")
        if accent != TARGET_ACCENT:
            return failure("UNSUPPORTED_ACCENT", "Only American English examples are available.")
        try:
            result = self.store.confirm(auth_context, attempt_id, text.strip(), accent, expected_revision)
        except AttemptUnavailable:
            return failure("ATTEMPT_UNAVAILABLE", "This practice session is unavailable.")
        if result is None:
            return failure("REVISION_CONFLICT", "The session changed. Reload it and confirm again.")
        snapshot, old_assets = result
        self._cleanup(old_assets)
        return {"ok": True, "session": snapshot}

    def generate_example(self, auth_context, attempt_id, input_revision):
        ids = {"attempt_id": attempt_id, "input_revision": input_revision}
        try:
            self.store.get_attempt(auth_context, attempt_id)
        except AttemptUnavailable:
            return failure("ATTEMPT_UNAVAILABLE", "This practice session is unavailable.", **ids)
        with self.lock:
            if self.busy:
                return failure("BUSY", "An example is being generated. Please try again shortly.", True, **ids)
            job_id = uuid.uuid4().hex
            try:
                result = self.store.begin(auth_context, attempt_id, input_revision, job_id)
            except AttemptUnavailable:
                return failure("ATTEMPT_UNAVAILABLE", "This practice session is unavailable.", **ids)
            if not result["ok"]:
                return {**result, **ids}
            self.busy = True
            self.idle.clear()
            self._cleanup(result["previous_assets"])
            self.executor.submit(self._run, auth_context, result["snapshot"], job_id)
            return {"ok": True, **ids, "job_id": job_id, "status": "queued"}

    def _run(self, auth_context, snapshot, job_id):
        attempt_id, revision = snapshot["attempt_id"], snapshot["input_revision"]
        started = time.perf_counter()
        try:
            if not self.store.update_job(auth_context, attempt_id, revision, job_id, "processing"):
                return
            try:
                result = self.backend.generate_audio(snapshot["confirmed_text"], snapshot["target_accent"], output_dir=self.output_dir)
                if result.get("ok") and not ASSET.fullmatch(result.get("generated_audio_id", "")):
                    raise ValueError("Invalid generated asset identifier")
            except Exception:
                result = failure("MODEL_UNAVAILABLE", "The example could not be generated. Please retry.", True)
            result.setdefault("timings_ms", {})["job_total"] = round((time.perf_counter() - started) * 1000, 2)
            accepted = self.store.update_job(auth_context, attempt_id, revision, job_id,
                "completed" if result.get("ok") else "failed", result)
            if not accepted and result.get("ok"):
                self._cleanup([{"audio_id": result["generated_audio_id"]}])
        finally:
            with self.lock:
                self.busy = False
                self.idle.set()

    def audio_path(self, auth_context, attempt_id, audio_id):
        with self.store.lock:
            snapshot = self.store.get_attempt(auth_context, attempt_id)
            if not any(asset["audio_id"] == audio_id and asset["input_revision"] == snapshot["input_revision"]
                       for asset in snapshot["generated_assets"]):
                raise AttemptUnavailable()
            if not ASSET.fullmatch(audio_id):
                raise AttemptUnavailable()
            return self.output_dir / (audio_id + ".wav")

    def delete_attempt(self, auth_context, attempt_id):
        self._cleanup(self.store.delete(auth_context, attempt_id))

    def close(self):
        self.backend.close() if hasattr(self.backend, "close") else None
        self.executor.shutdown(wait=True)
