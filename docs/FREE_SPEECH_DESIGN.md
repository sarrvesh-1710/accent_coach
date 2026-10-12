# Minimal custom-text and free-speech implementation

Design only. October 12, 2026. Inspected against commit `8c4fa45` and the current working tree. No application implementation is included.

## 1. Contract authority and scope

The project lead approved the TEAM_INTERFACE baseline and all four milestone decisions on October 12, 2026. The contract header and JSON examples have been reconciled. This design follows its public fields, statuses, ownership checks and signatures. These interfaces remain unimplemented; pipeline schema version 3 is retained behind adapters.

First milestone:

- Target accent: `en-US-general-american` only.
- Existing five-second recording and 10 MB upload limits; WAV input remains supported through the existing Gradio audio component.
- Short English text, initially 1–12 normalized words and at most 200 characters; the character cap is an accepted new input bound.
- Presets continue working. Custom text and free speech require explicit transcript confirmation before pronunciation analysis.
- Initially assess expected TH against S/T/F, IH against IY, and AE against EH. Broader phone mapping is not evidence of broader assessment validation.
- No reference recording, overall accent grade, percentage, or claim of verified pronunciation errors.
- Keep current CPU models, worker reuse, timeouts, MFA execution, and evidence thresholds. Performance optimization is a separate change.

## 2. Code findings that determine the design

| Current location | Consequence |
| --- | --- |
| `app_2.py:302`, `:367`; `pipeline.py:192` | Input is an existing lesson ID; unknown IDs are rejected. |
| `speech_content.py:42` | Independent recognition and preset comparison are one function. Separate them without changing inference settings. |
| `pipeline.py:239`, `:252` | ASR mismatch stops preset alignment; MFA receives preset text. Preserve the preset safeguard. |
| `phoneme_scoring/align_audio.py:241` | MFA already accepts a text argument. No replacement alignment engine is needed. |
| `phoneme_scoring/align_audio.py:204` | Word IDs already exist, but matching to confirmed-text token indices needs explicit validation. |
| `phoneme_scoring/gop_score.py:213` | Audio fingerprint checking exists; add transcript/revision provenance around it. |
| `phoneme_scoring/sequence_evidence.py:62` | Word spelling plus phone must match exactly once. Add occurrence-based target addressing. |
| `phoneme_scoring/sequence_evidence.py:41` | Unsupported context invalidates sequence comparison. Preserve abstention rather than dropping phones. |
| `assessment.py:18`; `app_2.py:91` | Content gates and result text must distinguish confirmation, ASR agreement, and sound evidence. |
| `attempt_history.py:48`; `site_server.py:57` | Local history is lesson-filtered and not an authenticated private session store. Lucas owns that integration. |

## 3. User flows

### Custom text

1. Select Custom text; type the intended sentence. This is editor state, not yet `confirmed_text`.
2. Validate basic English text/length and dictionary coverage; explain unsupported tokens without changing them silently.
3. Record or upload learner audio. The server stores an immutable learner asset and returns its ID.
4. Submit transcription. Show the original recognized words separately from the editable intended sentence.
5. The user listens, corrects the intended text, and presses Confirm transcript. Confirmation identifies the intended words, not proof of acoustic accuracy.
6. Enable Analyze only for the accepted revision. Analysis receives that confirmed text and the corresponding learner asset.
7. Show experimental supported/practice/inconclusive results, or an actionable processing error. Generation is an independent optional action.

### Free speech

1. Select Free speech and record up to five seconds. No target sentence is required before recording.
2. Transcribe the immutable original learner recording independently.
3. Populate an editable transcript with recognized words; show playback and require confirmation even if the user makes no edits.
4. Confirm the intended text; validate text/lexicon coverage and increment the revision if the confirmed text changes.
5. Analyze the confirmed text against the same learner recording.
6. If ASR fails, retain the recording and allow retry or manual confirmation. Manual text can be aligned for diagnostics, but absent independent content evidence yields inconclusive sound feedback under the initial policy.

### Presets

Keep the current dropdown, tips, and one-click preset analysis route. Selecting a preset remains the explicit choice of intended text; existing independent ASR checks and known `content_alternatives` still apply. Add a Correct transcript action when needed; editing preset wording switches to `custom_text`, clears lesson-specific targets/tips, and requires confirmation. Keep historical preset `prompt_id` values and legacy APIs intact.

## 4. Data boundaries and signatures

Use the approved public interfaces unchanged:

