"""Beginner interface. Run .venv/Scripts/python.exe app_2.py (localhost:7861).

Uses the existing pipeline and keeps its technical results available. Recording
acceptance and practice suggestions are never presented as pronunciation grades.
"""
import html
import math
import os
import re
from pathlib import Path

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
import gradio as gr

from app import result_views, pitch_html
from pipeline import load_prompts
from analysis_service import run_attempt
import attempt_history
from site_pages import (ASSETS, PRACTICE_TITLE, footer_html, header_html,
                        measurement_cards, row_cards)

BASE_DIR = Path(__file__).resolve().parent
CSS = (ASSETS / 'site.css').read_text(encoding='utf-8')
WAVEFORM_OPTIONS = {"waveform_color": "#334155", "waveform_progress_color": "#0E4D40"}


def sound_strip(prompt):
    targets = set(prompt.get("target_phones", []))
    words = []
    for entry in prompt.get("practice_words", []):
        word = entry["word"]
        controls = []
        for sound in entry["sounds"]:
            phone, label, cue = sound["phone"], sound["label"], sound["hint"]
            focus = phone in targets
            controls.append(f'<details class="{"focus" if focus else "sound"}"><summary>'
                         f'Practice {html.escape(label)}{" · lesson focus" if focus else ""}</summary>'
                         f'<p>{html.escape(cue)}</p></details>')
        words.append(f'<div class="sound-word"><h4>{html.escape(word)}</h4>{"".join(controls)}</div>')
    return ('<p>Tap “Practice” to read a hint. Teal marks the lesson focus, not your result.</p>'
            '<div class="sound-strip">' + ''.join(words) + '</div>'
            '<p class="strip-note">Expected sounds for practice, not detected mistakes or grades. '
            'Connected speech can vary.</p>')


def melody_html(result):
    """Scale each original recording to 0–100%; this is not DTW alignment."""
    scaled = {}
    for who in ("learner", "reference"):
        dsp = dict(result.get(f"{who}_dsp", {}))
        duration = result.get(f"{who}_audio", {}).get("duration_sec")
        if not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
            dsp = {}
        else:
            dsp["time_sec"] = [t / duration if isinstance(t, (int, float)) and math.isfinite(t)
                               else None for t in dsp.get("time_sec", [])]
        scaled[f"{who}_dsp"] = dsp
        scaled[f"{who}_audio"] = {"duration_sec": 1.0}
    graphic = pitch_html(scaled).split('</svg>')[0]
    if '<svg' not in graphic:
        return '<div class="melody"><h3>Sentence melody</h3><p>No reliable pitch curve is available for this try.</p></div>'
    graphic += '</svg>'
    graphic = (graphic.replace('background:#fff;color:#111', 'background:#161f30;color:#e2e8f0')
               .replace('#111', '#cbd5e1').replace('#888', '#475569')
               .replace('#2563eb', '#22d3ee').replace('#b45309', '#fbbf24')
               .replace('Original', 'You').replace('Reference', 'Example')
               .replace('0 s</text>', '0%</text>').replace('1.00 s</text>', '100%</text>')
               .replace('on original recording timelines', 'over percentage of each recording'))
    grid = ''.join(f'<path d="M{x}35V220" stroke="#334155" stroke-width="0.5"/>' for x in (225,390,555))
    graphic = graphic.replace('<path d="M60', grid + '<path d="M60', 1)
    return ('<div class="melody"><h3>Sentence melody</h3><p>See how your voice and the example rise and fall.</p>'
            + graphic + '<p>0–100% of each full recording, including pauses. This scales time; '
            'it does not align words using DTW. Gaps mean unavailable pitch, not mistakes. '
            'Pitch is relative to each voice’s median; curve similarity is not a grade.</p></div>')


def notice(title, message, next_step, attention=False, *, transcript=None):
    style = "simple-notice attention" if attention else "simple-notice"
    recognized = ('<div class="recognized-words"><span class="recognized-badge"><strong>Recognized:</strong> “'
                  + html.escape(transcript) + '”</span><small>The app may have misheard you.</small></div>') if transcript else ""
    return (f'<section class="{style}" role="status" aria-live="polite">{recognized}'
            f'<h3>{html.escape(title)}</h3><p>{html.escape(message)}</p>'
            f'<p><strong>Next:</strong> {html.escape(next_step)}</p></section>')


def ready_notice():
    return notice("Read the sentence", "We check your recording using speech models. No example audio is needed.",
                  "Record your voice or upload a recording.")


