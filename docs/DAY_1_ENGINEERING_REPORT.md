# Day 1 engineering report

**Date:** October 12, 2026, America/Chicago
**Owner:** Sarrvesh Mahadevan
**Scope:** establish the speed baseline and design short custom-text/free-speech support.

## Executive summary

The existing reference-free backend processed all nine benchmark attempts and saved results. Fresh workers took 30.99–32.81 seconds; repeated attempts took 20.47–21.63 seconds. MFA accounted for approximately 94–95% of repeated-run wall time, making alignment the first performance investigation target.

Free speech is not implemented. Repository tracing identified required lesson IDs, preset transcript checks, and manually selected sound targets as the primary dependencies. The team lead accepted the interface direction and four bounded milestone decisions. No application/model behavior was changed, no speed improvement was implemented, and pronunciation accuracy was not validated.

## 1. Baseline and environment: verified

- Agreed application starting commit: `2a3352f23a379a7f885b222b6dc23a3015d2283d`.
- Current HEAD: `8c4fa455621079da003134eb67b8d23080e00475`, shared team setup commit. The committed difference from the application baseline consists of documentation, contracts, fixtures and tooling, not application runtime code.
- Current branch: `feature/speed-free-speech`.
- Repository: `C:/Users/sarrv/Documents/Codex/2026-09-15/re/accent_coach`.
- Windows 11; Python 3.13.1 in `.venv`; Intel Core i7-1360P, 12 cores/16 logical processors. Benchmark used CPU inference with two configured model threads.
- Installed: PyTorch 2.14.0+cpu, Transformers 5.17.0, Gradio 6.28.0, NumPy 2.2.6, SciPy 1.15.3. MFA 3.3.7 runs in the separate `accent-coach-mfa` Conda environment through local settings.
- Cached pinned models: Whisper `openai/whisper-base.en` revision `911407f4214e0e1d82085af863093ec0b66f9cd6`; phoneme model `facebook/wav2vec2-xlsr-53-espeak-cv-ft` revision `2c733782da5604684829819a5eb744c193fe9398`.
- Working-tree checkpoint before handoff completion: modified `docs/TEAM_INTERFACE.md`; untracked `docs/FREE_SPEECH_DESIGN.md`, `tools/benchmark_pipeline.py`, and this report. This describes the pre-handoff checkpoint; see the completion addendum below.

The website health endpoint responded during Phase 3. It was an already-running local app; server startup was not timed or independently revalidated through a fresh launch.

## 2. Executed checks and processing result

| Executed check | Established result |
| --- | --- |
| `.venv/Scripts/python.exe -B tools/check_installation.py` | Ready; 12 valid lessons, required package checks, cached models and MFA command passed. Artifact: `runs/setup_check.json`. |
| `.venv/Scripts/python.exe -B -m pip check` | No broken requirements found. |
| GET `http://127.0.0.1:7861/site-health` | Service ready; public launch false. |
| `.venv/Scripts/python.exe -B tools/benchmark_pipeline.py` | Exit 0; three clips, three attempts each; all nine complete through the required backend path; zero failures/retries. |

Every benchmark run had content match, available alignment and sequence evidence, and successful feedback/save stages. All nine retained overall `partial` status because per-segment evidence was uncertain; think/ship also reported DSP warnings. This is successful processing with limited evidence, not a pronunciation pass or validated grade.

No full unit/regression suite, custom/free-speech implementation tests, private-user authorization tests, or new browser recording/upload workflow were executed in these phases. Tests listed in the design are proposed, not passed.

## 3. Benchmark evidence

Inputs were existing synthetic clips under `web_assets/examples`, submitted as learner inputs with reference comparison disabled. Each clip received a new worker for its first run and the same worker for two repeats. These are controlled software fixtures, not human accuracy samples.

All times are seconds:

