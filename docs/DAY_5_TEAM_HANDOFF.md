# Day 5 integration review and handoff

October 21, 2026. Integration coordinator: Sarrvesh Mahadevan.

## 1. Decision and scope

**Ready with caveats for controlled teammate integration review.** Regression and real-model checks passed on this local working tree. This is not acceptance of a public release, pronunciation accuracy, a complete browser journey, or reliable sub-20-second processing of new human recordings.

Day 5 status: Phase 1 inspection completed; Phase 2 browser testing partially completed with blockers; Phase 3 collected one human case and deferred five at the user's request; Phase 4 measured the available inputs; Phase 5 targeted-fix work was not executed. Phase 6 reviews these gaps rather than declaring the earlier phases complete. No new application fix or optimization was implemented in Phase 6.

## 2. Git baseline and preservation

- Branch: `feature/speed-free-speech`.
- Starting and ending HEAD: `e7f57d9ce37f95cb6c3cc30a870c8aae284656d7`. The baseline is included: `git merge-base --is-ancestor e7f57d9 HEAD` returned 0.
- Index empty at inspection and after verification. Five tracked files are modified, with 168 insertions and five deletions. There were 17 untracked files at the start; this report makes 18.
- The earlier integrated accounts/confirmed-practice/generation foundation is committed in `74978dc`; launcher support/handoff is in `e7f57d9`. Later playback, cache, and reliability changes are **not committed**.
- Hash comparisons before/after this phase confirm all five modified tracked files, the four untracked source/test files, and ignored `settings.local.json` are unchanged. No existing work was reset, stashed, reformatted, discarded, staged, committed, merged or pushed.
- Cached remote refs were inspected, not fetched. They show profiles at `76cef88`, voice conversion at `09f6de1`, and the speed branch at `e7f57d9`. They do not prove teammates have made no newer remote changes. No remote branch was integrated in this phase.

### Change attribution by scope

| Change | Current status and evidence |
| --- | --- |
| Day 3 original learner playback | Uncommitted portions of `web_assets/accounts.js`; untracked rendering tests. Uses the existing authenticated learner-asset route, preserves unchanged playback and stops old session audio. |
| Day 4 dictionary-resource optimization | Uncommitted `phoneme_scoring/align_audio.py`, untracked `mfa_dictionary_cache.py`, associated tests. Local opt-in is already enabled in ignored settings. Cache is resource-only; each assessment still aligns its recording/transcript. |
| Subsequent reliability fixes | Uncommitted `accounts/sessions.py`, additional portions of `accounts.js`, `test_practice_sessions.py` and rendering tests: prevent confirmation/analysis during recognition; clear obsolete retry feedback/timings; expose retry; scroll to opened History results and hide the other result panel. |
| Day 5 work | Two existing evidence reports plus this handoff; ignored measurement/verification artifacts. No Day 5 application-code fix was added. |

Playback and later reliability edits share the same JavaScript file and test file. Their historical scopes are distinguishable, but a clean whole-file split would overlap. Do not silently stage one file twice or rewrite work to manufacture separation.

## 3. Documentation, contracts and actual wiring

Reviewed `TEAM_INTERFACE.md`, `FREE_SPEECH_DESIGN.md`, `FILE_OWNERSHIP.md`, Day 3/4 handoffs, Day 4 verification/demo notes, `DEMO_FIXES_REPORT.md`, the integration report, both Day 5 reports and all three JSON contract examples. Examples are fictional, not test results. Older design headers saying interfaces are unimplemented and older cache-disabled statements describe earlier snapshots; actual code, committed history and later activation evidence supersede them.

Current runtime path:

1. `accounts/web.py` authenticates the opaque session cookie and checks CSRF on mutations.
2. `accounts/sessions.py` stores an immutable learner asset, recognized and confirmed text separately, input revision, job states and private outputs in SQLite.
3. `PracticeJobs.run` (`accounts/practice_jobs.py:42`) resolves a trusted snapshot, copies the original recording into temporary work, then dispatches independent transcription, confirmed analysis or synthetic generation.
4. `speech_content.transcribe_audio:47` recognizes without a lesson ID. `transcript_input.prepare_transcript:71` validates text and the configured lexicon. `confirmed_analysis.run_confirmed_attempt:65` uses the confirmed text, learner role/hash and job/revision identities for MFA and phoneme analysis.
5. `SessionMethods.publish_job:218` accepts only current authorized jobs with matching revision, asset and confirmed text. `session_asset:243` authorizes playback. Editing/replacing/deleting invalidates obsolete work.
6. Presets retain `/api/attempts` and the existing preset pipeline. Custom/free sessions use flat `/api/sessions` snapshots. `PracticeJobs.create_attempt` supports custom/free modes, not presets; callers must retain this routing distinction despite the contract's three-mode vocabulary.

