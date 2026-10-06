"""SpeechOcean aggregated annotations. Human ratings never enter inference."""
import json
import math
from pathlib import Path
import re


def _mapping(path):
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        key, value = line.split(maxsplit=1)
        if key in result:
            raise ValueError(f"Duplicate ID {key} in {path}")
        result[key] = value.strip()
    return result


def phones(value):
    result = value.split() if isinstance(value, str) else value
    if not isinstance(result, list) or not all(isinstance(x, str) for x in result):
        raise ValueError("Expected a phone string or list of strings")
    return result


def base_phone(value):
    return re.sub(r"[012]$", "", re.sub(r"_(B|E|I|S)$", "", value.strip())).upper()


def normalized_word(value):
    return re.sub(r"[^A-Z0-9']", "", value.upper().replace("’", "'"))


def _rating(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 2:
        raise ValueError("Invalid human phone rating (expected 0..2)")
    return float(value)


def load_records(root, split="train", scores_file="resource/scores.json"):
    """Return official split records. wav.scp is parsed as data, never executed."""
    if split not in {"train", "test"}:
        raise ValueError("split must be train or test")
    root = Path(root).expanduser().resolve()
    labels = json.loads((root / scores_file).read_text(encoding="utf-8"))
    texts = _mapping(root / split / "text")
    speakers = _mapping(root / split / "utt2spk")
    wavs = _mapping(root / split / "wav.scp")
    if set(texts) != set(speakers) or set(texts) != set(wavs):
        raise ValueError("Split metadata IDs do not agree")
    records = []
    for uid, transcript in texts.items():
        annotation = labels[uid]
        if [normalized_word(w) for w in transcript.split()] != [normalized_word(w["text"]) for w in annotation["words"]]:
            raise ValueError(f"Transcript/annotation word mismatch: {uid}")
        wav_value = wavs[uid]
        if "|" in wav_value:
            raise ValueError("wav.scp commands are unsupported; supply local WAV paths")
        wav_value = wav_value.replace("\\", "/")
        # Official scp paths can include a machine-specific prefix before WAVE/.
        pos = wav_value.upper().find("WAVE/")
        wav_path = root / wav_value[pos:] if pos >= 0 else root / wav_value
        words = []
        for wi, word in enumerate(annotation["words"]):
            ps = phones(word["phones"])
            ratings = [_rating(v) for v in word["phones-accuracy"]]
            if len(ps) != len(ratings):
                raise ValueError(f"Phone/rating count mismatch: {uid}, word {wi}")
            words.append({**word, "phones": ps, "phones-accuracy": ratings, "word_index": wi})
        records.append({"utterance_id": uid, "speaker_id": speakers[uid], "split": split,
                        "wav": str(wav_path), "text": transcript, "words": words,
                        "sentence_ratings": {k: annotation.get(k) for k in
                            ("accuracy", "fluency", "prosodic", "completeness", "total")}})
    return records


def attach_word_indices(segments, word_entries):
    """Add word IDs only where a phone fits in exactly one MFA word interval."""
    words = [{"word_index": i, "text": label, "start_sec": start, "end_sec": end}
             for i, (start, end, label) in enumerate(
                 (w for w in word_entries if w[2].strip() and w[2].lower() not in {"sil", "sp", "<eps>"}))]
    counts = {}
    for segment in segments:
        segment.update(word_index=None, phone_index_in_word=None)
        if segment["canonical_phone"].lower() in {"", "sil", "sp", "<eps>"}:
            continue
        matches = [w for w in words if w["start_sec"] - 1e-5 <= segment["start_sec"]
                   and segment["end_sec"] <= w["end_sec"] + 1e-5]
        if len(matches) == 1:
            wi = matches[0]["word_index"]
            segment.update(word_index=wi, phone_index_in_word=counts.get(wi, 0))
            counts[wi] = counts.get(wi, 0) + 1
    return words


def match_ratings(record, alignment, evidence):
    """Conservative join: exact word order and phone bases, otherwise abstain.

    Word-level sequence mismatch excludes that word rather than shifting labels.
    Phone stress is retained in human_phone; no stress score is inferred here.
    """
    aligned_words = alignment.get("words", [])
    word_order_ok = [normalized_word(w["text"]) for w in aligned_words] == [normalized_word(w["text"]) for w in record["words"]]
    scored = {s["segment_id"]: s for s in evidence.get("segments", [])}
    output = []
    for wi, word in enumerate(record["words"]):
        segments = [s for s in alignment.get("segments", []) if s.get("word_index") == wi]
        segments.sort(key=lambda s: s["start_sec"])
        sequence_ok = word_order_ok and [base_phone(s["canonical_phone"]) for s in segments] == [base_phone(p) for p in word["phones"]]
        for pi, (phone, rating) in enumerate(zip(word["phones"], word["phones-accuracy"])):
            row = {"utterance_id": record["utterance_id"], "speaker_id": record["speaker_id"],
                   "split": record["split"], "word_index": wi, "phone_index_in_word": pi,
                   "word": word["text"], "human_phone": phone, "human_rating": rating,
                   "match_status": "matched" if sequence_ok else "word_or_phone_sequence_mismatch"}
            if sequence_ok:
                segment = segments[pi]
                row["evidence"] = {**segment, **scored.get(segment["segment_id"], {})}
            output.append(row)
    return output
