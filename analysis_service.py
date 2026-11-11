"""One reusable CPU worker with a hard deadline and restart after failure.

Local single-server deployment. The private account site queues users through
this worker, which retains model caches across tries.
Do not move a timed-out computation to an unbounded background thread.
"""
import atexit
import multiprocessing as mp
import os
import queue
import subprocess
import threading
import time


def _worker(requests, responses):
    # Inference must not download weights during a learner attempt.
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    from pipeline import run_attempt
    while True:
        request = requests.get()
        if request is None:
            return
        if isinstance(request, dict):
            try:
                from phoneme_scoring.align_audio import load_settings
                from pathlib import Path
                settings = load_settings(Path(__file__).parent/'phoneme_scoring/settings.json')
                if request['kind']=='transcription':
                    from speech_content import transcribe_audio
                    result = transcribe_audio(request['path'],settings)
                elif request['kind']=='analysis':
                    from confirmed_analysis import run_confirmed_attempt
                    result = run_confirmed_attempt(request['snapshot'],settings)
                else:
                    raise ValueError('Unsupported operation')
                responses.put(('result',result))
            except Exception:
                responses.put(('error','The speech worker could not complete this operation.'))
            continue
        path, identity, compare_reference = request[:3]
        options = {"output_root": request[3]} if len(request) == 4 else {}
        try:
            result = run_attempt(path, identity, compare_reference=compare_reference,
                                 progress_callback=lambda message: responses.put(('progress', message)), **options)
            responses.put(('result', result))
        except Exception as exc:
            responses.put(('error', f'{type(exc).__name__}: {exc}'))


class AnalysisService:
    def __init__(self, timeout_sec=180, worker_target=_worker):
        self.timeout_sec = timeout_sec
        self.worker_target = worker_target
        self.lock = threading.Lock()
        self.process = None
        self.requests = self.responses = None

    def close(self):
        process = self.process
        if process is not None:
            if process.is_alive():
                if os.name == 'nt':
                    # Only this service's child PID/tree; also stops an MFA child.
                    subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   timeout=10, creationflags=subprocess.CREATE_NO_WINDOW, check=False)
                else:
                    process.terminate()
                process.join(timeout=5)
                if process.is_alive():
                    process.kill()
                    process.join(timeout=5)
            process.close()
        self.process = None
        for channel in (self.requests, self.responses):
            if channel is not None:
                channel.cancel_join_thread()
                channel.close()
        self.requests = self.responses = None

    def _start(self):
        if self.process is not None and self.process.is_alive():
            return
        self.close()
        context = mp.get_context('spawn')
        self.requests, self.responses = context.Queue(maxsize=1), context.Queue()
        self.process = context.Process(target=self.worker_target, args=(self.requests, self.responses), daemon=False)
        self.process.start()

    def run(self, path, identity, *, compare_reference=False, progress_callback=None, output_root=None, operation=None):
        if not self.lock.acquire(blocking=False):
            raise RuntimeError('Another recording is being checked. Please wait and try again.')
        try:
            self._start()
            deadline = time.monotonic() + self.timeout_sec
            self.requests.put(operation if operation is not None else ((path, identity, compare_reference) if output_root is None else (path, identity, compare_reference, str(output_root))))
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self.close()
                    raise TimeoutError('The recording check took too long. The worker was restarted; please try again.')
                try:
                    kind, payload = self.responses.get(timeout=min(0.25, remaining))
                except queue.Empty:
                    if not self.process.is_alive():
                        self.close()
                        raise RuntimeError('The analysis worker stopped. Please try again.')
                    continue
                if kind == 'progress' and progress_callback:
                    try:
                        progress_callback(payload)
                    except Exception:
                        pass
                elif kind == 'result':
                    return payload
                elif kind == 'error':
                    raise RuntimeError(payload)
        finally:
            self.lock.release()


SERVICE = AnalysisService()
atexit.register(SERVICE.close)


def run_attempt(path, identity, *, compare_reference=False, progress_callback=None, output_root=None):
    return SERVICE.run(path, identity, compare_reference=compare_reference, progress_callback=progress_callback, output_root=output_root)