| Clip (duration) | Condition | Backend total | ASR/content stage | MFA stage | Phoneme stage | Audio + DSP |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| think (1.73 s) | Fresh worker | 32.37 | 9.66 | 20.11 | 1.73 | 0.05 |
| think | Repeat 1 | 20.86 | 0.61 | 19.85 | 0.38 | 0.01 |
| think | Repeat 2 | 20.47 | 0.61 | 19.48 | 0.36 | 0.01 |
| ship (1.91 s) | Fresh worker | 32.81 | 9.41 | 20.57 | 1.72 | 0.06 |
| ship | Repeat 1 | 21.63 | 0.82 | 20.36 | 0.43 | 0.02 |
| ship | Repeat 2 | 21.36 | 0.72 | 20.22 | 0.40 | 0.02 |
| bad_bed (2.01 s) | Fresh worker | 30.99 | 9.16 | 19.75 | 0.93 | 0.08 |
| bad_bed | Repeat 1 | 21.22 | 0.68 | 20.09 | 0.42 | 0.02 |
| bad_bed | Repeat 2 | 21.16 | 0.77 | 19.91 | 0.46 | 0.02 |

Repeat averages: think **20.66 s**, ship **21.49 s**, bad_bed **21.19 s**. Corresponding MFA shares: **95.16%, 94.38%, 94.39%** of summed repeat wall time.

**Measured conclusion:** MFA is the dominant repeated-run stage. Recognition and phoneme stages become faster when the worker reuses loaded models; MFA remains near 20 seconds.

**Not yet measured:** how much MFA time is lock waiting, Conda/process startup, model initialization, or actual alignment. Those are hypotheses to investigate, not attributed timings.

Measurement limits:

- Total is the `AnalysisService.run` call, including fresh-worker start, saving and return. It excludes launcher imports, browser upload, UI queueing and rendering.
- Stage timers include first-use imports/loading. ASR/content is not pure transcription inference. Model loading and server startup lack independent measurements.
- Feedback and saving lack individual timers; displayed stage sums need not equal total.
- Reused models do not mean reused transcripts/results: each attempt recomputed analysis in a fresh run directory. Model files and OS disk caches were already present, including on fresh-worker runs.
- Only two repeats per clip, one laptop, serial execution, different clip lengths/phoneme counts, and uncontrolled background activity. Compare fresh/repeat within each clip.
- An earlier exploratory timing file used different run conditions; it is not pooled into this controlled table. The previously reported 40–60-second user experience is not claimed to be fixed.

Evidence: `runs/phase3-baseline-20261012T153332Z.json` includes raw timings, run IDs, versions and hashes; `runs/phase3-benchmark-console.log` records completion.

## 4. Preset dependencies: inspected code

| Actual location | Dependency and required direction |
| --- | --- |
| `app_2.py:302`, `:367`; `analysis_service.py:24` | Dropdown and worker pass lesson ID, not runtime text. Add mode/snapshot adapters while retaining preset calls. |
| `pipeline.py:192` | Rejects IDs absent from `prompts.json`. Add a confirmed-input path without catalog insertion. |
| `speech_content.py:13`, `:42`; `pipeline.py:239` | Recognition is coupled to preset comparison. Separate transcription and confirmation; preserve independent recognition. |
| `pipeline.py:252`; `align_audio.py:259` | MFA receives preset text, not recognized/confirmed text. Pass confirmed transcript with revision provenance on the new route. |
| `prompts.json:18`; `pipeline.py:218`; `gop_score.py:246` | Assessment requires manual word/phone/alternative targets. Select supported occurrences from validated alignment. |
| `lesson_catalog.py:43`; `sequence_evidence.py:62` | Unique spelling-plus-phone assumption prevents repeated-target occurrences. Use word/phone indices. |
| `align_audio.py:266`; `tools/audit_pronunciations.py:28` | MFA dictionary/acoustic model required; existing coverage audit scans presets only. Add runtime dictionary preflight. |
| `gop_score.py:158`; `sequence_evidence.py:41` | Segment-level unsupported handling exists, but any unsupported context phone stops sequence comparison. Preserve inconclusive handling; do not drop phones to produce scores. |
| `app_2.py:27`, `:118`, `:219`; `feedback.py:43` | Hints, tips, IPA, highlighting and example playback depend on lesson metadata. Use sound-specific hints or omit unavailable aids. |
| `app_2.py:369`; `gop_score.py:213` | Existing input changes clear UI results and scoring checks audio fingerprints; no confirmed-text revision exists. Add stale-result publication checks. |
| `attempt_history.py:48`; `site_server.py:57` | Lesson-filtered local history and broad local run-file access are not private authenticated sessions. Lucas owns integration. |

