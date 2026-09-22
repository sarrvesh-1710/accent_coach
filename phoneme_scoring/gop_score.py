"""Preliminary CTC segment evidence, NOT a calibrated GOP/error classifier.

Install in an MFA conda environment (Python 3.11 recommended):
  python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
  python -m pip install 'transformers>=4.40,<5' numpy scipy phonemizer
  mfa model download dictionary english_us_arpa
  mfa model download acoustic english_us_arpa
The processor may also require the eSpeak-NG system package.

Commands (run from the directory containing these four files):
  python gop_score.py --self-test
  python gop_score.py --audio test.wav --transcript 'Think about the sheep.'
  python gop_score.py --select-l2 --count 30
  python gop_score.py --check-l2 --start 0 --limit 5
  python gop_score.py --check-l2 --start 5 --limit 25

Edit l2_arctic_root before selection. No corpus access form is submitted for you.
--select-l2 fills settings.json using actual short annotated WAVs, preferring
TH/IH/IY/AE/EH coverage. It does not train, align, or infer. Check runs process
one recording at a time, use FRESH MFA output, and flush results after each clip.
Human annotations are never passed into alignment or model inference.

Score on evidence frames E:
  mean_E ln P(expected|frame) - max_q mean_E ln P(q|frame)
where q ranges over ALL non-special phonetic tokenizer labels (includes expected).
This score is <= 0 in natural-log units (nats), NOT dB, accuracy, or confidence.
competing_phone is the best OTHER label. CTC pooling is a provisional proxy,
not a CTC sequence likelihood or validated pronunciation metric. No error labels
are emitted, and low scores alone never determine status. Frame centers use
the actual convolution kernels/strides; contextual attention is not time-local.

Sources: model card and vocab at huggingface.co/facebook/wav2vec2-xlsr-53-espeak-cv-ft;
manual annotation conventions at psi.engr.tamu.edu/l2-arctic-corpus-docs/.
No real inference/corpus results are bundled. Page 7: choose 20-40 clips from
2-3 speakers, prefer 2-5 s, and record actual target/label coverage. Additions
and deletions are excluded from the substitution-only comparison. Each run
writes l2_check_results.json with license, attribution, samples and failures.
"""
import argparse
from collections import Counter
from functools import lru_cache
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import numpy as np
from scipy.io import wavfile

from align_audio import (align_audio, config_path, load_settings, parse_textgrid,
                         phone_tier, prepare_audio, split_phone, validate_segments)

UNITS = "natural_log_ratio_nats"


def _mapping(settings):
    return json.loads(config_path(settings["scoring"]["map_path"], settings).read_text(encoding="utf-8"))


def _resolve(seg, mapping):
    original = seg.get("original_phone", seg["canonical_phone"])
    phone, parsed_stress = split_phone(original)
    stress = seg.get("stress", parsed_stress)
    if phone.lower() in mapping["silence"]:
        return None, "silence"
    if phone.lower() in mapping["unsupported"]:
        return None, "nonphonetic_or_unknown"
    key = phone.upper()
    target = mapping["stress_overrides"].get(f"{key}{stress}", mapping["phones"].get(key))
    return target, None if target else "unmapped_phone"


@lru_cache(maxsize=1)
def _load_model(model_id, revision, cache_dir, local_only, threads):
    import torch
    from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
    torch.set_num_threads(int(threads))
    kwargs = dict(revision=revision, cache_dir=cache_dir, local_files_only=local_only,
                  trust_remote_code=False)
    from transformers import (
        Wav2Vec2FeatureExtractor,
        Wav2Vec2PhonemeCTCTokenizer,
    )

    feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained(
        model_id, **kwargs
    )
    tokenizer = Wav2Vec2PhonemeCTCTokenizer.from_pretrained(
        model_id, do_phonemize=False, **kwargs
    )
    processor = Wav2Vec2Processor(
        feature_extractor=feature_extractor,
        tokenizer=tokenizer,
    )
    model = Wav2Vec2ForCTC.from_pretrained(model_id, **kwargs).to("cpu").eval()
    return processor, model


def frame_geometry(config, n_samples, sample_rate, n_frames):
    """Return convolution receptive-field centers, not duration / frame_count."""
    if getattr(config, "add_adapter", False):
        raise ValueError("Adapter timing unsupported")
    stride, receptive_field, length = 1, 1, n_samples
    for kernel, step in zip(config.conv_kernel, config.conv_stride):
        receptive_field += (int(kernel) - 1) * stride
        stride *= int(step)
        length = (length - int(kernel)) // int(step) + 1
    if length != n_frames or length <= 0:
        raise ValueError("Model frame count does not match convolution timing")
    centers = (np.arange(n_frames) * stride + (receptive_field - 1) / 2) / sample_rate
    return centers, dict(stride_samples=stride, receptive_field_samples=receptive_field,
                         frame_step_sec=stride / sample_rate,
                         first_frame_center_sec=float(centers[0]))


