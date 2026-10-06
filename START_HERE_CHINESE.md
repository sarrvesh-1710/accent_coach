# Chinese accent profile for Accent Coach

This is a complete source snapshot based on `fix/pitch-and-phoneme-evidence`
at `cae6e8776dfe6e1f0b795ac1ab9d9d94fb9bb913`, with the Chinese profile additions.
No changes were pushed to GitHub. Extract into a NEW folder to preserve your
existing environment, recordings, local settings, and uncommitted work.

## Use the profile now

1. Open the extracted `accent_coach_chinese` folder in your working Accent Coach
   environment. Keep using your working Python/MFA setup; the original dependency
   files are included unchanged, not newly validated package-install instructions.
2. Copy your existing `phoneme_scoring/settings.local.json` if you use it. Make
   sure its MFA executable/model paths still point to your installed environment.
3. From this folder, run `python app.py`.
4. Select **Chinese accent** under **Learner profile**, select the sentence, upload
   a matching English WAV (up to 5 seconds), and click Analyze.

The profile means a Mandarin-speaking learner practicing General American English.
It does not generate Chinese-accented speech or assess Mandarin pronunciation.
No reference WAV is required in Chinese mode. Without one, reference comparison
is unavailable but alignment and phoneme scoring can still run. General practice
retains the original reference requirement. MFA and the acoustic scoring model
are still required for phoneme evidence in either mode.

`accent_profiles/chinese.json` is the editable configuration. The app calls
`pipeline.run_attempt(wav_path, prompt_id, "chinese")`, which loads this JSON,
records the selected profile, and loads the optional fitted calibration model.
The default two-argument `run_attempt` call continues to use General practice.

Before training, results say calibration is not trained and show raw evidence
where available. They do not invent human ratings. Changing learner profile
clears the previous result from the UI.

## Train SpeechOcean ratings later

The archive contains neither the corpus nor pretrained SpeechOcean calibration
weights. The JSON rubric is configuration; learning the mapping needs actual
recordings and human ratings. Obtain the public dataset from:
https://github.com/jimbozhang/speechocean762

One way to place it in the expected folder (run from the project root):

```powershell
git clone https://github.com/jimbozhang/speechocean762.git data/speechocean762
```

Expected dataset folders: `WAVE/`, `train/`, `test/`, and `resource/`.
The adapter uses `resource/scores.json`; ratings stay out of alignment and model
inference. The loader accepts both string and list phone representations. It
reads local paths from `wav.scp` and never executes commands from it.

Run a small setup check first:

```powershell
python -m phoneme_scoring.evaluate_speechocean --split train --limit 20 --output runs/speechocean_smoke
```

This may cover only one speaker. It is a setup check, not enough for fitting or
reporting dataset accuracy. Inspect `summary.json`: failures, unmatched phones,
uncertain evidence, and usable coverage are reported. Every run needs a fresh
output directory so existing results are never silently overwritten.

When the setup check works, process the training split and fit:

```powershell
python -m phoneme_scoring.evaluate_speechocean --split train --output runs/speechocean_train
python -m phoneme_scoring.calibrate_scores runs/speechocean_train/phone_rows.jsonl
```

The fitter writes `models/chinese_phone_calibration.json`, a small JSON regression
model loaded automatically on the next Chinese-profile attempt. It keeps 20%
of the available training speakers for development (at least one), rather than
randomly mixing phones from the same speakers into training and development.
The minimum of 30 usable phones and three speakers is only a software guard;
it is not evidence that a model is sufficiently trained.

Review development MAE, RMSE, correlation, and the constant training-mean baseline
printed by the fitter and saved in the model. The UI identifies estimates as
experimental if the model does not beat that baseline. Then evaluate once on
the official test split:

```powershell
python -m phoneme_scoring.evaluate_speechocean --split test --output runs/speechocean_test
```