```python
create_attempt(auth, *, input_mode, target_accent, lesson_id=None) -> dict
attach_recording(auth, attempt_id, upload, *, expected_revision) -> dict
confirm_transcript(auth, attempt_id, text, *, expected_revision) -> dict
submit_transcription(auth, attempt_id, *, input_revision) -> dict
submit_analysis(auth, attempt_id, *, input_revision) -> dict
submit_generation(auth, attempt_id, *, input_revision,
                  kind="synthetic_example") -> dict
```

These are adapters to implement, not current callables. Lucas supplies server identity, asset resolution, session persistence, and atomic publication. Sarrvesh supplies speech-job implementations. Keep a single serial analysis worker; do not introduce a distributed queue for this milestone. Submission records a job and returns the contract receipt; a bounded dispatcher invokes the existing worker, and the UI reads authorized session snapshots. When capacity is unavailable, return BUSY rather than accumulating unbounded work. UI polling reads storage only; it must not submit duplicate jobs.

Proposed internal additions, based on existing path-based functions:

```python
# speech_content.py: move existing Whisper inference here unchanged.
transcribe_audio(audio, settings) -> dict
# Keep check_content(audio, prompt, settings) as the preset wrapper.

# New small transcript preparation module; no model inference here.
prepare_transcript(text, settings) -> dict
select_targets(alignment, prepared_transcript) -> list[dict]

# pipeline.py: trusted server snapshot, never a browser-supplied dictionary.
run_confirmed_attempt(snapshot, *, progress_callback=None) -> dict
# Keep run_attempt(learner_path, prompt_id, ...) for existing callers.
```

`prepare_transcript` returns validated normalized tokens, token indices, lexicon coverage, and normalization version. `select_targets` runs after word/phone alignment, validates token correspondence, and returns occurrence-specific supported targets. Reuse only the small common audio/alignment/scoring/save sections needed by both pipeline routes; do not rewrite the DSP or scoring algorithms.

### Stage data

| Boundary | Minimum data |
| --- | --- |
| Server to transcription | Owner, attempt/job/revision IDs; learner asset ID/role; server-resolved original path; raw-file hash; model/settings identity. |
| Transcription to session | `recognized_text`, recognizer status/provenance, audio identity/hash, actual timings. Preserve the original text on correction. |
| Confirmation to session | Text, expected revision; server produces confirmed text, normalized token sequence, tokenization version, new revision, and text hash. |
| Session to analysis | Immutable snapshot: owner, attempt/job/revision IDs, mode, optional lesson ID, target accent, learner asset/path/hash, recognized and confirmed texts, ASR provenance, normalized tokens/text hash, settings identity, server-owned work directory. |
| Analysis to MFA | Learner waveform on the existing time-preserving 16 kHz analysis path; normalized confirmed transcript; configured lexicon/acoustic model; unique job directory. Record transcript source as user-confirmed for the new route. |
| MFA to phoneme model | Audio fingerprint, confirmed-text hash/revision, word/phone intervals, word indices, selected pronunciation phone indices, unique segment IDs, and supported target alternatives. |
| Analysis to feedback/store | Contract sound outcomes, reasons, limitations, job status, measured timings, and internal diagnostic artifact ID. Publication requires matching owner/job/revision. |

Keep the original waveform unmodified for playback. The deterministic mono/resampled analysis representation remains linked to it; distinguish the raw-file hash from the existing PCM fingerprint. Gradio temporary filenames are not permanent audio identity.

Session fields remain exactly those in TEAM_INTERFACE, including separate learner/generated audio IDs, nullable job statuses, and `sound_results`. Detailed hashes and model/configuration versions can live in server job metadata. A backend `run_id` identifies one execution; an `attempt_id` identifies the session and may contain multiple revisions/jobs. Preserve legacy diagnostic JSON using an adapter, not field renaming throughout the application.

`timings` uses milliseconds at the contract boundary. Convert existing `timings_sec` explicitly; do not treat model-load-plus-inference stage measurements as pure inference. Missing measurements stay omitted.

## 5. Transcript normalization and content policy

Proposed minimal normalization: trim and collapse whitespace; normalize curly apostrophes; case-fold for word comparison; allow ordinary sentence punctuation as separators; keep contractions intact. Store the exact confirmed display text separately from normalized alignment text. Use one versioned tokenization function for lexicon lookup, word indices, comparison, and alignment input. Reject digits, emoji, markup, non-English-letter tokens, and unsupported punctuation patterns with a specific instruction to rewrite them. Never silently discard meaningful input. This is English-only scope, not automatic language detection.

