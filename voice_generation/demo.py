"""Local Day 2 component demo. No production authentication or shared app wiring."""
import argparse
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
from urllib.parse import urlparse, parse_qs

from .generator import TARGET_ACCENT
from .service import DevelopmentStore, GenerationService, AttemptUnavailable, failure
from .worker import ModelWorker

ROOT = Path(__file__).resolve().parents[1]
ASSETS = Path(__file__).with_name("panel")


def create_server(port=8762, backend=None, output_dir=None):
    store = DevelopmentStore()
    fixture = json.loads((ROOT / "contracts/examples/session.json").read_text(encoding="utf-8"))
    auth_context = "local-development-reviewer"
    session = store.create(auth_context, fixture)
    attempt_id = session["attempt_id"]
    token = secrets.token_urlsafe(32)
    service = GenerationService(store, backend or ModelWorker(), output_dir or ROOT / "runs/day2_examples")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def send(self, status, data, content_type="application/json"):
            if isinstance(data, dict):
                data = json.dumps(data).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; media-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def allowed_host(self):
            return self.headers.get("Host") in (f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}")

        def do_GET(self):
            if not self.allowed_host():
                return self.send(403, failure("ATTEMPT_UNAVAILABLE", "This local page is unavailable."))
            url = urlparse(self.path)
            try:
                if url.path in ("/", "/panel.js", "/panel.css"):
                    name = {"/": "index.html", "/panel.js": "panel.js", "/panel.css": "panel.css"}[url.path]
                    mime = {"index.html": "text/html; charset=utf-8", "panel.js": "text/javascript; charset=utf-8", "panel.css": "text/css; charset=utf-8"}[name]
                    return self.send(200, (ASSETS / name).read_bytes(), mime)
                if url.path == "/api/session":
                    return self.send(200, {"ok": True, "session": store.get_attempt(auth_context, attempt_id), "csrf_token": token})
                if url.path == "/api/audio":
                    query = parse_qs(url.query)
                    identity = query.get("audio_id", [""])[0]
                    requested_attempt = query.get("attempt_id", [""])[0]
                    with store.lock:
                        path = service.audio_path(auth_context, requested_attempt, identity)
                        return self.send(200, path.read_bytes(), "audio/wav")
            except (AttemptUnavailable, FileNotFoundError):
                return self.send(404, failure("ATTEMPT_UNAVAILABLE", "This practice session or example is unavailable."))
            return self.send(404, failure("ATTEMPT_UNAVAILABLE", "This page is unavailable."))

        def do_POST(self):
            origin = self.headers.get("Origin")
            allowed_origins = (f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}")
            if not self.allowed_host() or (origin is not None and origin not in allowed_origins) or not secrets.compare_digest(self.headers.get("X-Example-Token", ""), token):
                return self.send(403, failure("ATTEMPT_UNAVAILABLE", "Reload this local page before continuing."))
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 16000:
                    raise ValueError()
                body = json.loads(self.rfile.read(length))
                if body.get("attempt_id") != attempt_id:
                    raise AttemptUnavailable()
                path = urlparse(self.path).path
                if path == "/api/confirm":
                    revision = body.get("expected_revision")
                    if type(revision) is not int:
                        raise ValueError()
                    result = service.confirm_text(auth_context, attempt_id, body.get("text"), body.get("target_accent"), revision)
                elif path == "/api/generate":
                    revision = body.get("input_revision")
                    if type(revision) is not int:
                        raise ValueError()
                    result = service.generate_example(auth_context, attempt_id, revision)
                elif path == "/api/delete":
                    service.delete_attempt(auth_context, attempt_id)
                    result = {"ok": True}
                else:
                    return self.send(404, failure("ATTEMPT_UNAVAILABLE", "This action is unavailable."))
                return self.send(200 if result["ok"] else 409, result)
            except AttemptUnavailable:
                return self.send(404, failure("ATTEMPT_UNAVAILABLE", "This practice session is unavailable."))
            except (ValueError, TypeError, AttributeError):
                return self.send(400, failure("UNSUPPORTED_TEXT", "Check the text and try again."))

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    server.service = service
    server.store = store
    server.auth_context = auth_context
    server.attempt_id = attempt_id
    return server


def main():
    parser = argparse.ArgumentParser(description="Run the localhost-only Hear an example component demo")
    parser.add_argument("--port", type=int, default=8762)
    args = parser.parse_args()
    server = create_server(args.port)
    print(f"Day 2 component demo: http://127.0.0.1:{server.server_port}/", flush=True)
    print("Development session only. First generation loads Kokoro; subsequent requests reuse it.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.service.close()


if __name__ == "__main__":
    main()