The earlier `AnalysisStore` protocol in `confirmed_analysis.py` remains a separately tested synchronous seam. The actual account integration uses `Store.job_snapshot`/`publish_job` through `PracticeJobs`; it is not blocked on replacing that protocol's test double. Likewise, `voice_generation.service.DevelopmentStore` is a standalone in-memory demo/test component, **not** the live application's private storage.

Contract safeguards remain: General American target; WAV maximum five seconds and 10 MiB; 1-12 normalized words and 200 characters, with contractions counted as one word; explicit confirmation; queued/processing/completed/failed/cancelled jobs; supported/practice/inconclusive sound outcomes. Missing dictionary words are preflight coverage failures, not mispronunciations. Initial contrasts are TH versus S/T/F, IH versus IY, AE versus EH. Other sounds are not implicitly graded.

App-managed generated assets have separate IDs/roles and cannot enter the learner path. Registered generated waveform reupload is also rejected. This does not detect every externally synthesized, modified or previously exported WAV. No synthetic-audio detector or validated overall accent grade is implemented.

## 4. Application and environment readiness

- Existing localhost server remained running; `/site-health` returned HTTP 200, `status=ready`, `public_launch=false`. Served account JavaScript matched the local source by SHA-256. Health/asset checks do not prove browser acceptance or warm models.
- Windows 11 build 26200; Python 3.13.1; i7-1360P; approximately 16 GB RAM. Current CPU inference uses two threads and 16 kHz preparation.
- Local Whisper `openai/whisper-base.en`, revision `911407f4214e0e1d82085af863093ec0b66f9cd6`; phoneme model `facebook/wav2vec2-xlsr-53-espeak-cv-ft`, revision `2c733782da5604684829819a5eb744c193fe9398`. Both actually executed in Phase 6.
- Direct installed MFA 3.3.7 with `english_us_arpa` dictionary/acoustic model; alignment timeout 120 seconds. Compiled-resource cache enabled locally; supported cache experiment is specific to this direct Windows runtime. No model downloads, dependency installations, settings changes or shared-service restarts.
- Windows System.Speech is the working default generation backend. Optional Kokoro environment and manifest are absent. Mocked Kokoro tests passing does not establish installed Kokoro inference. Voice-preserving conversion remains unfinished.
- `pip check` passed, but installed FastAPI 0.141.1 and Uvicorn 0.53.0 differ from declared 0.143.0/0.54.0. Deliberate reconciliation remains necessary; packages were not upgraded.

## 5. Day 5 browser acceptance evidence

These are the actual earlier Day 5 browser observations, not new Phase 6 browser tests. No API or mocked test is substituted for an unexecuted browser case.

| Case | Result | Observation / gap |
| --- | --- | --- |
| Authorized sign-in and private History | PARTIAL | User signed in manually; own saved sessions appeared. Assistant did not execute/verify the successful login submission, logout cycle or current invalid-login states. |
| Open saved preset result | PASS for saved navigation | Selected result/text/status and original audio were shown. Not a new preset browser analysis. |
| Open free-session recording | PASS for saved playback start | Original labeled player used that session's learner asset. Play became Pause. Audible accuracy was not independently reviewed. |
| History navigation | PASS for observed cases | Open action brought result panel into view. Full refresh/persistence and failed/unavailable-session combinations remain incomplete. |
| Fresh upload/recognition/correction/confirmation/analysis sequence | PARTIAL | Automated upload was denied by browser approval review; manual user action was required. Case 1 was later saved/analyzed by the user and its completed result inspected. Assistant did not observe all submission steps. |
| Recording replacement, stale edits and failed-job retry | NOT TESTED in Day 5 browser | Automated regression coverage exists, but the current full browser sequence has not been demonstrated. |
| Generated/original playback separation | NOT TESTED as a new Day 5 browser flow | Rendering and real HTTP/model tests pass; earlier browser evidence does not complete this current checklist. |
| Second-account isolation, empty History and network-error states | BLOCKED / NOT TESTED | No second authorized browser account or suitable isolated state was available. Temporary-account API tests are separate evidence. |
| Live microphone acceptance | NOT TESTED by assistant | User chose manual recording; assistant never activated microphone capture. |

