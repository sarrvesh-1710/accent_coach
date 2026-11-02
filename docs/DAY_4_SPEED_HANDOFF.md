# Day 4 speed handoff

October 18, 2026, America/Chicago. Owner/integration coordinator: Sarrvesh Mahadevan. Phase 6 is an evidence and Git audit, not another optimization or release.

## 1. Decision and current status

**Retain the opt-in dictionary-resource cache for controlled integration.** The Phase 4 warm-worker preset median decreased from **32.128 to 13.119 seconds**, saving **19.009 seconds / 59.2%** across six planned calls per path. Same-clip phone/word alignments and sound decisions were preserved. The change benefits different recordings using the same dictionary resources; it does not reuse an earlier pronunciation result.

**The application is not signed off for a reliable below-20-second free-speech demo.** Optimized fresh-worker requests took **31.336–46.749 seconds**; all six optimized warm preset calls were under 20 seconds. The dictionary-cache setting is still **disabled in persistent configuration**, so those optimized figures do not describe the current running website. Live free-speech timing, failed-analysis browser retry and fresh human acceptance remain incomplete. A preset-style saved result is available as an honestly labeled fallback, not as a substitute for a new speaker's result.

Current local HTTP health was checked during this audit and returned `service=accent-coach`, `status=ready`, `public_launch=false`. Earlier automated startup was blocked; the user subsequently started the app manually. Signed-in Practice and Free speech selection were observed in the browser. No service was restarted in Phase 6, and health alone is not an inference test.

This document **supersedes the initial readiness status in DAY_4_DEMO_RUNBOOK.md**. That file still says manual startup is pending because its attempted follow-up update was blocked by automatic approval review. Its startup/presenter/recovery steps remain useful; do not mistake its initial blocker chronology for the current server state. No old report was overwritten to conceal that history.

## 2. Git baseline, scope and preservation

- Repository: `C:\Users\sarrv\Documents\Codex\2026-09-15\re\accent_coach`.
- Branch: `feature/speed-free-speech`.
- Starting baseline and current HEAD: **e7f57d9ce37f95cb6c3cc30a870c8aae284656d7**. Baseline ancestor check returned exit 0. No new Day 4 commit exists.
- Recent history: e7f57d9 (MFA launch support/integration handoff), 74978dc (authenticated confirmed practice and synthetic examples), 2d42433 (Day 2 verification), cece3cd (MFA timers), bdabbea (confirmed-text backend).
- Index is empty. All application changes listed below remain unstaged. No reset, stash, merge, rebase, discard, history rewrite, commit or push was performed.
- Full tracked diff and every untracked code/test file were reviewed against their documented scopes. No additional unexplained application modification was found. This is a local working-tree conclusion; remote teammate branches were not fetched or merged, so their latest state is not established.
- Current application/settings hashes match all 14 entries retained in the Phase 4 benchmark source manifest. This includes the worker, pipeline, confirmed backend, transcription, scoring modules, optimization and settings. No code was changed after that benchmark to obtain this report.

### Separate Day 3 playback fix: preserved byte for byte

| File | Scope | Current SHA-256, matched to retained baseline |
| --- | --- | --- |
| web_assets/accounts.js | Day 3 only: +16/-1; authenticated original learner player, distinct from generated playback | 6f55e2354820f9b249d2bfe5739247a5ccb260b33fae8142f3bf966a3f076ee1 |
| tests/session_playback.cjs | Ten production-renderer scenarios using DOM/HTTP doubles | cdf5c35168ea0545d72ceba362429db925c5604152461736b44d97abfc290381 |
| tests/test_session_playback.py | Python wrapper for those JavaScript scenarios | b6c62cba0f0fd6a24afdc6ff64717f59f829cd77abf51269efbb06cb24832de2 |
| docs/DAY_3_TEAM_HANDOFF.md | Historical Day 3 evidence and limitations | 317868157f73756a8b50e8f42984b2c8c732b34f4780ecf4b29a7b758dfea71d |

