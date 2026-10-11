"""Run `python phoneme_practice.py` for reference-free American phoneme practice.

MFA supplies word/phone timing, not independently recognized words. Wav2Vec2
supplies acoustic evidence. Correct/Incorrect are experimental model judgments,
never calibrated accuracy claims. The original app and pipeline are unchanged.
"""
from datetime import datetime, timezone
import html
import json
import math
import os
from pathlib import Path
import re
import shutil
import threading
import uuid

import numpy as np
from scipy.io import wavfile

from phoneme_scoring.align_audio import (
    align_audio, load_settings, parse_textgrid, prepare_audio, split_phone,
    validate_segments,
)
from phoneme_scoring.gop_score import score_phonemes

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
BASE = Path(__file__).resolve().parent
LOCK = threading.Lock()
SILENCE = {"", "sil", "sp", "<eps>"}
COLORS = {"Correct": ("#dcfce7", "#166534"),
          "Incorrect": ("#fee2e2", "#991b1b"),
          "Uncertain": ("#f1f5f9", "#334155")}


def load_targets():
    return json.loads((BASE / "practice_targets.json").read_text(encoding="utf-8"))["accents"]


def select_target(accent_id, sentence_id):
    accents = load_targets()
    if accent_id not in accents:
        raise ValueError("Choose a supported accent.")
    accent = accents[accent_id]
    sentence = next((s for s in accent["sentences"] if s["id"] == sentence_id), None)
    if sentence is None:
        raise ValueError("Choose a sentence for the selected accent.")
    return accent, sentence


def target_markdown(accent_id, sentence_id):
    accent, sentence = select_target(accent_id, sentence_id)
    rows = "\n".join(f"| {w['text']} | /{w['ipa']}/ |" for w in sentence["words"])
    return (f"### Expected sounds — {accent['label']}\n\n"
            f"**{sentence['text']}**  /{sentence['ipa']}/\n\n"
            f"| Word | Draft target |\n|---|---|\n{rows}\n\n"
            f"{sentence['focus']}\n\n{accent['variation_note']}")


def _word(text):
    return re.sub(r"[^a-z']", "", text.lower())


def aligned_words(alignment, sentence):
    """Read word boundaries; never guess sentence onset from energy or file zero."""
    tiers = parse_textgrid(alignment["textgrid_path"])
    matches = [entries for name, entries in tiers.items() if name.lower() == "words"]
    if len(matches) != 1:
        raise ValueError("MFA word timing is unavailable; no first-word start can be established.")
    words = [dict(segment_id=f"w{i:04d}", text=label,
                  start_sec=start, end_sec=end)
             for i, (start, end, label) in enumerate(matches[0])
             if label.strip().lower() not in SILENCE]
    validate_segments(words, alignment["duration_sec"])
    if [_word(w["text"]) for w in words] != [_word(w["text"]) for w in sentence["words"]]:
        raise ValueError("Aligned word labels do not match the selected sentence. Record only that sentence.")
    return words


def _matches_phone(segment, target):
    phone, stress = split_phone(segment.get("original_phone", segment["canonical_phone"]))
    base, target_stress = split_phone(target)
    return phone.upper() == base.upper() and (target_stress is None or stress == target_stress)


def bind_targets(alignment, words, sentence):
    """Attach explicit word targets by interval containment, never by list index alone.

    A word whose dictionary phone sequence is outside the manual variants gets
    uncertain rows. It cannot silently change the expected pronunciation.
    """
    validate_segments(alignment["segments"], alignment["duration_sec"])
    mapping = json.loads((BASE / "phoneme_scoring" / "phoneme_map.json").read_text(encoding="utf-8"))
    start, end = words[0]["start_sec"], words[-1]["end_sec"]
    selected = []
    for segment in alignment["segments"]:
        if segment["canonical_phone"].lower() in SILENCE:
            continue
        owners = [i for i, word in enumerate(words)
                  if segment["start_sec"] >= word["start_sec"] - 1e-6
                  and segment["end_sec"] <= word["end_sec"] + 1e-6]
        if len(owners) != 1:
            raise ValueError("A speech phoneme crosses or falls outside word boundaries; timing needs review.")
        row = dict(segment, word_index=owners[0], word=words[owners[0]]["text"],
                   sentence_start_sec=max(0., segment["start_sec"] - start),
                   sentence_end_sec=segment["end_sec"] - start)
        selected.append(row)
    for index, target_word in enumerate(sentence["words"]):
        group = [s for s in selected if s["word_index"] == index]
        if not group:
            raise ValueError(f"No phoneme timing for {target_word['text']}.")
        variant = next((v for v in target_word["variants"] if len(v) == len(group)
                        and all(_matches_phone(s, p) for s, p in zip(group, v))), None)
        for position, (row, phone) in enumerate(zip(group, variant or [None] * len(group))):
            row["manual_target_supported"] = phone is not None
            row["manual_target_arpa"] = phone
            if phone:
                canonical, stress = split_phone(phone)
                row["canonical_phone"] = canonical
                # Preserve alignment stress when the manual target leaves it open.
                row["original_phone"] = phone if stress is not None else row["original_phone"]
                if stress is not None:
                    row["stress"] = stress
                # Only alternatives that differ at this phone are interchangeable.
                # Do not mix independent positions into unlisted word variants.
                alternatives = [v[position] for v in target_word["variants"] if len(v) == len(variant)
                                and all(a == b for i, (a, b) in enumerate(zip(v, variant)) if i != position)]
                row["accepted_target_tokens"] = list(dict.fromkeys(
                    mapping["stress_overrides"].get(p, mapping["phones"][split_phone(p)[0]])
                    for p in alternatives))
    return selected, start, end