Captured browser console checks had no warnings/errors. This does not establish absence of defects. On initial Case 1 inspection a History card said processing while its opened panel said completed. Possible stale list snapshot; not reproduced/refreshed systematically, so no confirmed root cause or fix. Lucas and Sarrvesh should reproduce before editing.

## 6. Six fresh human cases

| Case / intended words | Recognized / confirmed | Status and findings |
| --- | --- | --- |
| 1: I think so, intended correct TH | Both `I think so.` | Completed. TH inconclusive (`INSUFFICIENT_EVIDENCE`); IH experimentally supported. Not independently labeled pronunciation correctness. |
| 2: say I sink so; assess intended I think so | Not collected | DEFERRED, awaiting fresh recording. ASR disagreement may conservatively withhold judgment. |
| 3: I think, I think so | Not collected | DEFERRED; genuinely spoken repeated-occurrence behavior unverified. |
| 4: I don't think so | Not collected | DEFERRED; genuine spoken contraction behavior unverified. |
| 5: I keep doomscrolling | Not collected | DEFERRED. `doomscrolling` verified absent from the configured dictionary; spoken rejection untested. |
| 6: silence / unusable audio | Not collected | DEFERRED; fresh-human silence handling not observed. Automated unusable-input tests passed separately. |

Case 1: attempt `1411ea4ea5ab4191a8dd2bc052121c1f`, learner asset `0e98c3c86435494ab42f7bf41a46fe8c`, current revision 3; 1.920 seconds, 184,364 bytes, 48 kHz mono PCM16. Original transcription job revision 2 and analysis job revision 3 completed. Full job IDs and detailed evidence are in `DAY_5_FRESH_RECORDING_TESTS.md`. The assistant inspected the already completed attempt rather than submitting a duplicate. Two distinct sound IDs in one word do not prove repeated-word acceptance.

## 7. Performance evidence and target

Reproduced below from Phase 4's retained individual measurements, not rerun as a new performance experiment in Phase 6. Total is transcription-service wall time plus analysis-service wall time; nested MFA/phoneme times must not be added again. Browser upload, confirmation, queues and polling are excluded. All six calls did real inference/alignment; dictionary-resource hits do not mean assessment-output hits. No failures or automatic retries in this six-call series.

| Run / input / worker | ASR s | Analysis s | MFA lock ms | MFA subprocess s | MFA operation s | Phoneme s | Total s | Resources |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 human H1 / fresh worker | 46.551 | 22.660 | 0.401 | 17.725 | 18.409 | 2.042 | 69.211 | Hit |
| 2 ship fixture / reused | 1.343 | 18.091 | 0.409 | 16.258 | 17.111 | 0.643 | 19.434 | Hit |
| 3 H1 same audio / reused | 1.018 | 14.430 | 0.494 | 12.783 | 13.460 | 0.672 | 15.448 | Hit |
| 4 bad_bed fixture / reused | 1.069 | 13.291 | 0.464 | 11.705 | 12.379 | 0.642 | 14.359 | Hit |
| 5 H1 same audio / reused | 1.040 | 13.781 | 0.354 | 11.971 | 12.812 | 0.709 | 14.821 | Hit |
| 6 think fixture / reused | 1.049 | 13.908 | 0.345 | 12.348 | 12.992 | 0.634 | 14.957 | Hit |

Warm n=5 median **14.957 seconds**, range **14.359-19.434**. All five were below 20, but two repeat the single human waveform and three are synthetic engineering fixtures. This does not establish reliable new-human or whole-browser latency below 20 seconds. Human Case 1's original saved processing observation was **41.369 seconds** (ASR 2.316 + analysis 39.054), with unknown worker/cache state; retain it rather than reclassifying it as warm/cold.

Largest warm measured cost: MFA subprocess, **82.34% of aggregate warm total**. Sub-millisecond lock waits do not support removing locking. First-use ASR took 46.551 seconds; imports/loading/inference are not separately isolated. No preparation cost was moved outside requests.

Historical Day 4 controlled warm-preset median: **32.128 to 13.119 seconds, 59.2% lower**, six warm runs per configuration. That is a different preset workload from current confirmed-text runs. Same confirmed fixture ship: Day 4 baseline/optimized 26.075/10.638 seconds; Day 5 19.434. Bad_bed: 27.593/9.764 versus 14.359. Current observations are slower than the old optimized measurements, faster than old baselines, under different conditions; no new causal improvement percentage is claimed.

