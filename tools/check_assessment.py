"""Real local smoke checks; no human pronunciation labels or accuracy claims."""
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pipeline


def main():
    prompts = [{k: v for k, v in p.items() if k != "reference_wav"} for p in pipeline.load_prompts()]
    cases = [(p["id"], ROOT / "data/references" / (p["id"] + ".wav"), p["id"]) for p in prompts]
    partner = ROOT / "runs/20260929T143731_68aed8db2fee/learner.wav"
    if partner.exists():
        cases.append(("partner_think", partner, "think"))
    cases.append(("wrong_sentence", ROOT / "data/references/think.wav", "ship"))
    silent = ROOT / "runs/assessment_silence.wav"
    sf.write(silent, np.zeros(16000), 16000)
    cases.append(("silence", silent, "think"))
    checks = []
    destination = ROOT / "runs/assessment_smoke.json"
    for label, path, prompt_id in cases:
        if not path.is_file():
            checks.append(dict(case=label, outcome="not_run", reason="Recording missing"))
            continue
        start = time.monotonic()
        with patch.object(pipeline, "load_prompts", return_value=prompts):
            result = pipeline.run_attempt(str(path), prompt_id)
        content = result["spoken_words_verification"]
        targets = result["target_assessment"]["targets"]
        if label == "silence":
            success = result["overall_status"] == "failed" and result["stage_statuses"]["alignment"]["status"] == "skipped"
        elif label == "wrong_sentence" or content["status"] == "mismatch":
            success = content["status"] == "mismatch" and result["stage_statuses"]["alignment"]["status"] == "skipped" and all(
                t["status"] == "insufficient_evidence" for t in targets)
        else:
            success = (content["status"] in {"match", "target_variant"}
                       and result["alignment"].get("status") == "available"
                       and result["phoneme_results"].get("sequence_evidence", {}).get("status") == "available")
        success = success and result["pronunciation_grade"]["value"] is None and result["audio_paths"]["reference"] is None
        check = dict(case=label, outcome="pass" if success else "fail", seconds=round(time.monotonic()-start,2),
                     overall_status=result["overall_status"], content_check=content,
                     target_assessment=result["target_assessment"], results_path=result["results_path"],
                     note="Operational outcome only. Input correctness was not human labeled.")
        checks.append(check)
        destination.write_text(json.dumps(checks,indent=2),encoding="utf-8")
        print(json.dumps(check),flush=True)
    return int(any(r["outcome"] != "pass" for r in checks))


if __name__ == "__main__":
    raise SystemExit(main())
