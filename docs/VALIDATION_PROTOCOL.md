# Human validation: required before grading

## Keep intended speech separate from observed speech

An instruction to say “sink” is not proof that S was actually produced. Reviewers must listen to each recording and label the actual target sound as expected, altered, or unclear. Record reviewer identity and speaker permission. Do not infer a human label from the model's transcript, margin, or suggested practice cue.

## Minimum exploratory batch

Use the existing 36-row manifest at `data/evaluation/manifest.json`: three speakers, three core prompts, two repeats, and expected/altered conditions. It is currently a collection plan, not completed evaluation. Reserve S03 for held-out evaluation before inspecting results for threshold changes. Extra lessons and noisy/invalid inputs require additional clips; this small batch is not broad validation across accents or ages.

Add a second reviewer for disagreements and uncertain clips; resolve them by listening or retain “unclear.” Keep raw reviewer decisions in a separate review sheet when adjudicating. Deliberate changes should include TH/S/F, IH/IY, and AE/EH. Also check missing/extra words, wrong sentences, background noise, clipping, quiet speech, and natural pace differences.

## Run and summarize

Fill relative WAV paths, consent flags, reviewer names, and human_target_label in the manifest. Keep speakers entirely within one split. Then:

```powershell
.\.venv\Scripts\python.exe tools/evaluate_recordings.py --run
```

The tool rejects mixed speaker splits and duplicate IDs. It reports per split and sound:

- Reviewed clear examples and unreviewed/unclear examples.
- Decisions versus uncertain/unavailable outcomes.
- Correct decisions, false support (altered labeled as expected), and false alternative (expected labeled as altered).
- Coverage: decisions divided by reviewed clear examples.
- Agreement on decided examples, with its denominator.

Pronunciation accuracy remains unset as a product grade. Agreement on this small reviewed set must not be advertised as general accuracy. Do not exclude uncertain examples without reporting coverage.

To summarize an existing results.json without rerunning models, add its `result_path` to the manifest row and use `--reuse-results`. Ensure the file belongs to that exact recording; the tool verifies the selected prompt but cannot establish reviewer provenance.

## Inspect alignment and recognition

```powershell
.\.venv\Scripts\python.exe tools/export_alignment_review.py
.\.venv\Scripts\python.exe tools/audit_pronunciations.py --dictionary C:/path/to/english_us_arpa.dict
```

`runs/alignment_review.csv` exports recent target boundaries, durations, audio paths, recognized text, and model outcomes. Human columns are intentionally blank. Listen around target boundaries in an audio editor and mark whether they cover the intended sound. Valid numeric boundaries alone are not accurate alignment. The dictionary audit checks word/token coverage, not correct allophones or natural pronunciations.

Recognizer/model disagreement is expected in some cases: the recognizer may normalize “sink” to “think” while the phoneme model favors S. Compare raw audio and the separate outputs. `word_differences` in saved results records insertions, deletions, and substitutions in recognized text. Content mismatch still causes abstention; do not relax this gate merely to get positive feedback.

## Stop/go for the demo

The demo is ready to present as experimental feedback when setup checks and automated tests pass, all lessons have verified configuration/dictionary coverage, real inputs can complete or abstain appropriately, and the team can show reviewed examples of supported, alternative, and uncertain outcomes. If false support remains frequent, present that limitation and keep feedback exploratory. A numeric grade requires a separately validated decision rule and much more representative data.
