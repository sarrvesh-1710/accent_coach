# Approved team interface contract

**Status: Approved by project lead Sarrvesh on October 12, 2026; interfaces not yet implemented.** Application baseline: `2a3352f`; shared setup: `8c4fa45`. The lead authorized team decisions and accepted the four milestone limits/policies below. `contracts/examples/*.json` now demonstrates this flat format; examples are fictional, not runtime evidence.

## 1. Scope and compatibility

One week: short free speech, transcript confirmation/correction, feedback on supported sounds, General American synthetic listening examples, private profiles/history, and simple personalization. Voice-preserving accent conversion is a stretch goal. No validated percentage or overall accent grade.

Keep one Python application with separate modules; a separate generation environment is optional if dependencies conflict. Use plain dictionaries at module boundaries. Do not replace existing pipeline result JSON or Gradio output tuples directly.

Inspected current interfaces: `app_2.analyze_recording(path, identity, progress)` calls `analysis_service.run_attempt(path, identity, compare_reference=False, progress_callback=...)`; `pipeline.run_attempt(learner_path, prompt_id, ...)` requires a preset; `speech_content.check_content(audio, prompt, settings)` combines recognition and comparison. `attempt_history.list_attempts(prompt_id=None, limit=50)`, `read_attempt(run_id)` and `delete_attempt(run_id)` have no authenticated owner. The signatures below are proposed adapters, not existing functions.

## 2. Session fields

All keys are present in returned session snapshots. Use null for unavailable scalar values, never fake text, zero scores or empty identifiers.

| Field | Type and meaning |
| --- | --- |
| user_id | Nonempty opaque string, assigned from authenticated server identity; never accepted as proof of ownership from the browser. |
| attempt_id | Nonempty server-generated opaque string identifying one practice session. |
| input_mode | `preset`, `custom_text`, or `free_speech`; preserve preset compatibility. |
| recognized_text | String or null. Original recognizer output for the current learner audio; never overwritten by user corrections. |
| confirmed_text | Nonempty trimmed string or null. Text explicitly accepted by the user; typing/editing alone does not authorize analysis until submitted. |
| target_accent | Initially only `en-US-general-american`; reject unsupported values. This is a configured target, not an inferred user identity. |
| learner_audio_id | Opaque immutable original-audio asset ID or null before upload. No public disk path. |
| analysis_status | null before submission, otherwise one of the five lifecycle statuses below. |
| sound_results | Array of sound-result records, initially empty. Empty never means perfect pronunciation. |
| generation_status | null before submission, otherwise one of the five lifecycle statuses. Independent of analysis_status. |
| generated_audio_id | Opaque output asset ID or null. Exposed only after successful current-revision generation. |
| generated_audio_type | null before output, then `synthetic_example` or `voice_converted`; never label ordinary TTS as converted user speech. |
| timings | Object grouped by job (`transcription`, `analysis`, `generation`); each has measured `queue_ms`, `processing_ms`, and optional `stages_ms`. Missing measurements are omitted; all values are finite nonnegative milliseconds. |

Minimal supporting fields: `schema_version` (1 for this draft), `input_revision` (integer >=1), `lesson_id` (string/null), `created_at` and `updated_at` (UTC ISO-8601), `transcription_status` (same nullable lifecycle enum), `errors` (object keyed by job), and `limitations` (string array). A server-side job record additionally stores job_id, owner, kind and input_revision. This version is a proposal version, separate from existing pipeline schema_version 3.

For week one, keep one active generation job/output per attempt revision. If both example and conversion playback become required together, agree on an assets collection before implementing it.

## 3. Lifecycle and sound outcomes

Job transitions: null -> `queued` -> `processing` -> `completed` or `failed`. Queued/processing jobs may become `cancelled`. Retry creates a new job_id. Cancelling prevents publication even if computation cannot stop immediately. Preflight rejection does not create a queued job.

`completed` means processing produced a usable response, not correct pronunciation. `failed` means an operational error prevented that job's result (for example unavailable model or timeout). `cancelled` means intentionally abandoned or superseded work.