Keep test data out of fitting and threshold tuning. The fitter rejects test
records and duplicate phone records. Training is offline; the app never retrains
on a user's attempt. A signature prevents reuse after changes to the acoustic
model, phone mapping, evidence settings, or MFA model configuration.

The evaluation runner permits complete utterances up to 30 seconds independently
of the app's 5-second limit, and reports longer clips as failures. It does not
trim recordings while retaining full-sentence labels. CPU inference over a whole
split can take substantial time. Each utterance is flushed to disk as it finishes.
Batch commands do not resume automatically after an interrupted run.

## Implemented scope

- Chinese-profile selection, persistence in results, and UI reset on selection.
- SpeechOcean aggregate-label loading, official split selection, and speaker IDs.
- Word/phone indexing from MFA, with conservative matching to human annotations.
- Raw phoneme evidence plus optional estimated human phone ratings from 0 to 2.
- Small ridge regression using signed model margin, segment duration, evidence
  frame count, and phone identity. The acoustic model stays frozen.
- Uncertain, unsupported, single-frame, and unseen-phone cases abstain.
- Raw evidence is preserved when calibration is absent, malformed, or incompatible.
- Rating agreement and coverage reports. No automatic pass/fail or error threshold.

The JSON also documents word and sentence annotation fields for future work.
Word accuracy, stress, fluency, sentence prosody, and overall scores are NOT
predicted by this version. Completeness is retained raw because the dataset
documentation and examples disagree on its scale. Mispronunciation labels are
retained in word metadata but are not used as confirmed substitution diagnoses.

SpeechOcean's phone rubric distinguishes incorrect/omitted sounds (0), correct
but heavily accented sounds (1), and correct sounds (2). Aggregated ratings can
be fractional. Do not label every value below 2 an error. This corpus cannot
establish validity for every Chinese language, Portuguese learners, or other
target accents. Existing TH, IH/IY, and AE/EH practice groups are not assumptions
about an individual learner's errors.

Annotation joining intentionally excludes any word whose aligned base-phone
sequence differs from the dataset sequence. Repeated words are kept by position.
This prevents a missing phone from shifting all subsequent labels, but introduces
selection bias. Always report unmatched/excluded phones alongside rating accuracy;
coverage on matched phones is not full-corpus detection accuracy. MFA supplies
estimated boundaries, not human-verified timestamps. Preserved stress labels do
not themselves measure whether the speaker used the correct stress.

## Files added or changed

New: `accent_profiles/chinese.json`, `accent_profiles.py`,
`phoneme_scoring/speechocean_data.py`, `phoneme_scoring/calibration.py`,
`phoneme_scoring/calibrate_scores.py`, `phoneme_scoring/evaluate_speechocean.py`,
`tests/test_chinese_profile.py`, and this guide.

Changed: `app.py`, `pipeline.py`, `feedback.py`,
`phoneme_scoring/align_audio.py`, README.md, and two existing tests updated for
the profile callback argument and new rating column.

The existing phoneme map and raw GOP/CTC scorer are reused. No arbitrary accent
thresholds or fabricated trained weights were added. For an existing checkout,
use this exact base branch or review the included `chinese_profile.patch`; do
not blindly overwrite a newer local version. `main` alone lacks the integrated
app/scoring source needed by these additions.

## Validation performed

Seven profile/adapter/calibration integration tests and the 15 existing scorer
self-tests pass. These use synthetic fixtures and mocked neural/MFA calls, and
do not measure speech accuracy. The full live Gradio UI and actual SpeechOcean
inference were not run in the build environment because the audio/UI packages,
MFA models, and corpus were unavailable.

```powershell
python -m unittest discover -s tests -p test_chinese_profile.py -v
python phoneme_scoring/gop_score.py --self-test
```

Dataset citation: Zhang et al. (2021), "speechocean762: An Open-Source Non-native
English Speech Corpus For Pronunciation Assessment," Interspeech.
