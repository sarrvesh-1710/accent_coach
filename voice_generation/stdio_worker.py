"""Private JSON-lines transport. Run only in the isolated generation environment."""
import base64
import contextlib
import json
from pathlib import Path
import sys
import tempfile

from .generator import TARGET_ACCENT, _failure

def main():
    generator = None
    for line in sys.stdin.buffer:
        try:
            request = json.loads(line)
            # Text/accent come from authorized snapshots. work_root is a private
            # server-created job directory, never a browser-supplied path.
            text, accent = request["text"], request["target_accent"]
            if not isinstance(text, str) or not text.strip() or len(text) > 200:
                raise ValueError("Unsupported text")
            if accent != TARGET_ACCENT:
                raise ValueError("Unsupported accent")
            with tempfile.TemporaryDirectory(dir=request["work_root"], prefix="generated-") as folder:
                with contextlib.redirect_stdout(sys.stderr):
                    if generator is None:
                        from .kokoro_backend import KokoroGenerator
                        generator = KokoroGenerator()
                    result = generator.generate_audio(text, accent, output_dir=folder)
                response = {"result": result}
                if result.get("ok"):
                    data = (Path(folder) / (result["generated_audio_id"] + ".wav")).read_bytes()
                    if len(data) > 2_000_000:
                        raise ValueError("Generated output is too large")
                    response["audio_base64"] = base64.b64encode(data).decode("ascii")
            print(json.dumps(response), flush=True)
        except Exception:
            # Keep transport and model failures out of public diagnostic messages.
            print(json.dumps({"result": _failure("MODEL_UNAVAILABLE", "Kokoro could not generate the example. Check the isolated model setup and retry.", True)}), flush=True)


if __name__ == "__main__":
    main()
