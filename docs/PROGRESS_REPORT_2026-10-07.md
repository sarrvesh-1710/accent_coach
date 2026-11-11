# Accent Coach: implementation and Monday readiness report

**Prepared:** October 7, 2026, America/Chicago  
**Presentation:** Monday, October 12, 2026  
**Scope assessed:** three-sentence, local CPU pronunciation-practice prototype.

## Executive summary

The app now analyzes a learner recording using the selected sentence, without requiring a reference recording. Optional example audio remains a listening aid. Acoustic comparison is available as an explicitly enabled engineering feature and cannot block the learner analysis.

The software is working as a practice prototype. It is **not yet a validated pronunciation grader**. The current pretrained model supplies experimental sound evidence; the team has not trained a new accent model. Removing the reference dependency does not, by itself, improve the phoneme model's accuracy: that model already scored learner audio against expected phoneme labels, rather than against the example waveform.

**Estimated Monday prototype readiness: 70%.** This is a planning estimate using the weighted checklist below, not a measured accuracy or a percentage of all possible product work. The largest unfinished area is evaluation with human-reviewed recordings.

## 1. Changes implemented

| Area | Change and practical effect |
|---|---|
| Analysis pipeline | `run_attempt()` defaults to learner-only analysis. Missing, absent, or corrupt references no longer prevent learner DSP, alignment, or phoneme inference. |
| Optional comparison | `compare_reference=True` enables the existing reference DSP/comparison. Its failures remain separate from required learner stages. |
| Prompt configuration | Only sentence ID and text are required. Reference paths and lesson metadata can be omitted. Removed the stale settings instruction claiming the prompt texts were missing. |
| Beginner interface | Main flow is **Read → Record → Practice**. Examples are collapsed and optional. The comparison switch defaults off inside Engineering details. Graphs appear there only when comparison was requested and succeeded. |
| Feedback | Default results no longer discuss reference duration or unavailable reference pitch. Practice tips remain tied to the selected lesson, rather than being presented as detected mistakes. |
| Result contract | Schema version 2 records whether reference comparison was requested. Pronunciation grade is explicitly null/unvalidated, and independent spoken-word verification is explicitly not implemented. |
| Alignment output | Saved MFA word intervals and phone-to-word associations support target-word evaluation. For example, the vowel in “ship” can be distinguished from the vowel in “is.” These remain alignments to supplied text, not recognized speech. |
| Lesson consistency | Corrected the displayed vowel for “here” to match the installed MFA dictionary entry; connected-speech variants still need human review. |
| Startup | `app_2.py` now honors `GRADIO_SERVER_PORT` if 7861 is occupied. |
| Evaluation tools | Added offline pronunciation coverage audit, real-model reference-free smoke checks, and a 36-recording evaluation manifest/runner. |
| Documentation | Updated README instructions, optional-reference behavior, commands, and validation limitations. |

Main implementation files: `pipeline.py`, `feedback.py`, `app_2.py`, `app.py`, `phoneme_scoring/align_audio.py`, and `phoneme_scoring/settings.json`.

New tools: `tools/audit_pronunciations.py`, `tools/check_reference_free.py`, and `tools/evaluate_recordings.py`.

The pretrained model weights, pinned model revision, and experimental scoring gates were retained. No new model was trained, no pronunciation threshold was invented, and no accuracy claim was added. Existing audio files were retained. Changes are local; this update has not been committed or pushed to GitHub.

## 2. Verification completed

### Automated checks

- **43/43 repository tests passed.** Coverage includes default learner-only analysis, missing/corrupt optional references, result saving, UI state clearing, word association, and evaluation-label handling.
- **15/15 phoneme-scoring self-tests passed.** These include frame timing, CTC evidence handling, alignment failures, and invalid boundaries.
- **58 automated checks passed in total.** These check software behavior; they do not measure pronunciation accuracy.
- Windows/Gradio test cleanup emitted non-failing asyncio ResourceWarnings. The running server started without an error in its startup log.

### Real CPU model checks

The three existing local example recordings were used **only as learner inputs**. All reference paths were removed from the prompt objects in memory. No reference files were deleted and no comparison stage ran.

