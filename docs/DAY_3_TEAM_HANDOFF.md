# Day 3 handoff: verification, performance and history playback

October 14, 2026. Owner/integration coordinator: Sarrvesh Mahadevan.

## 1. Starting state and scope

- Branch: `feature/speed-free-speech`. Baseline and unchanged HEAD: `e7f57d9ce37f95cb6c3cc30a870c8aae284656d7`.
- Phase 1 started clean; `git merge-base --is-ancestor e7f57d9 HEAD` returned 0. Phase 6 started with only the approved playback edit and its two new test files.
- Windows, Python 3.13.1, CPU Torch 2.14.0+cpu and Transformers 5.17.0. Pinned local Whisper and phoneme assets and local MFA dictionary/acoustic model are installed.
- FastAPI 0.141.1 and Uvicorn 0.53.0 differ from requirements-accounts.txt pins 0.143.0/0.54.0. `pip check` reports no broken requirements. No dependency changes were made.
- Existing localhost server was not restarted. Phase 1 health reported ready/public_launch=false; that endpoint does not test inference.
- TEAM_INTERFACE, FREE_SPEECH_DESIGN, Day 1/2 handoffs, integration report, FILE_OWNERSHIP and fictional contract examples were inspected. Older design-only/unimplemented statements describe earlier snapshots; the integration report and source establish the subsequent implementation.
- No fetch, merge, stage, commit, push, reset or history rewriting was performed. Cached remote refs cannot establish today's latest teammate pushes.

## 2. Browser acceptance: actual Phase 2 evidence

The browser began signed in as Sarrvesh. The user approved ordinary saved test attempts but withheld microphone permission. Browser approval review denied automated file upload; no workaround or API substitution was used. The browser subsequently exposed a saved recording, recognized as "I think so." Its original preview duration was about 2.475 seconds. The assistant did not execute its upload/initial save successfully.

| Case | Observed result | Status / limitation |
| --- | --- | --- |
| Existing authenticated session | Practice accessible, account shown | Passed for existing session; not fresh login |
| Login validation | Blank username invalid; nonexistent username/dummy password showed "Username or password is incorrect." | Passed submission prevention/error; blank-field message not captured |
| Logout/access | Sign out redirected to login; History refresh also redirected | Passed |
| Fresh successful login | Credentials not supplied; later available tab still signed out | Blocked |
| Preset selection | Ship lesson selected, ship/sheep hint updated; submit disabled without audio | Controls passed; full new preset browser analysis blocked |
| Custom-text entry | Mode and text field available | Entry only; full initial custom-mode submission untested |
| Confirmation gate | Analyze/generate disabled before confirmation | Passed |
| Limits | Blank, 13 words and 201 characters rejected; 12 valid words and valid text padded to 200 characters accepted | Passed at confirmation boundary; automated fill can exceed HTML maxlength |
| Missing dictionary token | "I qzxvplm so" rejected with dictionary guidance, without pronunciation-error label | Passed text case, not fresh spoken acceptance |
| Analysis | Confirmed "I think so." completed with experimental TH/IH support | Processing passed; no independent pronunciation label |
| Learner playback | Play changed to Pause, media state playing | Playback start passed; audibility not independently judged |
| Generation | Synthetic example completed, separate media source/duration and explicit synthetic label | Passed observed separation, not waveform/provenance audit |
| Transcript edits | Unsaved edits hid results/disabled jobs; confirmation cleared old analysis/generation | Passed |
| ASR disagreement | Confirmed "I think we can." against recognition "I think so." yielded inconclusive TH/IH/AE with CONTENT_UNVERIFIED | Passed conservative behavior |
| Edit during analysis | Processing observed, then new text confirmed; old result did not reappear in refreshed history | Passed observed browser case; backend race tests separately cover identities |
| Saved original playback | Free-speech history lacked original player; only generated player existed, or zero players after invalidation | Reproducible defect; targeted below |
| Microphone, live speech | Not permitted | Blocked |
| Five-second/10 MiB boundary uploads, replacement recording, failed-job retry | Not executed through browser | Blocked/not tested; automated boundary tests are separate evidence |