Files named `align_audio.py`, `gop_score.py`, and `sequence_evidence.py` above are under `phoneme_scoring/`. No learner-result cache was found that currently reuses analysis by transcript; the new risk is obsolete results arriving after future transcript edits.

## 5. Agreed interface and milestone decisions

The lead authorized the shared interface direction and explicitly accepted these four choices after the design review:

1. Five-second/10 MB recordings; at most 12 words and 200 characters, enforcing both text bounds.
2. Corrections are allowed, but unresolved ASR disagreement/unavailability keeps sound feedback inconclusive. Confirmed-text diagnostic alignment is allowed; confirmation never fabricates an ASR match.
3. Missing dictionary words are named and assessment is paused for correction or another sentence. Unknown words are not mistakes. Automatic pronunciation generation is deferred.
4. Initial directed contrasts: TH against S/T/F, IH against IY, AE against EH, in eligible occurrences beyond preset words. No eligible targets produces an explicit coverage limitation.

Other agreed boundaries:

- Accent: `en-US-general-american`; modes: `preset`, `custom_text`, `free_speech`.
- Required session fields: `user_id`, `attempt_id`, `input_mode`, `recognized_text`, `confirmed_text`, `target_accent`, `learner_audio_id`, `analysis_status`, `sound_results`, `generation_status`, `generated_audio_id`, `generated_audio_type`, `timings`.
- Supporting fields include `input_revision`, optional lesson ID and independent transcription status. Job states: queued/processing/completed/failed/cancelled; null before submission.
- Sound outcomes: supported/practice/inconclusive. Practice means a possible model-supported substitution, not a verified error. Completed processing is not correct pronunciation.
- Server-authenticated ownership and immutable original learner assets. Generated examples have separate roles and must never become analysis inputs through app asset routing. Arbitrary external uploads cannot be certified as human speech.
- Original recognized text remains separate from corrected confirmed text. Existing diagnostic JSON is retained behind adapters; session timing units are milliseconds.

**Handoff update:** TEAM_INTERFACE now records lead approval and the four accepted decisions; contracts/examples now uses the agreed flat format. These are design examples, not implemented services.

## 6. Proposed implementation: not built

Custom text: type intended sentence -> record -> independently transcribe -> inspect/correct -> confirm -> analyze the original audio against confirmed text.

Free speech: record -> independently transcribe -> inspect/correct -> explicitly confirm -> analyze. Preserve preset one-click behavior; changing preset wording enters custom-text mode.

Revision rules: replacing audio, changing confirmed text, or changing relevant mode/accent invalidates dependent work. Audio replacement clears recognition and confirmation. Text edits retain original recognition but invalidate alignment, sound results and generated examples. Dirty unconfirmed editor text disables new analysis. Atomic publication requires current owner, attempt, input revision and active job ID. Late results/progress must not update the current view; deleted sessions cannot be recreated by workers.

Use existing MFA and scoring functions with a trusted confirmed-input snapshot, an extracted recognition-only function, dictionary checks, and occurrence-based target planning. Preserve evidence safeguards, original audio playback, worker timeouts and preset APIs. No broad refactor or UI redesign is needed.

Full design and proposed tests: `docs/FREE_SPEECH_DESIGN.md`. Its decision section now records the lead's acceptance of all four choices.

## 7. Changes and unexecuted work

| Artifact | Day 1 change/status |
| --- | --- |
| `docs/TEAM_INTERFACE.md` | Revised interface proposal; working-tree modification, not committed. |
| `tools/benchmark_pipeline.py` | Approved isolated benchmark update; nine real runs executed; currently untracked. |
| `docs/FREE_SPEECH_DESIGN.md` | New design, signatures, invalidation rules, integration plan and proposed tests; no implementation. |
| `docs/DAY_1_ENGINEERING_REPORT.md` | This new handoff report. |
| `runs/setup_check.json`, controlled benchmark JSON/log, individual run artifacts | Generated local evidence; not a substitute for committed application changes. |

