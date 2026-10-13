# Local account website: October 13, 2026

Local integration now includes custom text and free speech with explicit transcript confirmation, private revision-aware sessions, and separate synthetic playback. See [the integration report](docs/INTEGRATION_COMPLETION_REPORT.md) for verification, setup limits and remaining work. Preset lessons remain available. The local Windows speech backend works; the isolated Kokoro runtime is optional and is not installed by the main account requirements.

The website now has real local sign-up/sign-in, **My profile**, and **My history**. New recordings and analysis results are stored under the signed-in account and remain after restarting the app.

From your existing project environment:

```powershell
python -m pip install -r requirements-accounts.txt
python site_server.py
```

Open `http://127.0.0.1:7861/` and create an account. `python app_2.py` starts the same new site. Models/MFA still use your existing configuration. See [account setup and verification](docs/ACCOUNTS_SETUP.md). This integrated version supersedes the earlier standalone Day 1 patch. Old unowned `runs/` history is preserved separately.

The older release notes below describe previous versions. The October 13 account setup above is the current launch path.

# accent_coach

## Parallel team work: October 12, 2026

Start with [the team contract](docs/TEAM_INTERFACE.md), [file ownership](docs/FILE_OWNERSHIP.md), and [the week-one plan](docs/WEEK_ONE_PLAN.md). These describe the next implementation, not features already shipped.

Shared integration branch: `team/week1-foundation`. Feature branches: `feature/speed-free-speech` (Sarrvesh), `feature/voice-conversion` (Parthiban), and `feature/profiles-personalization` (Lucas). All initially point to the same foundation commit. Target feature PRs at the integration branch. Existing branches and `main` are preserved.

[Shared fixtures](tests/fixtures/team/README.md) include synthetic software inputs, not human pronunciation validation. Verify them with `python tools/check_team_fixtures.py`. [Example payloads](contracts/examples/README.md) let each teammate develop independently.

## Website update: October 11, 2026

Run `.\.venv\Scripts\python.exe app_2.py` for the current local website at `http://127.0.0.1:7861/`.
The practice page now has a responsive layout and mobile menu, a custom favicon, and Help (`/help`),
Privacy (`/privacy`), and Terms (`/terms`) pages. Missing page URLs return a branded HTTP 404.
Technical results use wrapping cards, with full data still available in the results download.
The pronunciation models and reference-free assessment rules are unchanged by this frontend update.

Shared styling and icons live in `web_assets/`. `site_pages.py` provides common navigation,
metadata, and page content; `site_server.py` mounts the existing Gradio app in a local FastAPI server.
`site_config.json` contains the team name and contact email. The phone and public URL are deliberately
unset because no phone number or domain is being used. Assets use system fonts, a compact SVG logo,
an ICO favicon, and compressed HTTP responses. Optional builder footer links are disabled.

Run `python tools/check_site_readiness.py` to see the remaining public-launch requirements.
The website remains localhost-only and requests no search-engine indexing. A domain, verified hosting,
reviewed hosted-service policies, and isolated user storage are still required before public launch.
See `docs/FRONTEND_REPORT_2026-10-11.md` for the verification results and known limits.
TAMU Capstone 403

## October 11 release preparation

- **12 preset lessons**, all defined in `prompts.json`: sentences, targets, alternatives, written sound hints, and practice actions. No UI edits or reference recordings are needed to add a configured lesson.
- **Local attempt history** with replay and explicitly confirmed deletion. History is for the person using this laptop, not an authenticated multi-user service.
- **Bounded processing**: one reusable offline worker, a three-minute attempt deadline, a two-minute MFA timeout, eight waiting UI requests, and a 10 MB upload cap. A failed worker is replaced for the next attempt.
- **Evaluation and diagnostics**: saved stage times and recognized-word differences; speaker-split checks and reviewer-based counts including abstentions and coverage.
- **Setup and reproducibility**: `tools/check_installation.py`, `tools/release_snapshot.py`, the [demo runbook](docs/DEMO_RUNBOOK.md), and the [human validation protocol](docs/VALIDATION_PROTOCOL.md).