def classify(row, minimum_margin=1.0):
    """Conservative, uncalibrated decision; retain evidence gates from the scorer."""
    if not row.get("manual_target_supported"):
        return "Uncertain", "Aligned pronunciation is outside the draft target variants."
    if row.get("status") != "scored" or row.get("evidence_frames", 0) < 2:
        return "Uncertain", (row.get("reason") or "Insufficient acoustic evidence.").replace("_", " ")
    margin = row.get("expected_vs_alternative_nats")
    if not isinstance(margin, (int, float)) or not math.isfinite(margin):
        return "Uncertain", "No finite acoustic comparison."
    if margin >= minimum_margin and row.get("target_token") and row.get("winning_phone") == row["target_token"]:
        return "Correct", "Model evidence favors the target sound (experimental)."
    if margin <= -minimum_margin and row.get("winning_phone") and row["winning_phone"] != row.get("target_token"):
        return "Incorrect", "Model evidence favors a different sound (experimental)."
    return "Uncertain", "Target and alternative are too close for a decision."


def join_results(segments, evidence, minimum_margin):
    by_id = {}
    valid_ids = {s["segment_id"] for s in segments}
    for score in evidence.get("segments", []):
        identity = score["segment_id"]
        if identity in by_id or identity not in valid_ids:
            raise ValueError("Scoring results do not join uniquely to the aligned sounds.")
        by_id[identity] = score
    rows = []
    for segment in segments:
        # Timing, word ownership and manual target flags come from alignment only.
        row = {**by_id.get(segment["segment_id"], {}), **segment}
        row["judgment"], row["explanation"] = classify(row, minimum_margin)
        rows.append(row)
    return rows


