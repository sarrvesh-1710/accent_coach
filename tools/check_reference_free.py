"""Local real-model smoke check. Uses existing recordings, not labeled evaluation."""
import argparse
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pipeline


def operational_pass(result):
    stages = result["stage_statuses"]
    evidence = result["phoneme_results"]
    # A completed model run may honestly report uncertain pronunciation evidence.
    return (stages["alignment"]["status"] == "available"
            and evidence.get("status") in {"available", "uncertain"}
            and bool(evidence.get("timing")) and bool(evidence.get("model_revision"))
            and bool(evidence.get("segments"))
            and stages["learner_dsp"]["status"] in {"ok", "warning"}
            and stages["save"]["status"] == "ok"
            and all(stages[s]["status"] == "skipped" for s in ("reference_audio", "reference_dsp", "comparison"))
            and result["audio_paths"]["reference"] is None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-saved", action="store_true", help="Recheck saved real-run outputs without repeating inference")
    args = parser.parse_args()
    destination = ROOT / "runs" / "reference_free_smoke.json"
    if args.verify_saved:
        checks = json.loads(destination.read_text(encoding="utf-8"))
        for row in checks:
            if not row.get("results_path"):
                continue
            result = json.loads(Path(row["results_path"]).read_text(encoding="utf-8"))
            row["outcome"] = "pass" if operational_pass(result) else "fail"
            row["verification"] = "Saved real-model output checked; limited evidence is not an operational failure."
            print(f"{row['prompt_id']}: {row['outcome']} ({row['seconds']} seconds)")
        destination.write_text(json.dumps(checks, indent=2), encoding="utf-8")
        return 0 if len(checks) == 3 and all(c["outcome"] == "pass" for c in checks) else 1
    prompts = pipeline.load_prompts()
    # Remove all reference paths in memory, without changing or deleting assets.
    no_references = [{k: v for k, v in p.items() if k != "reference_wav"} for p in prompts]
    checks = []
    for p in prompts:
        source = ROOT / "data" / "references" / (p["id"] + ".wav")
        if not source.is_file():
            checks.append({"prompt_id": p["id"], "outcome": "not_run", "reason": "Local smoke recording missing"})
            continue
        start = time.monotonic()
        with patch.object(pipeline, "load_prompts", return_value=no_references):
            result = pipeline.run_attempt(str(source), p["id"])
        stages = result["stage_statuses"]
        operational = operational_pass(result)
        row = {"prompt_id": p["id"], "outcome": "pass" if operational else "fail",
               "seconds": round(time.monotonic() - start, 2), "overall_status": result["overall_status"],
               "results_path": result["results_path"], "stages": stages,
               "aligned_words": [w["word"] for w in result["alignment"].get("words", [])],
               "note": "Existing example used only as learner input. No reference comparison or accuracy test."}
        checks.append(row)
        print(json.dumps(row), flush=True)
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(checks, indent=2), encoding="utf-8")
    return 0 if len(checks) == 3 and all(c["outcome"] == "pass" for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