def _row(seg, status, reason=None):
    return dict(seg, raw_score=None, score_units=UNITS, competing_phone=None,
                status=status, reason=reason)


def _score_logprobs(logp, centers, segments, mapping, vocab, special_ids, cfg):
    if cfg["min_evidence_frames"] < 1 or cfg["min_winner_margin_nats"] < 0:
        raise ValueError("Invalid evidence frame/margin settings")
    for key in ("min_evidence_fraction", "min_top_phone_probability", "min_phonetic_mass"):
        if not 0 <= cfg[key] <= 1:
            raise ValueError(f"Invalid {key}")
    if logp.ndim != 2 or len(centers) != len(logp) or not np.isfinite(logp).all():
        raise ValueError("Non-finite/malformed model log probabilities")
    if set(vocab.values()) != set(range(logp.shape[1])):
        raise ValueError("Tokenizer/logit vocabulary mismatch")
    inverse = {i: label for label, i in vocab.items()}
    candidates = np.array(sorted(set(vocab.values()) - set(special_ids)), dtype=int)
    if len(candidates) < 2:
        raise ValueError("No phonetic competitor inventory")
    global_winners = np.argmax(logp, axis=1)
    phonetic_mass = np.exp(logp[:, candidates]).sum(axis=1)
    top_prob = np.exp(logp[np.arange(len(logp)), global_winners])
    evidence = (np.isin(global_winners, candidates) &
                (top_prob >= cfg["min_top_phone_probability"]) &
                (phonetic_mass >= cfg["min_phonetic_mass"]))
    rows = []
    for seg in segments:
        target, reason = _resolve(seg, mapping)
        if reason:
            rows.append(_row(seg, "unsupported", reason))
            continue
        if target not in vocab or vocab[target] in special_ids:
            rows.append(_row(seg, "unsupported", "target_not_in_real_tokenizer"))
            continue
        region = (centers >= seg["start_sec"]) & (centers < seg["end_sec"])
        keep = region & evidence
        total, retained = int(region.sum()), int(keep.sum())
        row = _row(seg, "uncertain", "insufficient_phonetic_evidence")
        row.update(target_token=target, target_token_id=vocab[target],
                   total_frames=total, evidence_frames=retained,
                   evidence_fraction=retained / total if total else 0.0,
                   blank_or_special_frames=int((region & ~np.isin(global_winners, candidates)).sum()))
        if retained < cfg["min_evidence_frames"] or row["evidence_fraction"] < cfg["min_evidence_fraction"]:
            rows.append(row)
            continue
        mean_logp = logp[keep].mean(axis=0)
        ranked = candidates[np.argsort(mean_logp[candidates])[::-1]]
        best = int(ranked[0])
        alternative = next(int(i) for i in ranked if i != vocab[target])
        margin = float(mean_logp[ranked[0]] - mean_logp[ranked[1]])
        ambiguous = margin < cfg["min_winner_margin_nats"]
        row.update(raw_score=float(mean_logp[vocab[target]] - mean_logp[best]),
                   competing_phone=inverse[alternative], winning_phone=inverse[best],
                   winner_margin_nats=margin, status="uncertain" if ambiguous else "scored",
                   reason="ambiguous_acoustic_winner" if ambiguous else None)
        rows.append(row)
    return rows


