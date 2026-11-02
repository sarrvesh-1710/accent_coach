# Accent Coach: pre-presentation fixes and verification

October 18, 2026. Branch `feature/speed-free-speech`; HEAD remains `e7f57d9ce37f95cb6c3cc30a870c8aae284656d7`.

## Outcome

The confirmation/transcription race, misleading History navigation, and analysis retry presentation have been addressed. The previously tested MFA compiled-dictionary cache is now enabled in local settings and populated by real inference. The user restarted the app; the new process responds successfully and serves the updated JavaScript. No staging, commits, pushes, schema changes, model upgrades, or scoring-threshold changes.

This report supersedes earlier statements that the local dictionary cache was disabled. It does not supersede historical benchmark records or turn incomplete browser/human tests into passes.

## Changes delivered

| Area | Change | Evidence |
| --- | --- | --- |
| Transcript confirmation | UI disables confirmation and analysis while transcription is queued/processing. The authoritative storage transaction rejects early requests with existing `BUSY` handling instead of invalidating/cancelling recognition. | Deterministic queued/processing HTTP/storage tests plus rendering tests. |
| Analysis retry | Starting a new analysis clears old sound results, limitations, and analysis timings. Failed analysis shows `Retry analysis`; controls disable while the replacement job runs. | Controlled failure/retry tests and isolated real-model retry. |
| History | Clicking `Open recording and results` scrolls to the loaded panel. Switching between preset and free-speech entries hides the other panel and pauses old playback. | Rendering scenarios for both History entry types and switching. |
| Learner playback | Prior Day 3 original-recording player is retained with the authenticated learner-asset route. | Original ten rendering scenarios remain passing; real retry check compares playback bytes with the uploaded fixture. |
| MFA speed | Enabled versioned compiled-dictionary resources in ignored local settings. New audio/transcript alignment still runs; assessment outputs are not cached. | First alignment reports cache `miss`; three later alignments report `hit`, including two different recordings. |

Backend changes: `accounts/sessions.py`. UI changes: `web_assets/accounts.js`. Tests extended: `tests/test_practice_sessions.py` and `tests/session_playback.cjs`. The earlier `phoneme_scoring/align_audio.py`, dictionary-cache module/tests, MFA timing tests, Day 3 playback tests and Day 4 documentation remain present. These shared accounts files should be reviewed with Lucas before merge through Sarrvesh's integration ownership.

Local activation changed only `mfa.dictionary_cache_directory` in `phoneme_scoring/settings.local.json` to this checkout's `runs/mfa_dictionary_resources` directory. Settings backup and activation record: `runs/demo-fixes-20261018T204101Z/`. Do not commit machine-specific settings or private data. To disable the optimization, remove only that cache option, preserving any subsequent local settings edits; the ordinary dictionary-compilation path remains available. Existing cache failure-path tests cover missing/corrupt resource handling. Runtime MFA failures remain failures with safe retry, not a silent duplicate long-running alignment.

## Verification executed

Commands run from the repository:

```powershell
node --check web_assets/accounts.js
node --test tests/session_playback.cjs
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_practice_sessions.py' -v
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py' -v
.\.venv\Scripts\python.exe -B runs/demo_fixes_real_check.py
git diff --check
```

- JavaScript syntax: passed. Rendering: 15 scenarios passed (the original ten plus five new scenarios).
- First focused private-session run: 12 tests passed. One further guard test was then added and included in the full run.
- Full suite: 168 tests run in 32.510 seconds, 167 passed, one existing Windows symlink test skipped, no failures. Includes 13 private-session tests and the Python wrapper invoking the rendering scenarios; do not double-count these as additional Python tests.
- Full regression log: `runs/demo-fixes-regressions.log`. Existing dependency deprecation warnings were not fixed by upgrading packages.
- The suite covers preset/content checks, input limits, transcript preparation, audio identity, private ownership, revisions/stale publication, generated-versus-learner separation, MFA timing/cache behavior, timeout/recovery paths and conservative unsupported/inconclusive outcomes. Much of this uses controlled engines/test doubles; it is not a fresh human accuracy study.
- Real-model HTTP integration: passed using real authentication, isolated temporary SQLite storage, real Whisper/MFA/phoneme inference, and the existing engineering WAV fixtures. No production sessions were created or directly edited. Harness: ignored `runs/demo_fixes_real_check.py`; outputs: `runs/demo-fixes-real.log` and `runs/demo-fixes-20261018T204101Z/real-check.json`.
- Failure recovery deliberately injects one adapter exception before inference, then retries through the real models. It verifies cleared old results, a new job ID, unchanged audio/revision and original playback bytes. This is not a naturally occurring MFA failure or a browser-click retry test.
- `git diff --check`: passed; Git reports line-ending conversion notices, not whitespace errors.

