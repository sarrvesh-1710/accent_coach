# accent_coach

Chinese learner profile: see [START_HERE_CHINESE.md](START_HERE_CHINESE.md) for
the selectable JSON profile, setup, SpeechOcean evaluation, and calibration.
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
Real phoneme evidence requires the separate MFA environment and CPU model
dependencies described below. Model inference runs sequentially.

### Full local alignment and neural scoring setup

Install the additional CPU packages into the app environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-scoring.txt
conda create -n accent-coach-mfa --override-channels -c conda-forge python=3.11 montreal-forced-aligner=3.3.7 -y
conda run -n accent-coach-mfa mfa model download dictionary english_us_arpa
conda run -n accent-coach-mfa mfa model download acoustic english_us_arpa
```

If Conda is not on PATH, use the full path to its executable. Keep personal
paths in `phoneme_scoring/settings.local.json`, which is excluded from Git.
Its section values override matching shared settings without changing the
other fields. For example (replace the Conda executable path):

```json
{
  "mfa": {
    "command": ["C:/path/to/conda.exe", "run", "--no-capture-output", "-n", "accent-coach-mfa", "mfa"]
  },
  "model": {"cache_dir": "../models/huggingface", "local_files_only": false}
}
```

The app runs MFA through Conda so its native dependencies are available while
the UI stays in `.venv`. No global PATH change is needed. The first analysis
downloads the pretrained Wav2Vec2 checkpoint (about 1.3 GB). After it has loaded
successfully, set `local_files_only` to `true` to reuse the cached checkpoint
offline. The shared configuration pins the exact model revision. The tested
Gradio version needs Transformers 5 and a compatible Hugging Face Hub version;
use the pinned scoring requirements rather than the older Transformers 4 setup.
Restart the app after installing packages or changing Python files.

Silence intervals are marked `skipped` and receive no score. Uncertain or
unsupported speech still produces a partial result. Comparing a recording with
itself should give duration ratio 1 and MFCC DTW distance 0; it does not force
every neural segment to be scored or establish pronunciation accuracy.

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
The main requirements cover DSP and the app; requirements-scoring.txt adds the
CPU neural model. MFA is installed separately as described above. L2-ARCTIC
evaluation requires separately obtained corpus files. Rachel's English lesson
links are available in the app.

Keep recordings in `data/`, generated results in `runs/`, and downloaded models
in `models/`. These local folders are excluded from Git.

## Interpreting results and checking the September 29 fixes

The app reports **Pronunciation grade unavailable** even when processing finishes.
Processing success means the software ran; it does not mean a speaker passed a
pronunciation test. Pass/fail decisions require separate human-labeled evaluation
and calibration, which this prototype has not completed.

The sound table displays **Evidence frames** (retained/total). The earlier fixed
three-frame rejection rule has been replaced: even a two-frame consonant interval
can retain a diagnostic comparison. CTC produces sparse emissions (see the
[original CTC paper](https://www.cs.toronto.edu/~graves/icml_2006.pdf)). A qualified
single frame produces a comparison but remains `uncertain` in JSON, with
`evidence_quality: sparse` and **limited evidence** in the interface. Blank-only
segments still have no comparison. Probability, phonetic-mass and winner-margin
checks remain; blank-frame fraction is reported rather than used to reject longer
segments by default. These are experimental checks, not accuracy guarantees.

**Model margin** is `expected_vs_alternative_nats`: mean log probability of the
expected phone minus that of its strongest alternative. Positive favors expected,
negative favors the alternative; neither is a correctness verdict or percentage.
This avoids displaying identical zeros whenever the expected phone wins.
The original nonpositive `raw_score` remains in JSON for compatibility and is a
different quantity. One-frame evidence stays visibly limited even with a large
margin. No evidence means blank, not zero. Multiple frames are not necessarily
independent. Alignment with a supplied transcript does not verify the spoken words.

Pitch uses a Gaussian-filtered analysis copy followed by Praat autocorrelation,
with a 50–500 Hz search range. Weak periodicity, estimates near the search limits,
large adjacent jumps, and very short voiced runs are omitted and recorded in
`pitch_invalid_reason`. Original recordings and model/alignment audio are unchanged.
Background energy is now checked on the original signal: the floor is the larger
of the absolute minimum and a level 20 dB below the 90th-percentile frame RMS.
When that percentile is at least three times the quiet decile, twice the quiet
decile is also used as a background floor. This suppresses quiet hum without a
fixed frequency cutoff. `pitch_frame_rms` and `pitch_effective_energy_floor` make
rejections inspectable. It is an energy heuristic, not a trained speech detector;
very quiet speech can be omitted and loud noise may still survive. Relative energy
checks are also described in [Praat's silence analysis documentation](https://praat.org/manual/Sound__To_TextGrid__silences____.html).
This follows the filtering principle in the [Praat filtered autocorrelation
documentation](https://praat.org/manual/pitch_analysis_by_filtered_autocorrelation.html);
it is implemented with SciPy because the bundled older Praat lacks that command.
These are heuristic quality checks: gaps do not mean pronunciation errors, and
some genuine pitch changes or voices outside the configured range may be omitted.

After restarting `python app.py`, refresh the browser and analyze a new attempt
(existing saved results are historical and do not change):

1. Choose **I think so** and upload the partner recording used previously.
   Expect the grade-unavailable label, evidence counts, and signed model margins.
   Single-frame sounds should say **limited evidence**, not require three frames.
   Inspect the reference pitch: quiet background regions should now have gaps.
2. Upload each reference as its own learner recording under the matching prompt.
   Expect duration ratio 1.00 and overlapping pitch contours. Phoneme evidence
   may still be uncertain; this checks consistency, not pronunciation accuracy.
3. Play both audio controls and download the saved results. Under measurements,
   inspect `pitch_method`, `pitch_invalid_reason`, and `pitch_rejected_frames`.

Run both automated test suites from the repository folder:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe phoneme_scoring\gop_score.py --self-test
```

These check software behavior, including low/high steady pitches and evidence
gating. They are not a measured pronunciation accuracy score.