def score_phonemes(audio, alignment, settings) -> dict:
    """Return top-level available/unavailable and scored/uncertain/unsupported rows.

    Exceptions from model download/load/inference (including MemoryError) become
    unavailable. An OS hard OOM kill cannot be caught; check logs/laptop memory.
    """
    result = dict(status="unavailable", segments=[], reason=None,
                  score_units=UNITS, calibrated=False, confirmed_errors=False)
    segments = alignment.get("segments", [])
    try:
        settings = load_settings(settings)
        if alignment.get("status") != "available":
            raise ValueError("Alignment unavailable: " + str(alignment.get("reason")))
        x, sr, fingerprint = prepare_audio(audio, settings)
        if fingerprint != alignment.get("audio_sha256"):
            raise ValueError("Alignment belongs to different audio; rerun MFA")
        validate_segments(segments, len(x) / sr)
        mapping = _mapping(settings)
        mc = settings["model"]
        if mc["id"] != mapping["model_id"]:
            raise ValueError("Model/map mismatch")
        cache_dir = str(config_path(mc["cache_dir"], settings)) if mc.get("cache_dir") else None
        processor, model = _load_model(mc["id"], mc["revision"], cache_dir,
                                      mc["local_files_only"], mc["cpu_threads"])
        if processor.feature_extractor.sampling_rate != sr:
            raise ValueError("Processor sample rate mismatch")
        import torch
        inputs = processor(x, sampling_rate=sr, return_tensors="pt", padding=False)
        with torch.inference_mode():
            logits = model(**{k: v.to("cpu") for k, v in inputs.items()}).logits[0]
            logp = torch.log_softmax(logits.float(), dim=-1).cpu().numpy()
        centers, timing = frame_geometry(model.config, len(x), sr, len(logp))
        tokenizer = processor.tokenizer
        vocab = tokenizer.get_vocab()
        special = set(tokenizer.all_special_ids)
        blank = model.config.pad_token_id
        if blank is None or blank != tokenizer.pad_token_id:
            raise ValueError("CTC blank/pad mismatch")
        special.add(blank)
        # Delimiters can be non-special in some tokenizer configurations.
        for attr in ("word_delimiter_token_id", "phone_delimiter_token_id"):
            value = getattr(tokenizer, attr, None)
            if isinstance(value, int):
                special.add(value)
        result["segments"] = _score_logprobs(logp, centers, segments, mapping, vocab,
                                              special, settings["scoring"])
        result.update(status="available", model_id=mc["id"],
                      model_revision=getattr(model.config, "_commit_hash", None) or mc["revision"],
                      device="cpu", audio_sha256=fingerprint, timing=timing,
                      blank_token_id=blank, excluded_token_ids=sorted(special),
                      scored_count=sum(r["status"] == "scored" for r in result["segments"]))
    except Exception as exc:
        reason = f"{type(exc).__name__}: {exc}"
        result.update(status="unavailable", reason=reason)
        # Retain silence/unmapped distinctions even if the model cannot run.
        try:
            mapping = _mapping(load_settings(settings))
            result["segments"] = [_row(s, "unsupported" if _resolve(s, mapping)[1] else "uncertain",
                                       _resolve(s, mapping)[1] or "scoring_unavailable") for s in segments]
        except Exception:
            result["segments"] = []
    return result


def parse_manual_annotations(path, settings):
    """Official L2-ARCTIC phones: unchanged, CPL,PPL,s / sil,PPL,a / CPL,sil,d.

    Unknown tags/deviations retain their raw label. Never reinterpret err or '*'
    as a model-confirmed error. Silence has no correct/incorrect human label.
    """
    entries = phone_tier(parse_textgrid(path), settings["l2_arctic"]["annotation_tiers"])
    rows = []
    for i, (start, end, raw) in enumerate(entries):
        parts = [p.strip() for p in raw.split(",")]
        canonical, stress = split_phone(parts[0])
        perceived, label = None, "unknown"
        if len(parts) == 1:
            label = "silence" if canonical.lower() in ("", "sil", "sp") else "correct"
            if canonical.lower() in ("err", "spn") or "*" in canonical:
                label = "unknown"
            perceived = parts[0]
        elif len(parts) == 3:
            perceived = parts[1]
            label = {"s": "substitution", "a": "addition", "d": "deletion"}.get(parts[2].lower(), "unknown")
        rows.append(dict(annotation_id=f"a{i:04d}", start_sec=start, end_sec=end,
                         original_label=raw, canonical_phone=canonical.upper(), stress=stress,
                         expected_phone=parts[0], realized_phone=perceived,
                         error_type=label if label in ("substitution", "addition", "deletion") else None,
                         perceived_phone=perceived, human_label=label))
    return rows


def _compare(rows, manual, settings):
    """Conservative one-to-one time overlap + canonical match, not index zip.

    Additions and deletions are excluded from substitution-only comparison.
    Retain all excluded and unmatched annotations in the log.
    Ambiguous candidates and duplicate claims are rejected, not auto-repaired.
    """
    cfg = settings["l2_arctic"]
    proposals = {}
    for ri, row in enumerate(rows):
        candidates = []
        for ai, ann in enumerate(manual):
            if ann["human_label"] not in ("correct", "substitution"):
                continue
            if row["canonical_phone"].upper() != ann["canonical_phone"]:
                continue
            overlap = max(0, min(row["end_sec"], ann["end_sec"]) - max(row["start_sec"], ann["start_sec"]))
            union = max(row["end_sec"], ann["end_sec"]) - min(row["start_sec"], ann["start_sec"])
            iou = overlap / union if union > 0 else 0
            if iou >= cfg["minimum_match_iou"]:
                candidates.append((iou, ai))
        candidates.sort(reverse=True)
        if candidates and (len(candidates) == 1 or candidates[0][0] - candidates[1][0] >= cfg["ambiguity_iou_gap"]):
            proposals[ri] = candidates[0]
    claims = Counter(ai for _, ai in proposals.values())
    comparisons, matched = [], set()
    for ri, row in enumerate(rows):
        record = dict(row, human_label=None, manual_match_status="unmatched_or_ambiguous")
        if ri in proposals:
            iou, ai = proposals[ri]
            if claims[ai] == 1:
                ann = manual[ai]
                record.update(human_label=ann["human_label"], manual_annotation=ann,
                              manual_match_status="matched", match_iou=iou)
                matched.add(ai)
        comparisons.append(record)
    return comparisons, [a for i, a in enumerate(manual) if i not in matched]