### Day 4 changes and untracked inventory

| Path | Git state at audit | Purpose |
| --- | --- | --- |
| phoneme_scoring/align_audio.py | Modified, +17 lines | Guarded resource-cache hook inside existing lock |
| tests/test_mfa_timings.py | Modified, +40 lines | Three cache-hook/failure tests; existing timing behavior retained |
| phoneme_scoring/mfa_dictionary_cache.py | Untracked | Version/resource identity, verified request copies, atomic publication |
| tests/test_mfa_dictionary_cache.py | Untracked | Six filesystem/resource/fallback tests |
| docs/DAY_4_MFA_INVESTIGATION.md | Untracked | Source/profile evidence and approved experiment |
| docs/DAY_4_PHASE_4_VERIFICATION.md | Untracked | All individual performance tables and correctness evidence |
| docs/DAY_4_DEMO_RUNBOOK.md | Untracked | Startup, presenter steps, timing worksheet and fallback; initial status superseded above |
| docs/DAY_4_SPEED_HANDOFF.md | New in Phase 6 | This consolidated handoff |

The other untracked files are the three Day 3 test/handoff files in the preceding table. Before this report there were three modified tracked files and eight untracked files; adding this report makes nine untracked files. No application/test edit was made in Phase 6. `git diff --check` passed during the audit. Git warns about future LF/CRLF conversion on two tracked files; no conversion was performed.

Ignored benchmark reports/scripts/logs, private account data, recordings, model weights and `settings.local.json` are not proposed for Git. Do not force-add them. In particular, the new comparative harnesses currently live under ignored `runs/`; teammates do not automatically receive them through a documentation-only commit. A reviewed, sanitized tooling export is a remaining reproducibility task, not an implemented change.

## 3. Environment and exact execution boundaries

Measured installation: Windows 11 build 26200; application Python 3.13.1; i7-1360P, 12 cores/16 logical processors; about 16 GB RAM. MFA 3.3.7 runs in the separate existing Python 3.11.16 Conda environment. Torch 2.14.0+cpu, Transformers 5.17.0, NumPy 2.2.6, SciPy 1.15.3, Gradio 6.28.0. Model CPU thread settings remain 2.

Pinned local models:

- ASR: `openai/whisper-base.en`, revision `911407f4214e0e1d82085af863093ec0b66f9cd6`.
- Phones: `facebook/wav2vec2-xlsr-53-espeak-cv-ft`, revision `2c733782da5604684829819a5eb744c193fe9398`.
- MFA dictionary/acoustic model: `english_us_arpa`; existing installed local assets. No dictionary/pronunciation edits or model downloads.

The effective local MFA command uses its direct Windows executable with child-only PATH/CONDA_PREFIX settings. Full machine-local PATH is deliberately omitted here. It remains in ignored local configuration, whose hash was unchanged. MFA subprocess timeout is 120 seconds; file-lock acquisition timeout 120 seconds; service deadline 180 seconds plus owned-process cleanup. No limits, locking, inference settings or public interfaces were weakened.

Command structure, with W a fresh request directory:

```text
C:\Users\sarrv\anaconda3\envs\accent-coach-mfa\Scripts\mfa.exe
  align_one W\corpus\clip.wav W\corpus\clip.lab
  english_us_arpa english_us_arpa W\aligned.TextGrid
  --output_format long_textgrid --no_use_mp --temporary_directory W\temp
```

Only a validated resource hit adds `--no_clean`, selecting the installed MFA load branch. Working directory remains inherited; W is not a reused corpus/result directory.

Dependency caveat: current FastAPI 0.141.1 and Uvicorn 0.53.0 differ from requirements-accounts.txt pins 0.143.0/0.54.0. The earlier Phase 5 `pip check` passed, which does not establish exact declared-version reproducibility. No package was upgraded to remove this discrepancy.

## 4. Baseline verification and root-cause evidence

