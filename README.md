# accent_coach
TAMU Capstone 403

## Parthiban: local application and feedback

The four application files are `app.py`, `pipeline.py`, `feedback.py`, and
`prompts.json`. From the repository folder, using Python 3.12:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

The application opens on localhost. Select a sentence, upload a WAV of the
same sentence (ideally 2–5 seconds, maximum 5), and click Analyze. Each attempt
saves `runs/<run_id>/results.json`; accepted learner audio is copied into that
run folder for playback. Delete a run folder to remove its retained recording
and results. These files stay local and are excluded from Git.

Supply permitted or consenting team reference recordings at:

- `data/references/think.wav` saying **I think so**
- `data/references/ship.wav` saying **The ship is here**
- `data/references/bad_bed.wav` saying **That is a bad bed**

These assets are intentionally not fabricated or bundled. A missing reference
is rejected. A team recording is not automatically a validated General American
target. The learner must read the selected text; this application does not verify
the transcript with speech recognition.

Lucas's `settings.json`, `align_audio.py`, `gop_score.py`, and `phoneme_map.json`
belong in `phoneme_scoring/`. The pipeline imports that package and resolves
scoring configuration paths relative to its `settings.json`. Both alignment
and scoring receive the same saved learner WAV; DSP stages use prepared arrays.
Lucas's `available` status is validated and accepted as a successful stage.
Until settings arrive, the pipeline uses
Sarrvesh's documented default settings (16 kHz, five seconds, CPU) and reports
that fallback. Without alignment/scoring, valid acoustic comparisons produce an
explicit partial result. No fabricated scores or overall percentages are shown.
Lucas must supply his MFA environment, downloaded model and dependencies for real
phoneme evidence. Model inference runs sequentially.

Scores join alignment by `segment_id`, never array position. Scored segments need
finite `raw_score` and explicit `score_units`; uncertain/unsupported/missing
segments keep the result partial. Pitch is plotted on each recording's original
timeline with gaps for unvoiced frames. Sarrvesh's DTW-aligned pitch arrays and
formant validity flags remain available in the measurement details and JSON.
Reference audio/features are cached by absolute path, modification time, file size
and settings (up to three entries). Restart the app after changing teammate code.

Practice cues are prompt-based suggestions, not detected errors. The linked
Rachel's English lessons cover [TH](https://rachelsenglish.com/english-pronounce-th-consonants/),
[IH versus EE](https://rachelsenglish.com/english-pronounce-ih-vowel/), and
[AA](https://rachelsenglish.com/english-pronounce-aa-ae-vowel/).
Only opening these links needs internet; the pipeline does not fetch lesson
content or audio. Voice conversion remains outside this laptop milestone.

Run the integration and failure tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests use real audio/DSP on synthetic tones and mocked alignment/scoring to check
integration contracts. They do not validate pronunciation quality, model accuracy,
or a real learner/reference speech pair. Those checks require the team assets.

## Sarrvesh: CPU audio analysis

Use Python 3.11–3.13. From this repository in PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe compare_audio.py data/learner.wav data/reference.wav --output runs/comparison.json
```

Use two WAV recordings of **the same text**, each no longer than five seconds.
The loader converts recordings to 16 kHz mono without trimming timestamps.
Silence, invalid files and overlong clips return an explicit unavailable status.
The JSON contains pitch, exploratory F1/F2/F3 formants, duration ratio and
MFCC dynamic time warping (DTW) distance. Missing features are `null`.
Pitch contours are measured in semitones relative to each recording's median.
These measurements are not calibrated pronunciation scores; formants are not
normalized across speakers. Real speech validation and team integration remain.

### Integration contracts

- `audio_io.prepare_audio(path, settings=None)` returns audio metadata and a
  NumPy `samples` array. Exclude `samples` when serializing to JSON.
- `dsp_features.extract_features(audio, settings=None)` returns JSON-ready features.
- `compare_audio.compare_audio(learner_audio, reference_audio, learner_dsp,
  reference_dsp, settings=None)` returns JSON-ready comparisons.
- Every result has `status` (`ok`, `warning`, or `unavailable`), `reason`, and
  `warnings`. Check status before consuming features. Invalid settings raise
  `ValueError`. Settings are optional flat dictionaries; defaults are documented
  in each module. Optional `prompt_id` values in both audio dictionaries must match.

Lucas owns alignment/scoring; Parthiban owns the pipeline, feedback and UI.
The requirements currently cover only this DSP component. Add their tested
dependencies during integration. L2-ARCTIC evaluation and Rachel's English
resource links will be integrated by those components.

Keep recordings in `data/`, generated results in `runs/`, and downloaded models
in `models/`. These local folders are excluded from Git.