Enumerate words from zero in the normalized confirmed transcript. Associate MFA word intervals to this ordered sequence, validating labels and counts under the same normalization. Do not align indices using a dictionary keyed by spelling. If MFA splits/merges a contraction or supplies unknown labels inconsistently, abstain for the affected mapping; do not guess. Each selected phone is addressed by word index plus phone index, with segment ID retained for diagnostics.

Initial content policy for custom/free speech:

- Matching normalized ASR and confirmed words: eligible for experimental sound assessment, subject to all quality checks. Recognition agreement is not proof of correctness.
- Different words: preserve differences as CONTENT_MISMATCH. Do not change the ASR result to match. The explicitly confirmed text may be aligned for diagnostics, but all published sound outcomes remain inconclusive for this revision.
- Missing/failed ASR: allow confirmed-text diagnostics but publish inconclusive results with a content-verification limitation. Transcription failure remains separately recorded.
- No automatic target-variant whitelist for arbitrary custom sentences. Existing curated preset alternatives remain available only on the unchanged preset route.

This conservative policy permits correction and realignment but can withhold useful feedback on genuine ASR mistakes. Reliable assessment after arbitrary ASR disagreement needs a separately evaluated content-consistency method; forced alignment alone is not that method. Do not expand heuristics or thresholds just to make results appear decisive.

## 6. Revisions, invalidation, and publication

`input_revision` is the authoritative monotonically increasing server version. All mutations use `expected_revision`; stale updates receive REVISION_CONFLICT. A job additionally has a unique job ID. Hashes are integrity checks, not replacements for ownership/revision checks.

| Event | Required effect |
| --- | --- |
| Replace recording | Increment revision; clear recognition, confirmation, alignment/analysis links, sound results, generation links, affected errors/statuses/timings; cancel superseded jobs. |
| Confirm changed text | Increment revision; retain original recognition for this audio; invalidate alignment, targets, sound results, analysis/generation output links and their timings. |
| Reconfirm identical stored text | No revision increment; do not create duplicate work automatically. |
| Edit without submitting | Mark editor dirty locally; hide/mark previous results as belonging to the previous confirmation and disable new analysis/generation until confirm or discard. |
| Change mode, preset, or accent | Invalidate dependent work; changing preset retains the existing recording-reset behavior. Reject unsupported accents. |
| Delete attempt | Mark unavailable first, cancel jobs, remove assets; reject late publication and clean temporary artifacts. |

Before returning a visible result, storage atomically verifies that the session exists, the authenticated owner matches, the revision matches, and the job is still the active job of that kind. Ignore stale progress as well as stale final results. Repeated submission of an active identical revision returns its current receipt rather than starting a duplicate. Explicit retry creates a new job ID.

Always rerun MFA and phoneme analysis after confirmed-text changes. Do not add result caching in this milestone. ASR can be reused for unchanged immutable audio when its model/preprocessing identity is unchanged; retain provenance even if the session revision advances due to a text edit. Reject a late ASR response for an obsolete revision rather than overwriting the editor. Existing in-memory model caches can remain.

## 7. Unsupported inputs, failures, and feedback

| Condition | Minimal behavior |
| --- | --- |
| Empty/unconfirmed/invalid text | Preflight rejection; no new job; TRANSCRIPT_CONFIRMATION_REQUIRED or UNSUPPORTED_TEXT. |
| Missing lexicon words | Return UNSUPPORTED_TEXT with the word list before queueing analysis. Keep recording/text; offer correction. No incorrect-sound result. No G2P model in milestone one. |
| Dictionary/model missing or unreadable | Operational configuration/model error, not evidence that the learner's word is invalid. |
| Valid words but unknown/unmapped MFA phone | Preserve unsupported diagnostic rows; affected feedback is inconclusive with UNSUPPORTED_SOUND. |
| Unsupported phone anywhere in full-sequence context | Preserve the existing sequence abstention; all sequence-dependent targets are inconclusive with UNSUPPORTED_CONTEXT. Do not delete context phones. |
| No eligible contrast in a supported transcript | `analysis_status=completed`, empty sound results, explicit NO_SUPPORTED_TARGETS limitation. No implied perfect score or request to fix pronunciation. |
| MFA process failure, timeout, or invalid output | `analysis_status=failed`; actionable error, no sound judgments. Use contract TIMEOUT or a documented stage-specific ALIGNMENT_FAILED code. |
| Valid alignment but ambiguous word/phone occurrence | Completed response with inconclusive affected results; no guessed occurrence identity. |
| Weak, sparse/ambiguous, out-of-contrast, or too-close evidence | Preserve existing method-specific safeguards; inconclusive outcomes where its rules abstain. Never promote diagnostic frame scores to validated errors. |
| Phoneme model cannot load/run | `analysis_status=failed`, MODEL_UNAVAILABLE or a documented processing error; do not disguise an operational failure as a pronunciation result. |
| Clipping or other existing assessment quality block | Preserve the block; inconclusive sound outcomes and actionable recording advice. |
| Generated example fails | Independent `generation_status=failed`; analysis results remain available. |

