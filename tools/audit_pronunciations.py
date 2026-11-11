"""Check dictionary coverage and exact tokenizer labels; not phonetic validation."""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline import load_prompts
from phoneme_scoring.align_audio import config_path, load_settings, split_phone
from phoneme_scoring.gop_score import _mapping, _resolve


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dictionary", type=Path, required=True)
    args = parser.parse_args()
    from transformers import Wav2Vec2PhonemeCTCTokenizer
    settings = load_settings(ROOT / "phoneme_scoring/settings.json")
    cfg = settings["model"]
    cache = str(config_path(cfg["cache_dir"], settings)) if cfg.get("cache_dir") else None
    tokenizer = Wav2Vec2PhonemeCTCTokenizer.from_pretrained(
        cfg["id"], revision=cfg["revision"], cache_dir=cache, local_files_only=True,
        do_phonemize=False, trust_remote_code=False)
    vocab, specials = tokenizer.get_vocab(), set(tokenizer.all_special_ids)
    mapping = _mapping(settings)
    requested = {word.lower() for p in load_prompts() for word in re.findall(r"[A-Za-z']+", p["text"])}
    entries = {word: [] for word in sorted(requested)}
    for line in args.dictionary.read_text(encoding="utf-8-sig").splitlines():
        fields = line.split()
        if not fields or fields[0].lower() not in requested:
            continue
        phones = []
        for item in fields[1:]:
            try:
                float(item)  # MFA probability columns
            except ValueError:
                phones.append(item)
        resolved = []
        for phone in phones:
            base, stress = split_phone(phone)
            label, reason = _resolve(dict(canonical_phone=base, original_phone=phone, stress=stress), mapping)
            supported = label in vocab and vocab.get(label) not in specials
            resolved.append(dict(phone=phone, label=label, supported=supported, reason=reason))
        entries[fields[0].lower()].append(resolved)
    labels = set(mapping["phones"].values()) | set(mapping["stress_overrides"].values())
    missing = sorted(label for label in labels if label not in vocab or vocab[label] in specials)
    report = dict(model_id=cfg["id"], model_revision=cfg["revision"], dictionary=str(args.dictionary),
                  map_label_count=len(labels), missing_map_labels=missing,
                  missing_words=[w for w, v in entries.items() if not v], words=entries,
                  limitation="Coverage only. Dictionary variants, allophones, and pronunciation judgments require human review.")
    destination = ROOT / "runs/pronunciation_audit.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "words"}, indent=2))
    print(f"Details: {destination}")
    return int(bool(missing or report["missing_words"] or any(not p["supported"] for variants in entries.values() for v in variants for p in v)))


if __name__ == "__main__":
    raise SystemExit(main())
