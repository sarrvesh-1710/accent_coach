# Day 2 Phase 4: confirmed-text backend foundation

October 13, 2026. Branch: `feature/speed-free-speech`. Changes are local.

## Inspection and coordination boundary

Read the approved TEAM_INTERFACE contract, FREE_SPEECH_DESIGN, contract examples, pipeline, assessment guards, alignment and phoneme scorer. Fetched origin: Lucas's `origin/feature/profiles-personalization` remains at `8c4fa45`, with shared setup documents but no storage/auth implementation.

Consequently, no real storage interface was changed or duplicated. The public approved submit/session APIs remain unchanged. The `AnalysisStore` protocol below is a **proposed internal integration seam**, not an agreed new public API or a claim of coordination completed with Lucas. Lucas and integration owner Sarrvesh must reconcile these method names with his implementation before wiring production. The only store supplied here is a clearly labeled test double inside the tests.

## Worker input

`confirmed_analysis.run_confirmed_attempt(snapshot, settings)` accepts a trusted server-resolved snapshot. It must never be exposed directly to browser JSON.

```python
snapshot = {
    "attempt_id": "server-attempt-id",
    "job_id": "server-analysis-job-id",
    "input_revision": 2,
    "confirmed_text": "I think so.",
    "transcript_confirmed": True,
    "target_accent": "en-US-general-american",
    "learner_audio_id": "server-original-asset-id",
    "learner_audio_role": "learner",
    "learner_audio_path": "server-resolved private path",
    "source_audio_sha256": "verified original-file digest",
    "transcription": {
        "status": "completed",
        "recognized_text": "I think so.",
        "source_audio_sha256": "same original-file digest",
        "audio_sha256": "prepared PCM digest",
        "model_id": "recognizer model ID",
        "model_revision": "recognizer revision"
    }
}
```

This is an illustrative schema, not runtime evidence. Role, confirmation and path must come from trusted storage; client assertions do not establish them. There is no client user-ID authorization shortcut.

## Execution and reuse

- Validate identity/revision, accent, confirmation and learner role, then run Phase 3 text/dictionary preflight.
- Validate recording limits and original-file hash. Copy verified bytes into a temporary private worker directory so alignment and scoring consume the same audio even if the upload changes.
- Reuse the existing shared pipeline lock, audio preparation, MFA `align_audio`, alignment validator, `score_phonemes`, score validator and `summarize_assessment` guards.
- MFA receives the normalized **confirmed** text. Raw confirmed text remains in the result. There is no preset lookup or reference recording.
- Match MFA word labels/count/order to prepared tokens. Plan TH/S-T-F, IH/IY and AE/EH comparisons by aligned segment identity. The sequence scorer's only change adds an optional segment-ID selector; old preset targets retain the old spelling-based behavior.
- Retain attempt/job/revision, learner asset ID, original/prepared hashes and saved recognition provenance in the unpublished result. Report measured analysis queue/processing/stage milliseconds. Queue time here measures the local lock wait, not a future external scheduler delay.
- Clean up temporary audio/MFA artifacts. Do not write a second persistent history store.

## Outcomes and safeguards

Public sound outcomes remain `supported`, `practice`, or `inconclusive`; no percentage grade or claim of a confirmed pronunciation error. Unsupported target phones remain inconclusive. Sequence abstention and clipping guards are retained. Dictionary-missing words fail preflight rather than producing pronunciation labels.

ASR must be completed, carry model provenance, match both original/prepared audio hashes, and normalize to the confirmed words before sound judgments can be shown. Otherwise confirmed-text alignment is diagnostic only and all planned results remain inconclusive. No arbitrary-text target-variant whitelist is introduced.

Ambiguous word mapping returns completed processing with an explicit `ALIGNMENT_WORD_MISMATCH` limitation and no guessed sound identities. Unsupported occurrence context is similarly explicit. No eligible contrast yields `NO_SUPPORTED_TARGETS`, not a perfect result.

Operational alignment/model failure returns failed analysis with no sound judgments. Existing public `MODEL_UNAVAILABLE`/`TIMEOUT` codes are used; internal reasons distinguish `ALIGNMENT_FAILED`, `INVALID_ALIGNMENT`, and `PHONEME_ANALYSIS_FAILED`. Error messages do not expose exception paths. Invalid audio and missing confirmation use their approved public codes.

## Authorized resolution and stale publication

`execute_confirmed_analysis(auth, attempt_id, job_id, input_revision, *, store, settings)` is a synchronous internal adapter, not the public queue submission function.

Lucas's implementation must provide these operations or equivalent wrappers:

1. `resolve_analysis_snapshot`: authenticate the opaque auth context; authorize owner access to attempt, job and original learner asset; verify explicit confirmation, revision, active processing state and analysis job kind; return an immutable server-resolved snapshot. Missing/deleted/unauthorized resources raise `PermissionError` and receive a generic `ATTEMPT_UNAVAILABLE` response.
2. `publish_analysis_if_current`: **atomically** compare owner, existence, active job ID/kind/state, input revision, text and learner asset identity before storing the result. Return false for obsolete, cancelled, deleted or superseded work. A separate read followed by write is insufficient.

The adapter checks returned attempt/job/revision identities, then publishes only through the second operation. Rejected publication returns `REVISION_CONFLICT` without sound results. The fake store demonstrates these semantics under a lock; it does not establish production security. Cancellation can discard results even if expensive computation has already started.

Preflight must also run before the future public submission queues a job. The worker repeats validation defensively. Auth, ownership, immutable assets and accurate role classification remain mandatory storage responsibilities; a caller bypassing the trusted adapter is not protected by a hash or role string alone.

## Verification actually run

- 13 focused tests passed. Real components: WAV preparation, transcript preparation against a fixture dictionary, validators, assessment guards, and CTC sequence arithmetic/segment selection.
- Mocked components: MFA and phoneme inference. Storage is an explicitly fake in-memory test class, not production persistence/auth.
- Cases cover no-preset analysis, confirmed transcript delivery, original audio/hash/asset identity, attempt/job/revision retention, repeated sound occurrences, stale revisions/retries/text/audio changes, deletion/cancellation and ownership changes during processing, unauthorized client user IDs, generated-role rejection, ASR mismatch/provenance loss, uncertainty/unsupported/practice outcomes, clipping, missing confirmation, missing vocabulary, ambiguous word mapping, no targets, alignment/model failure and timeout.
- Full suite: 116 tests, 115 passed, one existing Windows symlink test skipped, no failures. This includes existing preset pipeline and sequence-evidence regressions. Afterward, failure results were hardened to clear partial sound results and the focused tests were rerun: all 13 passed.
- No real MFA/model end-to-end run or production storage test was performed in this phase. Test fixtures and mocks are not pronunciation-accuracy evidence.

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_confirmed_analysis.py -v
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py' -v
```

Logs: `runs/day2-phase4-focused.log` and `runs/day2-phase4-regression.log` (ignored by Git).

## Files and next work

New: `confirmed_analysis.py`, `tests/test_confirmed_analysis.py`, this report. Modified: optional occurrence selector in `phoneme_scoring/sequence_evidence.py`. Existing Phase 2/3 local changes were preserved. No UI, preset entry point, dictionary, generated-audio implementation, model threshold or dependency changes.

Next: Lucas implements/reconciles the authorized snapshot and atomic publication boundary; Sarrvesh integrates public submission, preflight, confirmation and worker dispatch without bypassing it. Then test real recordings with actual MFA/scoring, including repeated words and contractions, followed by ownership/revision races against real storage. Parthiban's generated assets must have distinct trusted roles and must never resolve as learner assets.