Job lifecycle remains `queued`, `processing`, `completed`, `failed`, `cancelled`, with null before submission. Do not map legacy `overall_status=partial` directly to failed; inspect stage outcomes. Preflight rejections are not queued jobs and must not expose previous-revision feedback as current.

Public outcome mapping:

- `expected_supported` -> `supported`: expected sound favored among the tested alternatives.
- `alternative_favored` -> `practice`: possible substitution, explicitly experimental.
- `insufficient_evidence` or unsupported target evidence -> `inconclusive`: no judgment.

The current implementation does not establish genuine verified pronunciation errors. Therefore the UI must distinguish model-supported practice suggestions from uncertainty without calling either a certified diagnosis. No pass/fail grade or confidence percentage. General American is the configured lexicon/example target, not a validated accent classifier.

Feedback hints come from the selected sound/contrast and actual word occurrence. Existing practice examples such as ship/sheep can remain explicitly labeled examples. Missing hints or IPA never block analysis. Hide preset-specific underline/IPA/example controls when no applicable metadata exists.

## 8. Learner versus generated audio

Resolve learner assets server-side through Lucas's store and require role `learner_original`, correct ownership, and matching attempt/audio identity before transcription or analysis. Never accept a generated-audio ID or browser filesystem path as proof of a learner asset. Generation writes a distinct asset role and consumes confirmed text of a specific revision. Playback does not attach it as learner audio; missing learner input must never fall back to generated output.

Generated audio is never used as a scoring reference. Parthiban's generated-example job is independent of MFA/analysis and may proceed after text confirmation, even if assessment is inconclusive. Same revision/publication checks apply.

This enforces separation for app-managed assets. It cannot prove that an arbitrary uploaded WAV was spoken by a human or detect every externally generated/reuploaded file. Synthetic-audio detection is outside this milestone; do not promise that capability.

## 9. Minimum file changes

| File/area | Proposed scoped change |
| --- | --- |
| `app_2.py` | Add mode choice, custom-text field, editable transcript and explicit confirmation action in existing cards. Wire contract adapters and revision-aware results. Retain preset controls and result renderers; no broad visual redesign. |
| `pipeline.py` | Add confirmed-input route using trusted snapshot; bypass lesson lookup for custom/free modes; use saved ASR provenance instead of retranscribing during analysis; supply confirmed text to MFA; plan occurrence targets after alignment; retain legacy preset wrapper and diagnostic format. |
| `speech_content.py` | Extract recognition-only function from check_content; keep existing model cache/inference settings and preset comparison wrapper. |
| `analysis_service.py` | Extend request/response envelope with job kind/ID/revision and immutable payload; dispatch transcription, confirmed analysis, or legacy preset analysis. Retain bounded serial execution and timeout cleanup. |
| New `transcript_input.py` | Small pure validation/normalization and dictionary-coverage helpers, plus occurrence-specific target planner. Parse the exact configured dictionary; do not depend on audit-tool output from another sentence. |
| `phoneme_scoring/align_audio.py` | Preserve current function compatibility; allow accurate optional transcript provenance and validate ordered word correspondence through helper integration. Keep fingerprint and fresh-directory protections. |
| `phoneme_scoring/sequence_evidence.py` | Address new targets by segment/occurrence identity; retain legacy unique-word fallback for presets. No CTC equation/threshold change. |
| `assessment.py`, `feedback.py` | Add explicit new-mode content policy and per-sound hints; preserve preset safeguards; distinguish operational failures from inconclusive results. |
| New thin job/result adapter | Implement approved submit interfaces using Lucas's store and the existing worker; translate outcomes/timings without replacing diagnostic JSON. |
| `attempt_history.py` and Lucas's modules | Authorized history, revision metadata and legacy display compatibility; no implicit ownership of preexisting local recordings. |
| Shared docs/examples/tests | Reconcile approved contract status and JSON examples; add focused tests. Update help text only where the input flow changes. |