Each sound result contains: `word` (string), `word_index` (zero-based token index in confirmed_text), `phone_index` (zero-based within the selected word pronunciation), `expected_phone` (canonical label), `outcome` (`supported`, `practice`, `inconclusive`), `alternative_phone` (label/null), `reason_code` (string/null), and `message` (plain string). Never identify a repeated word by spelling alone.

- Supported: expected sound favored over tested alternatives, subject to experimental safeguards.
- Practice: a tested alternative was favored; not a confirmed error.
- Inconclusive: no reliable judgment, e.g. unsupported sound, ambiguous alignment or weak evidence.

Example: analysis_status=`completed` with outcome=`inconclusive`, reason_code=`UNSUPPORTED_SOUND` is valid. Model-loading failure instead produces analysis_status=`failed` and an error. If no sounds are supported, return completed with an empty array and an explicit limitation; never report success at pronunciation.

Adapter mapping: existing `expected_supported` -> `supported`, `alternative_favored` -> `practice`, `insufficient_evidence` -> `inconclusive`. Retain diagnostic data separately; do not convert margins into percentages or map pipeline `partial` blindly to failure.

## 4. Agreed Python boundaries (to implement)

`auth` below is a server-validated identity context, not a client-supplied dictionary. Return dictionaries using the session format or job receipt. These can be ordinary Python calls; HTTP endpoints are not required yet.

```python
# Lucas: session/storage boundary
create_attempt(auth, *, input_mode, target_accent, lesson_id=None) -> dict
get_attempt(auth, attempt_id) -> dict
list_attempts(auth, *, limit=50, cursor=None) -> dict
delete_attempt(auth, attempt_id) -> dict
attach_recording(auth, attempt_id, upload, *, expected_revision) -> dict
confirm_transcript(auth, attempt_id, text, *, expected_revision) -> dict
get_practice_suggestions(auth) -> dict

# Sarrvesh: app-facing speech jobs
submit_transcription(auth, attempt_id, *, input_revision) -> dict
submit_analysis(auth, attempt_id, *, input_revision) -> dict

# Parthiban: app-facing audio job
submit_generation(auth, attempt_id, *, input_revision,
                  kind="synthetic_example") -> dict
```

Receipt: `{ok: true, attempt_id, input_revision, job_id, status: "queued"}`. Poll/read the authorized session snapshot for completion. Existing progress callbacks can update job progress internally.

Trusted workers receive immutable server-resolved input snapshots. Lucas's storage layer atomically accepts results only for the matching active job_id, input_revision and owner. Internal processing may keep existing path-based functions; externally, retrieve files through authorized asset IDs. Sarrvesh adapts the preset pipeline to runtime text and separates transcription from transcript comparison. Parthiban consumes confirmed text for examples, and authorized learner audio only for true conversion. Neither worker writes around storage ownership/revision checks.

## 5. Identity, ownership and audio separation

Lucas establishes identity through the selected authentication mechanism. Every read, playback, download, generation, update and deletion verifies attempt ownership, including direct requests. Unauthorized/missing attempts receive a generic ATTEMPT_UNAVAILABLE response. Storage location secrecy is not authorization. Existing directory-wide runs access cannot be used unchanged for private multiuser hosting.

Original learner audio and generated outputs have distinct asset roles. Analysis accepts only the learner asset. Example audio is a listening aid, never a scoring reference, substitute learner input, human label or personalization evidence. Generated files inherit their attempt's access controls and deletion policy. Recommendations may use user preferences and usable findings; inconclusive outcomes are not mistakes.

## 6. Confirmation, edits and stale results

Free speech: record -> independent transcription -> show editable transcript -> explicit confirmation -> analysis/generation. No automatic confirmation of recognized text. Recognition failure asks for retry/correction; it never fabricates words.

Confirmation uses expected_revision to reject concurrent edits. Recording replacement, confirmed-text change or accent change increments input_revision atomically; clear current sound results, generated output links, affected statuses, errors and timings. Replacement audio also clears recognized_text and confirmed_text. Text edits retain original recognition. Accent changes may retain confirmed text. An unsent editor change disables new submission until confirmed or discarded.

Cancel superseded jobs; reject late results whose revision or job_id differs. Keep older audit records separate from current results. Deletion first marks the attempt unavailable, then cancels jobs and removes assets; late workers cannot recreate it. Clean up their temporary outputs.

