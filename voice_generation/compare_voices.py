"""Fresh model process per sentence: one cold call and three warm repeats."""
import argparse
from datetime import datetime, timezone
import html
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import uuid

from .benchmark import EXAMPLES
from .generator import DEFAULT_OUTPUT

OUTPUT = DEFAULT_OUTPUT.parent / "kokoro_examples"


def write_review(report, baseline):
    cards = []
    for label, text in EXAMPLES:
        rows = [x for x in report["runs"] if x["example"] == label and x["ok"]]
        if not rows:
            continue
        sample = next((x for x in rows if x["condition"] == "warm"), rows[0])
        old = next((x for x in baseline.get("examples", []) if x["example"] == label and x["ok"]), None)
        old_player = f'<p>Microsoft Zira baseline</p><audio controls src="../synthetic_examples/{old["generated_audio_id"]}.wav"></audio>' if old else ''
        cold = next((x for x in rows if x["condition"] == "cold"), None)
        warm = [x["timings_ms"]["request"] for x in rows if x["condition"] == "warm"]
        timing = f'Warm median: {statistics.median(warm)/1000:.3f} s ({len(warm)} runs).' if warm else ''
        if cold:
            timing += f' Cold total: {cold["timings_ms"]["total"]/1000:.3f} s, including model load.'
        cards.append(f'''<section data-example="{label}" data-audio-id="{sample['generated_audio_id']}"><h2>{html.escape(label.replace('_',' '))}</h2>
<p>{html.escape(text)}</p><p>Kokoro af_heart · Synthetic American English example</p>
<audio controls src="{sample['generated_audio_id']}.wav"></audio>{old_player}<p>{timing}</p>
<label>Are all words correct? <select name="words_match"><option value="">Choose</option><option>yes</option><option>no</option><option>unsure</option></select></label>
<label>Naturalness <select name="naturalness_1_to_5"><option value="">Choose</option><option value="1">1 — very robotic</option><option value="2">2 — mostly robotic</option><option value="3">3 — mixed</option><option value="4">4 — mostly natural</option><option value="5">5 — very natural</option></select></label>
<label>General American suitability <select name="accent_suitability"><option value="">Choose</option><option>sounds suitable</option><option>unsure</option><option>needs improvement</option></select></label>
<label>Notes: missing/changed words, think (TH), ship (IH), bad (AE), stress, pauses, glitches<textarea name="pronunciation_notes" rows="3"></textarea></label></section>''')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Kokoro listening review</title>
<style>body{font:17px system-ui;color:#183c40;max-width:850px;margin:30px auto;padding:18px}section{border-top:1px solid #ccc;padding:24px 0}audio,textarea{width:100%}label{display:block;margin:14px 0}select,input,textarea,button{font:inherit;padding:7px}button{cursor:pointer}</style>
<h1>Kokoro listening review</h1><p>Compare each synthetic clip with Zira. Timing is measured automatically; you only record what you hear.</p>
<p>Cold = first call in a fresh model process, including imports/model load. Warm = model already loaded. Downloads are excluded.</p>
<label>Reviewer name <input id="reviewer"></label>'''
    page += ''.join(cards)
    page += '''<button id="export">Download my review</button><p id="message">Download your review when finished; it is not automatically saved to the repository.</p>
<script>document.getElementById('export').onclick=()=>{const reviews=[...document.querySelectorAll('section')].map(s=>({example:s.dataset.example,generated_audio_id:s.dataset.audioId,...Object.fromEntries([...s.querySelectorAll('[name]')].map(e=>[e.name,e.value]))}));const data={benchmark_id:BENCHMARK_ID,reviewer:document.getElementById('reviewer').value,reviewed_at:new Date().toISOString(),reviews};const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));a.download='kokoro-listening-review.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);document.getElementById('message').textContent='Review downloaded. Keep it beside comparison_results.json.'};</script></html>'''
    page = page.replace("BENCHMARK_ID", json.dumps(report["benchmark_id"]))
    (OUTPUT / "listen.html").write_text(page, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", choices=[label for label, _ in EXAMPLES])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--resume", action="store_true", help="Reuse complete saved sentence trials after an interruption")
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("At least one warm repeat is required")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if args.worker:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        from .kokoro_backend import KokoroGenerator
        generator = KokoroGenerator()
        text = dict(EXAMPLES)[args.worker]
        runs = []
        for repeat in range(args.repeats + 1):
            result = generator.generate_audio(text)
            runs.append({"example": args.worker, "repeat": repeat, **result})
            print(args.worker, repeat, result["status"], result.get("timings_ms"), flush=True)
        (OUTPUT / (args.worker + "_runs.json")).write_text(json.dumps(runs, indent=2), encoding="utf-8")
        return 0 if all(x["ok"] for x in runs) else 1
    runs = []
    for label, _ in EXAMPLES:
        saved_path = OUTPUT / (label + "_runs.json")
        if args.resume and saved_path.exists():
            saved = json.loads(saved_path.read_text(encoding="utf-8"))
            manifest = json.loads((Path(__file__).resolve().parents[1] / "models/kokoro/manifest.json").read_text(encoding="utf-8"))
            if (len(saved) == args.repeats + 1 and all(x["ok"] and x["text"] == dict(EXAMPLES)[label]
                and x.get("model_revision") == manifest["revision"]
                and (OUTPUT / (x["generated_audio_id"] + ".wav")).exists() for x in saved)):
                runs.extend(saved)
                print("Reusing saved trials:", label, flush=True)
                continue
        completed = subprocess.run([sys.executable, "-m", "voice_generation.compare_voices",
                                    "--worker", label, "--repeats", str(args.repeats)], check=False, timeout=180)
        if completed.returncode != 0:
            return completed.returncode
        runs.extend(json.loads((OUTPUT / (label + "_runs.json")).read_text(encoding="utf-8")))
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.SubprocessError):
        commit = None
    report = {"benchmark_id": uuid.uuid4().hex, "recorded_at": datetime.now(timezone.utc).isoformat(), "git_commit": commit,
              "uncommitted_benchmark_changes": True,
              "resumed_from_saved_trials": args.resume,
              "python": platform.python_version(),
              "hardware": {"os": platform.platform(), "cpu": platform.processor(),
                           "logical_cpu_count": os.cpu_count(), "device": "cpu", "torch_threads": 4},
              "versions": {name: importlib.metadata.version(name) for name in
                           ["kokoro", "torch", "transformers", "misaki", "soundfile", "spacy"]},
              "timing_method": "perf_counter; one cold and repeated warm calls per sentence; fresh process per sentence; no downloads in timed calls; cold total includes Python imports/model/voice initialization but excludes interpreter launch; warm request includes phonemization, synthesis and WAV write/validation; sidecar write excluded.",
              "baseline_review": "User reported the three Zira clips sounded correct but robotic; numeric naturalness and accent suitability were not rated.",
              "runs": runs}
    hardware_file = OUTPUT / "hardware.json"
    if hardware_file.exists():
        report["hardware"].update(json.loads(hardware_file.read_text(encoding="utf-8-sig")))
    (OUTPUT / "comparison_results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (OUTPUT / ("comparison_" + report["benchmark_id"] + ".json")).write_text(json.dumps(report, indent=2), encoding="utf-8")
    baseline = json.loads((DEFAULT_OUTPUT / "day1_results.json").read_text(encoding="utf-8")) if (DEFAULT_OUTPUT / "day1_results.json").exists() else {}
    write_review(report, baseline)
    for label, _ in EXAMPLES:
        warm = [x["timings_ms"]["request"] for x in runs if x["example"] == label and x["condition"] == "warm"]
        print(label, "warm median ms:", round(statistics.median(warm), 2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
