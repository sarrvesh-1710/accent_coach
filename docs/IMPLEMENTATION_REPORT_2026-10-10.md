# Accent Coach implementation report

**Date:** October 10, 2026 (Chicago)  
**Presentation:** Monday, October 12, 2026  
**Status:** Implemented and tested locally. Changes have not been committed or pushed in this session.

## What the app can now do

The new `app_2.py` experience requires only a selected sentence and the learner's recording. It does not load a reference recording, compare reference pitch, or penalize differences in reference duration. The five-second input limit still applies.

1. **Check the spoken words independently.** Whisper base.en transcribes the audio without receiving the selected sentence as a hint. A disagreement asks the learner to check the sentence or try again. Recognition can be wrong, so this is not a pronunciation failure.
2. **Locate speech sounds.** MFA aligns the selected sentence with compatible audio. MFA provides timing and dictionary phone labels; it does not independently grade pronunciation. Alignment is skipped for a clear sentence mismatch.
3. **Compare target sounds using the neural model.** The existing wav2vec2 phoneme model supplies probabilities. A new CTC sequence calculation compares the expected phone sequence with configured target substitutions, summing valid paths over the recording, including blank frames. This replaces reliance on a single-frame margin for the new target result.
4. **Show understandable feedback.** The main card reports that the model supports the expected sound, favors an alternative sound, or has insufficient evidence. It provides a practice action. Detailed model results and processing messages remain expandable.
5. **Avoid unsupported judgments.** Unverified content, clipping, unsupported context, weak local evidence, or close comparisons prevent sound judgments. Each attempt saves its transcript, model evidence, statuses, and audio locally.

### Current assessment scope

| Sentence | Assessed sound | Tested alternatives |
| --- | --- | --- |
| I think so | TH in think | S, T, F |
| The ship is here | IH in ship | IY |
| That is a bad bed | AE in bad | EH |

Other sounds may appear as practice hints or technical diagnostics. They are not all assessed by the new decision rule. In particular, the vowel in **bed** is not separately assessed.

## Software and model changes

- Added `speech_content.py`: independent CPU speech recognition and sentence compatibility checks.
- Added `phoneme_scoring/sequence_evidence.py`: log-space CTC forward calculation and target-substitution comparisons.
- Added `assessment.py`: combines content and audio-quality checks with target evidence.
- Updated `pipeline.py`, `gop_score.py`, `feedback.py`, and `app.py`: new processing stages, guarded feedback, and results schema 3.
- Updated `app_2.py`: removed the reference player and comparison control; added reference-free assessment messages.
- Updated `prompts.json` and scoring settings: explicit target contrasts and limited lexical variants such as ship/sheep.
- Added model setup and real-recording check tools; extended the evaluation tool and automated tests.
- Updated README setup and method documentation.

Whisper uses `openai/whisper-base.en`, pinned revision `911407f4214e0e1d82085af863093ec0b66f9cd6`. The existing phoneme checkpoint remains `facebook/wav2vec2-xlsr-53-espeak-cv-ft`, pinned revision `2c733782da5604684829819a5eb744c193fe9398`. Models were downloaded to the ignored local cache; runtime inference uses local files on the CPU. No new model was trained and no recordings were uploaded by the model setup or checks.

## Verification completed

**56 repository tests and 15 phoneme-scoring self-tests passed: 71 automated tests total.** These cover CTC path calculations against brute-force enumeration, repeated tokens, impossible paths, decision signs, abstention, sentence mismatches, missing recognition, quality guards, and UI state handling.

Six local operational checks also passed. These checks confirm processing and expected safeguards, **not pronunciation accuracy**. Existing recordings in the references folder were used only as learner inputs; reference fields were removed during these checks.

| Input/check | Observed behavior |
| --- | --- |
| Existing think recording | Recognized sentence matched; TH comparison was too close, so insufficient evidence was shown. |
| Existing ship recording | Recognized sentence disagreed; alignment was skipped and no sound judgment was shown. |
| Existing bad/bed recording | Recognizer returned a permitted target-word variant; model supported AE in bad. This does not confirm the word bed was pronounced correctly. |
| Partner's think recording | Recognized sentence matched; model supported TH over the configured alternatives. |
| Think recording with ship selected | Sentence mismatch blocked alignment and sound judgment. |
| Synthetic silence | Recording rejected before recognition/alignment. |

Full alignment/scoring cases took approximately **24–40 seconds** on this laptop. These timings are observations from a few clips, not a performance guarantee. The app allows extra time for CPU processing.

