"""Verify shared fixture integrity and WAV format without speech-model inference."""
import hashlib
import json
from pathlib import Path
import wave

ROOT = Path(__file__).resolve().parents[1]

def main():
    manifest = json.loads((ROOT / "tests/fixtures/team/manifest.json").read_text(encoding="utf-8"))
    for case in manifest["cases"]:
        path = (ROOT / case["path"]).resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError("Fixture path escapes repository")
        if hashlib.sha256(path.read_bytes()).hexdigest() != case["sha256"]:
            raise ValueError(f"Hash mismatch: {case['id']}")
        with wave.open(str(path), "rb") as audio:
            if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, 16000):
                raise ValueError(f"Unexpected WAV format: {case['id']}")
            if not 0 < audio.getnframes() / audio.getframerate() <= 5:
                raise ValueError(f"Unexpected duration: {case['id']}")
        print(f"OK {case['id']}")
    print("Integrity verified; pronunciation accuracy was not evaluated.")

if __name__ == "__main__":
    main()
