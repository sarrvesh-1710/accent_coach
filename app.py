"""Run `python app.py` from the team environment to open the local application."""

import html
import math
import os
from pathlib import Path
from urllib.parse import urlparse

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")

from pipeline import load_prompts, run_attempt


def lesson_html(prompt):
    links = []
    for link in prompt.get("lesson_links", []):
        url = link.get("url", "")
        parsed = urlparse(url)
        if parsed.scheme == "https" and parsed.hostname in {"rachelsenglish.com", "www.rachelsenglish.com"}:
            links.append(f'<li><a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(link.get("title", "Learn this sound"))}</a></li>')
    return "<ul>" + "".join(links) + "</ul><p>Rachel’s English lessons open online. Analysis runs locally.</p>"


def pitch_html(result):
    """Plot measured contours on their own original timelines; do not bridge silence."""
    series, all_points = [], []
    for key, label, color in (("learner_dsp", "Original", "#2563eb"), ("reference_dsp", "Reference", "#b45309")):
        dsp = result.get(key, {})
        points = []
        for t, y, voiced in zip(dsp.get("time_sec", []), dsp.get("pitch_semitones", []), dsp.get("voiced_mask", [])):
            valid = (voiced and isinstance(t, (int, float)) and isinstance(y, (int, float))
                     and math.isfinite(t) and math.isfinite(y))
            point = (t, y) if valid else None
            points.append(point)
            if point is not None:
                all_points.append(point)
        series.append((label, color, points))
    if not all_points:
        return "<p>Pitch comparison unavailable: no reliable voiced frames.</p>"
    xmax = max(max(t for t, y in all_points), 0.1)
    low = min(-1, min(y for t, y in all_points))
    high = max(1, max(y for t, y in all_points))
    def xy(t, y):
        return 60 + t / xmax * 660, 220 - (y - low) / (high - low) * 180
    parts = ['<svg viewBox="0 0 760 280" role="img" aria-label="Voiced pitch in semitones on original recording timelines" style="width:100%;background:#fff;color:#111">',
             '<path d="M60 35V220H725" fill="none" stroke="#888"/>',
             '<text x="60" y="20" fill="#111">Pitch relative to each recording’s median (semitones)</text>']
    for value in (low, 0, high):
        _, yy = xy(0, value)
        parts.append(f'<text x="8" y="{yy:.1f}" fill="#111">{value:.1f}</text>')
    parts.append(f'<text x="60" y="240" fill="#111">0 s</text><text x="675" y="240" fill="#111">{xmax:.2f} s</text>')
    for index, (label, color, points) in enumerate(series):
        pen = False
        path = []
        for point in points:
            if point is None:
                pen = False
                continue
            x, y = xy(*point)
            path.append(f'{"L" if pen else "M"}{x:.2f},{y:.2f}')
            pen = True
            parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="1.5" fill="{color}"/>')
        parts.append(f'<path d="{" ".join(path)}" fill="none" stroke="{color}" stroke-width="2"/>')
        parts.append(f'<text x="{60 + index * 150}" y="266" fill="{color}">{label}</text>')
    return "".join(parts) + "</svg><p>Original timestamps; contours are not time-warped. Gaps indicate unavailable pitch. DTW comparison arrays are in the saved measurements.</p>"


def evidence_rows(result):
    scores = {s["segment_id"]: s for s in result.get("phoneme_results", {}).get("segments", [])}
    rows = []
    for segment in result.get("alignment", {}).get("segments", []):
        score = scores.get(segment["segment_id"], {})
        rows.append([str(segment["segment_id"]), segment["canonical_phone"],
                     segment["start_sec"], segment["end_sec"], score.get("raw_score"),
                     score.get("score_units", ""), score.get("competing_phone") or "",
                     score.get("status", "unavailable")])
    return rows