def _write_json(path, data):
    path = Path(path)
    payload = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     prefix=path.name + ".", suffix=".tmp", delete=False) as handle:
        handle.write(payload)
        temporary = handle.name
    os.replace(temporary, path)


TARGETS = ("TH", "IH", "IY", "AE", "EH")


def _coverage(annotations):
    return {p: {label: sum(a["canonical_phone"] == p and a["human_label"] == label
                          for a in annotations) for label in ("correct", "substitution", "addition", "deletion")}
            for p in TARGETS}


def _license_record(root, settings):
    path = root / settings["l2_arctic"]["license_path"]
    return dict(license=settings["l2_arctic"]["license"], license_path=str(path),
                license_text=path.read_text(encoding="utf-8-sig"),
                attribution=settings["l2_arctic"]["attribution"],
                official_access_url=settings["l2_arctic"]["official_access_url"])


def _manual_path(root, sample):
    path = (root / sample["manual_annotation"]).resolve()
    expected = (root / sample["speaker_id"] / "annotation").resolve()
    if path.parent != expected:
        raise ValueError("Manual ground truth must come from speaker/annotation/, not textgrid/")
    return path


def select_l2_samples(settings_path, count=30):
    """Select real annotated <=5 s clips; save paths and selection failures."""
    settings = load_settings(settings_path)
    if not 20 <= count <= 40:
        raise ValueError("Page 7 requires a requested selection of 20-40 recordings")
    root = config_path(settings["l2_arctic_root"], settings).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Obtain official L2-ARCTIC access and set l2_arctic_root: {root}")
    provenance = _license_record(root, settings)
    targets = set(TARGETS)
    requested_speakers = settings["l2_arctic"].get("speaker_ids", [])
    if requested_speakers and len(set(requested_speakers)) not in (2, 3):
        raise ValueError("Configure two or three distinct speaker IDs")
    candidates, failures = [], []
    for annotation in sorted(root.glob("*/annotation/*.TextGrid")):
        speaker, utterance = annotation.parent.parent.name, annotation.stem
        if requested_speakers and speaker not in requested_speakers:
            continue
        wav = root / speaker / "wav" / f"{utterance}.wav"
        transcript = root / speaker / "transcript" / f"{utterance}.txt"
        try:
            x, sr, _ = prepare_audio(wav, settings)
            if not transcript.read_text(encoding="utf-8-sig").strip():
                raise ValueError("Empty transcript")
            annotations = parse_manual_annotations(annotation, settings)
            validate_segments([dict(a, segment_id=a["annotation_id"]) for a in annotations], len(x) / sr)
            phones = {a["canonical_phone"] for a in annotations}
            errors = sum(a["canonical_phone"] in targets and a["human_label"] == "substitution" for a in annotations)
            candidates.append((len(phones & targets), errors, speaker, utterance,
                               dict(speaker_id=speaker, utterance_id=utterance,
                                    wav=str(wav.relative_to(root)), transcript=str(transcript.relative_to(root)),
                                    manual_annotation=str(annotation.relative_to(root)), duration_sec=len(x) / sr,
                                    target_coverage=_coverage(annotations))))
        except Exception as exc:
            failures.append(dict(speaker_id=speaker, utterance_id=utterance, reason=str(exc)))
    # Deterministic exploratory selection, NOT representative calibration data.
    candidates.sort(key=lambda c: (-c[0], -c[1], c[2], c[3]))
    pools = {}
    for c in candidates:
        pools.setdefault(c[2], []).append(c[-1])
    speakers = requested_speakers or sorted(pools, key=lambda s: (-len(pools[s]), s))[:3]
    selected, covered = [], set()
    # Balance speakers while favoring previously unseen target/label pairs.
    while len(selected) < count:
        progress = False
        for speaker in speakers:
            pool = pools.get(speaker, [])
            if not pool or len(selected) >= count:
                continue
            def priority(record):
                pairs = {(p, label) for p, labels in record["target_coverage"].items()
                         for label in ("correct", "substitution") if labels[label]}
                return (record["duration_sec"] >= settings["l2_arctic"]["preferred_min_duration_sec"],
                        len(pairs - covered), len(pairs))
            best = max(pool, key=priority)
            pool.remove(best)
            selected.append(best)
            covered.update((p, label) for p, labels in best["target_coverage"].items()
                           for label in ("correct", "substitution") if labels[label])
            progress = True
        if not progress:
            break
    settings["l2_arctic"]["selected_samples"] = selected
    settings["l2_arctic"]["selection_actual_count"] = len(selected)
    settings["l2_arctic"]["selection_requested_count"] = count
    settings["l2_arctic"]["selection_failures"] = failures
    settings["l2_arctic"]["selection_provenance"] = provenance
    settings["l2_arctic"]["selection_speaker_counts"] = dict(Counter(s["speaker_id"] for s in selected))
    settings["l2_arctic"]["selection_coverage"] = {p: {label: sum(s["target_coverage"][p][label] for s in selected)
        for label in ("correct", "substitution", "addition", "deletion")} for p in TARGETS}
    warnings = []
    if len(selected) < count:
        warnings.append(f"Only {len(selected)} eligible clips available; requested {count}")
    if len({s["speaker_id"] for s in selected}) < 2:
        warnings.append("Fewer than two speakers available; page 7 selection unfinished")
    settings["l2_arctic"]["selection_warnings"] = warnings
    settings.pop("_settings_dir", None)
    _write_json(settings_path, settings)
    return dict(status="available" if selected else "unavailable", selected_count=len(selected),
                selection_failures=len(failures), warnings=warnings, message="Selection only; no inference run")


