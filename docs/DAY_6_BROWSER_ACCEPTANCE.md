# Day 6, Phase 2: Browser acceptance checklist

October 21, 2026. **Partial execution; new-upload and second-account prerequisites remain blocked. Do not advance this checklist to complete.**

## Environment and scope

- Branch `feature/speed-free-speech`, HEAD `e7f57d9ce37f95cb6c3cc30a870c8aae284656d7`.
- Actual in-app browser, signed in to the authorized Sarrvesh account. Practice tab 3; separate History tab 4. The original Practice tab remains in Free speech for a manual upload.
- Tested actual UI navigation, saved-session inspection, playback start and unsaved-editor invalidation. No mocked engine/browser results are included.
- No application, configuration, model, migration or database records were edited directly. No inference/analysis job was submitted, no account created, no existing attempt deleted, and no code fix attempted.
- Earlier automated upload was denied by browser approval review. It was not retried or bypassed through an API, file injection, alternate browser or native picker. A manual upload was requested; no completion reply or enabled Save control was observed before this report.
- The current private database contains one account. A second authorized browser account is unavailable. No credential was read or requested in chat.

## Test session and evidence

Inspected only the designated existing human Case 1 for detailed result evidence:

- Attempt `1411ea4ea5ab4191a8dd2bc052121c1f`.
- Learner asset `0e98c3c86435494ab42f7bf41a46fe8c`.
- Recognized and saved confirmed text: `I think so.`
- Input revision 3; analysis job `d8362af5ff8f476aa9f890cc7ab72a44`, revision 3, completed.
- Displayed findings: TH inconclusive, IH experimentally supported. Neither is a validated pronunciation grade.
- Original player source `/api/sessions/1411ea4ea5ab4191a8dd2bc052121c1f/audio/0e98c3c86435494ab42f7bf41a46fe8c`; duration 1.920 seconds; media readyState 4.

Evidence folder: `runs/day6-phase2-browser-1792617859487/` (ignored/local):

- `saved-session-persistence.jpg` and `.json`.
- `unsaved-edit-gates-results.jpg`.
- `upload-waiting.jpg`.
- `console.json` (captured warnings/errors: none in either tab).

The DOM inspection of the file input's FileList was unavailable through the read-only browser scope. This automation inspection limitation is not an application console error or evidence of a failed upload. The visible Save control remained disabled and the page had no new preview.

## A. Upload to analysis

**Overall: BLOCKED.**

Precondition: a permitted test WAV selected through the browser upload control. Selected Free speech in the actual Practice page. Requested manual upload of the existing `data/references/think.wav`, with instructions not to press Save yet. This is an engineering fixture used as learner input, not a fresh human acceptance clip or scoring-reference comparison.

Expected: selected preview, enabled Save/transcribe, recognized text, editable/confirmed text and analysis tied to the same original learner asset.

Observed: Free speech selected; Save and transcribe remains disabled. No new recording/transcription/confirmation/analysis was submitted. No new attempt/job/revision IDs exist for this case. Mark all downstream A steps NOT TESTED, not failed.

Dependency: user completes manual upload. No new application defect established.

## B. Replace a recording

**Overall: BLOCKED.**

Requires a disposable completed test session and a second permitted, different recording. Neither new upload was completed in this phase. Did not replace or modify the existing human Case 1.

Expected: previous feedback is removed or clearly identified as belonging to old input; late work cannot publish as the new recording's result.

Actual: no browser replacement or in-flight replacement was executed. Backend revision tests and source inspection do not substitute for this acceptance test.

Source-review hypothesis for later reproduction: `acceptRecording` changes the upload preview/Save state, while session rendering is handled separately. Check explicitly whether old session feedback remains visible when a different file is selected, and whether the UI creates a distinct attempt or replaces the current asset. This is **not a reproduced defect**. Do not implement a fix based only on this hypothesis.

## C. Edit confirmed text

**Unsaved-edit subcase: PASS. Saved reconfirmation/reanalysis: BLOCKED.**

Steps actually performed:

1. Opened the completed Case 1 from History.
2. Verified its saved text/results and original player.
3. Changed only the editor draft from `I think so.` to `I think we can.`; did not press Confirm transcript or Analyze.
4. Inspected the visible state and DOM.
5. Reloaded History, then reopened the same dated session to discard the draft and preserve original stored data.

Expected and actual: old sound results became empty; Analyze and generation disabled; recognized words remained `I think so.`; original learner source remained unchanged. After reload/reopen, saved confirmed text `I think so.`, completed status and original findings returned.