No application refactor, dependency installation/upgrade, model change, server migration, commit or push was performed in these phases. Existing regression tests were inspected but not executed as a suite. There is no evidence yet that custom/free-speech, private profiles, or generated-session integration works.

## 8. Independent teammate handoff

| Owner | Interface/work to implement | Coordination point |
| --- | --- | --- |
| Sarrvesh | `submit_transcription(auth, attempt_id, *, input_revision)` and `submit_analysis(auth, attempt_id, *, input_revision)`; runtime text, timings, sound-result adapter. | Coordinates `app_2.py`/`pipeline.py`; preserves existing preset API. |
| Lucas | `create_attempt`, `attach_recording`, `confirm_transcript`, `get/list/delete_attempt`, authorized assets and atomic revision/job publication. | Client IDs are not authorization; enforce ownership for playback/download/delete as well as job submission. Do not assign legacy recordings to new users automatically. |
| Parthiban | `submit_generation(auth, attempt_id, *, input_revision, kind="synthetic_example")`; consumes confirmed text and produces distinct generated asset. | Generation failure does not fail analysis; stale generation cannot publish after edits. True voice conversion remains a stretch goal. |

Use exact public signatures/field definitions in TEAM_INTERFACE; reconcile examples first. Submit small coordinated changes to `team/week1-foundation` per FILE_OWNERSHIP. This report is local; it has not been sent to teammates or pushed.

## 9. Remaining blockers and Day 2 priorities

Unresolved implementation choices: exact normalization/tokenization and MFA contraction reconciliation; auth provider and persistent storage; local-history migration and retention; generation model/license/voice and local versus external provider; dispatcher/polling implementation and deployment. The design's bounded serial-worker approach is a proposal, not a measured multiuser capacity result.

The current model cannot validate overall accent quality or certify genuine errors. Broader vocabulary/contrast accuracy, corrected-transcript consistency, and human-recording evaluation remain unfinished. No evidence yet supports a server purchase.

### Next three actions, in priority order

1. **Make the handoff contract consistent.** Record accepted decisions in the contract/design, synchronize JSON examples, settle normalization/indexing, and agree Lucas's asset/revision boundary. Deliverable: consistent contract/examples and focused schema/ownership/revision test specifications, with implementation status explicit.
2. **Implement the smallest confirmed-transcript path.** Extract recognition; add input snapshot, lexicon preflight, occurrence-based targets and confirmation controls; integrate revision checks and preserve presets. Deliverable: automated confirmation/stale-result/unsupported-input/preset tests plus real preset and custom/free-speech smoke runs. Do not claim completion until those execute successfully.
3. **Measure inside MFA before optimizing.** Separate lock waiting, process startup and alignment where observable; retain identical input/work for comparisons. Deliverable: attributed timing evidence and one bounded optimization proposal. Keep caching, parallelism and hardware claims conditional on measurements.

Suggested 20-minute meeting: 4 minutes baseline/timings, 5 minutes agreed flows/safeguards, 6 minutes teammate interfaces/blockers, 5 minutes Day 2 deliverables.

## Day 1 handoff completion addendum

The lead authorized completing the remaining Day 1 handoff. The contract/design approval wording and fictional JSON payloads have been synchronized. `docs/DAY_1_BENCHMARK.json` provides portable measured evidence without local machine paths. `docs/DAY_1_TEAM_HANDOFF.md` is the teammate entry point. Application code, model behavior and Day 2 implementation remain unchanged. The original report sections describe the earlier phase checkpoint; repository commit/push confirmation is reported separately after completion.

Handoff verification executed: `tools/check_team_fixtures.py` passed all five fixture integrity/format checks (synthetic_think, synthetic_wrong_sentence, synthetic_custom, silence, noise); a read-only Python check validated the three JSON examples, matching attempt/revision identities, nine benchmark records, and benchmark-script syntax. `git diff --check` passed. These checks do not validate implemented auth, free speech, or pronunciation accuracy. No additional speech-model runs were needed.