The approximately 32-second warm baseline and 94.5% MFA share belong to the completed Day 3 series. Day 4 Phase 1 remeasured, rather than assuming those figures still held. No optimization had yet been applied.

| Phase 1 clip | Worker | Total seconds | Outcome/condition |
| --- | --- | ---: | --- |
| think | Fresh | 65.538 | Completed; first-use variability |
| think | Warm 1 | 21.633 | Completed |
| think | Warm 2 | 21.320 | Completed |
| ship | Fresh | 34.447 | Completed |
| ship | Warm 1 | 20.216 | Completed |
| ship | Warm 2 | 21.087 | Completed |
| bad_bed | Fresh | 34.907 | Completed |
| bad_bed | Warm 1 | 23.002 | Completed, overlaps standby entry; excluded from unaffected summary |
| bad_bed | Warm 2 | 914.733 | Timeout after standby interval; no complete stage data; retained |

Unaffected think/ship warm median was 21.203 s; MFA accounted for about 94.4%. Thus Day 3's absolute time was not a guaranteed current baseline. Phase 1's slow/failed runs remain in `runs/phase3-baseline-20261018T185807Z.json`; no missing stage duration is inferred from the timeout. Standby affects deadline observation and wall-clock comparability and is not removed by caching.

Installed-source inspection found that every original request created a fresh MFA temporary dictionary directory. MFA's `command_line/align_one.py:135` loads compiled resources only if L.fst exists and CLEAN is false; otherwise it reloads pronunciations and builds/writes the dictionary graphs. Each request therefore repeated dictionary initialization, despite identical installed resources. Four matching artifacts totaled 110,072,628 bytes across retained builds. The same CLI also initializes its acoustic model/aligner and runs dependency checks. Shared model extraction still justifies the existing lock. MFA's `server` command manages a database service, not a tested alignment RPC worker.

The lead approved one diagnostic cProfile run before approving the cache experiment:

| Diagnostic cumulative entry | Seconds |
| --- | ---: |
| Initial MFA package import | 4.817 |
| load_pronunciations | 3.378 |
| create_fsts | 11.659 |
| AcousticModel constructor, including archive unpacking | 0.470 |
| Third-party executable checks | 0.815 |
| generate_mfccs | 3.001 |
| KalpyAligner constructor | 0.452 |
| align_utterance | 0.159 |

The profiled process returned 0 in 27.245 s, and parsed output matched its fixture baseline. Profiling is diagnostic, not a latency benchmark. Cumulative entries can overlap and cannot be added into a normal-runtime budget or subtracted to predict a saving. Evidence: `runs/day4-mfa-profile-20261018T192328Z/{diagnostic.json,mfa.pstats}`.

## 5. Approved optimization and failure behavior

The lead explicitly approved a versioned cache of **compiled dictionary resources**, preserving per-request audio/transcript/output directories and all ownership/revision safeguards. It is not exact-input alignment caching or a persistent initialized MFA service.

- `mfa_dictionary_cache.plan` keys resources by dictionary/acoustic content, installed runtime metadata, relevant MFA settings/global configuration/profile and installation identity. Only the inspected direct Windows MFA 3.3.7 path is supported.
- Inside the existing MFA lock, `seed` checks the manifest/file shapes, nonempty files and SHA-256 integrity, copies all four files into staging, verifies copies, and atomically exposes a request-specific dictionary directory. No hardlinks or shared mutable FST files.
- `publish` atomically publishes complete resource copies after successful subprocess/nonempty-output checks. The cache contains only L.fst, L_align.fst, words.txt, phones.txt and a manifest. Never learner WAVs, LAB transcripts, TextGrids or sound findings.
- Missing/corrupt cache or preparation errors use normal compilation where possible. Publication failure does not invalidate a successful alignment. Existing invalid entries are retained for review rather than deleted. A runtime MFA load failure remains an ordinary unavailable alignment; no hidden second 120-second attempt is added.
- The original disabled path remains the fallback. About 110 MB shared storage per resource identity plus per-request copies is required; no eviction/retention system was introduced.
- Phase 3 review exposed a valid-JSON list manifest causing AttributeError. The expanded test reproduced it (one error among six resource tests) before a narrow type-validation fix. Subsequent focused/full checks passed. This failure and correction are retained in the investigation narrative; it was not concealed.