Model assessment remains experimental. Expanded lesson configuration and synthetic smoke checks do not establish human pronunciation accuracy. Public hosting and validated grading are not part of this local release.

## Current demo: reference-free target-sound assessment (October 10)

Run `.\.venv\Scripts\python.exe app_2.py` and open http://127.0.0.1:7861/.
No reference recording is loaded or compared by this screen.

The beginner screen now shows **Recognized words**, simpler experimental sound feedback,
result playback, and **Record again**. **Practice** buttons open written hints;
teal marks the lesson focus rather than a score. Processing messages follow the
actual pipeline stages without estimated percentages. See
`docs/UI_UPDATE_REPORT_2026-10-10.md` for verification and the manual checklist.

- **Whisper base.en** independently transcribes the recording, without the selected sentence as a hint.
- **MFA** aligns supplied text only when the recognized content is compatible. A clear disagreement asks for another recording; it is not a pronunciation failure.
- **wav2vec2** supplies phoneme probabilities. A new log-space CTC forward calculation compares the complete expected phone sequence with target-substitution alternatives, summing all valid paths including blank frames.
- Target assessments cover **TH in think**, **IH in ship**, and **AE in bad**, now across twelve short sentences. The main result describes a sound closer to expected, suggests practice for a possible alternative, or says the app is unsure. These are experimental model-evidence categories, not validated grades.
- No reference duration, reference pitch, numeric pronunciation percentage, or whole-sentence grade is used. Legacy frame-level margins remain in Engineering details.

### Setup and tests

The existing `requirements-scoring.txt` packages suffice. Download the pinned ASR
weights once (already completed on this laptop):

```powershell
.\.venv\Scripts\python.exe tools/setup_content_model.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe phoneme_scoring/gop_score.py --self-test
.\.venv\Scripts\python.exe tools/check_assessment.py
```

The setup command downloads public model files; it does not upload recordings.
The runtime uses local cached weights. MFA and the phoneme model still require
the setup below. Results schema 3 includes `spoken_words_verification`,
`phoneme_results.sequence_evidence`, and `target_assessment`. `pronunciation_grade`
remains null/unvalidated.

The experimental sequence margin is `log P(expected sequence|audio) - log P(best
configured substitution sequence|audio)`. The default ±1 nat decision boundary
is an abstention heuristic, not a calibrated accuracy threshold. Missing sentence
verification, clipping, unsupported target context, weak local sound evidence,
or a close comparison prevent positive/negative sound feedback. Accepted lexical
contrast variants (e.g. ship/sheep) allow diagnostic assessment; they do not count
as matching the exact words or as correct pronunciation. Dictionary variants
selected by MFA condition the baseline sequence. The method does not assess
insertions, deletions, all possible alternatives, rhythm, stress, or accent identity.

Use the existing human evaluation manifest and `tools/evaluate_recordings.py --run`
to collect both legacy frame margins and new guarded sequence assessments. **Human
labels and held-out evaluation are still required before any correctness grade.**


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

Optional listening examples can be supplied, with speaker permission, at:

- `data/references/think.wav` saying **I think so**
- `data/references/ship.wav` saying **The ship is here**
- `data/references/bad_bed.wav` saying **That is a bad bed**

