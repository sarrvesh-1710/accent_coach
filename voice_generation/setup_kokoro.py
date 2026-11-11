"""Explicit model download; never part of a timed synthesis call."""
import hashlib
import json
from pathlib import Path
import time
import shutil
import urllib.request

ROOT = Path(__file__).resolve().parents[1] / "models" / "kokoro"


def main():
    started = time.perf_counter()
    repo = "hexgrad/Kokoro-82M"
    manifest_path = ROOT / "manifest.json"
    if manifest_path.exists():
        revision = json.loads(manifest_path.read_text(encoding="utf-8"))["revision"]
    else:
        with urllib.request.urlopen("https://huggingface.co/api/models/" + repo, timeout=90) as response:
            revision = json.load(response)["sha"]
    ROOT.mkdir(parents=True, exist_ok=True)
    files = ["config.json", "kokoro-v1_0.pth", "voices/af_heart.pt"]
    for name in files:
        destination = ROOT / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".download")
        try:
            with urllib.request.urlopen(f"https://huggingface.co/{repo}/resolve/{revision}/{name}", timeout=90) as response, temporary.open("wb") as output:
                shutil.copyfileobj(response, output, length=1024 * 1024)
            temporary.replace(destination)
            print("Downloaded", name, flush=True)
        finally:
            temporary.unlink(missing_ok=True)
    manifest = {"repo_id": repo, "revision": revision, "voice": "af_heart",
                "download_seconds": round(time.perf_counter() - started, 3),
                "sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files}}
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