| Sentence | Operational result | Observed elapsed time | Evidence result |
|---|---|---:|---|
| I think so | Passed: DSP, MFA, model inference, save | 112.94 seconds | Limited; 7 diagnostic phone comparisons |
| The ship is here | Passed: DSP, MFA, model inference, save | 96.57 seconds | Limited; 8 diagnostic phone comparisons |
| That is a bad bed | Passed: DSP, MFA, model inference, save | 93.31 seconds | Limited; 11 diagnostic phone comparisons |

All three overall statuses remain **partial**, reflecting uncertain or unsupported phoneme evidence. An operational pass means the software completed its stages; it does not mean the speaker passed pronunciation. Timings are one observation per sentence on this laptop, not a performance benchmark.

The initial smoke-check assertion incorrectly required an `available` evidence status and flagged honest `uncertain` results as failures. That assertion was corrected to distinguish completed inference from model-load failure, regression-tested, and the saved real-run outputs were rechecked successfully. Model thresholds and results were not changed to make the check pass.

Evidence files:

- `runs/reference_free_smoke.json`: real-run outcomes and paths to complete saved results.
- `runs/pronunciation_audit.json`: dictionary/tokenizer coverage report.
- `runs/team_evaluation.json`: current evaluation coverage report.

Run folder names use UTC and may show October 8 even though this work was completed on October 7 in Chicago.

### Coverage and interface checks

- All **40 configured phoneme labels** exist as non-special tokenizer entries.
- Every word in the three prompts appears in the installed MFA dictionary.
- This is label/word coverage, not proof that allophones or pronunciation judgments are correct.
- The updated page was visually inspected. Examples and Engineering details are collapsed; the optional comparison checkbox is off.
- The app is running at **http://127.0.0.1:7861/**.
- The in-app browser reported **No microphone found**. Live microphone capture remains a manual browser/device check. No new browser upload was used for the real-model checks; those ran directly through the local pipeline.

## 3. Readiness estimate

| Workstream | Available points | Earned estimate | Basis and remaining gap |
|---|---:|---:|---|
| Learner audio and DSP pipeline | 20 | 20 | Working audio preparation, quality handling, and reference-free processing |
| Alignment and model integration | 25 | 20 | Real inference and phone mapping work; evidence quality/phonetic correctness need evaluation |
| Learner interface | 20 | 18 | Simple workflow working; microphone and beginner usability checks remain |
| Validation | 25 | 7 | Automated checks and smoke checks complete; human-reviewed evaluation has not been run |
| Delivery and demo preparation | 10 | 5 | Local startup and documentation available; teammate reproduction, shared-repo delivery, and rehearsal remain |
| **Total** | **100** | **70** | **Planning estimate for the three-sentence prototype** |

A trustworthy automatic pronunciation grade is still an unfinished capability. This report's 70% figure must not be shown to learners as pronunciation accuracy or represented as 70% accuracy to the TA.

## 4. Remaining deliverables and proposed owners

### Sarrvesh — recording quality and repeatability

1. Coordinate **36 consented recordings**: 3 speakers × 3 prompts × 2 takes × 2 conditions (expected and deliberately altered target sound).
2. Use the prepared `data/evaluation/manifest.json`. Supply WAV paths; do not treat the requested condition as a human assessment.
3. Check every recording is readable, contains the intended full utterance, stays within 5 seconds, and has no obvious clipping or excessive background noise.
4. Record actual analysis times and report failures for all 36. The current observed baseline is approximately 1.5–2 minutes per recording.

**Deliverable:** completed manifest, 36 usable clips or an honest shortfall count, and a timing/failure summary.

### Lucas — phoneme evidence and validation

1. Have a listener review the target sound and assign `expected`, `altered`, or `unclear`, with a reviewer identifier. A second listener should review ambiguous cases.
2. Review MFA target-word boundaries and dictionary alternatives. Alignment can fit the supplied sentence even when a speaker says something else.
3. Use speakers S01/S02 for development. Reserve S03's **12 clips** before changing any rules or thresholds.
4. Run the evaluation tool. Inspect the **18 matched pairs** and target-word evidence, including unavailable/uncertain results. Report coverage and whether margins respond consistently to the deliberate changes; do not equate positive margins with correct pronunciation.
5. If sparse CTC evidence does not distinguish these pairs, investigate sequence-aware scoring or a more suitable assessment model. Do not simply lower gates or force a numerical grade.

