# Demo polish integration, November 1, 2026

## Completed

Selectively adapted Parthiban's `parth/profile-improvements` commit `fac7219` and the user-facing processing copy in `parth/demo-ready` at `dd29abd`. The lead approved this limited integration. The current local speed build remains the base; neither the combined remote branch, its default-Kokoro launcher, nor its generation adapter replaced the working implementation.

The profile page now has understandable TH/think, IH/ship and AE/bad cards, visible unsaved-change state, Save and Discard, disabled controls during saving, explicit success/failure feedback, and immediate updates to the displayed name. Canonical saved values come back from the authenticated server. Network errors preserve draft edits and allow retry; duplicate submission is blocked while saving.

The existing optional Mandarin learner-guidance field participates in change detection, save, discard and server responses. Older clients that omit it retain the saved preference. The General American target and the distinction between guidance and trained grading are unchanged. Profile JS/CSS are content-versioned and loaded only on the profile page; the old duplicate save listener was removed from the shared account script.

Practice/session status copy now describes recognizing words, analyzing confirmed sounds and generating a listening example. Failed jobs keep explicit errors and retry controls. A Processing times disclosure formats the existing saved millisecond timers as seconds; no instrumentation or speculative timing was added. Existing uncertainty/content-verification limitations remain visible outside the disclosure, with raw analysis details/downloads retained. A no-target result suggests the supported TH/IH/AE practice scope without pretending that unsupported speech is incorrect.

## Scope and preservation

Branch: `feature/speed-free-speech`. HEAD remains `e7f57d9ce37f95cb6c3cc30a870c8aae284656d7`. Index empty. No commit, push, branch checkout, merge, reset, stash or history rewrite was performed. Existing dirty and untracked teammate work was preserved.

Changed preexisting files in this task only:

- `accounts/web.py`: profile markup/versioned assets, signed-in-name hook and canonical profile response.
- `web_assets/accounts.js`: remove duplicate profile handler; friendly session messages and timing summaries.
- `tests/session_playback.cjs`: assert dedicated profile-script ownership and the new status/timing presentation while retaining all prior scenarios.

New source/test files:

- `web_assets/profile.css`, `web_assets/profile.js`: adapted teammate assets, with Mandarin field support added.
- `tests/test_profile_preferences.py`: teammate HTTP/account tests adapted for the existing guidance field, plus round-trip and asset-scope checks.
- `tests/profile_rendering.cjs`, `tests/test_profile_rendering.py`: production profile-script regression scenarios and Python test wrapper.

All 15 protected paths matched their pre-edit SHA-256 hashes: `analysis_service.py`, `pipeline.py`, `confirmed_analysis.py`, `speech_content.py`, `accounts/store.py`, `accounts/sessions.py`, `accounts/practice_jobs.py`, `voice_generation/runtime.py`, `phoneme_scoring/align_audio.py`, `gop_score.py`, `persistent_mfa.py`, `mfa_worker.py`, `fst_resource_cache.py`, `mfa_dictionary_cache.py`, and ignored `settings.local.json`.

This retains the reusable MFA interpreter, compiled-resource/graph caches, idle retention, locking, deadlines, original-recording identity, ownership/revision checks, conservative findings, and separate learner/generated assets. No model, dependency, dictionary, scoring threshold, worker/concurrency setting, generation backend or schema change was made. The ordinary desktop voice remains the default; Kokoro was not installed or enabled.

## Executed verification

| Check | Actual result |
| --- | --- |
| `node --check web_assets/accounts.js`; `node --check web_assets/profile.js` | Passed. |
| `node --test tests/session_playback.cjs` | 29 scenarios passed; controlled DOM/HTTP. Covers old playback/stale-input protections and the new messages/timing summaries. |
| `node --test tests/profile_rendering.cjs` | Eight scenarios passed; controlled DOM/API. Covers initial/dirty/discard/save, canonical name/guidance, network failure, duplicate submissions, blank names, and text-safe name rendering. |
| unittest discovery for `test_profile_preferences.py` | Seven tests passed; real temporary HTTP/SQLite/authentication, including CSRF, ownership, canonical response, existing Mandarin preference, invalid-input preservation and versioned profile-only assets. Speech inference is not used. |
| First full suite | 222 tests run in 100.078 seconds: 220 passed, one error and one existing Windows symlink skip. The error was the existing `test_worker_reuses_process_and_recovers_after_timeout`, where recovery exceeded the test's ten-second deadline. |
| Unchanged focused recovery rerun | Eleven tests run in 6.951 seconds: ten passed, one existing Windows skip. The recovery test passed without changing application or test deadlines. |
| Final full suite: `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py' -v` | 222 tests run in 82.951 seconds: **221 passed, one existing Windows symlink skip, zero failures**. The two JS suites are included as Python wrapper tests; their individual scenarios are not extra Python tests. |
| Hygiene | `git diff --check` passed. Changed Python sources compile. Original speed/storage/backend files and local settings matched the preservation manifest. |