def assessment_notice(result):
    content = result.get("spoken_words_verification", {})
    transcript = content.get("transcript")
    if content.get("status") == "mismatch":
        return notice("Let's check the sentence", "The words we heard do not match the sentence. We may have misheard you.",
                                  "Listen to your recording, then read the sentence and record again.", True, transcript=transcript)
    if content.get("status") not in {"match", "target_variant"}:
        return notice("Sentence check unavailable", "We cannot check this sound reliably yet.",
                      "Listen to your recording and try again. Your project helper can check Engineering details.", True, transcript=transcript)
    targets = result.get("target_assessment", {}).get("targets", [])
    if not targets:
        return notice("Sound check unavailable", "We could not check the practice sound.",
                      "Listen to your recording and try again.", True, transcript=transcript)
    labels = {"TH": "th", "S": "s", "T": "t", "F": "f", "IH": "i in ship", "IY": "ee in sheep", "AE": "a in bad", "EH": "e in bed"}
    cards = []
    for target in targets:
        word = target["word"]
        sound = labels.get(target["expected_phone"], target["expected_phone"])
        state = target["status"]
        if state == "expected_supported":
            title = f'Your “{sound}” in “{word}” sounded closer to the expected sound.'
            message = "This is an experimental result, not a final grade. The app can make mistakes."
            action = "Listen below, then say the sentence again."
        elif state == "alternative_favored":
            other = labels.get(target.get("alternative_phone"), target.get("alternative_phone", "another sound"))
            title = f'Let’s practice “{word}”.'
            message = f'The app heard something closer to “{other}” than “{sound}”. It may be mistaken. This is not a final grade.'
            action = result.get("prompt", {}).get("practice_tip", "Practice the target word, then repeat the sentence.")
        else:
            title = f'We’re not sure about the sound in “{word}” yet.'
            message = "We need a clearer result before giving sound feedback. This does not mean you said it wrong."
            action = "Try the whole sentence again in a quiet place. Speak naturally."
        cards.append(notice(title, message, action, state != "expected_supported",
                            transcript=transcript if not cards else None))
    return "".join(cards)


def learner_notice(result):
    """Summarize operational outcomes, not raw model numbers or voice similarity."""
    stages = result.get("stage_statuses", {})
    if result.get("overall_status") == "failed":
        if stages.get("save", {}).get("status") == "unavailable":
            return notice("We could not save this try", "Your recording has not been saved.",
                          "Ask your project helper to check the app, then try again.", True)
        reason = result.get("learner_audio", {}).get("reason") or ""
        if reason == "audio_too_long":
            return notice("Make a shorter recording", "Record just the sentence, in 5 seconds or less.",
                          "Choose Record again and record the sentence once.", True)
        if reason in {"silent_audio", "empty_audio"}:
            return notice("We could not hear your voice", "Your recording is silent or too quiet to use.",
                          "Choose Record again and speak closer to the microphone.", True)
        return notice("We could not check this recording", "Try a clear recording of the whole sentence.",
                      "Choose Record again. If this keeps happening, ask your project helper.", True)
    quality = result.get("learner_audio", {}).get("warnings", [])
    if "possible_clipping" in quality:
        return notice("Your recording may be too loud", "Some sound may be distorted.",
                      "Choose Record again and move a little farther from the microphone.", True)
    if "target_assessment" in result:
        return assessment_notice(result)
    prompt_id = result.get("prompt", {}).get("id", result.get("prompt_id"))
    tip = result.get("prompt", {}).get("practice_tip", "Listen to your recording, then say the sentence again.")
    card = notice("Focus area for this prompt",
                  "Listen to your recording. This is a practice suggestion, not a detected mistake. "
                  "Pronunciation grading is not available.", tip)
    duration = result.get("learner_audio", {}).get("duration_sec")
    if isinstance(duration, (int, float)) and math.isfinite(duration) and duration > 0:
        card += f'<span class="duration-tag">Your recording · {duration:.2f} seconds</span>'
    return card


def cleared(message=None):
    # Message, eight technical components, and playback beside the result.
    return (message or ready_notice(), "", "", "", "", "", "", "", None,
            gr.update(value=None, visible=False))


def attempt_views(result):
    old = result_views(result)
    plot = ""  # Beginner assessment uses no reference comparison.
    playback = result.get("audio_paths", {}).get("original")
    saved_note = '<p class="save-message" role="status">Check finished. This attempt was saved on this computer.</p>' if result.get('results_path') else ''
    return (learner_notice(result) + saved_note, old[0], plot,
            row_cards(['Segment', 'Expected sound', 'Start (s)', 'End (s)', 'Model margin', 'Units', 'Alternative sound', 'Evidence frames', 'Details', 'Status'], old[2]),
            old[3], measurement_cards(old[6]), row_cards(['Stage', 'Status', 'Message'], old[7]), old[8], old[9],
            gr.update(value=playback, visible=bool(playback)))