def run_practice(path, accent_id, sentence_id, output_root=None):
    """Analyze a complete recording. No reference WAV or fixed-duration slicing."""
    with LOCK:
        _, sentence = select_target(accent_id, sentence_id)
        run_dir = Path(output_root or BASE / "runs" / "phoneme_practice") / (
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_") + uuid.uuid4().hex[:10])
        run_dir.mkdir(parents=True)
        result = dict(status="failed", accent_id=accent_id, sentence=sentence,
                      rows=[], messages=[], calibrated=False,
                      timing_method="MFA word/phone forced alignment; transcript is not independently verified",
                      original_audio=None, sentence_audio=None, results_path=None)
        try:
            if not path or not Path(path).is_file() or Path(path).suffix.lower() != ".wav":
                raise ValueError("Record or upload a WAV first.")
            settings = load_settings(BASE / "phoneme_scoring" / "settings.json")
            # Allow leading silence and natural pauses without changing the old app.
            settings["max_duration_sec"] = 15
            cfg = settings.get("practice", {})
            margin = float(cfg.get("decision_margin_nats", 1.0))
            if not math.isfinite(margin) or margin <= 0:
                raise ValueError("practice.decision_margin_nats must be positive and finite.")
            settings["scoring"] = {**settings["scoring"],
                                   "min_evidence_frames": max(2, settings["scoring"]["min_evidence_frames"])}
            x, sr, fingerprint = prepare_audio(path, settings)
            original = run_dir / "original.wav"
            shutil.copyfile(path, original)
            result.update(original_audio=str(original), sample_rate_hz=sr,
                          duration_sec=len(x) / sr, audio_sha256=fingerprint,
                          decision_margin_nats=margin)
            alignment = align_audio((x, sr), sentence["text"], settings, run_dir)
            result["alignment"] = alignment
            if alignment["status"] != "available":
                raise ValueError(alignment.get("reason") or "Alignment unavailable.")
            words = aligned_words(alignment, sentence)
            segments, start, end = bind_targets(alignment, words, sentence)
            sentence_path = run_dir / "sentence.wav"
            wavfile.write(sentence_path, sr, np.rint(x[round(start * sr):round(end * sr)] * 32768).astype(np.int16))
            result.update(words=words, sentence_onset_sec=start, sentence_offset_sec=end,
                          sentence_audio=str(sentence_path))
            scoring_alignment = {**alignment, "segments": segments}
            evidence = score_phonemes((x, sr), scoring_alignment, settings)
            result["phoneme_evidence"] = evidence
            result["rows"] = join_results(segments, evidence, margin)
            # Per-phone playback keeps a little context, but never crosses recording ends.
            for i, row in enumerate(result["rows"]):
                lo = max(0, round((row["start_sec"] - .04) * sr))
                hi = min(len(x), round((row["end_sec"] + .04) * sr))
                clip = run_dir / f"phone_{i:03d}.wav"
                wavfile.write(clip, sr, np.rint(x[lo:hi] * 32768).astype(np.int16))
                row["audio_path"] = str(clip)
            result["status"] = "complete" if all(r["judgment"] != "Uncertain" for r in result["rows"]) else "partial"
            if evidence.get("reason"):
                result["messages"].append(evidence["reason"])
        except Exception as exc:
            result["messages"].append(f"{type(exc).__name__}: {exc}")
        result["results_path"] = str(run_dir / "results.json")
        Path(result["results_path"]).write_text(
            json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        return result


def highlights(result):
    if not result.get("rows"):
        return "<p>No phoneme judgments available.</p>"
    parts = ['<p>Green: Correct · Red: Incorrect · Gray: Uncertain. Experimental model judgments.</p>']
    previous = None
    for row in result["rows"]:
        if row["word_index"] != previous:
            if previous is not None:
                parts.append("</div>")
            parts.append(f'<h4>{html.escape(row["word"])}</h4><div style="display:flex;flex-wrap:wrap;gap:8px">')
            previous = row["word_index"]
        background, color = COLORS[row["judgment"]]
        target = " or ".join(row.get("accepted_target_tokens", [])) or row.get("target_token") or row["canonical_phone"]
        heard = row.get("winning_phone") or "?"
        parts.append(f'<div style="background:{background};color:{color};border:1px solid {color};'
                     f'border-radius:8px;padding:9px;min-width:100px">'
                     f'<strong>/{html.escape(target)}/</strong> · {row["judgment"]}<br>'
                     f'Model: {html.escape(heard)}<br>'
                     f'{row["sentence_start_sec"]:.2f}–{row["sentence_end_sec"]:.2f} s</div>')
    parts.append("</div>")
    return "".join(parts)


def table_rows(result):
    return [[r["word"], " or ".join(r.get("accepted_target_tokens", [])) or r.get("target_token") or r["canonical_phone"],
             r.get("winning_phone") or "—", r["judgment"],
             round(r["sentence_start_sec"], 3), round(r["sentence_end_sec"], 3),
             round(r["start_sec"], 3), round(r["end_sec"], 3),
             r.get("expected_vs_alternative_nats"), r.get("evidence_frames", 0), r["explanation"]]
            for r in result.get("rows", [])]


def result_views(result):
    counts = {key: sum(r["judgment"] == key for r in result.get("rows", [])) for key in COLORS}
    status = "Analysis unavailable." if result["status"] == "failed" else (
        "Experimental result: " + ", ".join(f"{n} {key.lower()}" for key, n in counts.items()) + ".")
    if "sentence_onset_sec" in result:
        status += (f"\nFirst aligned word begins at {result['sentence_onset_sec']:.3f} s in the original recording. "
                   "Sentence playback and sentence times start there at 0 s; internal pauses are preserved.")
    if result["messages"]:
        status += "\n" + "\n".join(result["messages"])
    return (status, highlights(result), table_rows(result), result.get("sentence_audio"),
            result.get("original_audio"), None, "Select a table row to hear that sound.",
            result.get("results_path"), result)


def clear_views(message="Ready"):
    return message, "", [], None, None, None, "Select a table row to hear that sound.", None, None


def build_app():
    import gradio as gr
    accents = load_targets()
    first_accent = next(iter(accents))
    first_sentence = accents[first_accent]["sentences"][0]["id"]
    with gr.Blocks(title="Accent Coach — Phoneme Practice") as demo:
        gr.Markdown("# Phoneme Practice\nChoose a sentence, read it once, then analyze. "
                    "Leading silence is OK; keep the whole recording under 15 seconds. "
                    "Record only the selected sentence, without an introduction or extra words.")
        with gr.Row():
            accent = gr.Dropdown(choices=[(v["label"], k) for k, v in accents.items()],
                                 value=first_accent, label="Target accent", interactive=True)
            sentence = gr.Dropdown(choices=[(s["text"], s["id"]) for s in accents[first_accent]["sentences"]],
                                   value=first_sentence, label="Practice sentence", interactive=True)
        draft = gr.Markdown(target_markdown(first_accent, first_sentence))
        recording = gr.Audio(sources=["microphone", "upload"], type="filepath", format="wav", label="Your recording")
        analyze = gr.Button("Analyze phonemes", variant="primary")
        status = gr.Textbox(label="Result", value="Ready", interactive=False)
        state = gr.State(None)
        with gr.Tab("Detected phonemes"):
            gr.Markdown("**Correct / Incorrect are experimental model judgments, not validated grades.** "
                        "Weak or unsupported evidence is Uncertain. Word timing comes from the selected transcript; "
                        "the app does not independently check which words you said.")
            cards = gr.HTML()
            sentence_audio = gr.Audio(label="Sentence playback — first word at 0 seconds", interactive=False)
            evidence = gr.Dataframe(headers=["Word", "Target IPA", "Model heard", "Judgment", "Sentence start (s)",
                                             "Sentence end (s)", "Original start (s)", "Original end (s)",
                                             "Model margin (nats)", "Evidence frames", "Explanation"],
                                    datatype=["str"] * 4 + ["number"] * 6 + ["str"], interactive=False)
            gr.Markdown("Select a row to hear its interval with 40 ms of surrounding context. "
                        "Sentence times follow your pace and pauses; sounds are not assigned fixed time slots.")
            segment_audio = gr.Audio(label="Selected phoneme", interactive=False)
            segment_detail = gr.Textbox(label="Selected interval", interactive=False)
        with gr.Tab("Recording and saved results"):
            original_audio = gr.Audio(label="Original recording — including leading silence", interactive=False)
            saved = gr.File(label="Download detailed results", interactive=False)
        outputs = [status, cards, evidence, sentence_audio, original_audio, segment_audio, segment_detail, saved, state]

        def analyze_attempt(path, accent_id, sentence_id):
            yield (*clear_views("Aligning words and measuring phonemes on CPU…"),
                   *[gr.update(interactive=False) for _ in range(4)])
            try:
                views = result_views(run_practice(path, accent_id, sentence_id))
            except Exception as exc:
                views = clear_views(f"Analysis unavailable: {type(exc).__name__}: {exc}")
            yield (*views, *[gr.update(interactive=True) for _ in range(4)])

        def change_accent(identity):
            sentences = accents[identity]["sentences"]
            selected = sentences[0]["id"]
            return (gr.update(choices=[(s["text"], s["id"]) for s in sentences], value=selected),
                    target_markdown(identity, selected), *clear_views())

        def inspect_sound(result, event: gr.SelectData):
            if not result or not event.selected:
                return None, "Select a table row to hear that sound."
            index = event.index[0] if isinstance(event.index, (tuple, list)) else event.index
            rows = result.get("rows", [])
            if not isinstance(index, int) or not 0 <= index < len(rows):
                return None, "Select a valid phoneme row."
            row = rows[index]
            return row["audio_path"], (f"{row['word']}: {row['judgment']}. "
                f"Sentence {row['sentence_start_sec']:.3f}–{row['sentence_end_sec']:.3f} s; "
                f"original {row['start_sec']:.3f}–{row['end_sec']:.3f} s. {row['explanation']}")

        analyze.click(analyze_attempt, [recording, accent, sentence],
                      outputs + [analyze, recording, accent, sentence], concurrency_limit=1)
        accent.input(change_accent, accent, [sentence, draft] + outputs, queue=False)
        sentence.input(lambda a, s: (target_markdown(a, s), *clear_views()),
                       [accent, sentence], [draft] + outputs, queue=False)
        recording.change(lambda: clear_views(), outputs=outputs, queue=False)
        evidence.select(inspect_sound, state, [segment_audio, segment_detail], queue=False)
    return demo


if __name__ == "__main__":
    build_app().queue(default_concurrency_limit=1).launch(
        server_name="127.0.0.1", share=False, inbrowser=True,
        allowed_paths=[str(BASE / "runs" / "phoneme_practice")])