Correct audio/text joins, learner role, ownership, job/attempt identity, input revision, stale publication, preset entry points, conservative evidence, locking/timeouts and cleanup were not redesigned. No auth/storage/schema/generation/UI interface change belongs to Day 4's optimization.

## 6. Comparative performance and target assessment

Phase 4 used three 16 kHz mono PCM16 fixtures: think (1.730 s, 55,406 bytes), ship (1.905 s, 61,006 bytes), bad_bed (2.010 s, 64,366 bytes). They are synthetic engineering fixtures, not fresh human speech or accuracy labels. Identical source hashes/settings were used across paths; optional reference comparison was false.

There were 18 planned preset service calls, six independent transcription calls, six confirmed-text analysis calls and one later baseline numeric-repeatability control. Real Whisper/MFA/phoneme engines ran. Each preset path used a fresh worker, then two reused-worker calls per clip. Path order alternated across clips; no concurrency or cache flushing. The optimized cache namespace started empty. Existing per-worker model-object caches were retained, not assessment-result caches.

### Individual planned preset totals

All numbers are seconds; each cell lists separate retained calls, not a range or fastest-only selection. Every call completed its required processing, feedback and save path; overall status remained partial where local evidence was uncertain.

| Clip | Baseline fresh, resources disabled | Baseline warm 1 / 2 | Optimized fresh | Optimized warm 1 / 2 |
| --- | ---: | --- | --- | --- |
| think | 45.830 | 33.733 / 33.685 | 46.749, resource miss/build | 15.021 / 14.406, hits |
| ship | 46.846 | 29.189 / 30.570 | 32.111, resource hit built from think | 13.267 / 12.971, hits |
| bad_bed | 44.836 | 33.819 / 30.279 | 31.336, resource hit built from think | 10.450 / 10.364, hits |

### Like-for-like changes

| Clip/condition | Baseline | Optimized | Seconds saved | Percent saved |
| --- | ---: | ---: | ---: | ---: |
| think fresh, first resource build | 45.830 | 46.749 | -0.920 | -2.0% |
| ship fresh, resources available | 46.846 | 32.111 | 14.735 | 31.5% |
| bad_bed fresh, resources available | 44.836 | 31.336 | 13.500 | 30.1% |
| think warm median, two each | 33.709 | 14.713 | 18.996 | 56.4% |
| ship warm median, two each | 29.880 | 13.119 | 16.761 | 56.1% |
| bad_bed warm median, two each | 32.049 | 10.407 | 21.642 | 67.5% |
| All planned warm calls, six each, median | 32.128 | 13.119 | 19.009 | 59.2% |

Warm baseline range was 29.189–33.819 s; optimized 10.364–15.021 s. Mean/sample standard deviation: baseline 31.879/2.096 s; optimized 12.746/1.959 s. Small-sample descriptive statistics, not a reliability guarantee. Warm MFA-subprocess median decreased from 29.762 to 10.259 s. Lock waiting remained milliseconds.

The first optimized build was slightly slower; do not report it as an improvement. No model preparation was moved outside the request. Worker spawn/import readiness is included in first-call totals; existing timers do not isolate pure model loading from inference. Fresh worker is not a cold machine/OS disk cache. Cache plan/verification/copy/publication costs are included in MFA-operation/outer totals but are not separately timed.

### Confirmed-text flow: actual separate service calls

| Clip | Baseline transcription / analysis | Optimized transcription / analysis | Baseline sum | Optimized sum |
| --- | --- | --- | ---: | ---: |
| think | 11.251 / 20.684 | 12.371 / 10.716 | 31.934 | 23.087 |
| ship | 0.710 / 25.365 | 0.821 / 9.816 | 26.075 | 10.638 |
| bad_bed | 0.993 / 26.600 | 0.666 / 9.098 | 27.593 | 9.764 |

