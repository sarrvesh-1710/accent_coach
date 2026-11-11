# Practice results update, October 27, 2026

## Implemented

Practice now tracks its active attempt and latest authorized server response. Preset submissions and confirmed-text analysis display their progress, completion or failure in Practice. Completed output includes original learner playback, sound findings, limitations, expandable structured analysis details and the existing JSON download. The current result is brought into view automatically. No numerical pronunciation grade has been added.

The result panel provides **Start new practice** and **View in History**. Starting again clears the browser's selected recording/result and polling, without deleting the saved attempt. Both pages use the existing authorized attempt/session APIs and the same renderers. An attempt query parameter restores the current result after refresh or opens the exact saved result in History.

Changing the recording, lesson or mode invalidates the previous browser selection. Submission inputs are captured before asynchronous calls. Selection epochs and read sequence checks prevent late submission, confirmation and polling responses from reopening an abandoned result. Editing a transcript hides its previous findings until it is reconfirmed. Existing server revision and ownership enforcement remains authoritative.

Network status-read failures show **Check status again**, which repeats the read rather than creating another analysis job. A completed preset job without saved result details is shown as an actionable loading error, not a successful result display. Analysis failure remains distinct from inconclusive pronunciation evidence.

Account assets now have content-versioned URLs, matching the site's existing stylesheet approach. This prevents older browser-cached JavaScript from masking the update. The History loading function was renamed to avoid shadowing the browser's native `history` API used for current-result URLs.

## Files changed for this feature

- `web_assets/accounts.js`: active Practice state, progress/completion, shared result rendering, navigation, read retry and stale-response protection. This file already contained earlier playback/reliability work, which is retained.
- `web_assets/accounts.css`: hidden result regions, progress styling, completion banner and responsive result actions.
- `accounts/web.py`: content-versioned account script and stylesheet links only; no API, persistence or model changes.
- `tests/session_playback.cjs`: expands the existing production-renderer test harness to cover Practice submissions, shared History data, failures and asynchronous races.
- `tests/test_accounts_integration.py`: verifies both pages reference and serve the current account assets.
- This report.

## Verification observed

| Command | Result | Scope |
| --- | --- | --- |
| `node --check web_assets/accounts.js` | Passed | JavaScript syntax |
| `node --test tests/session_playback.cjs` | 25 passed, 0 failed | Production JS executed with DOM/HTTP test doubles, not a real browser or model |
| `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py' -v` | 178 tests run: 177 passed, 1 skipped | Existing regression suite, including real temporary HTTP/SQLite integrations with controlled speech engines; includes the Node wrapper as one Python test |
| `git diff --check` | Passed | Whitespace/diff check |

The skip is the existing Windows symlink-creation limitation. The suite emitted an unclosed event-loop ResourceWarning; it did not fail the suite. No new real-model inference or fresh human-recording acceptance test was required or claimed for this UI change. The 25 Node scenarios are not 25 additional Python tests.

Logs: `runs/practice-view-rendering-final.log` and `runs/practice-view-regressions-final.log`.

## Live browser verification

The signed-in browser initially continued executing the older unversioned cached script. After the user restarted the app and the browser reloaded the versioned links, these actual browser checks passed using an existing authorized completed preset attempt:

- Opening `/practice?attempt=...` displayed the original recording, recognized words, TH feedback, completion banner, analysis-details control, download and both action controls. Completion brought the result card into view.
- Clicking **View in History** opened the same saved attempt. Its original-audio URL and displayed recognized words/sound finding matched Practice.
- Returning to the Practice result URL restored it without creating another attempt.
- Clicking **Start new practice** hid the old result, cleared the selected input and changed the URL back to `/practice` with a ready message.
- Reopening the same attempt in History after that reset still displayed its recording and results. The saved record was preserved.
- The result was left open in Practice. Browser console diagnostics contained no captured warnings or errors in the final check.

Screenshot: `runs/practice-results-completed.jpg`.

This live check reopens an existing assessment; it is not a new human-recording or live model-submission test. New submission progress/completion and free-speech confirmation flows were exercised through production-renderer tests with HTTP/DOM doubles. Existing HTTP/SQLite regressions exercise persistence and authorization with controlled engines. Those categories must remain separate from a full new-recording browser acceptance run.

## Preservation and integration

Branch remains `feature/speed-free-speech`, HEAD `e7f57d9ce37f95cb6c3cc30a870c8aae284656d7`. Nothing was staged, committed, merged or pushed.

SHA-256 comparison with the pre-feature snapshot confirms no changes to `accounts/sessions.py`, `phoneme_scoring/align_audio.py`, `mfa_dictionary_cache.py`, `mfa_worker.py`, `persistent_mfa.py` or local model/execution settings. Earlier uncommitted speed, storage and reliability work remains in place. Original learner playback and generated-versus-learner labeling remain covered by the renderer scenarios.

This feature changes shared account/History UI, so Lucas should review it with the integration owner before merging. No schema, storage interface, audio-generation contract or model-setting change is required from Lucas or Parthiban. Keep this feature's diff separate from the pre-existing uncommitted backend/speed changes when preparing commits.