def analyze_recording(path, identity, progress=gr.Progress()):
    """Yield a clean busy state before running learner-first CPU analysis."""
    if not path:
        yield (*cleared(), gr.update(interactive=False), gr.update(interactive=True),
               gr.update(interactive=True), gr.update(visible=False, interactive=True))
        return
    busy = notice("Analyzing pronunciation…", "Demo processing may take a few moments.",
                  "Please wait. The current step appears while we work; this can take up to three minutes.")
    yield (*cleared(busy), gr.update(interactive=False), gr.update(interactive=False),
           gr.update(interactive=False), gr.update(visible=False, interactive=False))
    try:
        views = attempt_views(run_attempt(path, identity, compare_reference=False,
            progress_callback=lambda message: progress((0, None), desc=message)))
    except TimeoutError as exc:
        values = list(cleared(notice("The check took too long", "No sound result is available for this try.",
                                    "Record again. The app is ready for another attempt.", True)))
        values[1] = str(exc)
        views = tuple(values)
    except Exception as exc:
        values = list(cleared(notice("Something went wrong", "The app could not finish this try.",
                                    "Try again or ask your project helper.", True)))
        values[1] = f"{type(exc).__name__}: {exc}"
        views = tuple(values)
    yield (*views, gr.update(interactive=True), gr.update(interactive=True),
           gr.update(interactive=True), gr.update(visible=True, interactive=True))


def reference_file(prompt):
    if not prompt.get("reference_wav"):
        return None
    path = (BASE_DIR / prompt["reference_wav"]).resolve()
    if not path.is_file():
        return None
    try:
        import soundfile as sf
        info = sf.info(str(path))
        return str(path) if info.frames > 0 else None
    except Exception:
        return None


def sentence_html(prompt):
    spellings = {'think': 'th', 'ship': 'i', 'bad': 'a', 'bed': 'e'}
    targets = {word.lower() for word in prompt.get('target_words', [])}
    def highlight(word):
        part = spellings.get(word.lower()) if word.lower() in targets else None
        if not part:
            return html.escape(word)
        index = word.lower().index(part)
        return (html.escape(word[:index]) + '<mark class="target-sound">'
                + html.escape(word[index:index + len(part)]) + '</mark>'
                + html.escape(word[index + len(part):]))
    # Escape each non-word piece as well; prompt content never becomes markup.
    phrase = ''.join(highlight(chunk) if re.fullmatch(r'[A-Za-z]+', chunk)
                     else html.escape(chunk) for chunk in re.split(r'([A-Za-z]+)', prompt['text']) if chunk)
    identity = prompt.get('id', '')
    example = ''
    if re.fullmatch(r'[a-z0-9_]+', identity) and (ASSETS / 'examples' / f'{identity}.wav').is_file():
        example = (f'<button type="button" class="example-play" data-example="/site-assets/examples/{identity}.wav" '
                   'aria-label="Listen to the synthetic English example" aria-pressed="false">'
                   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">'
                   '<path d="M11 5 6 9H3v6h3l5 4V5Zm4 3a6 6 0 0 1 0 8m3-11a10 10 0 0 1 0 14"/></svg>'
                   '<span>Listen</span></button>')
    ipa = html.escape(prompt.get('practice_ipa', ''))
    return ('<div class="sentence"><small>Read aloud</small><div class="sentence-line">'
            f'<span class="sentence-text">{phrase}</span>{example}</div>'
            + (f'<p class="sentence-ipa" aria-label="Phonetic guide">/{ipa}/</p>' if ipa else '')
            + '<p class="sentence-note">Underline marks the practice sound. General American guide; connected speech varies.</p>'
            + ('<p class="example-status" role="status" aria-live="polite">Synthetic English example. Listening only; not used for scoring.</p>' if example else '') + '</div>')


