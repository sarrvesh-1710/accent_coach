# Optional evidence-bound coaching

Implemented locally on `feature/speed-free-speech`, based on `529e28e79fd996b228f8d8309a0642aee5caea6b`. Existing uncommitted UI, playback, storage and performance changes are retained. Nothing is staged, committed or pushed by this task.

## What it does

The saved result renders first, with the original learner recording and the existing recovery/continuation actions. `Explain this result` is a separate action. No transcription, MFA, phoneme inference, speech-worker slot, audio upload or plan update is performed by coaching. The default unconfigured state does not even download the optional coaching JavaScript.

When configured, one authenticated, CSRF-protected request to `POST /api/attempts/{id}/coaching` resolves the owned attempt on the server. The client supplies an evidence fingerprint, language, and (for an external provider) disclosure consent/version, never a trusted user ID or model evidence. The service revalidates ownership and the saved input/result version before reading or publishing coaching. Transcript revision, original audio ID, analysis result, prompt, provider/model, language, catalog and persisted plan changes invalidate reuse. Deletion removes saved coaching. Revoked sessions cannot read it.

The service uses the existing private SQLite database, in a separate `coach_explanations` table. It stores only validated short output, retaining at most three versions per owned attempt. No second persistent session system is introduced. A small startup migration creates the table and deletion trigger. It does not modify existing attempts.

## Conservative result interpretation

Six coaching categories are explicit: `expected_sound_favored`, `alternative_sound_favored`, `target_word_not_confirmed`, `insufficient_evidence`, `audio_quality_issue`, `processing_error`.

Capitalization/punctuation/whitespace alone do not create a missing-target finding. An empty transcript has its own reason. If the target appears but surrounding words differ and the authoritative pipeline has not established qualified sound evidence, the UI explains **insufficient evidence**, not an absent word or a pronunciation error. The existing stricter content gate is preserved; this feature does not bypass it or promote an ineligible sound comparison. Audio-quality coaching requires an actual saved clipping/silence flag. Unsupported coverage and uncertain comparisons remain inconclusive.

There is no change to the application-controlled categories, starting-check completion, result saving or analysis eligibility. Coaching has no API fields capable of changing those decisions. General practice suggestions come only from the existing lesson catalog; starting-check suggestions additionally require the current persisted step to have completed under the existing rules.

## Reviewed-language policy and tradeoff

Versioned evidence: `coach-evidence-v1`. Runtime prompt: `ai_coaching/prompts/explain_v1.txt`, `coach-prompt-v1`. The server provides two short, category/reason-specific approved explanations, approved tip IDs and eligible exercise IDs. The provider selects one explanation verbatim and at most one tip/exercise. The server validates the schema, 45-word/two-sentence bound, exact compatible explanation, IDs and contradictory/unsupported claims. It renders catalog text itself. All browser output uses plain text, never model HTML.

This deliberately restricts creative personalization. It gives a predictable first release that can select a relevant explanation and next exercise without inventing evidence. The tip catalog reuses the app's existing general practice guidance; it is not a measurement of the learner's tongue or mouth. Broader free-form explanations, translations and pronunciation-expert review are future work, not established capabilities.

## Provider setup (not yet configured or live-evaluated)

No runtime AI credentials or approved model were found. Coaching is **disabled by default** and the complete base application works without it. No new dependency was installed: the adapter uses the already declared `httpx` and Pydantic/FastAPI stack.

The adapter accepts an operator-configured Chat Completions-compatible endpoint supporting strict `response_format: json_schema`, enum-constrained string/null fields, `max_completion_tokens`, and the standard `choices[0].message.content` response. The protocol was checked against the [official structured-output documentation](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat). This does not establish compatibility with every provider or model. There is no default model identifier and no assumption that this development agent's model powers the runtime feature.

Set these **server-side environment variables** before starting the app:

| Variable | Meaning |
| --- | --- |
| `ACCENT_COACH_AI_ENABLED` | `1` enables the configured adapter; absent means disabled. |
| `ACCENT_COACH_AI_ENDPOINT` | Exact HTTPS endpoint ending `/chat/completions`. No credentials/query/fragment in URL. HTTP permitted only for exact loopback hosts. Redirects and environment proxy inheritance are disabled. |
| `ACCENT_COACH_AI_MODEL` | Explicit compatible model selected by the operator. No default. |
| `ACCENT_COACH_AI_API_KEY` | Provider credential, server only. Required for external providers. Never paste into client code or commit it. |
| `ACCENT_COACH_AI_ALLOW_EXTERNAL` | Must be `1` to permit a non-loopback endpoint. |
| `ACCENT_COACH_AI_TIMEOUT_SEC` | Initial maximum `5`, permitted `0.1`–`5`. Invalid configuration disables the adapter. |

Use the existing launch command from the project directory: `.\.venv\Scripts\python.exe app_2.py`. Restart after changing server configuration. No external provider has been enabled by this implementation.

Before any external request, the result screen names the configured host and requires an unchecked choice allowing **selected text and limited analysis observations** to leave the computer. Recordings, audio links, account names, email addresses and unrelated History are not sent. The privacy page describes this optional path and saved coaching. Provider retention/training behavior has not been verified; no promises are made. The operator must review the actual service before enabling it. Loopback configuration is a local text-only adapter, not proof that a separately operated local server never forwards requests.

## Speed, timeout and failure behavior

The provider is called only on an explicit click, once per uncached requested explanation. No automatic retries, repair calls or agent loops. The server's monotonic deadline covers lookup, provider, validation and publish, capped at five seconds. The browser also aborts its optional request after at most five seconds. Two coaching generations maximum can be in flight; repeated clicks are suppressed in the UI and duplicate server requests are rejected as busy (or reuse the completed cache).

Leaving or editing detaches/aborts the browser work immediately. An already received server request may finish and save valid coaching for the old owned attempt; it cannot update another attempt or accept stale evidence. Blocking SQLite calls run in a separate thread with a short busy timeout, not the speech pool. Thread cancellation cannot undo a completed valid transaction, so publish rechecks ownership, revision and plan atomically.

Timeouts, invalid output, contradictions, missing credentials, refusals, rate limits and provider failures leave the saved base result untouched. The UI shows: “The extra explanation isn’t available right now. Your result is still ready.” Retry is explicit. Provider errors, credentials and prompt text are not displayed. No live provider latency, new-recording inference speed or pronunciation-detection accuracy improvement is claimed.

## Verification commands and evaluation

- `.\.venv\Scripts\python.exe -m unittest tests.test_ai_coaching -v`
- `node --test tests/session_playback.cjs`
- `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`
- `node --check web_assets/accounts.js`
- `node --check web_assets/result_coach.js`
- `git diff --check`

The new Python tests use actual private SQLite/auth/HTTP code with fake language-model responses; provider protocol tests use `httpx.MockTransport`. JavaScript tests use controlled DOM/HTTP/media doubles. `contracts/evaluations/coaching_v1.json` contains versioned grounding cases and cross-runtime evidence hashes. These are deterministic safety checks, not broad model accuracy or human coaching-usefulness evaluations. A live compatible provider, bounded paid evaluation, learner usefulness review, screen-reader testing and physical-phone testing remain unverified.

See `AI_COACHING_VERIFICATION_2026-11-10.md` for observed counts, browser evidence and performance measurements.

The runtime uses Python 3.11+ (`asyncio.timeout`); this implementation was tested with the existing Python 3.13 environment. In-flight duplicate suppression is scoped to the current app process. A future multi-worker deployment needs a distributed claim/lease before relying on server-side deduplication across workers. The browser duplicate-click guard still applies.