Captured practice console checks had no warning/error entries. Server tail contained existing Transformers warnings; exact browser network payloads/revision numbers were not captured. The Phase 2 test attempt remains saved; its latest confirmed text is "I think we can.", original recognition "I think so.", and superseded outputs cleared. Nothing was deleted.

## 3. Fresh human recordings: deferred Phase 3

All six required cases remain blocked: correctly spoken target, deliberate substitution, repeated words, contraction, dictionary-missing word and silence/unusable recording. No fresh human clips were supplied or recorded. The user requested synthetic substitution; no such result was presented as human acceptance. Earlier edited transcripts paired with an existing recording do not verify genuinely spoken repeats/contractions.

Resume with consented human clips under five seconds/10 MiB. Preserve intended, recognized and confirmed text separately; retain attempt/audio/revision identifiers. A completed job does not prove accurate sound judgment.

## 4. Performance: Phase 4 actual measurements

Command executed twice without editing: `.\.venv\Scripts\python.exe -B tools/benchmark_pipeline.py`.

Existing synthetic engineering fixtures, not human acceptance: think ("I think so", 1.730 s, 55,406 bytes), ship ("The ship is here", 1.905 s, 61,006 bytes), bad_bed ("That is a bad bed", 2.010 s, 64,366 bytes). All mono 16 kHz WAV. Preset backend through AnalysisService, reference comparison disabled, local pinned CPU models/two configured threads, direct MFA/english_us_arpa, existing locks and 120-second MFA/180-second worker timeouts.

F = fresh worker; R = same worker reused for that clip. Disk caches were not cleared; no cold-disk claim. Models persist across R calls; alignments/results were recomputed in fresh MFA subprocesses/work directories. No automatic retries. Series B is a full manual repeat after Series A stopped. Source/settings hashes match across series.

Times in seconds except lock milliseconds. Content check includes transcription, preparation, comparison, imports/model loading where applicable. MFA execution is nested within MFA total; do not sum both. Outer total includes worker startup, save/return; browser, upload, review and UI queue time are excluded.

| Run | Clip/cache | Content check | Lock ms | MFA execution | MFA total | Phoneme stage | DSP | Outer total | Condition |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| A1 | think/F | 42.921 | .496 | 32.800 | 32.836 | 1.753 | .185 | 79.165 | Initial startup variability |
| A2 | think/R | 1.072 | .458 | 34.147 | 34.155 | .550 | .023 | 35.812 | Completed |
| A3 | think/R | 1.080 | .468 | 31.187 | 31.195 | .702 | .016 | 33.000 | Completed |
| A4 | ship/F | 21.063 | .759 | 34.569 | 34.599 | 1.737 | .077 | 59.416 | Completed |
| A5 | ship/R | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | 572.369 | Timeout, standby-affected; excluded from normal speed comparison |
| B1 | think/F | 16.867 | 1.317 | 32.936 | 32.945 | 1.384 | .075 | 53.018 | Completed |
| B2 | think/R | .983 | .329 | 30.276 | 30.283 | .621 | .021 | 31.920 | Completed |
| B3 | think/R | 1.055 | .372 | 30.776 | 30.782 | .647 | .023 | 32.519 | Completed |
| B4 | ship/F | 15.201 | .568 | 30.446 | 30.462 | 1.442 | .067 | 48.862 | Completed |
| B5 | ship/R | 1.039 | .461 | 29.769 | 29.778 | .727 | .025 | 31.579 | Completed |
| B6 | ship/R | 1.019 | .402 | 29.882 | 29.890 | .680 | .021 | 31.621 | Completed |
| B7 | bad_bed/F | 14.241 | .553 | 30.253 | 30.277 | 1.517 | .069 | 47.878 | Completed |
| B8 | bad_bed/R | 1.023 | .378 | 30.242 | 30.252 | .781 | .026 | 32.095 | Completed |
| B9 | bad_bed/R | 1.117 | .381 | 31.621 | 31.629 | .726 | .026 | 33.509 | Completed |