def practice_theme():
    colors = {
        'body_background_fill': '#f5f5ef', 'body_text_color': '#192b30',
        'body_text_color_subdued': '#52666c', 'background_fill_primary': '#ffffff',
        'background_fill_secondary': '#eef2ed', 'block_background_fill': '#ffffff',
        'block_border_color': '#d3ddd7', 'block_label_background_fill': '#ffffff',
        'block_label_text_color': '#52666c', 'block_title_text_color': '#192b30',
        'block_info_text_color': '#52666c', 'input_background_fill': '#ffffff',
        'input_background_fill_focus': '#ffffff', 'input_background_fill_hover': '#f5f7f3',
        'input_border_color': '#b6c7be', 'input_placeholder_color': '#52666c',
        'border_color_primary': '#d3ddd7', 'panel_background_fill': '#ffffff',
        'accordion_text_color': '#192b30', 'link_text_color': '#11675b',
        'button_primary_background_fill': '#11675b', 'button_primary_background_fill_hover': '#0a5248',
        'button_primary_text_color': '#ffffff', 'button_secondary_background_fill': '#ffffff',
        'button_secondary_background_fill_hover': '#e9f1ec', 'button_secondary_text_color': '#192b30',
        'table_text_color': '#192b30', 'table_even_background_fill': '#ffffff',
        'table_odd_background_fill': '#f5f7f3', 'table_border_color': '#d3ddd7',
    }
    return gr.themes.Base(font=['Arial', 'Helvetica', 'sans-serif'], font_mono=['Consolas', 'monospace']).set(
        **colors, **{key + '_dark': value for key, value in colors.items()})


def lesson_html(prompt):
    links = ''.join('<a target="_blank" rel="noopener noreferrer" href="' + html.escape(link['url'], quote=True)
                    + '">' + html.escape(link['title']) + ' (external lesson)</a>'
                    for link in prompt.get('lesson_links', []))
    return '<div class="lesson-links">' + links + '</div><p class="helper-text">Lessons open on Rachel’s English. Recording analysis stays on this computer.</p>'


def refresh_history(identity):
    choices = attempt_history.list_attempts(identity)
    message = "Saved attempts refreshed. Choose an attempt to review." if choices else "No saved attempts for this sentence yet. Record it and complete a check first."
    return gr.update(choices=choices, value=None), message, None, False


def open_history(identity):
    try:
        text, audio = attempt_history.history_view(identity)
        return text, audio, False
    except (ValueError, OSError):
        return "This attempt is no longer available. Refresh the list.", None, False


def remove_history(identity, confirmed, prompt_id):
    if not confirmed:
        return gr.update(), "Select the confirmation box to delete this saved attempt.", None, False
    try:
        attempt_history.delete_attempt(identity)
        return gr.update(choices=attempt_history.list_attempts(prompt_id), value=None), "Deleted the saved attempt folder and its audio. A recording already open in a browser may remain until you refresh/close that page.", None, False
    except (ValueError, OSError):
        return gr.update(), "Could not delete this attempt. Refresh the list and choose a completed attempt.", None, False