**Deliverable:** reviewed labels, target evidence report, held-out findings, and a documented decision about whether grading is supportable. This small study is preliminary, not sufficient for a general-purpose accent grader.

### Parthiban — interface and demonstration

1. Test live microphone recording in Chrome or Edge, all 3 sentences, upload, playback, retry, and sentence changes.
2. Test missing example audio, no upload, silence, and an over-5-second file. Each should provide a useful response and avoid stale results.
3. Have at least **3 people unfamiliar with the code** complete one practice attempt without coaching. Record where they get stuck.
4. Verify a second team machine can follow the README. Prepare a recorded backup demo and saved example outputs.

**Deliverable:** signed manual checklist, usability notes, reproducible startup instructions, and backup demonstration.

### Shared scope decisions

- **Independent word verification is not implemented.** For Monday, explicitly require the displayed sentence. Later, evaluate an ASR-based content check; recognition output also has errors and must not become a pronunciation grade by itself.
- **Validated grades/percentages are not implemented.** They require labeled data, calibration, and held-out assessment.
- **No new custom accent model has been trained.** Continue with pretrained inference for this milestone; a new training effort requires its own dataset and evaluation plan.
- **Translations and language-neutral onboarding remain open.** Simpler English alone does not make the interface accessible to someone who cannot read English.
- **Public deployment is not done.** This is a localhost prototype. A hosted website needs a separate deployment plan for the CPU/MFA runtime, storage, and concurrency.

## 5. Schedule to Monday

| Date | Priority | Completion evidence |
|---|---|---|
| Thu, Oct 8 | Collect and review recordings; check microphone | Manifest with actual clips, labels, reviewer IDs; browser test results |
| Fri, Oct 9 | Evaluate development speakers; resolve reproducible faults | Evaluation JSON and issue list with evidence |
| Sat, Oct 10 | Run held-out speaker; complete novice usability check | Held-out report including uncertainty; 3 usability observations |
| Sun, Oct 11 | Freeze demo version, reproduce setup, rehearse | Agreed Git version, all software checks passing, backup video/results |
| Mon, Oct 12 | Present demonstrated capability and limitations | Live or backup three-sentence practice demo; actual validation counts |

## 6. How to check the updated app

Open http://127.0.0.1:7861/ while the current server is running. If you close it, start from the repository folder:

```powershell
.\.venv\Scripts\python.exe app_2.py
```

If another program uses that port, either use the existing app or choose a different port:

```powershell
$env:GRADIO_SERVER_PORT = "7862"
.\.venv\Scripts\python.exe app_2.py
```

1. Select a sentence and record/upload its WAV. Leave the example and Engineering sections closed.
2. Press **Check my recording** and allow roughly two minutes on this laptop.
3. Expect a practice tip and access to your recording. A limited-evidence message in Engineering details is possible and is not a pronunciation failure.
4. Open Engineering details. Confirm reference audio, reference DSP, and comparison show **skipped** with the default setting.
5. Download the JSON: expect `reference_comparison_requested: false`, grade `value: null`, and spoken-word verification `not_implemented`.
6. Change the sentence or choose **Try again**. Confirm the previous analysis clears.

Commands for the project team:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe phoneme_scoring/gop_score.py --self-test
.\.venv\Scripts\python.exe tools/check_reference_free.py --verify-saved
.\.venv\Scripts\python.exe tools/evaluate_recordings.py
```

The final command currently reports **36 planned, 0 analyzed, 0 human-reviewed** in the new evaluation manifest. Populate the manifest, then add `--run` to perform inference. Existing historical recordings are not automatically relabeled or counted as this study's data.

## Suggested presentation claim

“Our prototype accepts one of three practice sentences, processes learner speech locally, aligns expected sounds, and provides experimental phoneme evidence plus guided practice. Reference recordings are optional. We have verified the software pipeline; human validation and reliable pronunciation grading remain our next milestone.”