The updated page was opened and visually inspected at `http://127.0.0.1:7861/`. The in-app browser reported no microphone device, so live microphone capture remains a manual browser/device check. Real recordings were tested directly through the pipeline rather than by browser upload automation.

## Important limitations

- **There is still no validated pronunciation grade or percentage.** The new categories describe experimental model evidence. A model preference is not proof of a correct or incorrect sound.
- The default positive/negative sequence-margin boundary is **±1 nat**, an uncalibrated rule with an uncertain region. It must be evaluated before being used as a correctness threshold.
- CTC predictions can still be sparse. The sequence calculation considers all valid paths, but it does not manufacture additional independent evidence.
- The comparison is conditioned on MFA's selected dictionary sequence and configured substitutions. It is not a complete GOP implementation or a detector for all substitutions, insertions, deletions, stress, rhythm, or accent identity.
- Speech recognition disagreed with the existing ship recording. Review that recording and test fresh speakers; do not weaken checks merely to make it pass.
- The 36-recording human evaluation manifest currently has **zero supplied recording paths and zero completed reviewer labels**. Automated tests do not replace this evaluation.

## How to run and check it

The updated app was left running on port 7861. Open `http://127.0.0.1:7861/`. If restarting is necessary, use this PowerShell command from the repository folder:

```powershell
.\.venv\Scripts\python.exe app_2.py
```

If port 7861 is occupied, first open its existing page rather than starting a second copy. To deliberately use another port:

```powershell
$env:GRADIO_SERVER_PORT = '7862'
.\.venv\Scripts\python.exe app_2.py
```

Repeat automated checks with:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe phoneme_scoring/gop_score.py --self-test
.\.venv\Scripts\python.exe tools/check_assessment.py
```

The last command uses recordings already present on this laptop. Missing files are reported as not run. It is an operational check, not a pronunciation benchmark. Its summary is saved in `runs/assessment_smoke.json`.

For another team machine, follow README setup for Python dependencies, MFA, and the phoneme model, then download the added ASR model once:

```powershell
.\.venv\Scripts\python.exe tools/setup_content_model.py
```

## Finishing touches and tests before Monday

### 1. Human-reviewed recordings — Lucas and the team

Complete the existing 36-recording manifest with real clips from three speakers and reviewer labels. Include expected target sounds, deliberate target substitutions, wrong/missing words, and unclear recordings. Keep one speaker separate from any threshold adjustment. Review uncertain labels rather than assuming intended pronunciation equals actual pronunciation.

**Deliverable:** populated manifest, reviewed labels, and an evaluation summary reporting sentence-check mismatches, expected/alternative decisions, uncertain cases, and false-positive/false-negative counts with denominators. Report coverage as well as agreement; excluding uncertain cases can hide poor coverage. This small set is exploratory and is not sufficient to establish broad accent-grading accuracy.

```powershell
.\.venv\Scripts\python.exe tools/evaluate_recordings.py --run
```

### 2. Audio and failure checks — Sarrvesh

Test the three prompts with fresh normal recordings. Also test silence, background noise, clipped audio, a file longer than five seconds, an invalid upload, and an intentionally different sentence. Confirm no unusable recording produces a positive sound judgment. Check that varying speaking speed does not create a reference-duration penalty.

**Deliverable:** a short checklist with input name, expected behavior, actual behavior, and saved run ID. Preserve failures for investigation. Recheck the existing ship recording in particular.

### 3. Complete interface run-through — Parthiban

Use Chrome or Edge to test microphone permission, recording, upload, playback, check, try again, and sentence switching. Confirm switching input clears old results and only the current attempt is displayed. Verify missing model/MFA conditions show a recoverable message. Check text and controls at presentation resolution and on a narrow screen.

**Deliverable:** one successful full user flow for each prompt plus documented error/retry flows. Success here means the software completes or abstains appropriately, not that every recording earns positive feedback.

### 4. Freeze the presentation build — whole team

After the checks, commit and push the tested code, record the commit and model revisions, and rehearse on the actual presentation laptop. Prepare consented demo clips and screenshots as a fallback. Confirm locally cached models work without an internet connection. Explain to the TA that MFA locates sounds and the neural model compares target hypotheses; the prototype supplies experimental feedback rather than a validated accent grade.

**Deliverable:** reproducible setup, frozen code version, test results, and a two-minute demo showing a supported target, an uncertain result, and a wrong-sentence retry.

## What remains beyond this demo

A trustworthy grade requires more human-labeled recordings, validated phone mappings and alignment, evaluation across speakers and recording conditions, and calibration on separate data. Multilingual instructions and spoken/visual practice guidance would also improve accessibility. The current interface remains English. These tasks cannot be replaced by inventing a percentage from model probabilities.