No immediate changes to model weights, inference thresholds, DSP algorithms, lesson catalog data, or Python dependencies are required. `app.py` and existing CLI tests continue using legacy signatures. Do not fabricate a preset ID for every custom sentence or append user text to `prompts.json`.

## 10. Focused tests and acceptance criteria

Tests below are proposed, not run in this design phase.

1. Preset regression: all 12 catalog entries remain valid; preset match, allowed target variant, mismatch skip, and reference-free paths preserve existing behavior.
2. Confirmation gate: free/custom modes cannot reach MFA/scoring before explicit confirmation, including direct submit calls that bypass the UI.
3. Corrected transcript: MFA receives the latest normalized confirmed text; original ASR text is preserved; disagreement does not become an automatic match or decisive pronunciation result.
4. Same original audio: all stages resolve the same immutable learner asset; fingerprints agree; substituted files/assets are rejected.
5. Stale work: edit, replace audio, cancel, delete, or retry while jobs are running. Old progress/results/generated links cannot publish, even if computation finishes later.
6. Occurrences: repeated words and multiple same-phone occurrences receive distinct word/phone indices. MFA token-count/label disagreement produces explicit inconclusive output.
7. Lexicon coverage: unknown name/word is listed without an incorrect label; missing dictionary is reported as configuration failure. Invalid tokens are not silently removed.
8. Unsupported context: mapped and unmapped phones retain separate diagnostic outcomes; sequence abstention remains intact. No-target text returns an explicit coverage limitation.
9. Model outcomes: expected-supported, alternative-favored, weak/ambiguous evidence, and clipping produce the correct public outcomes without fabricated grades.
10. Failures: ASR failure, MFA timeout, model-load failure, save failure, and generation failure remain distinct and retryable where appropriate; worker timeout recovery still works.
11. Asset ownership/roles: another user's asset, generated asset as learner input, and unauthorized read/play/download/delete all fail server-side. UI hiding alone does not pass.
12. Limits and escaping: five-second/10 MB bounds, text length, contractions/apostrophes, punctuation, markup and Unicode edge cases; safe rendering and consistent token indices.
13. Real local smoke tests: preset; newly typed known-vocabulary sentence; free-speech recording with confirmed text; corrected ASR with conservative inconclusive outcome. Capture exact artifacts and timings; no claim of accuracy from these tests.

Use pure/unit tests and fake workers for deterministic race/error cases, then a small real-model integration set. Compare latency only for equivalent analysis work. Transcript review time is a user interaction interval, not model processing time.

## 11. Team dependencies and implementation order

1. Sarrvesh: normalization, recognition extraction, runtime analysis adapter and target indexing; test in isolation with fake storage snapshots.
2. Lucas: approved auth/session/asset interfaces, atomic revision updates/publication, deletion, and private playback. A test double is acceptable for development but must not be presented as private authenticated production storage.
3. Sarrvesh: wire the small confirmation controls and session/job adapters after the storage boundary is available. Preserve preset route throughout.
4. Parthiban: independent confirmed-text generation job, generated-asset role, revision invalidation and playback component. Its absence must not block speech analysis.
5. Team: integration tests, model smoke tests, documentation/contract examples, then latency regression check. Shared app/pipeline wiring remains coordinated by Sarrvesh.

## 12. Accepted milestone decisions

The lead explicitly accepted all four choices below after reviewing their tradeoffs. This document records design approval, not completed implementation:

1. Keep the five-second/10 MB bounds and adopt the 1–12 words/200-character input cap.
2. For arbitrary custom/free text, withhold decisive sound feedback when ASR disagrees with confirmed text or is unavailable; permit diagnostic alignment only. This favors caution over immediate feedback on recognition mistakes.
3. Reject unknown dictionary words before analysis in milestone one; postpone automatic pronunciation generation.
4. Keep only the existing directed TH, IH, and AE target contrasts initially; allow explicit no-supported-target results.

Internal reason codes and any additional operational error codes should be documented in the contract/examples PR. Auth provider/storage implementation and generation model selection remain Lucas's and Parthiban's deliverables, respectively. This design does not choose a hosting provider, purchase hardware, or broaden the frontend redesign.