Day 5 ran on battery (73% to 70%), about 1.79 GiB free RAM, preview/idle worker present; Day 4 comparison was on AC without that app workload. No active production attempts or material lock contention were observed; OS/thermal/paging effects were not isolated. All fixture alignments and sound-result records matched the prior optimized confirmed-text outputs. Human TH/IH outcomes remained unchanged. Too few independent samples for a trustworthy 95th percentile or real-user failure rate. Full settings, clip sizes, timings and raw artifact locations are in `DAY_5_PHASE_4_PERFORMANCE.md`.

## 8. Phase 6 tests actually executed

Commands were run from the repository. Evidence folder: `runs/day5-phase6-20261021T202558Z/` (ignored/local). For the two real-model tools, copies of the existing scripts changed **only ROOT and output destination** so prior evidence files were not overwritten. Original tools and application sources remained unchanged; original tool hashes are retained. Test logic, inference and assertions were not changed.

```powershell
node --check web_assets/accounts.js
node --test tests/session_playback.cjs
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py' -v
.\.venv\Scripts\python.exe -B -m pip check
.\.venv\Scripts\python.exe -B runs/day5-phase6-20261021T202558Z/private_smoke.py
.\.venv\Scripts\python.exe -B runs/day5-phase6-20261021T202558Z/preset_parity_smoke.py
git diff --check
```

| Check | Actual outcome | Category / limitation |
| --- | --- | --- |
| JS syntax | Exit 0 | Syntax only. |
| Rendering | 15 passed, zero failed | Production JS with DOM/HTTP doubles; no real browser/audio decoding. |
| Full Python regression | 168 run; 167 passed, one skipped; 40.163 s; exit 0 | Mixed unit, real DSP/filesystem/process and isolated HTTP/SQLite tests; speech engines usually controlled. Python wrapper includes the 15 JS scenarios; do not double-count. |
| Dependencies | No broken requirements | Does not establish pin equality or fresh-install reproducibility. |
| Private real-model smoke | All 17 checks passed; exit 0 | Actual auth/CSRF, temporary SQLite, Whisper, MFA, phoneme inference and Windows TTS via FastAPI TestClient. Not a browser or new human test. |
| Preset/confirmed parity smoke | All six checks passed; exit 0 | Real ASR; preset wrapper parity against HEAD; real preset processing; committed MFA path versus current parsed-output parity; confirmed snapshot processing; generated-role rejection. Trusted snapshot portion has no production auth/publication. |
| Diff whitespace | Passed | Existing CRLF-conversion notices only. |

Regression groups: transcription 11; transcript preparation 12; confirmed analysis 13; private practice 13; accounts 6; preset pipeline 22; beginner UI 14; reference-free 5; sound assessment/evidence quality 19; cache/timing 14; generation service/HTTP/Kokoro/default backend 18; release safeguards 11 (one skip); site 9; rendering wrapper 1. These sum to 168. Group details and full outputs are retained in `test-groups.json`, `regression.log` and `rendering.log`.

The skip is the existing Windows symlink-creation test. Real subprocess timeout/recovery and cross-process lock-release tests passed; simulated cache corruption, copy/publication failure and timeout nonpublication tests passed. Starlette/httpx deprecations, Transformers generation warnings and unclosed event-loop ResourceWarnings remain visible in the logs. No package changes were made to hide them. Read-only inspection initially encountered PowerShell quoting and default-text-encoding errors; corrected checks succeeded. Neither was an application/model failure.

Real-model details:

- Private smoke attaches the existing `data/references/think.wav` as a disclosed engineering learner fixture, not scoring-reference audio. Original-text analysis completed with TH inconclusive/IH supported. Repeated/contraction **text edits against that same original recording** produced four/two inconclusive results with CONTENT_UNVERIFIED. This verifies abstention, not correctly spoken repeats or contractions.
- Analysis processing times were 18.079 / 14.651 / 14.001 seconds for the three different confirmed texts; generation 1.412 seconds. These are separate smoke-job measurements, not three equivalent latency trials or new human recordings. ASR/complete browser wait is not separately summarized by this smoke script.
- Synthetic playback returned WAV bytes; registered generated reupload was rejected. Temporary smoke account/database were cleaned by the tool. Production sessions were not created/requeued/edited.
- Preset real processing had alignment available, uncertain phoneme evidence and overall `partial`; feedback/save succeeded and all reference-comparison stages were skipped. That is a valid conservative processing result, not an operational failure. Current alignment used a dictionary-resource hit and a real 14.870-second subprocess. The committed-path comparison matched parsed labels, boundaries, prepared identity, duration/rate and boundary corrections exactly for this one clip.
- Confirmed snapshot retained explicit learner/attempt/job/revision identities and completed; generated-role input was rejected. These checks do not prove sound judgment accuracy.