One pair per clip/path. Think starts a fresh worker for ASR; analysis follows in that worker. Ship and bad_bed then reuse it. Confirmation delay/browser transport/rendering are excluded. Different target sets mean confirmed and preset totals are not pooled as equivalent work. Analysis used actual saved ASR provenance and trusted diagnostic snapshots, not an authenticated browser session or a fabricated recognized transcript.

Supplementary control run 31, unoptimized ship with a new worker: 39.279 s total, 24.621 s MFA subprocess, 0.953 ms lock wait. It is retained separately, not substituted for the preplanned baseline. No Phase 4 operational failures or retries occurred among the 31 calls. Its different timing illustrates background/time-order variability.

The preceding Phase 3 seven-call alignment-only experiment is separate evidence: totals in order were 27.722 baseline think; 25.573 think build/miss; 10.248 ship hit; 26.602 ship baseline; 24.994 bad_bed baseline; 10.658 bad_bed hit; 9.700 think hit. All seven were available with matching parsed outputs. Do not combine alignment-only timings, profiled time and service-call totals into one speed claim.

### Was the below-20-second goal achieved for new recordings?

- **Yes, narrowly:** in the experiment's existing-resource, reused-worker conditions, all six warm preset calls were below 20 s. Resource hits also supported different audio/transcripts: ship and bad_bed reused dictionary resources built from think, with fresh per-request alignment and inference.
- **Not reliably for first-use/new-worker requests:** all three optimized fresh-worker preset calls exceeded 20 s. The first confirmed transcription+analysis pair also exceeded it (23.087 s). A different recording in a fresh worker is not equivalent to a warm repeat.
- **Not established for new human recordings, five-second clips or whole-browser waits:** those are not covered by this three-fixture backend series. Current website configuration still uses the disabled/baseline resource path, so it has no demonstrated live optimized speed gain yet.

## 7. Correctness, tests and known failures

Phase 4 completed 25 real MFA alignments (18 preset, six confirmed and one control) in distinct request directories. Same-clip phone/word sequences, boundaries, prepared hashes, transcripts, duration/rate and sound decision labels matched. Confirmed results retained source bytes/hash, confirmed/normalized text, learner ID, attempt/job identity and revision 2. Confirmed temporary MFA directories were gone after return; preset audit outputs were intentionally retained.

Local uncertainty remained visible: think's seven speech segments and ship's ten remained uncertain; bad_bed retained eleven uncertain and one scored. Silence was skipped, not judged correct. Target support is experimental, not a validated pronunciation label. Confirmed sound-result/limitation records matched across paths.

Raw neural scores were not universally bit-identical. Ship differed by at most **0.000048100948333740234** in the inspected values without changing alignment, categorical outcomes, selected alternatives or feedback. An extra unoptimized restart reproduced the optimized phoneme/target output exactly while differing from the first unoptimized run. The observed variation is not specific to dictionary reuse; the lower-level numerical cause and near-threshold behavior remain unverified.

Tests actually executed earlier in Day 4, verified from retained logs during this audit:

| Command/check | Actual outcome | Evidence/limitations |
| --- | --- | --- |
| `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_mfa*.py' -v` | 14 passed; Phase 4 rerun 0.259 s | Six resource filesystem tests plus eight controlled clock/subprocess hook tests; no real MFA inference in this group |
| `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py' -v` | Phase 3: 165 run, 164 passed/1 skipped, 32.636 s; Phase 4: same counts, 27.615 s | Mixed unit, real file/DSP/text and temporary SQLite/HTTP tests; engines mocked in many tests |
| Embedded playback renderer wrapper | Ten JavaScript scenarios passed within the Python suite | DOM/HTTP doubles; do not add ten again to the 165-test count; no audibility claim |
| Real process/lock recovery tests in full suite | Passed | Owned subprocess timeout followed by a successful process; cross-process file-lock exclusion/release after crash; controlled worker restart/concurrency rejection |
| `.\.venv\Scripts\python.exe -B -m pip check` (Phase 5) | No broken requirements | Does not establish declared-version equality or model readiness |
| `git diff --check` and source-hash audit (Phase 6) | Passed; retained source/settings/Day 3 hashes unchanged | No new neural or browser run claimed |