14 attempts: 13 processing paths completed, one timeout. Completed overall results were partial because some sound evidence was uncertain; recognition matched, MFA/sequence evidence were available, feedback/save succeeded. Windows Modern Standby events overlap A5, including approximately 14:52:31-15:00:49 local time. This confounds its deadline/wall time; no missing stage was estimated. No standby event occurred within Series B's processing interval.

**Measured bottleneck:** MFA subprocess execution used 94.5% of aggregate outer time across B's six R runs. R median total 32.008 s; range 31.579-33.509 s. Lock waits across B were .329-1.317 ms. Fresh totals versus average R totals: think 53.018/32.220 s, ship 48.862/31.600 s, bad_bed 47.878/32.802 s. Model initialization matters but cannot be separated precisely from stage imports/preparation/inference.

Unmeasured: server startup-to-ready, pure model-load/inference split, MFA startup/features/decoding split, individual feedback/save costs and whole-browser latency. OS background load uncontrolled; input order fixed. These are not confirmed-text UI end-to-end timings.

Proposed only: exact-input alignment reuse for the same authorized learner recording, transcript and complete model/dictionary/configuration identity. It could avoid a roughly 30-second repeated alignment, but would not speed up new recordings. Requires parity, invalidation, ownership and stale-publication tests plus cache-hit/miss measurements. No cache or speed optimization was implemented.

Raw evidence (ignored/local): runs/phase3-baseline-20261014T194748Z.json, runs/phase3-baseline-20261014T200753Z.json and referenced per-run results.json. The script's historical missing-measurement list is outdated: lock/subprocess metrics above were recovered from existing saved alignment timers without adding instrumentation.

## 5. One approved fix

Lead explicitly approved the shared account-UI scope and coordination through Sarrvesh; Lucas review remains required before merge.

Cause: showSession rendered generated audio but never learner_audio_id, despite an existing authenticated asset route. web_assets/accounts.js now adds a labeled "Your original recording" player outside the feedback area. It uses only the session's learner asset URL, updates/clears the source when identity changes, preserves unchanged playback during polling/text edits and pauses prior session media when switching sessions.

Acceptance covered by focused rendering tests: custom/free history without generation, distinct original/generated players, unchanged polling/play position, edit/reconfirmation invalidation, replacement/missing asset, session switching, encoded URL segments and preset playback. Before fix: 9 failed/1 preset test passed. After fix and Phase 6 rerun: all 10 passed.

The tests execute production JS with a small DOM/HTTP double. They do not decode media or establish browser audibility. The available browser remains signed out; post-fix real-browser acceptance is pending manual sign-in. No schema, backend, model, threshold, dictionary or configuration changes.

## 6. Phase 6 verification

| Command/check | Actual result | Evidence type / limits |
| --- | --- | --- |
| `node --check web_assets/accounts.js` | Passed | Syntax only |
| `node --test tests/session_playback.cjs` | 10 passed | Production renderer/events with DOM/HTTP doubles |
| `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py' -v` | 156 tests, 155 passed, 1 skipped; zero failures; 33.989 s | Mixed unit/file/DSP/HTTP/SQLite/process tests; mocked speech/generation in many cases; one Python test wraps the 10 JS cases, do not add as independent Python tests |
| `.\.venv\Scripts\python.exe -B -m pip check` | No broken requirements | Does not establish installed versions match declarations |
| `git diff --check` | Passed | Whitespace review |

Full-suite evidence: runs/day3-phase6-regression.log. The existing symlink test skips because this Windows environment cannot create symlinks. Existing Starlette/httpx deprecation and asyncio event-loop warnings remain; no failure is concealed.

