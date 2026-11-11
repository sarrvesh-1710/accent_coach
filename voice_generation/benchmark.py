"""Generate the three Day 1 examples, plus a local listening-review page."""

import html
import json
import platform

from .generator import DEFAULT_OUTPUT, generate_audio

EXAMPLES = [
    ("short", "I think so."),
    ("longer", "After class, I will walk to the library and practice speaking clearly with my friends."),
    ("practice_sounds", "I think the ship is here beside that bad bed."),
]


def main():
    examples = []
    for label, text in EXAMPLES:
        result = generate_audio(text)
        examples.append({"example": label, **result})
        print(label, result["status"], result.get("timings_ms", {}))
    DEFAULT_OUTPUT.mkdir(parents=True, exist_ok=True)
    report = {"platform": platform.platform(), "python": platform.python_version(),
              "timing_conditions": "Separate desktop-voice process per call; includes process startup. Not neural-model cold/warm timings.",
              "examples": examples}
    (DEFAULT_OUTPUT / "day1_results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    cards = []
    for item in examples:
        if item["ok"]:
            cards.append(f'<section><h2>{html.escape(item["example"].replace("_", " "))}</h2>'
                         f'<p>{html.escape(item["text"])}</p><p>Synthetic example · American English · Microsoft desktop voice</p>'
                         f'<audio controls src="{item["generated_audio_id"]}.wav"></audio>'
                         '<p>Listen for missing or changed words and TH, IH, AE. Record your review in the JSON sidecar.</p></section>')
    page = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Day 1 listening review</title>'
    page += '<style>body{font:18px system-ui;max-width:760px;margin:40px auto;padding:20px;color:#183c40}section{padding:20px;border:1px solid #ccc;border-radius:12px;margin:20px 0}audio{width:100%}</style>'
    page += '<h1>Day 1 listening review</h1><p>These are synthetic examples. Word matching and pronunciation review are pending.</p>'
    page += ''.join(cards) + '</html>'
    (DEFAULT_OUTPUT / "listen.html").write_text(page, encoding="utf-8")
    return 0 if all(item["ok"] for item in examples) else 1


if __name__ == "__main__":
    raise SystemExit(main())
