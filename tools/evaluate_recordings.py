"""Prepare/run a 36-clip team evaluation. Human labels are never inferred."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline import run_attempt
from pipeline import load_prompts


def validate_splits(records):
    speakers = {}
    ids = set()
    for row in records:
        if not row.get('id') or row['id'] in ids:
            raise ValueError('Missing or duplicate recording ID.')
        ids.add(row['id'])
        speaker, split = row.get('speaker_id'), row.get('split')
        if not speaker or split not in {'development', 'held_out'}:
            raise ValueError('Every recording needs a speaker and development/held_out split.')
        if speaker in speakers and speakers[speaker] != split:
            raise ValueError(f'Speaker {speaker} appears in both development and held-out data.')
        speakers[speaker] = split


def decision_metrics(records):
    """Report abstentions and denominators; never use intended conditions as truth."""
    counts = Counter(reviewed_clear=0, decided=0, correct=0, false_support=0,
                     false_alternative=0, uncertain=0, unreviewed=0, reviewed_unclear=0)
    for row in records:
        label = row.get('human_target_label')
        if not row.get('reviewer') or label not in {'expected', 'altered', 'unclear'}:
            counts['unreviewed'] += 1
            continue
        if label == 'unclear':
            counts['reviewed_unclear'] += 1
            continue
        counts['reviewed_clear'] += 1
        targets = row.get('sequence_assessment', {}).get('targets', [])
        matching = [t for t in targets if t.get('word') == row.get('target_word') and t.get('expected_phone') == row.get('target_phone')]
        state = matching[0].get('status') if len(matching) == 1 else None
        if state not in {'expected_supported', 'alternative_favored'}:
            counts['uncertain'] += 1
            continue
        counts['decided'] += 1
        if (label == 'expected') == (state == 'expected_supported'):
            counts['correct'] += 1
        elif state == 'expected_supported':
            counts['false_support'] += 1
        else:
            counts['false_alternative'] += 1
    return dict(counts, coverage=counts['decided'] / counts['reviewed_clear'] if counts['reviewed_clear'] else None,
                agreement_on_decided=counts['correct'] / counts['decided'] if counts['decided'] else None)

TARGETS = {"think": ("think", "TH", "I sink so"),
           "ship": ("ship", "IH", "The sheep is here"),
           "bad_bed": ("bad", "AE", "That is a bed bed")}


def template():
    records = []
    for speaker in ("S01", "S02", "S03"):
        for prompt, (word, phone, altered) in TARGETS.items():
            for repeat in (1, 2):
                for condition in ("expected", "altered"):
                    records.append(dict(id=f"{speaker}_{prompt}_{repeat}_{condition}", speaker_id=speaker,
                        split="held_out" if speaker == "S03" else "development", prompt_id=prompt,
                        pair_id=f"{speaker}_{prompt}_{repeat}", requested_condition=condition,
                        requested_altered_text=altered if condition == "altered" else None,
                        target_word=word, target_phone=phone, wav=None,
                        consent_confirmed=False, human_target_label=None, reviewer=None))
    return dict(note="Fill WAV paths relative to this manifest. A reviewer must listen and label expected/altered/unclear. Requested conditions are not labels. Reserve S03 before tuning.", records=records)


def summarize(records):
    validate_splits(records)
    groups = {f"{split}/{phone}": decision_metrics([r for r in records if r['split'] == split and r.get('target_phone') == phone])
              for split in ('development', 'held_out') for phone in sorted({r.get('target_phone', '') for r in records})}
    return dict(planned=len(records), analyzed=sum(r.get("result_path") is not None for r in records),
                human_reviewed=sum(r.get("human_target_label") in {"expected", "altered", "unclear"} and bool(r.get("reviewer")) for r in records),
                outcomes=dict(Counter(r["outcome"] for r in records)), records=records,
                pronunciation_accuracy=None,
                per_split_and_sound=groups, reviewed_outcomes=decision_metrics(records),
                content_statuses=dict(Counter(r.get('content_check', {}).get('status', 'not_run') for r in records)),
                limitation="Operational report and exploratory target margins only. No grading threshold or pronunciation accuracy has been validated.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/evaluation/manifest.json")
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--run", action="store_true", help="Run real CPU alignment/scoring for provided, consented clips")
    parser.add_argument("--reuse-results", action="store_true", help="Summarize previously saved result_path entries without rerunning models")
    args = parser.parse_args()
    manifest = args.manifest.resolve()
    if args.init:
        manifest.parent.mkdir(parents=True, exist_ok=True)
        with manifest.open("x", encoding="utf-8") as stream:  # Never overwrite labels.
            json.dump(template(), stream, indent=2)
        print(f"Created {manifest}")
        return
    source = json.loads(manifest.read_text(encoding="utf-8"))["records"]
    validate_splits(source)
    prompts = {p['id']: p for p in load_prompts()}
    records = []
    for entry in source:
        row = dict(entry, outcome="missing_recording", result_path=None)
        records.append(row)
        if args.reuse_results and entry.get('result_path'):
            result = json.loads((manifest.parent / entry['result_path']).read_text(encoding='utf-8'))
            if result.get('prompt_id') != entry['prompt_id']:
                raise ValueError('Saved result has a different prompt.')
            row.update(outcome=result['overall_status'], result_path=entry['result_path'],
                       content_check=result.get('spoken_words_verification', {}), sequence_assessment=result.get('target_assessment', {}))
            continue
        if not entry.get("wav"):
            continue
        path = (manifest.parent / entry["wav"]).resolve()
        if not path.is_file():
            continue
        if entry.get("consent_confirmed") is not True:
            row["outcome"] = "consent_not_confirmed"
            continue
        if entry.get("prompt_id") not in prompts:
            row["outcome"] = "unknown_prompt"
            continue
        row["outcome"] = "ready_to_run"
        if not args.run:
            continue
        result = run_attempt(str(path), entry["prompt_id"])
        row.update(outcome=result["overall_status"], result_path=result["results_path"], target_evidence=[])
        row["content_check"] = result.get("spoken_words_verification", {})
        row["sequence_assessment"] = result.get("target_assessment", {})
        word, phone = entry['target_word'], entry['target_phone']
        for segment in result["phoneme_results"].get("segments", []):
            if segment.get("word", "").lower() == word and segment.get("canonical_phone") == phone:
                row["target_evidence"].append({key: segment.get(key) for key in
                    ("segment_id", "word", "canonical_phone", "expected_vs_alternative_nats", "status", "reason")})
        print(f"{entry['id']}: {row['outcome']}", flush=True)
    report = summarize(records)
    destination = ROOT / "runs/team_evaluation.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "records"}, indent=2))
    print(f"Report: {destination}")


if __name__ == "__main__":
    main()
