import argparse
import json

from .generator import generate_audio, _failure

parser = argparse.ArgumentParser(description="Generate a labeled local synthetic listening example.")
parser.add_argument("text")
parser.add_argument("--target-accent", default="en-US-general-american")
parser.add_argument("--backend", choices=["zira", "kokoro"], default="zira")
args = parser.parse_args()
if args.backend == "kokoro":
    try:
        from .kokoro_backend import KokoroGenerator
        generator = KokoroGenerator()
        result = generator.generate_audio(args.text, args.target_accent)
    except (ImportError, OSError, RuntimeError, ValueError):
        result = _failure("MODEL_UNAVAILABLE", "Kokoro is unavailable. Complete the isolated installation and model setup first.", True)
else:
    result = generate_audio(args.text, args.target_accent)
print(json.dumps(result, indent=2))
raise SystemExit(0 if result["ok"] else 1)