## 9. Workflow status matrix

| Workflow | Integration / verification status |
| --- | --- |
| Independent ASR, confirmed text, dictionary/token occurrences | Implemented in committed baseline; unit/controlled and real-model checks passing. Human repetition/contraction acceptance incomplete. |
| Preset lessons | Implemented; regression checks and one real preset passing. New Day 5 preset browser submission not tested. |
| Original playback, History discovery | Local uncommitted fix; rendering/HTTP passing; observed saved browser playback start/navigation passing. Full playback/error matrix incomplete. |
| Private profiles, sessions, ownership and persistence | Implemented SQLite integration; temporary-account HTTP tests passing, including second-user denial/restart. Current multi-account browser acceptance not tested. |
| Revision invalidation / stale publication | Implemented; controlled edit/delete/logout/job tests passing. Current complete browser edit-and-recording-replacement sequence not tested. |
| Recognition race / analysis retry | Local uncommitted fixes; queued/processing and injected-failure regressions passing. Real browser failure/retry remains unverified. |
| Dictionary-resource speed cache | Local uncommitted implementation enabled only by ignored machine settings; tests and real-MFA parity passing; historical speed evidence retained. General new-human latency target unverified. |
| Synthetic examples | Windows backend integrated and real HTTP/model checks passing; target accent/word quality requires listening review. Optional Kokoro is not installed here. |
| Voice-preserving conversion | Not implemented/verified as an integrated feature. |
| Human acceptance / validated grades | One collected case, five deferred. No validated overall grade or accuracy claim. |

## 10. Complete Git inventory

Modified tracked files (all unstaged):

| File | Scope |
| --- | --- |
| accounts/sessions.py | Recognition/confirmation guard and clean analysis retry state. |
| phoneme_scoring/align_audio.py | Guarded dictionary-resource cache hook under existing lock. |
| tests/test_mfa_timings.py | Cache/lock/timeout boundaries and fallback tests. |
| tests/test_practice_sessions.py | Three reliability regression cases. |
| web_assets/accounts.js | Day 3 original playback plus later History/confirmation/retry reliability. |

Untracked files, including this new report:

```text
docs/DAY_3_TEAM_HANDOFF.md
docs/DAY_4_DEMO_RUNBOOK.md
docs/DAY_4_MFA_INVESTIGATION.md
docs/DAY_4_PHASE_4_VERIFICATION.md
docs/DAY_4_SPEED_HANDOFF.md
docs/DAY_5_FRESH_RECORDING_TESTS.md
docs/DAY_5_PHASE_4_PERFORMANCE.md
docs/DAY_5_TEAM_HANDOFF.md
docs/DEMO_FIXES_REPORT.md
output/presentation/team_execution_editable.pptx
output/presentation/team_execution_plan.png
output/presentation/team_execution_plan.svg
output/presentation/team_execution_timeline.png
output/presentation/team_execution_timeline.svg
phoneme_scoring/mfa_dictionary_cache.py
tests/session_playback.cjs
tests/test_mfa_dictionary_cache.py
tests/test_session_playback.py
```

Presentation exports are preexisting unrelated artifacts, excluded from proposed application commits. No additional teammate-authored edits can be attributed solely from unstaged metadata; all current files are identified for affected-owner review. Accounts/generation foundations already imported in history must not be misrepresented as newly authored by Sarrvesh.

Ignored runtime items are not Git-untracked candidates: private account database/recordings, models, `.venv`, machine-local settings, compiled resource cache and `runs/` diagnostics. Phase 6 added only this handoff and isolated ignored verification artifacts, not application or contract edits. Keep raw recordings, account data and personal machine paths out of commits. Test tools currently require locally available model/fixture assets; a fresh clone alone is insufficient.

## 11. Teammate dependencies and commit proposal

**Lucas:** review the actual `accounts/store.py`/`sessions.py`/`practice_jobs.py` integration and shared `accounts.js`. Preserve opaque server authentication, ownership on every read/play/update/delete, immutable original assets, atomic input revisions/job publication and restart recovery. Required integration interfaces already exist; do not introduce duplicate persistent storage. Reproduce the History list/panel status discrepancy and complete two-account browser/persistence/error cases. Review the uncommitted shared reliability changes before merge.