The one skip is the existing Windows symlink-creation limitation. Existing dependency/deprecation/resource warnings remain. Before fixing malformed manifest handling in Phase 3, one resource test errored; that was corrected and rerun, not hidden. Phase 1's standby-associated timeout remains documented above. No new tests or benchmarks were rerun in Phase 6 merely to restate earlier results; its executed checks were evidence parsing, source/hash/configuration audit, Git checks, installed metadata and HTTP health.

Regressions cover preset behavior, transcription parameters/model cache/provenance, text/recording limits, repeated occurrence IDs, unsupported dictionary words/sounds, conservative inconclusive evidence, ownership, learner/generated separation, input revisions and stale publication. They support those software safeguards, not a completed human evaluation. Live timeout/failed-job retry was not performed in the browser, and no service was deliberately killed to manufacture it.

## 8. Demo rehearsal: current evidence and blockers

Use `docs/DAY_4_DEMO_RUNBOOK.md` for exact presenter steps/recovery/fallback, with this section as the current readiness correction:

| Check | Evidence | Current conclusion |
| --- | --- | --- |
| Startup and HTTP health | Initial automated launch rejected; user then started documented app command; later/current health returns ready | Server available; launch-to-ready preparation interval unmeasured |
| Sign-in / Free speech control | Agent observed signed-in Practice and selected Free speech in the in-app browser | Passed navigation/control observation, not complete analysis |
| New file submission | Automated upload had been rejected; manual file selection requested | Agent did not time/execute the full fresh upload/transcription sequence |
| Free-speech result with cancelled ASR | User screenshot shows transcription cancelled, analysis completed, TH/IH inconclusive and CONTENT_UNVERIFIED | Processing occurred; correct abstention; not a successful verified-content free-speech rehearsal |
| Cancellation investigation | Confirmed text change calls accounts/sessions.py:155 `_invalidate`; lines 103–108 cancel queued/processing jobs, including ASR; Confirm is not gated on ASR completion | Plausible premature-confirmation workflow failure; exact click order not independently captured; no fix implemented |
| History Open recording and results | Source inserts selected results after the entire list without scrolling; user later supplied a visible saved result | Navigation/discoverability concern; live scroll behavior not independently reproduced in this session |
| Successful saved result | User screenshot shows recognized "I think so.", TH expected-sound support, saved recording/result and download link | Preset-style rendering evidence; not proof of the full free-speech confirmation path; no timing |
| Microphone/fresh human acceptance | No fresh consented recordings or new microphone permission | Deferred; synthetic fixtures are not a substitute |
| Failed analysis retry / stale current display | Covered by controlled backend regressions; no complete live browser failure/retry rehearsal | Browser check remains unverified |

No screenshot supplies click-to-completion durations; card timestamps are not processing measurements. The browser tab later ceased being available to automation, so the user screenshots are explicitly user-provided evidence rather than agent-executed acceptance cases. No private database access was used to bypass sign-in or reconstruct a browser test.

### Practical presentation procedure and fallback

From the repository directory, use `.\.venv\Scripts\python.exe app_2.py`, or the documented equivalent `python site_server.py`, and only one server. Reuse a healthy instance; do not restart shared services or change port/configuration casually. Sign in, choose Free speech, select/record permitted audio, press Save and transcribe, **wait for completed transcription and visible recognized words**, then review/confirm and analyze. Treat errors/inconclusive evidence honestly. These steps are a workaround for rehearsal, not an implemented confirmation-gating fix.