These assets are intentionally not fabricated or bundled. Missing or corrupt examples do not block learner analysis. Reference comparison is off by default. A team recording is not automatically a validated General American
target. The learner must read the selected text. The current pipeline checks
recognized words with Whisper before alignment; recognition can still mishear speech.

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
  "model": {"cache_dir": "../models/huggingface", "local_files_only": true}
}
```

The app runs MFA through Conda so its native dependencies are available while
the UI stays in `.venv`. No global PATH change is needed. Run
`tools/setup_models.py` explicitly to download both pinned model checkpoints before
opening the app. Inference uses the cached checkpoints offline; first-use downloads
are disabled in the beginner worker. The shared configuration pins the exact model revision. The tested
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

## Beginner practice interface (`app_2.py`)

From the repository folder, run:

```powershell
.\.venv\Scripts\python.exe app_2.py
```

Open http://127.0.0.1:7861. The original `app.py` remains available separately.
This screen uses the same prompts, settings, and analysis pipeline, with no reference audio controls.
No additional packages are needed beyond the existing team environment.

1. **Read:** choose a sentence and review the practice sound hints.
2. **Your turn:** record with the microphone (browser permission required) or
   upload audio, then press **Check my recording**. Keep the recording at most
   five seconds long.
3. **Practice again:** review the experimental target-sound feedback and your recording, and press **Try again** to clear the recording and previous results.

The main view uses simple English and actionable recording messages. It does
not translate instructions or assign a pronunciation grade. Reference-comparison graphs are absent from the new interface. Diagnostic model margins, processing status, warnings,
and downloadable JSON remain in the collapsed **Engineering data & processing details** section. English lesson links have a separate
collapsed section. Changing the sentence or recording clears stale results.
The server is local to this computer; accepted attempts are saved under `runs/`.

Quick manual check: select each sentence; upload
a recording, run the check, and inspect Technical details. Choose Try again and
confirm the recording/results clear. Change sentences and confirm the Check button stays disabled until a new recording is supplied.
Automated interface behavior is covered by `tests/test_app_2.py` in the test suite
above. Microphone capture needs a manual check on a browser with a microphone.

### Lesson hints and assessment

Clickable hints describe expected sounds for practice; teal marks lesson focus,
not correctness. The assessment card describes model evidence for the configured
target sound only. Recording and result changes clear prior evidence.

## Historical milestone (October 7, 2026; superseded by the update above)

The required path is **prompt text + learner WAV → learner DSP → MFA alignment →
pretrained phoneme evidence → practice feedback**. No reference WAV is loaded by
this analysis unless explicitly requested. The sentence is supplied to MFA;
forced alignment is not independent recognition of the spoken words.

`run_attempt(path, prompt_id)` defaults to learner-only analysis. Use
`run_attempt(path, prompt_id, compare_reference=True)` for the optional legacy
acoustic comparison. A missing/broken example cannot stop phoneme inference.
Results schema 2 records `reference_comparison_requested`, `pronunciation_grade`
(null, not validated), and `spoken_words_verification` (not implemented).
MFA word intervals and phone-to-word associations are retained when available.
The pretrained model, pinned model revision, and evidence gates are unchanged.

From the repository folder:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe phoneme_scoring/gop_score.py --self-test
.\.venv\Scripts\python.exe tools/check_reference_free.py
```

The last command runs the real MFA/model on the three local examples **as learner
inputs**, with every reference path removed in memory. It does not delete files
or measure pronunciation accuracy. It writes `runs/reference_free_smoke.json`.

### Human evaluation deliverable

```powershell
.\.venv\Scripts\python.exe tools/evaluate_recordings.py --init
.\.venv\Scripts\python.exe tools/evaluate_recordings.py
.\.venv\Scripts\python.exe tools/evaluate_recordings.py --run
```

Initialize once (`--init` refuses to overwrite). Fill
`data/evaluation/manifest.json` with consented WAV paths and listener labels.
The plan has 3 speakers × 3 prompts × 2 takes × 2 conditions = 36 recordings.
Reserve speaker S03's 12 clips before tuning. Requested altered pronunciations
are recording instructions, **not human labels**. Use an independent listener
and mark unclear cases. `--run` saves results and target-word/phone evidence in
`runs/team_evaluation.json`; it does not turn margins into pass/fail or accuracy.
The manifest and recordings stay local under ignored `data/`.

Tokenizer/dictionary coverage audit (use your installed dictionary path):

```powershell
.\.venv\Scripts\python.exe tools/audit_pronunciations.py --dictionary "C:/path/to/english_us_arpa.dict"
```

This offline audit checks labels and word coverage, not whether the model judges
pronunciation correctly. Human review of dictionary variants and phone mappings,
held-out evaluation, wrong-sentence detection, and validated grading remain open.