def run_l2_check(settings, start=0, limit=5):
    """Save automatic evidence JSONL + counts, never a separate prose report."""
    settings = load_settings(settings)
    output = config_path(settings["l2_arctic"]["output_dir"], settings)
    output.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix="check_", dir=output))
    root = config_path(settings["l2_arctic_root"], settings)
    selected = settings["l2_arctic"]["selected_samples"][start:start + limit]
    summary = dict(status="unavailable", selected_count=len(selected), attempted_count=0,
                   inference_available_count=0, clips_with_scored_segments=0,
                   clips_with_matched_scored_evidence=0, failure_count=0, matched_scored_segments=0,
                   unmatched_annotations=0, segment_status_counts={}, failures=[],
                   events_path=str(run / "checks.jsonl"), run_dir=str(run))
    status_counts = Counter()
    report = dict(schema_version=2, purpose="exploratory software check; no detection accuracy",
                  decision_rule=None, evaluation_policy=settings["l2_arctic"]["evaluation_note"],
                  settings={k: v for k, v in settings.items() if not k.startswith("_")},
                  samples=[], summary=summary, annotation_coverage=_coverage([]),
                  matched_scored_coverage=_coverage([]), exclusions=[],
                  license_provenance=None, provenance_failure=None)
    try:
        report["license_provenance"] = _license_record(root, settings)
    except Exception as exc:
        report["provenance_failure"] = str(exc)
    report_path = run / "l2_check_results.json"
    summary["results_path"] = str(report_path)
    all_manual, scored_manual = [], []
    _write_json(report_path, report)
    with (run / "checks.jsonl").open("w", encoding="utf-8") as log:
        for sample in selected:
            record = dict(sample=sample, sample_id=f"{sample['speaker_id']}/{sample['utterance_id']}",
                          status="unavailable", failures=[])
            summary["attempted_count"] += 1
            try:
                if report["provenance_failure"]:
                    raise ValueError("Retain corpus LICENSE and configure license_path: " + report["provenance_failure"])
                annotation_path = _manual_path(root, sample)
                audio = root / sample["wav"]
                transcript = (root / sample["transcript"]).read_text(encoding="utf-8-sig").strip()
                alignment = align_audio(audio, transcript, settings, run)
                record["alignment"] = alignment
                evidence = score_phonemes(audio, alignment, settings)
                record["evidence"] = evidence
                if evidence["status"] != "available":
                    record["failures"].append(evidence["reason"])
                else:
                    summary["inference_available_count"] += 1
                    summary["clips_with_scored_segments"] += int(evidence["scored_count"] > 0)
                status_counts.update(s["status"] for s in evidence["segments"])
                # Manual file is read AFTER inference and cannot leak into it.
                manual = parse_manual_annotations(annotation_path, settings)
                if alignment.get("duration_sec") is not None:
                    validate_segments([dict(a, segment_id=a["annotation_id"]) for a in manual], alignment["duration_sec"])
                compared, unmatched = _compare(evidence["segments"], manual, settings)
                excluded = [dict(a, exclusion_reason="excluded_from_substitution_only_comparison")
                            for a in manual if a["human_label"] in ("addition", "deletion")]
                record.update(comparisons=compared, manual_annotations=manual,
                              excluded_manual_annotations=excluded, unmatched_manual_annotations=unmatched,
                              uncertain_cases=[r for r in compared if r["status"] == "uncertain"])
                all_manual.extend(manual)
                scored_manual.extend(r["manual_annotation"] for r in compared
                                     if r["status"] == "scored" and r["manual_match_status"] == "matched")
                report["exclusions"].extend(dict(a, sample_id=record["sample_id"]) for a in excluded)
                matched = sum(r["status"] == "scored" and r["manual_match_status"] == "matched" for r in compared)
                summary["matched_scored_segments"] += matched
                summary["clips_with_matched_scored_evidence"] += int(matched > 0)
                summary["unmatched_annotations"] += len(unmatched)
                if not matched:
                    record["failures"].append("No scored segments with unambiguous manual matches")
                record["status"] = "available" if not record["failures"] else "unavailable"
            except Exception as exc:
                record["failures"].append(f"{type(exc).__name__}: {exc}")
            if record["failures"]:
                summary["failure_count"] += 1
                summary["failures"].append(dict(sample_id=record["sample_id"], reasons=record["failures"]))
            log.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
            log.flush()
            summary["segment_status_counts"] = dict(status_counts)
            report["samples"].append(record)
            report["annotation_coverage"] = _coverage(all_manual)
            report["matched_scored_coverage"] = _coverage(scored_manual)
            report["actual_speaker_counts"] = dict(Counter(r["sample"]["speaker_id"] for r in report["samples"]))
            _write_json(report_path, report)
            _write_json(run / "counts.json", summary)
            print(record["sample_id"], record["status"], flush=True)
    summary["status"] = "available" if selected and summary["failure_count"] == 0 else "unavailable"
    if not selected:
        summary["reason"] = "No selected samples in this slice; run --select-l2 first"
    _write_json(run / "counts.json", summary)
    _write_json(report_path, report)
    return summary