def result_views(result):
    state = result["overall_status"]
    status = {"complete": "Analysis complete — preliminary evidence only.",
              "partial": "Partial result — not a complete pronunciation analysis.",
              "failed": "Analysis unavailable — correct the problem and retry."}[state]
    if result.get("results_path"):
        status += f"\nSaved attempt: {result['run_id']}"
    messages = "\n".join(result["messages"])
    stage_rows = [[name, stage["status"], stage.get("message") or ""] for name, stage in result["stage_statuses"].items()]
    paths = result["audio_paths"]
    measurements = {key: result.get(key, {}) for key in ("learner_audio", "reference_audio", "learner_dsp", "reference_dsp", "comparison")}
    return (status, pitch_html(result), evidence_rows(result), "\n\n".join(result["feedback"]),
            paths["original"], paths["reference"], measurements, stage_rows, messages, result["results_path"])


def build_app():
    import gradio as gr
    prompts = load_prompts()
    by_id = {prompt["id"]: prompt for prompt in prompts}
    with gr.Blocks(title="Accent Coach") as demo:
        gr.Markdown("# Accent Coach\nRead the selected sentence exactly and upload a WAV, ideally 2–5 seconds. Feedback is exploratory. Record only with the speaker’s permission.")
        prompt = gr.Dropdown(choices=[(p["text"], p["id"]) for p in prompts], value=prompts[0]["id"], label="Practice sentence")
        upload = gr.File(label="Learner WAV (maximum 5 seconds)", file_types=[".wav"], type="filepath")
        analyze = gr.Button("Analyze", variant="primary")
        status = gr.Textbox(label="Processing status", value="Ready", interactive=False)
        plot = gr.HTML("<p>Analyze a recording to compare pitch.</p>")
        evidence = gr.Dataframe(headers=["Segment", "Expected phone", "Start (s)", "End (s)", "Raw score", "Units", "Competing phone", "Status"],
                                datatype=["str", "str", "number", "number", "number", "str", "str", "str"], interactive=False)
        feedback = gr.Textbox(label="Observations and practice cues", interactive=False, lines=7)
        lessons = gr.HTML(lesson_html(prompts[0]))
        with gr.Row():
            original = gr.Audio(label="Original recording", interactive=False)
            reference = gr.Audio(label="Reference recording", interactive=False)
        gr.Markdown("Pitch and formants are measurements, not correctness scores. Raw cross-speaker formant differences do not establish vowel errors. Team demo references are not automatically validated pronunciation targets.")
        with gr.Accordion("Measurements and processing details", open=False):
            measurements = gr.JSON(label="Acoustic measurements")
            stages = gr.Dataframe(headers=["Stage", "Status", "Message"], interactive=False)
            messages = gr.Textbox(label="Warnings and recovery details", interactive=False, lines=5)
            saved = gr.File(label="Saved results.json", interactive=False)
        outputs = [status, plot, evidence, feedback, original, reference, measurements, stages, messages, saved]

        def cleared(message="Ready"):
            return (message, "", [], "", None, None, {}, [], "", None)

        def analyze_attempt(path, identity):
            # First yield clears old evidence/playback before CPU work starts.
            yield (*cleared("Processing on CPU…"), gr.update(interactive=False), gr.update(interactive=False), gr.update(interactive=False))
            try:
                views = result_views(run_attempt(path, identity))
            except Exception as exc:
                views = cleared(f"Analysis unavailable: {type(exc).__name__}: {exc}")
            yield (*views, gr.update(interactive=True), gr.update(interactive=True), gr.update(interactive=True))

        analyze.click(analyze_attempt, [upload, prompt], outputs + [analyze, upload, prompt], concurrency_limit=1)
        prompt.change(lambda identity: (*cleared(), lesson_html(by_id[identity])), prompt, outputs + [lessons], queue=False)
        upload.change(lambda: cleared(), outputs=outputs, queue=False)
    return demo


if __name__ == "__main__":
    try:
        build_app().queue(default_concurrency_limit=1).launch(server_name="127.0.0.1", share=False, inbrowser=True)
    except ModuleNotFoundError as exc:
        raise SystemExit(f"Missing dependency: {exc.name}. Run python -m pip install -r requirements.txt") from exc