def build_app():
    prompts = load_prompts()
    by_id = {p['id']: p for p in prompts}
    first = prompts[0]
    with gr.Blocks(title=PRACTICE_TITLE, analytics_enabled=False, delete_cache=(3600, 86400)) as demo:
        gr.HTML(header_html(), elem_id='site-header-wrap')
        gr.HTML('<section id="welcome"><p class="eyebrow">English speaking practice</p>'
                '<h1>Practice English pronunciation.</h1>'
                '<p class="intro">Record a short sentence. Get feedback on a practice sound, '
                'then listen and try again.</p></section>')
        with gr.Column(elem_id='main-content'):
            with gr.Row(equal_height=True, elem_id='practice-steps'):
                with gr.Column(scale=1, min_width=280, elem_classes='step-panel'):
                    gr.HTML('<h2 class="section-heading"><span class="step-label">01</span> Choose a sentence</h2>')
                    prompt = gr.Dropdown([(p['text'], p['id']) for p in prompts], value=first['id'], label='Practice sentence', interactive=True)
                    sentence = gr.HTML(sentence_html(first))
                    with gr.Accordion('Practice hints for this sentence', open=False):
                        strip = gr.HTML(sound_strip(first))
                    with gr.Accordion('Watch a pronunciation lesson', open=False):
                        lessons = gr.HTML(lesson_html(first))
                with gr.Column(scale=1, min_width=280, elem_classes=['step-panel', 'record-panel']):
                    gr.HTML('<h2 class="section-heading"><span class="step-label">02</span> Record your voice</h2>')
                    gr.HTML('<p class="helper-text">Say the whole sentence naturally. Keep the recording under five seconds.</p>')
                    recording = gr.Audio(sources=['microphone', 'upload'], type='filepath', format='wav',
                        label='Your recording', editable=False, buttons=[], elem_id='learner-audio', waveform_options=WAVEFORM_OPTIONS)
                    gr.HTML('<p class="helper-text">Use the microphone or upload a WAV file, up to 10 MB. '
                            'You can listen before checking.</p>')
                    check = gr.Button('Check my recording', variant='primary', interactive=False, elem_id='check-button')
                    gr.HTML('<p class="helper-text">Demo processing may take a few moments, up to three minutes. No reference recording is needed.</p>')
            gr.HTML('<h2 class="section-heading"><span class="step-label">03</span> Review and practice</h2>')
            summary = gr.HTML(ready_notice(), elem_id='practice-result')
            playback = gr.Audio(label='Listen to my recording', interactive=False, visible=False, buttons=[], waveform_options=WAVEFORM_OPTIONS)
            retry = gr.Button('Record again', visible=False, elem_id='retry-button')
            with gr.Accordion('Saved attempts', open=False):
                gr.HTML('<p class="history-note">Earlier recordings for the selected sentence are saved on this computer. '
                        'Model outcomes are experimental and do not measure improvement.</p>')
                history_refresh = gr.Button('Refresh saved attempts')
                history_pick = gr.Dropdown(choices=attempt_history.list_attempts(first['id']), label='Choose an earlier attempt', value=None)
                history_text = gr.Textbox(label='Saved attempt status', value='Choose an attempt to review its result and recording.', interactive=False, elem_id='history-status')
                history_audio = gr.Audio(label='Listen to earlier attempt', interactive=False, buttons=[], waveform_options=WAVEFORM_OPTIONS)
                history_confirm = gr.Checkbox(label='Permanently delete the selected attempt and its saved audio', value=False)
                history_delete = gr.Button('Delete selected attempt', variant='stop')
                history_refresh.click(refresh_history, prompt, [history_pick, history_text, history_audio, history_confirm], queue=False)
                history_pick.input(open_history, history_pick, [history_text, history_audio, history_confirm], queue=False)
                history_delete.click(remove_history, [history_pick, history_confirm, prompt], [history_pick, history_text, history_audio, history_confirm])
                prompt.input(refresh_history, prompt, [history_pick, history_text, history_audio, history_confirm], queue=False)
            with gr.Accordion('Technical details', open=False):
                gr.Markdown('These measurements are **not pronunciation grades**. Whisper checks the sentence, MFA locates sounds, and the phoneme model compares the practice sound with selected alternatives.')
                plot = gr.HTML()
                status = gr.Textbox(label='Processing status', interactive=False)
                gr.Markdown('### Sound evidence')
                evidence = gr.HTML()
                feedback = gr.Textbox(label='Full observations', interactive=False)
                with gr.Accordion('Measurement summaries', open=False):
                    measurements = gr.HTML()
                    gr.Markdown('Download the result for full arrays and model diagnostics.')
                gr.Markdown('### Processing stages')
                stages = gr.HTML()
                messages = gr.Textbox(label='Warnings and recovery details', interactive=False)
                saved = gr.File(label='Download analysis results', interactive=False)
            gr.HTML('<p class="helper-text">Record only with the speaker’s permission. Audio and results are saved on this computer. '
                    'Feedback is experimental and may be wrong. Read the <a href="/privacy">privacy policy</a> for storage and deletion details.</p>')
        gr.HTML(footer_html(), elem_id='site-footer-wrap')
        outputs = [summary, status, plot, evidence, feedback, measurements, stages, messages, saved, playback]
        controls = [check, recording, prompt, retry]
        check.click(analyze_recording, [recording, prompt], outputs + controls, concurrency_limit=1)

        def on_recording(path):
            message = notice('Recording ready', 'Listen to your recording before checking.',
                             'Press Check my recording.') if path else ready_notice()
            return (*cleared(message), gr.update(interactive=bool(path)), gr.update(visible=False))

        recording.input(on_recording, recording, outputs + [check, retry], queue=False)
        recording.start_recording(lambda: (*cleared(notice('Recording', 'Say the sentence once.',
                                                         'Stop recording when you finish.')),
                                  gr.update(interactive=False), gr.update(visible=False)),
                                  outputs=outputs + [check, retry], queue=False)
        retry.click(lambda: (*cleared(notice('Ready for another try', 'Your previous saved attempt remains in history.',
                                            'Record the sentence again.')), None, gr.update(interactive=False), gr.update(visible=False)),
                    outputs=outputs + [recording, check, retry], queue=False)

        def change_sentence(identity):
            selected = by_id[identity]
            return (*cleared(), None, gr.update(interactive=False), gr.update(visible=False),
                    sentence_html(selected), lesson_html(selected), sound_strip(selected))

        prompt.input(change_sentence, prompt,
                     outputs + [recording, check, retry, sentence, lessons, strip], queue=False)
    return demo


if __name__ == '__main__':
    from site_server import serve
    serve(build_app(), practice_theme(), CSS)