The suite includes preset checks, transcription settings/cache/identities, transcript limits/dictionary/repeated occurrence indexing, confirmed-text worker guards, actual SQLite/login ownership/revision publication tests with controlled engines, stale edit/delete/logout behavior, generated reupload rejection and conservative evidence arithmetic. These establish safeguards, not human accuracy or full browser acceptance.

Real-model smoke command: `.\.venv\Scripts\python.exe -B tools/check_private_free_speech.py`. Exit 0; all 17 checks passed. Actual Whisper, MFA, phoneme inference, Windows speech synthesis, temporary SQLite storage and login/CSRF/HTTP routes were used. HTTP requests ran through FastAPI TestClient in-process, not an actual browser/network acceptance run. Temporary smoke accounts/storage were cleaned by the tool, without changing the running site's user database.

The source was the existing local demo data/references/think.wav, not newly consented speech. Original recognition/confirmed "I think so" completed with TH inconclusive and IH supported. Subsequent confirmed texts "I think I think so" and "I don't think so" deliberately disagreed with that same recording; both completed with all sound outcomes inconclusive and CONTENT_UNVERIFIED. Synthetic generation/playback succeeded and reupload of that registered generated file as learner input returned rejection. These checks do not establish human accuracy, genuinely spoken repetition/contraction handling, or post-fix browser media decoding.

Measured account-job processing: original-text analysis 39.014 s, repeated-word correction 33.936 s, contraction correction 33.672 s, generation 1.521 s. These use different audio/text and timing boundaries from the Phase 4 preset study and are not pooled into its comparisons. Raw Phase 6 evidence: runs/day3-phase6-real-smoke.log and runs/day3-phase6-real-smoke.json. The smoke tool's prior default JSON was preserved as runs/day3-phase6-prior-private-smoke.json before rerunning. No new real-model failure occurred.

## 7. Git review and proposed commits

Only approved source change: web_assets/accounts.js (16 insertions, 1 deletion). New tests: tests/session_playback.cjs and tests/test_session_playback.py. This handoff is new documentation. No unrelated teammate edits were present. No staged files; HEAD unchanged.

Proposed scopes, not staged or committed:

1. **Restore original learner playback in private session history**: web_assets/accounts.js, tests/session_playback.cjs, tests/test_session_playback.py.
2. **Document Day 3 verification and remaining acceptance gaps**: docs/DAY_3_TEAM_HANDOFF.md.

Do not commit ignored logs, private databases, raw recordings, model weights or machine-local configuration. Approval is required before staging/committing/pushing. No performance change is bundled.

## 8. Dependencies and next actions

- **Lucas:** review shared session/history playback against GET /api/sessions/{attempt_id}/audio/{asset_id}, including ownership, no-asset behavior, replacement, deletion and transitions between history/practice. No schema change requested. Coordinate shared accounts.js edits through Sarrvesh. Confirm storage/auth/history behavior on the team baseline before merge.
- **Parthiban:** preserve generated_audio_id/generated_audio_type and synthetic labels; review that synthetic playback remains distinct and invalidates on edits. No generation-interface change requested. Voice/accent listening review and optional isolated Kokoro testing remain outstanding; conversion is still stretch work.
- **Sarrvesh/user:** sign in and verify the actual fixed history player, then finish boundary upload/replacement/retry and microphone checks. Supply six fresh consented human cases; do not replace learner acceptance with synthesized speech.
- **Team:** review current remote changes before integration, reconcile dependency pins deliberately, investigate timeout behavior under Modern Standby separately, and collect independent sound labels before trusting grades. No public production readiness claim.

## 9. Integration assessment

Suitable for the next controlled teammate integration review, supported by regression coverage, measured backend runs and the targeted renderer tests. It is not yet accepted for real learners or public release. Fresh-human accuracy/occurrence cases, physical microphone behavior, browser boundary cases and post-fix live playback remain unverified. Phase 3 is explicitly deferred; this is not a claim that every Day 3 phase passed.
