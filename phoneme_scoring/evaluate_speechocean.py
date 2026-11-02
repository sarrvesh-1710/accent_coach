"""Batch inference with separate human-label joining and explicit coverage."""
import argparse
from collections import Counter
import json
from pathlib import Path

from accent_profiles import apply_profile
from .align_audio import align_audio, load_settings
from .gop_score import score_phonemes
from .speechocean_data import load_records, match_ratings
from .calibration import apply_calibration, feature_values, metrics, signature

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, help="Local SpeechOcean repository containing WAVE, train, test, resource")
    parser.add_argument("--split", choices=["train", "test"], default="train")
    parser.add_argument("--settings", type=Path, default=ROOT / "phoneme_scoring/settings.json")
    parser.add_argument("--output", type=Path, required=True, help="New run directory; existing directory is rejected")
    parser.add_argument("--limit", type=int, help="Smoke test only; omitted processes the full split")
    args = parser.parse_args()
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be positive")
    settings = apply_profile(load_settings(args.settings), "chinese")
    cfg = settings["accent_profile"]["dataset"]
    settings["max_duration_sec"] = cfg["evaluation_max_duration_sec"]
    records = load_records(args.root or ROOT / cfg["root"], args.split, cfg["scores_file"])
    selected = records[:args.limit] if args.limit else records
    args.output.mkdir(parents=True, exist_ok=False)
    sig = signature(settings)
    counts, failures, ys, ps = Counter(), [], [], []
    report = {"dataset": "speechocean762", "split": args.split, "signature": sig,
              "official_split_utterances": len(records), "selected_utterances": len(selected),
              "smoke_test": args.limit is not None, "counts": counts, "failures": failures,
              "matching_policy": "Exact word sequence and exact within-word base-phone sequence; mismatched words excluded"}
    def save_report():
        report["rating_metrics"] = metrics(ys, ps)
        report["usable_phone_fraction"] = counts["usable_for_calibration"] / counts["human_phones"] if counts["human_phones"] else 0.
        (args.output / "summary.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    with (args.output / "phone_rows.jsonl").open("w", encoding="utf-8") as output:
        for index, record in enumerate(selected):
            counts["processed_utterances"] += 1
            counts["human_phones"] += sum(len(w["phones"]) for w in record["words"])
            alignment, evidence = {}, {}
            try:
                # Only WAV and reference text are passed to inference, never ratings.
                alignment = align_audio(record["wav"], record["text"], settings, str(args.output / "alignment"))
                if alignment.get("status") != "available":
                    raise ValueError(alignment.get("reason", "Alignment unavailable"))
                evidence = score_phonemes(record["wav"], alignment, settings)
                if evidence.get("status") != "available":
                    raise ValueError(evidence.get("reason", "Scoring unavailable"))
                apply_calibration(evidence, settings, ROOT)
            except Exception as exc:
                failures.append({"utterance_id": record["utterance_id"], "reason": str(exc)})
                counts["failed_utterances"] += 1
            for row in match_ratings(record, alignment, evidence):
                row["signature"] = sig
                counts[row["match_status"]] += 1
                ev = row.get("evidence", {})
                counts["status_" + ev.get("status", "unavailable")] += 1
                counts["usable_for_calibration"] += int(feature_values(ev) is not None)
                estimate = ev.get("predicted_phone_rating")
                if estimate is not None:
                    ys.append(row["human_rating"]); ps.append(estimate)
                output.write(json.dumps(row, allow_nan=False)+"\n")
            output.flush()
            save_report()
            print(f"{index+1}/{len(selected)}: {record['utterance_id']}", flush=True)
    save_report()
    print(f"Report: {args.output / 'summary.json'}")


if __name__ == "__main__":
    main()