Until measured live, quote the prior **current/default backend** confirmed-flow sums of about 26–32 seconds, excluding editing/browser overhead; first-use preset measurements were about 45–47 seconds. Reserve presentation time without promising a deadline. The optimized 10–15-second warm figures are experimental and not active website timings.

If live analysis is slow or fails, keep the honest job status. Present a clearly dated earlier saved attempt, saying it is a previous example and is not the new recording's result. If the website is unavailable, show the actual Phase 4 report/measurement table locally with its synthetic-fixture limitation. Never relabel cached output, generated speech or a screenshot as a new human assessment. Do not disable safeguards or stage a fake success.

## 9. Remaining bottlenecks, risks and teammate dependencies

**Measured remaining work:** MFA still starts/imports/models/features/decodes per request; warm optimized MFA subprocess median is 10.259 s. Fresh ASR/check stages were 12.777–16.408 s versus 0.761–1.417 s warm; loading/inference are not separately measured. Lock waiting was negligible without contention. There is no evidence here that removing locks, speculative parallelism or buying a larger server is the next validated improvement.

**Uncertainties:** OS caches were not reset; order was fixed/partly alternated, not randomized; only two warm trials per clip/path; only one first dictionary build; 1.73–2.01 s synthetic clips; background CPU/thermal/antivirus effects unisolated. Phase 4 was AC/Balanced, one analysis job at a time, with no recorded standby events; Phase 1 standby demonstrates sensitivity. Multiserver contention, maximum-length clips, broad dictionary variants, human judgment accuracy and near-threshold numerical stability are not established.

**Resource/cache risks:** supported installation is narrow; integrity/config changes cause recompilation. Corrupt entries are retained and may repeatedly miss until reviewed. Disk storage grows by resource identity without automatic eviction. An MFA runtime loading failure has ordinary failure behavior rather than an automatic uncached retry. These are reasons to keep the feature opt-in, not to claim flawless or universal acceleration.

| Owner | Required coordination / next action |
| --- | --- |
| Sarrvesh | Own speed/alignment integration; obtain explicit local cache-activation approval before changing configuration; coordinate one bounded confirmation/transcription fix and browser rerun; preserve source/evidence and export reviewed benchmark tooling if needed |
| Lucas | Review the separate Day 3 accounts.js playback change; review confirmation/invalidation semantics in accounts/sessions.py and History result discovery before any fix; preserve authorization/revision/CAS and private asset routes |
| Parthiban | Preserve generated asset role/type and synthetic labels; avoid generation workload during comparable speed measurement; coordinate any runtime/resource changes that could alter cache identity; no voice-conversion success claimed |
| Team | Review current remote branch work before integration; reconcile dependency pins intentionally; provide consented human clips and independent sound labels; do not promote to public/validated grading from synthetic backend tests |

No new public session field, service contract or storage schema was introduced by the optimization. No teammate branch was merged or overwritten.

## 10. Proposed commits: approval required, nothing staged

The files separate cleanly by feature; no history rewriting or file changes are needed to separate playback from speed:

1. **Restore original learner playback in private sessions (Day 3):** web_assets/accounts.js, tests/session_playback.cjs, tests/test_session_playback.py, docs/DAY_3_TEAM_HANDOFF.md. Lucas review before merge. No MFA optimization files.
2. **Reuse versioned MFA compiled dictionary resources (Day 4):** phoneme_scoring/mfa_dictionary_cache.py, the +17-line align_audio.py hook, tests/test_mfa_dictionary_cache.py, the +40-line test_mfa_timings.py additions. No UI/auth/personalization files. The cache remains opt-in.
3. **Document measured speed, limitations and handoff (Day 4):** docs/DAY_4_MFA_INVESTIGATION.md, docs/DAY_4_PHASE_4_VERIFICATION.md and this report. DAY_4_DEMO_RUNBOOK.md is also Day 4 documentation, but reconcile its obsolete readiness statements or explicitly package it as the initial blocked-rehearsal record before committing it as current instructions. This report supplies the latest correction; the original file was not silently changed.

