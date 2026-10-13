import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

from voice_generation.demo import create_server
from voice_generation.worker import ModelWorker

ROOT = Path(__file__).resolve().parents[1]


class ExampleHTTPTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "runs").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "runs")
        self.server = create_server(port=0, backend=object(), output_dir=self.temp.name)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        with urllib.request.urlopen(self.url + "/api/session") as response:
            self.session = json.load(response)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.server.service.close()
        self.thread.join()
        self.temp.cleanup()

    def test_mutation_requires_token_and_same_origin(self):
        data = json.dumps({"attempt_id": self.session["session"]["attempt_id"]}).encode()
        for headers in ({}, {"X-Example-Token": self.session["csrf_token"], "Origin": "https://outside.example"}):
            request = urllib.request.Request(self.url + "/api/delete", data=data, headers=headers)
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(request)
            self.assertEqual(caught.exception.code, 403)
        self.assertTrue(self.server.store.get_attempt(self.server.auth_context, self.server.attempt_id))

    def test_playback_rejects_unknown_assets_and_paths(self):
        for audio_id in ("synthetic-" + "0" * 32, "../../secret"):
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(self.url + f"/api/audio?attempt_id={self.server.attempt_id}&audio_id={audio_id}")
            self.assertEqual(caught.exception.code, 404)

    def test_component_assets_served_with_restricted_policy(self):
        with urllib.request.urlopen(self.url + "/") as response:
            self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
            self.assertIn(b"Synthetic example", response.read())
        for name in ("panel.js", "panel.css"):
            with urllib.request.urlopen(self.url + "/" + name) as response:
                self.assertTrue(response.read())


class FakeProcess:
    def __init__(self):
        self.alive = True
    def is_alive(self): return self.alive
    def terminate(self): self.alive = False
    def join(self, timeout=None): pass
    def close(self): pass


class WorkerTimeoutTests(unittest.TestCase):
    def test_timeout_kills_worker_and_cleans_only_its_new_files(self):
        (ROOT / "runs").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "runs") as folder:
            root = Path(folder)
            existing = root / ("synthetic-" + "1" * 32 + ".wav")
            new = root / ("synthetic-" + "2" * 32 + ".wav")
            existing.write_bytes(b"retained")
            class Pipe:
                def send(self, value): pass
                def poll(self, timeout):
                    new.write_bytes(b"incomplete")
                    return False
                def close(self): pass
            worker = ModelWorker(timeout_seconds=0)
            process = FakeProcess()
            worker.process, worker.pipe = process, Pipe()
            result = worker.generate_audio("Hi", "en-US-general-american", output_dir=root)
            self.assertEqual(result["error"]["code"], "TIMEOUT")
            self.assertFalse(process.alive)
            self.assertIsNone(worker.process)
            self.assertTrue(existing.exists())
            self.assertFalse(new.exists())


if __name__ == "__main__":
    unittest.main()