**Parthiban:** review default `generate_audio(confirmed_text, target_accent, output_dir=...)` wiring through `PracticeJobs`, generated ID/type and authorized asset publication. Preserve the approved flat session contract rather than replacing it with the standalone DevelopmentStore's nested fixture shape. Confirm generation failure/stale-output behavior on the combined branch; review actual words, General American suitability and voice licensing. Select/install an optional replacement backend only as separately agreed; conversion remains a separate experiment. Internal standalone helpers permit longer text, so public calls must continue through confirmed-text validation rather than bypassing it.

**Sarrvesh:** coordinate shared-file reviews, retain speed/cache safeguards, finish browser/new-human acceptance and produce controlled latency evidence. No current fix changes `app_2.py` or `pipeline.py`.

Proposed commit boundaries, **not staged or approved in this phase**:

1. **Private practice playback and lifecycle reliability:** `accounts/sessions.py`, `web_assets/accounts.js`, `tests/test_practice_sessions.py`, `tests/session_playback.cjs`, `tests/test_session_playback.py`. Combines adjacent playback/reliability edits because their whole-file changes overlap; Lucas review required. If separate historical commits are desired, review exact hunks and seek approval rather than rewriting files/history.
2. **Versioned MFA compiled-dictionary resource reuse:** `phoneme_scoring/align_audio.py`, `phoneme_scoring/mfa_dictionary_cache.py`, `tests/test_mfa_timings.py`, `tests/test_mfa_dictionary_cache.py`. Separate from account/UI work; no local settings/cache/model files included.
3. **Engineering evidence and handoff:** the nine listed untracked docs. Clearly retain historical dates and newer superseding conclusions. Update stale contract/setup prose in a separately reviewed documentation change if desired; no schema change is proposed here.

No presentation files in these commits. Benchmark harnesses/raw logs remain local and ignored; agree on a sanitized reproducibility package before teammates rely on unavailable evidence files. Approval is still needed before staging/committing; push and integration-branch merges require explicit authorization. Earlier approvals applied to earlier committed scopes, not these pending changes.

## 12. Next integration sequence

| Order | Owner | Work / dependency | Acceptance criteria |
| --- | --- | --- | --- |
| 1 | Sarrvesh with Lucas/Parthiban | Review current actual remote changes and the scopes above before integration; no blind teammate-branch merge. | Approved file ownership and commit scope; all local work preserved; no private/runtime artifacts staged. |
| 2 | Sarrvesh + Lucas | Integrate reviewed private playback/lifecycle changes and reviewed cache change as separate scopes. Reconcile documentation/runtime setup and dependency pins deliberately. | Team checkout can locate required models/MFA/fixtures; full regressions and isolated real smoke pass on integration branch. Cache remains opt-in with documented safe fallback. |
| 3 | Lucas + Sarrvesh/user | Complete the browser checklist, including second-account isolation, upload, correction, replacement, retry and persistence. Reproduce History status mismatch before fixing. | Recorded actual browser steps/results; correct learner/text/revision association; old results absent after edits; unauthorized assets inaccessible. |
| 4 | User + Sarrvesh | Supply and test human cases 2-6; retain original recognition, confirmation, identities and conservative outcomes. | Six-case report completed or specific blockers retained; missing coverage/silence never fabricated as pronunciation findings. |
| 5 | Parthiban + Lucas | Confirm synthetic output on authorized current revisions; listening review and failure/stale-output checks. | Correct words/acceptable target voice reviewed; synthetic labeled separately; generation failure leaves valid assessment intact; no stale or cross-user playback. |
| 6 | Sarrvesh | Broaden equivalent new-recording benchmarks under documented power/load; then rehearse the complete demo. | Individual fresh/warm runs, all slow/failing cases retained; processing and browser waits separate; under-20 target claimed only for supported measured conditions. |

Retain the dictionary optimization and reliability/playback fixes for review: observed regression and model evidence supports them. **Final readiness: ready with caveats for controlled integration, not full acceptance.** Remaining unverified behavior is the complete current browser edit/replacement/retry/multi-account journey, five fresh-human cases, independent sound accuracy, generated voice quality, broad new-human under-20-second performance and optional voice conversion. Local uncommitted code is not evidence that teammates already have these changes.