Hold all ignored logs, machine-local paths/settings, private data, model files and raw recordings out of these commits. A sanitized repeatable benchmark harness could be proposed separately after review; no new tooling export was performed here. Do not stage or push until explicitly approved. The old Day 3 proposed two documentation/code commits can remain separate instead of combining them if the team prefers; both arrangements preserve feature separation.

## 11. Reproduction commands and evidence index

Commands already executed during Day 4, from the repository directory:

```powershell
.\.venv\Scripts\python.exe -B tools/benchmark_pipeline.py
.\.venv\Scripts\python.exe -B runs/day4_phase4_verify.py
.\.venv\Scripts\python.exe -B runs/day4_phase4_control.py runs/day4-phase4-20261018T194539Z
.\.venv\Scripts\python.exe -B runs/day4_phase4_summarize.py runs/day4-phase4-20261018T194539Z
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_mfa*.py' -v
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py' -v
.\.venv\Scripts\python.exe -B -m pip check
```

The comparative harness creates a new timestamped directory/cache; on a future approved rerun, pass that new directory to the control/summarizer rather than overwriting the retained historical outputs. The approved profiler used MFA-environment Python with `-B -m cProfile -o <profile> <mfa-script.py> align_one ...` under the existing lock; exact arguments are in diagnostic.json. Do not mix its times with unprofiled runs.

Phase 6 executed Git status/log/diff/index/untracked/ancestor/whitespace checks, read the retained artifacts and installed source, recomputed SHA-256 comparisons, queried package metadata/configuration without exposing full PATH/credentials, and read `/site-health`. No new inference/test execution is implied by that audit.

| Evidence | Purpose |
| --- | --- |
| docs/DAY_4_MFA_INVESTIGATION.md | Lifecycle/profile/source and approved implementation/fallback |
| docs/DAY_4_PHASE_4_VERIFICATION.md | Every Phase 4 individual row: startup observation, ASR/content, lock, subprocess, phonemes, totals and extra existing timers |
| docs/DAY_4_DEMO_RUNBOOK.md | Presenter/recovery/fallback procedure; initial blocked status superseded in this handoff |
| runs/phase3-baseline-20261018T185807Z.json | All nine Phase 1 calls, including standby/timeout |
| runs/day4-mfa-profile-20261018T192328Z/diagnostic.json and mfa.pstats | One approved diagnostic profile, not benchmark |
| runs/day4-dictionary-cache-20261018T192902Z/measurements.json | Seven real alignment-only experiment calls |
| runs/day4-phase4-20261018T194539Z/measurements.json | Thirty planned service calls, source/settings/harness hashes, model-cache observations and complete results |
| Same folder: numeric-control.json, verification.json, tables.md | Extra control, every comparison/difference and individual tables |
| runs/day4-phase4-mfa-tests.log and day4-phase4-regressions.log | Observed 14-test and 165-test outputs |
| runs/day4-phase3-verification.log | Earlier full-suite rerun |
| runs/day4-demo-readiness.json | Static runtime-subset presence and disabled cache; not live inference proof |

User screenshots in the conversation supply the cancelled-transcription/inconclusive display, History card and successful preset-style saved result. They are not timing logs or a full identity/network audit; no such measurements were fabricated from them.

## Final recommendation

**Keep the optimization, opt-in, with the stated installation/fallback limits.** The tested gain for real alignment of different fixture recordings is substantial, and no alignment or sound-decision regression was observed. Tiny neural-score variation and incomplete human/near-threshold coverage remain explicit risks.

**Demo status: ready with caveats for a clearly labeled preset/previous-example walkthrough; not yet signed off for the intended reliable, below-20-second live free-speech demo.** Finish confirmation/ASR sequencing and History-discovery review with Lucas, authorize configuration activation separately if desired, then time the actual browser path with a new consented recording, a warm repeat, a different recording and a safe retry. Do not promise the experimental warm-backend speed as current website performance.
