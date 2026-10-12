# Team interface v1: week-one integration contract

Status: proposed implementation contract approved for repository setup by Sarrvesh; teammates should review before changing it. These interfaces are not yet implemented. Existing app callbacks and result JSON keep their current format until adapters are added.

## Scope and common base

Starting application: commit `2a3352f`. All three new feature branches start at the same foundation commit containing this document. Initial target accent ID: `en-US-general-american`. Input modes: `preset`, `custom_text`, `free_speech`. Keep the initial recording limit at five seconds and 10 MB; unsupported words/sounds must produce explicit limitations. Custom text is the first milestone, short free speech with transcript confirmation follows. Only supported sound contrasts are assessed. Synthetic examples are required; voice-preserving conversion is a stretch goal. No percentage grade or claimed validated accuracy.

## Service boundaries

These are language-neutral contracts, not a requirement to deploy three servers. Start with separate Python modules. Use a separate environment/service if generation dependencies conflict.

- Sessions (Lucas): `create_attempt(auth_context, input_mode, target_accent)`, `get_attempt(auth_context, attempt_id)`, `list_attempts(auth_context)`, `delete_attempt(auth_context, attempt_id)`, `get_practice_suggestions(auth_context)`.
- Input (Sarrvesh, through Lucas's storage API): `attach_recording(auth_context, attempt_id, audio_upload)`, `confirm_text(auth_context, attempt_id, text, expected_revision)`.
- Analysis (Sarrvesh): `transcribe(auth_context, attempt_id, input_revision)`, `analyze(auth_context, attempt_id, input_revision)`.
- Generation (Parthiban): `generate_example(auth_context, attempt_id, input_revision)` and future `convert_accent(auth_context, attempt_id, input_revision)`.

The server loads audio, confirmed text and accent from the authorized attempt snapshot. Do not trust a browser-supplied owner ID, raw file path, transcript or accent as an authorization boundary. Pass identifiers across components, not unrestricted disk paths. Authentication context is server-issued and never saved in the session JSON.

## Session fields and types

See `contracts/examples/session.json` for a fictional development example.

| Field | Type / meaning |
| --- | --- |
| schema_version | integer, initially 1 |
| attempt_id | opaque string, unique per session |
| user_id | opaque owner string assigned by authenticated server context |
| created_at, updated_at | UTC ISO-8601 strings |
| input_mode | preset / custom_text / free_speech |
| lesson_id | string or null; never required for free speech |
| input_revision | integer >= 1 |
| target_accent | supported accent ID |
| learner_audio_id | opaque asset ID or null |
| recognized_text | string or null; preserve recognition output |
| confirmed_text | string or null; assessment/generation require confirmation |
| transcript_confirmed | boolean |
| jobs | transcription, analysis, example_generation and accent_conversion job records |
| sound_results | array; empty before assessment, not evidence of perfect pronunciation |
| generated_assets | array; each contains audio_id, type and input_revision |
| limitations | array of plain-language strings |

Job record: `job_id` (string or null), `input_revision` (integer), `status`, `timings_ms` (object of nonnegative numbers), `error` (null or error object). Status is `not_requested`, `queued`, `processing`, `completed`, `failed`, or `cancelled`. A completed job can return inconclusive findings. Timing values are measurements, not targets; record cold/warm conditions separately.

Sound result: `word`, `word_index` (zero-based), `expected_phone`, `outcome` (`supported`, `practice`, `inconclusive`), `alternative_phone` (string or null), `message`, `calibrated` (false for this release). Optional segment boundaries and diagnostic margins retain explicit units. Adapt existing `expected_supported`, `alternative_favored`, and `insufficient_evidence` to these outcomes at the boundary. Never reinterpret margins as percentages.

Asset type: `synthetic_example` or `voice_converted`. Learner audio remains a separate immutable asset. Generated assets must never become assessment input or human evaluation labels.

## Response envelope

Successful job submission: `ok`, `attempt_id`, `input_revision`, `job_id`, `status` (normally queued). Consumers read updated session state for completion. Failure: `ok: false`, identifiers where available, and `error: {code, user_message, retryable}`. Never return stack traces, credentials or raw storage paths. Examples are in `contracts/examples/` and are development fixtures, not real findings.

Suggested errors: `INVALID_AUDIO`, `UNSUPPORTED_TEXT`, `CONTENT_MISMATCH`, `TRANSCRIPT_CONFIRMATION_REQUIRED`, `UNSUPPORTED_ACCENT`, `REVISION_CONFLICT`, `BUSY`, `TIMEOUT`, `MODEL_UNAVAILABLE`, `ATTEMPT_UNAVAILABLE`.

## Revision and cancellation rules

1. Recording replacement, confirmed-text edit, or target-accent change increments input_revision atomically. Uploading a new recording clears recognition, confirmed text and confirmation. Text/accent edits preserve the learner audio.
2. Invalidate sound results and generated asset links after an input change. Cancel superseded jobs where possible. Retain original recognition separately from corrected text.
3. Workers submit results with job_id and input_revision. Storage accepts them only if both still match the active job, revision and owner, and the attempt is not deleted.
4. Deletion marks an attempt unavailable before cancelling jobs and removing its assets. Late results cannot recreate it; cleanup temporary outputs from stale jobs. Do not bypass this with direct folder writes.
5. Generation and analysis have independent statuses. Failure in either does not erase the other result. Whether they run simultaneously depends on resource measurements.

## Security and recommendations

Lucas owns centralized authorization; every operation including playback, download, conversion and deletion invokes it. Reject access by user B to user A's identifiers. Development mocks must never be enabled on a public deployment. Do not commit learner recordings or authentication secrets.

Recommendations may use user-selected goals, completed practice and usable target findings. Inconclusive is not a mistake; synthetic clips are not human performance. No improvement percentage without a validated measurement.

## Change coordination

Each owner reviews this contract on Day 1. Changes require a small PR with an example payload update and review from affected teammates. Add fields compatibly where possible; breaking changes increment schema_version. Integration checks must cover revision changes, independent failures, authorization and deletion during processing.