User confirmation expresses intended text, not proof that audio contains it. Preserve recognition differences and existing quality guards. A correction must not simply force content status to match. For custom/free speech, unresolved ASR disagreement or unavailable ASR permits confirmed-text diagnostic alignment only; published sound feedback remains inconclusive. Existing preset content-alternative rules remain unchanged.

## 7. Errors, missing data and limits

Error envelope: `{ok: false, error: {code, user_message, retryable}}`, with attempt/revision/job identifiers when available and authorized. Keep stack traces and disk paths in internal logs. Failed jobs store this error under their job key; analysis and generation failure remain independent.

Codes: INVALID_AUDIO, TRANSCRIPT_CONFIRMATION_REQUIRED, CONTENT_MISMATCH, UNSUPPORTED_TEXT, UNSUPPORTED_ACCENT, REVISION_CONFLICT, BUSY, TIMEOUT, MODEL_UNAVAILABLE, ATTEMPT_UNAVAILABLE. Unsupported individual sounds normally yield inconclusive outcomes, not a failed whole job. Unknown words require explicit handling; never silently invent reliable pronunciation evidence.

Accepted milestone limits: five seconds, 10 MB, 1–12 words and at most 200 characters, enforcing both text limits. Unknown dictionary words reject analysis preflight with UNSUPPORTED_TEXT; no incorrect-sound label or automatic pronunciation generation. Initially assess TH against S/T/F, IH against IY, and AE against EH at eligible occurrences; no eligible targets yields an explicit coverage limitation. Missing learner audio blocks transcription/analysis. Missing confirmed text blocks analysis/generation. Missing generated audio disables its playback. Optional fields do not make a recording unusable. Do not upload audio to an external provider without an agreed consent/data-handling flow.

## 8. Ownership and coordination

| Owner | Modules/interfaces |
| --- | --- |
| Sarrvesh | audio_io.py, dsp_features.py, speech_content.py, analysis_service.py, assessment.py, analysis/alignment modules; transcription/analysis contracts, speed and free-speech preparation. Coordinates app_2.py and pipeline.py integration. |
| Parthiban | New generation module, isolated generation dependencies/tests and playback component; synthetic-example contract and conversion investigation. |
| Lucas | New auth/session-storage modules, attempt_history.py adapter, profile/history components and ownership tests; storage/auth contracts and personalization. |

Coordinate changes to app_2.py, pipeline.py, site_server.py, shared CSS/JS, requirements files, settings, prompts, phoneme mappings and this contract. Schema/status/unit changes require affected teammate review. Target small PRs at team/week1-foundation; do not change another owner's interface without agreement. See FILE_OWNERSHIP.md for branch assignments.

## 9. Unresolved decisions for team review

October 13 integration note: `accounts.practice_jobs.PracticeJobs` now supplies the agreed method names for custom/free sessions over Lucas-derived SQLite/account storage. HTTP `/api/sessions` snapshots use the flat fields above. Auth is an opaque login-session token revalidated in storage, never a browser user ID. This integration is local and awaiting commit/team review; earlier design-only status describes the original baseline. Internal domain exceptions are converted to the public error envelope by the HTTP adapter. Preset routes remain compatible with the prior account patch. See `INTEGRATION_COMPLETION_REPORT.md` for actual tests and limits.

- Lucas: authentication library/provider, persistent store, deployment destination and legacy local-history migration. Do not automatically assign existing recordings to a new user.
- Sarrvesh + Lucas: exact normalization/tokenization, word indexing and MFA contraction reconciliation. The conservative ASR-disagreement policy above is accepted; a more permissive acoustic-consistency method needs evaluation.
- Sarrvesh: implement dictionary preflight and occurrence targeting under the accepted scope. Expanding duration, contrasts or vocabulary fallbacks requires a later decision.
- Parthiban: TTS model/provider, license, supported target voice, local versus external generation, and conversion feasibility.
- All: processing concurrency, polling mechanism, retention/deletion requirements, and whether simultaneous example/conversion outputs are needed.
- All: implement contract, authorization and stale-job integration tests. Contract approval and synchronized fictional examples do not establish implementation or passing integration tests.