This demonstrates unsaved-editor gating and persistence, not revision advancement or stale-result publication rejection. No saved edit/reconfirmation/in-flight race was tested. Those steps remain blocked pending a new disposable test session.

## D. Failed-analysis retry

**Overall: BLOCKED.**

No failed analysis occurred in the observed browser session. A controlled analysis failure was not fabricated by changing settings, killing services, intercepting responses or modifying records.

Potential next safe case: manually upload the existing two-second `tests/fixtures/team/silence.wav` control. Observe its actual transcription/validation behavior. If the normal UI permits confirmed diagnostic analysis and that job fails, test its visible retry. If rejection happens before an analysis job exists, record it as input validation, not an analysis-retry pass.

No error text, duplicate-job outcome, retry outcome or current server failure log can be claimed for an unexecuted case. Previous injected-failure tests are separate historical evidence.

## E. Saved-session persistence

**Existing-session navigation/playback subcases: PASS. New-session creation: BLOCKED with A.**

Steps:

1. Open My history; select Case 1 dated October 21, 3:04:59 PM.
2. Verify recognized words, confirmed editor, completed status, sound findings and original media source.
3. Press Play: the control changed to Pause, demonstrating playback start. Audibility/phonetic quality was not independently rated.
4. Navigate to How it works, return to My history, and reopen the same session.
5. Verify all saved values and the same learner asset. Also reload after C's unsaved draft and reopen again.

Actual: all inspected saved fields persisted; original audio remained available; no missing data or loading error observed. The panel scrolled into view (observed top approximately 29 px on initial opening). There was no app/server restart, so this phase establishes navigation/reload persistence, not a new restart-survival test.

No new save was performed in this phase. E's create/save step remains unexecuted rather than inferred from the already existing session.

## F. Account isolation

**Overall: BLOCKED.**

Precondition: two authorized browser test accounts with distinct disposable data. Only one local account currently exists. No second login or cross-account read/play/history/results request was attempted.

Required next evidence: user provides/creates a second authorized account and enters credentials directly in the app; create distinct test data, then verify the first test attempt's direct asset/session access is denied and each History contains only its permitted sessions. Do not use another person's real account. Existing temporary-account HTTP isolation tests are not counted as browser passes.

## G. History processing/completed mismatch

**Existing saved-session consistency: PASS. Live-transition reproduction: BLOCKED / NOT TESTED.**

Steps actually performed:

1. Load History fresh and inspect Case 1's dated card: `completed`.
2. Open it: panel reports `transcription: completed; analysis: completed; generation: not started`.
3. Navigate away/back and later reload/reopen: completed status remains consistent.
4. Read the exact attempt through a read-only SQLite query for supporting evidence, without writing records.

Persisted evidence: History `attempts.status=completed`; session `analysis_status=completed`, `transcription_status=completed`, revision 3; active analysis job record revision 3/status completed. UI and persisted status agree for this inspected completed session. The historical mismatch is **not currently reproduced** by opening/reloading it.

To reproduce the suspected transition issue: start analysis on a new disposable recording; open History while it is processing; open that attempt and leave the list unchanged while the panel polls to completion. Compare card, panel and exact persisted job/revision state before refresh, then after reload. This was not possible without a new submitted recording.

Likely presentation/list-refresh behavior remains a hypothesis; no inconsistent backend state was observed here.

## Prioritized Phase 4 defect list

**No new confirmed application defect was established by this partial run. Do not manufacture a targeted fix.**

Prioritized diagnostic queue before choosing a Phase 4 fix:

1. **High acceptance priority:** complete A/B with new disposable recordings. Verify recording association and visible invalidation; test the possible stale old-feedback presentation. Owner: Sarrvesh with Lucas for shared session UI.
2. **Medium investigation priority:** reproduce G during a real processing-to-completed transition. If card-only staleness is demonstrated, capture exact IDs/statuses and scope a list-refresh fix. Owner: Lucas/Sarrvesh.
3. **High acceptance priority:** complete D's genuine failure/retry and F's two-account isolation. These are verification gaps, not demonstrated bugs. Owners: Sarrvesh/Lucas; second-account/manual-upload prerequisites required.

No new severity can be assigned to an unexecuted failure. Current limitations prevent complete browser acceptance sign-off. Stop here: no Phase 4 implementation, test-account creation, staging, commit, push or service restart.