def self_test():
    """Offline synthetic tests. Passing does NOT validate real MFA/model quality."""
    class Tests(unittest.TestCase):
        def setUp(self):
            self.settings = load_settings(Path(__file__).with_name("settings.json"))
            self.mapping = _mapping(self.settings)
            self.audio = (np.sin(np.arange(16000) * 0.1).astype(np.float32) * 0.1, 16000)

        def test_audio_and_duration(self):
            x, sr, h = prepare_audio(self.audio, self.settings)
            self.assertEqual((len(x), sr), (16000, 16000))
            self.assertEqual(h, prepare_audio((x, sr), self.settings)[2])
            with self.assertRaises(ValueError):
                prepare_audio((np.zeros(96000), 16000), self.settings)
            with self.assertRaises(ValueError):
                prepare_audio((np.zeros(16000), 16000), self.settings)

        def test_stress_and_map(self):
            self.assertEqual(split_phone("IH1_B"), ("IH", 1))
            self.assertEqual(_resolve(dict(canonical_phone="AH", original_phone="AH0", stress=0), self.mapping)[0], "ə")
            self.assertEqual(self.mapping["phones"]["TH"], "θ")

        def test_textgrid(self):
            with tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp) / "test.TextGrid"
                p.write_text('File type = "ooTextFile"\nObject class = "TextGrid"\nitem [1]:\nclass = "IntervalTier"\nname = "phones"\nintervals: size = 1\nintervals [1]:\nxmin = 0\nxmax = 1\ntext = "IH1"\n')
                self.assertEqual(parse_textgrid(p)["phones"], [(0, 1, "IH1")])
                p.write_text('File type = "ooTextFile short"\n"TextGrid"\n0\n1\n<exists>\n1\n"IntervalTier"\n"phones"\n0\n1\n1\n0\n1\n"TH,S,s"\n')
                self.assertEqual(parse_manual_annotations(p, self.settings)[0]["human_label"], "substitution")

        def test_bad_boundaries(self):
            for end in (-1, 2, float("nan")):
                with self.assertRaises(ValueError):
                    validate_segments([dict(segment_id="x", start_sec=0, end_sec=end)], 1)
            with self.assertRaises(ValueError):
                validate_segments([dict(segment_id="a", start_sec=0.4, end_sec=0.8),
                                   dict(segment_id="b", start_sec=0.2, end_sec=0.3)], 1)

        def test_mfa_failures(self):
            with tempfile.TemporaryDirectory() as tmp:
                with patch("align_audio.subprocess.run", side_effect=FileNotFoundError("mfa missing")):
                    self.assertEqual(align_audio(self.audio, "test", self.settings, tmp)["status"], "unavailable")
                with patch("align_audio.subprocess.run") as run:
                    run.return_value.returncode = 0
                    self.assertIn("missing", align_audio(self.audio, "test", self.settings, tmp)["reason"])
                with patch("align_audio.subprocess.run") as run:
                    run.return_value.returncode = 1
                    self.assertIn("exited 1", align_audio(self.audio, "test", self.settings, tmp)["reason"])

        def test_mfa_success_mock_only(self):
            from types import SimpleNamespace
            def fake_mfa(args, **kwargs):
                dest = Path(args[6])
                dest.write_text('File type = "ooTextFile short"\n"TextGrid"\n0\n1\n<exists>\n1\n"IntervalTier"\n"phones"\n0\n1\n1\n0\n1\n"IH1"\n')
                return SimpleNamespace(returncode=0)
            with tempfile.TemporaryDirectory() as tmp:
                with patch("align_audio.subprocess.run", side_effect=fake_mfa):
                    result = align_audio(self.audio, "test", self.settings, tmp)
                self.assertEqual(result["status"], "available")
                self.assertEqual(result["segments"][0]["stress"], 1)
                self.assertTrue((Path(result["run_dir"]) / "corpus" / "clip.lab").is_file())

        def test_model_load_failure(self):
            _, _, fingerprint = prepare_audio(self.audio, self.settings)
            alignment = dict(status="available", audio_sha256=fingerprint, segments=[
                dict(segment_id="a", canonical_phone="TH", start_sec=0, end_sec=1)])
            with patch(__name__ + "._load_model", side_effect=MemoryError("test OOM")):
                result = score_phonemes(self.audio, alignment, self.settings)
            self.assertEqual(result["status"], "unavailable")
            self.assertEqual(result["segments"][0]["status"], "uncertain")
            self.assertIsNone(result["segments"][0]["raw_score"])

        def test_manual_match_and_duplicate(self):
            row = dict(segment_id="p", canonical_phone="TH", start_sec=0, end_sec=1,
                       raw_score=-2, status="scored")
            manual = [dict(annotation_id="a", canonical_phone="TH", start_sec=0, end_sec=1,
                           human_label="substitution", original_label="TH,S,s")]
            compared, unmatched = _compare([row], manual, self.settings)
            self.assertEqual(compared[0]["human_label"], "substitution")
            self.assertEqual(unmatched, [])
            compared, unmatched = _compare([row, row], manual, self.settings)
            self.assertTrue(all(r["human_label"] is None for r in compared))
            self.assertEqual(len(unmatched), 1)

        def test_empty_l2_logging(self):
            with tempfile.TemporaryDirectory() as tmp:
                self.settings["l2_arctic"]["selected_samples"] = []
                self.settings["l2_arctic"]["output_dir"] = tmp
                result = run_l2_check(self.settings)
                self.assertEqual(result["attempted_count"], 0)
                self.assertEqual(result["status"], "unavailable")
                self.assertTrue((Path(result["run_dir"]) / "counts.json").is_file())
                report = json.loads(Path(result["results_path"]).read_text())
                self.assertEqual(report["samples"], [])
                self.assertIsNone(report["decision_rule"])

        def test_composites_excluded(self):
            with tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp) / "manual.TextGrid"
                p.write_text('File type = "ooTextFile short"\n"TextGrid"\n0\n1\n<exists>\n1\n"IntervalTier"\n"phones"\n0\n1\n3\n0\n0.3\n"TH,S*,s"\n0.3\n0.6\n"IH,sil,d"\n0.6\n1\n"sil,AE,a"\n')
                manual = parse_manual_annotations(p, self.settings)
                self.assertEqual(manual[0]["realized_phone"], "S*")
                self.assertEqual(manual[1]["error_type"], "deletion")
                self.assertEqual(manual[2]["expected_phone"], "sil")
                row = dict(segment_id="p", canonical_phone="IH", start_sec=0.3, end_sec=0.6,
                           raw_score=-2, status="scored")
                compared, unmatched = _compare([row], manual, self.settings)
                self.assertIsNone(compared[0]["human_label"])
                self.assertEqual(len(unmatched), 3)

        def test_automatic_textgrid_rejected(self):
            with self.assertRaises(ValueError):
                _manual_path(Path("/tmp/corpus"), dict(speaker_id="ABA",
                             manual_annotation="ABA/textgrid/arctic_a0001.TextGrid"))

        def test_selection_speaker_balance_mock_audio(self):
            # Synthetic corpus fixture tests selection only, not real inference.
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / "LICENSE").write_text("Synthetic test license fixture")
                for speaker in ("A", "B", "C", "D"):
                    for sub in ("annotation", "transcript", "wav"):
                        (root / speaker / sub).mkdir(parents=True)
                    for i in range(8):
                        label = "TH,S,s" if i % 2 else "IH"
                        (root / speaker / "annotation" / f"clip{i}.TextGrid").write_text(
                            'File type = "ooTextFile short"\n"TextGrid"\n0\n2\n<exists>\n1\n"IntervalTier"\n"phones"\n0\n2\n1\n0\n2\n"' + label + '"\n')
                        (root / speaker / "transcript" / f"clip{i}.txt").write_text("test")
                self.settings["l2_arctic_root"] = str(root)
                self.settings["l2_arctic"]["speaker_ids"] = []
                settings_path = root / "settings.json"
                _write_json(settings_path, self.settings)
                with patch(__name__ + ".prepare_audio", return_value=(np.ones(32000), 16000, "fixture")):
                    result = select_l2_samples(settings_path, 20)
                saved = json.loads(settings_path.read_text())
                self.assertEqual(result["selected_count"], 20)
                self.assertEqual(len(saved["l2_arctic"]["selection_speaker_counts"]), 3)
                self.assertGreater(saved["l2_arctic"]["selection_coverage"]["TH"]["substitution"], 0)
                self.assertGreater(saved["l2_arctic"]["selection_coverage"]["IH"]["correct"], 0)

        def test_frame_timing(self):
            from types import SimpleNamespace
            config = SimpleNamespace(conv_kernel=[10, 3, 3, 3, 3, 2, 2], conv_stride=[5, 2, 2, 2, 2, 2, 2])
            centers, timing = frame_geometry(config, 16000, 16000, 49)
            self.assertEqual(timing["stride_samples"], 320)
            self.assertEqual(timing["receptive_field_samples"], 400)
            self.assertAlmostEqual(centers[0], 199.5 / 16000)

        def test_ctc_blank_and_scores(self):
            vocab = {"<pad>": 0, "θ": 1, "s": 2, "æ": 3}
            segments = [dict(segment_id="a", canonical_phone="TH", start_sec=0, end_sec=0.5),
                        dict(segment_id="b", canonical_phone="sil", start_sec=0.5, end_sec=0.7),
                        dict(segment_id="c", canonical_phone="XYZ", start_sec=0.7, end_sec=1)]
            logits = np.array([[9., 0, 0, 0], [0, 2, 5, 0], [0, 2, 5, 0]])
            lp = logits - np.logaddexp.reduce(logits, axis=1)[:, None]
            rows = _score_logprobs(lp, np.array([0.01, 0.1, 0.2]), segments, self.mapping, vocab, {0}, self.settings["scoring"])
            self.assertAlmostEqual(rows[0]["raw_score"], -3)
            self.assertEqual(rows[0]["evidence_frames"], 2)
            self.assertEqual(rows[0]["competing_phone"], "s")
            self.assertEqual([r["status"] for r in rows], ["scored", "unsupported", "unsupported"])
            blank = np.tile([10., 0, 0, 0], (3, 1))
            blank -= np.logaddexp.reduce(blank, axis=1)[:, None]
            rows = _score_logprobs(blank, np.array([0.01, 0.1, 0.2]), segments, self.mapping, vocab, {0}, self.settings["scoring"])
            self.assertIsNone(rows[0]["raw_score"])
            self.assertEqual(rows[0]["status"], "uncertain")

        def test_mismatched_audio(self):
            alignment = dict(status="available", audio_sha256="wrong", segments=[])
            self.assertIn("different audio", score_phonemes(self.audio, alignment, self.settings)["reason"])

    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    return result.wasSuccessful()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--settings", default=str(Path(__file__).with_name("settings.json")))
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--audio")
    parser.add_argument("--transcript")
    parser.add_argument("--run-dir", default="runs/single")
    parser.add_argument("--select-l2", action="store_true")
    parser.add_argument("--check-l2", action="store_true")
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    if args.self_test:
        return 0 if self_test() else 1
    if args.start < 0 or args.limit <= 0 or args.count <= 0:
        parser.error("start must be nonnegative; count and limit must be positive")
    try:
        if args.select_l2:
            result = select_l2_samples(args.settings, args.count)
        elif args.check_l2:
            result = run_l2_check(args.settings, args.start, args.limit)
        elif args.audio and args.transcript:
            start = time.monotonic()
            alignment = align_audio(args.audio, args.transcript, args.settings, args.run_dir)
            evidence = score_phonemes(args.audio, alignment, args.settings)
            result = dict(status=evidence["status"], alignment=alignment, evidence=evidence,
                          elapsed_sec=time.monotonic() - start)
            run_dir = Path(args.run_dir)
            run_dir.mkdir(parents=True, exist_ok=True)
            destination = run_dir / ("result_" + str(time.time_ns()) + ".json")
            _write_json(destination, result)
            result["output_path"] = str(destination)
        else:
            parser.error("Choose --self-test, --select-l2, --check-l2, or --audio plus --transcript")
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0 if result.get("status") == "available" else 2
    except Exception as exc:
        print(json.dumps(dict(status="unavailable", reason=f"{type(exc).__name__}: {exc}")))
        return 2


if __name__ == "__main__":
    sys.exit(main())