## Actual real-model measurements

Serial isolated HTTP integration on this machine, same inference settings. Service durations exclude browser, upload, human confirmation and polling overhead. No exact-assessment-result cache. The worker is reused after the first transcription; OS file cache was not reset. Each row retains the observed run, not a best-of selection.

| Run | Worker/resources | Transcription (s) | Analysis (s) | MFA lock wait (s) | MFA subprocess (s) | MFA operation (s) | Phoneme stage (s) | Transcription + analysis (s) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `think` | Fresh worker; dictionary miss/build | 21.063 | 32.093 | 0.000757 | 29.811 | 30.498 | 1.385 | 53.156 |
| `think` retry | Reused worker; dictionary hit; actual alignment rerun | not rerun | 12.393 | 0.000297 | 10.776 | 11.343 | not separately summarized | analysis only |
| `ship` | Reused worker; dictionary hit; different recording | 1.299 | 15.897 | 0.000393 | 13.896 | 14.445 | 1.213 | 17.196 |
| `bad_bed` | Reused worker; dictionary hit; different recording | 0.916 | 14.935 | 0.000294 | 13.597 | 14.144 | 0.525 | 15.851 |

The injected failure is excluded from inference timings because it intentionally performs no inference. All actual inference calls completed. Recognized text was `I think so.`, `The ship is here.`, and `That is a bad bed.`; confirmed text was the corresponding sentence without its final period. Completed sound outcomes were respectively two, two, and three `supported` results. These are experimental model outputs, not validated ground-truth pronunciation labels.

The first 53.156 seconds includes worker/model first use and dictionary construction. These costs were not individually isolated, so no separate precise initialization duration is claimed. The new persistent dictionary resources are now populated, but a restarted worker must still load its speech models. Two different warm-worker recordings completed below 20 seconds in this integration check; this does not guarantee a fresh browser recording will always finish below 20 seconds. Historical controlled before/after comparisons remain in `docs/DAY_4_PHASE_4_VERIFICATION.md`.

## Running app and final rehearsal

The user manually restarted the app after the code changes. Listener PID changed from 38000 to 22548 (new process started 15:46:32 local). `GET /site-health` returned HTTP 200 with ready status; the served `/site-assets/accounts.js` matched the working-tree bytes by SHA-256. This proves app reachability and updated asset delivery, not an authenticated browser acceptance test. No microphone use was requested or performed.

Before presenting:

1. Keep the laptop awake and avoid competing analysis jobs. Start with `.\.venv\Scripts\python.exe app_2.py` from this repository, then sign in.
2. Refresh the browser to load the updated interface. Rehearse one permitted engineering recording, wait for recognition to complete, inspect the words, confirm, then analyze. Count this as disclosed warm-up, not the audience's new recording.
3. Test a different permitted recording. Expect warm-model analysis around the observed range, while allowing additional browser/polling time. Do not promise an immediate first result.
4. Open History and check that the selected result becomes visible and its original audio plays. A failed analysis should offer retry and should not retain previous sound feedback.
5. Existing attempts with cancelled recognition are not retroactively repaired. Make a new attempt rather than presenting an old unverified result as fixed. If recognition genuinely fails, manual text can remain diagnostic/inconclusive; the software must not manufacture support.
6. If live processing fails or is slow, disclose it and show a clearly identified earlier saved result. Never label that saved assessment as the result for a new recording.

The post-fix authenticated browser sequence still needs manual rehearsal. Rendering and HTTP integration tests do not substitute for it.

## Remaining limitations

- Five-second recordings, 10 MiB uploads, 12 words and 200 characters remain enforced.
- General American English and the existing supported sound targets remain the current scope; arbitrary text is not full coverage of every English sound.
- Dictionary-missing words, uncertain evidence and content mismatches remain unsupported/inconclusive, not automatically incorrect.
- Recognition may mishear speech. Confirmation corrects alignment text but does not prove the recording actually contains those words.
- No validated overall accent percentage/pass-fail grade; no claim of human-speaker accuracy from engineering fixtures.
- Synthetic examples are generated voices, not voice-preserving accent conversion. No new conversion functionality was added.
- Model startup and MFA remain latency sources. Cache activation removes repeated dictionary preparation when valid; it does not eliminate all initialization or alignment work.
- No domain/public deployment or new hardware provisioned. Existing app remains local/private.

## Recommendation

Retain the fixes and locally enabled dictionary cache. Software regression and real-model integration evidence support them. The demo is ready with caveats for engineering functionality after the final manual browser rehearsal; human accuracy validation and reliable sub-20-second first-use performance remain unverified. Presentation preparation can use the observed results above without claiming these remaining limitations are solved.
