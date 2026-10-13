import argparse
import json

from .generator import generate_audio

parser = argparse.ArgumentParser(description="Generate a labeled local synthetic listening example.")
parser.add_argument("text")
parser.add_argument("--target-accent", default="en-US-general-american")
args = parser.parse_args()
result = generate_audio(args.text, args.target_accent)
print(json.dumps(result, indent=2))
raise SystemExit(0 if result["ok"] else 1)