The initial recovery timeout is retained rather than concealed. About 1.6 GiB of free physical RAM was observed when investigating it; low resources are a plausible contributor, not an established root cause. No power settings, timeouts, packages or user applications were changed to obtain a pass. Existing dependency/resource warnings remain.

## Live browser evidence

The user manually started the app and signed in. Automated launch had previously been blocked, so it was not retried through another mechanism. All following checks used the actual signed-in in-app browser:

1. Profile initially displayed the saved name, all existing choices, the Mandarin selector, and disabled Save/Discard controls.
2. Edited an unsaved name, selected Mandarin and checked TH. Unsaved feedback appeared and both actions became available.
3. Discard restored the original name, general guidance and unchecked goals; nothing from that draft was saved.
4. Submitted only whitespace around the original name. The server returned the canonical original name, the page displayed success, controls reset, and reload preserved the original profile. No net change to the user's name, goals or guidance was left behind.
5. Narrow-layout preview displayed stacked sound cards and no horizontal overflow at the observed 493 CSS-pixel width. The requested override was 390 pixels, but the browser reported 493; this does not establish an actual 390-pixel-device test. The viewport override was reset.
6. Opened the saved October 27 I think so session from History. Original learner playback, experimental TH/IH findings, visible limitations, analysis download and the new readable status were present. Processing times expanded to show the historical transcription 4.0 seconds and analysis 7.9 seconds. No new analysis or generation was run to obtain those values.
7. No browser warning/error messages were captured. The finished profile page was left open.

Screenshots and logs are in ignored `runs/demo-polish-20261102T051925Z/` (directory timestamp is UTC; work was on November 1 in America/Chicago). Artifacts include `profile-save-browser.jpg`, `profile-mobile-browser.jpg`, `saved-result-times-browser.jpg`, `regressions.log` (initial failure), `recovery-rerun.log`, `regressions-rerun.log`, and the pre-edit source snapshot/manifest.

## Speed and demo interpretation

This is a presentation/profile integration, not a speed optimization. It adds no model call or network request to assessment and does not alter queue/poll cadence. The additional canonical-profile read occurs only when saving a profile. New profile assets are not loaded on Practice. No new real-model or browser-latency benchmark was performed in this task, so neither a new speed gain nor a strict ten-second maximum is claimed.

Historical evidence remains in `SPEED_COMPLETION_REPORT_2026-10-27.md` and `TEAM_FEATURE_INTEGRATION_2026-10-28.md`: website prepared-analysis median 8.19 seconds in that earlier series; later isolated warm transcription-plus-analysis median 5.63 seconds. These have different timing boundaries and are not interchangeable. Startup can be much slower. The saved 7.9-second browser result is an old attempt, not a fresh measurement today.

## Tomorrow's walkthrough

1. Start the existing app normally with `.\.venv\Scripts\python.exe app_2.py` and sign in. Keep the current environment and desktop voice default.
2. Show profile sound cards, the optional guidance selector, unsaved edits, Discard and Save feedback. Describe preferences as guidance rather than grades.
3. Run one complete practice workflow before presenting to prepare the existing models. Keep first-use preparation separate from the live timing.
4. During the demonstration, record a new short utterance, save/transcribe, review/correct and confirm the words, then analyze. Show the actual processing/completion state and experimental findings in Practice.
5. Open Processing times, replay the original recording and reopen the same session in History. Request a desktop synthetic example separately if desired; label it synthetic, not a converted learner voice.
6. If the live job is slow/fails, retain the real status/error and use an explicitly identified previous saved attempt to explain the output. Do not present it as the new recording's result.

Remaining limits: incomplete broader fresh-human acceptance/accuracy validation; no calibrated overall grade; eligible TH/IH/AE contrasts only; five-second/10-MB recording and 12-word/200-character text scope; cold-start/resource variability; and optional Kokoro/voice-preserving conversion outside this demo polish. No public deployment occurred.

## Suggested commit boundaries

Keep this task separate from earlier uncommitted playback/speed/reliability/guide work. A reviewed profile-polish scope can contain the profile route/canonical response, dedicated assets and profile tests. A second scope can contain the friendly status/timing presentation, corresponding rendering tests and this report. Shared files have overlapping existing edits, so use reviewed hunks rather than staging every changed file. No staging, commit or push is authorized/performed by this report.
