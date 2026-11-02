# Day 4, Phase 4: Speed and correctness verification

Date: October 18, 2026. Branch: `feature/speed-free-speech`. HEAD: `e7f57d9ce37f95cb6c3cc30a870c8aae284656d7` throughout. Approved optimization: reuse versioned MFA compiled dictionary resources across different recordings. No additional optimization, application-source edits, persistent configuration edits, service restarts, staging, commits or pushes occurred in this phase.

## Decision

**Retain the opt-in dictionary-cache implementation.** In the planned warm-worker preset series, median backend latency decreased from **32.128 to 13.119 seconds**, a **19.009-second / 59.2% reduction**. Every measured request still performed real MFA alignment and phoneme inference. Phone/word alignments, decision labels, uncertainty statuses and original recording associations were preserved in the tested cases.

This does **not** establish a reliable below-20-second website demo for every request. All six optimized warm preset requests were below 20 seconds (10.364–15.021 s), but fresh optimized requests took 31.336–46.749 s. The first optimized request had to build the cache and was 0.920 s slower than its baseline. The setting remains absent from persistent configuration, so the normal application is not yet using this cache. Activation or model preloading is not part of this verification.

## Conditions and method

- Windows 11 build 26200, Python 3.13.1, Intel i7-1360P (12 cores / 16 logical processors), about 16 GB RAM. Installed MFA 3.3.7 in its existing Python 3.11 environment. Torch 2.14.0+cpu, Transformers 5.17.0, NumPy 2.2.6, SciPy 1.15.3. Existing CPU/model-thread settings, pinned local Whisper and phoneme models, sample rate, dictionary, acoustic model, scoring thresholds and validation rules were unchanged.
- Existing Balanced power plan. Battery reported 100%; AC power confirmed online. A pre-run CPU sample was 13%. No project Python/MFA process or local application listener was detected before benchmarking. Only one analysis worker/job ran at a time; regression tests ran after the benchmarks. Other operating-system activity and thermal state were not controlled. No Kernel-Power sleep/standby events (42/107/506/507) were found in the benchmark interval.
- Baseline means the implemented code with the opt-in option absent, retaining the previous compilation path. Optimized means the same settings with only an isolated absolute `mfa.dictionary_cache_directory` added in memory. The application configuration was never edited. Model/resource content was not changed or downloaded.
- Primary series: three assessments per clip/path, first in a fresh spawned worker, then twice in that worker. Path order was baseline/optimized for think, optimized/baseline for ship, baseline/optimized for bad_bed. No order randomization; only two warm repetitions per clip/path.
- A new empty dictionary-cache directory was used. Run 4 paid the first build/publication cost. Runs 7 and 16 assessed different recordings with a fresh worker and resources built from think. All subsequent optimized alignments were resource hits. No exact-input assessment-result cache was added or used. Whisper and phoneme model-object caches remained the existing per-worker caches, with misses on first use and hits on subsequent use; inference still ran each request.
- Additional confirmed-text comparison: real independent transcription followed by analysis using the original file bytes and a trusted diagnostic snapshot with explicit confirmed text, attempt/job/learner identities and revision 2. One worker per path processed the three clips serially. These snapshots are diagnostic fixtures, not authenticated persistent sessions. ASR recognition was retained separately and never overwritten by confirmation. Authorization/publication checks were exercised separately by regression tests.
- One extra unoptimized fresh-worker ship control investigated numerical repeatability. It is retained as run 31 and excluded from the preplanned latency summaries because it was a later diagnostic control. Its timing is still reported below.
- Temporary harness observers forwarded the actual inputs/outputs and collected existing MFA/stage timers. The cache toggle existed only inside those child processes. Total is `AnalysisService.run` elapsed wall time, including worker spawn where applicable, processing, result saving/return and observer overhead. Browser upload, HTTP queue, UI rendering, server startup and time spent reviewing the transcript are excluded. All comparisons are backend measurements, not browser acceptance tests.

### Clips

These are existing synthetic engineering fixtures intentionally used for performance tests, not fresh human recordings or pronunciation-accuracy labels. Human acceptance testing remains deferred. No reference-comparison audio was requested.

| Clip | Confirmed/preset text | Duration | WAV bytes | Format |
| --- | --- | ---: | ---: | --- |
| think | I think so | 1.730 s | 55,406 | 16 kHz mono PCM16 |
| ship | The ship is here | 1.905 s | 61,006 | 16 kHz mono PCM16 |
| bad_bed | That is a bad bed | 2.010 s | 64,366 | 16 kHz mono PCM16 |

Original-file hashes, settings/source hashes, complete results, existing timers and model-cache observations are retained in `runs/day4-phase4-20261018T194539Z/measurements.json`. The planned series ran from 19:45:39 to 19:56:29 UTC. Control data is `numeric-control.json` in the same directory. No run was discarded and no retry was performed.

## Summary by worker/resource state

| Condition | Baseline seconds | Optimized seconds | Comparison |
| --- | ---: | ---: | --- |
| Fresh worker, first dictionary build (think; one each) | 45.830 | 46.749 | 0.920 s slower; 2.0% slower in this pair |
| Fresh worker, existing resources (ship; one each) | 46.846 | 32.111 | 14.735 s / 31.5% saved |
| Fresh worker, existing resources (bad_bed; one each) | 44.836 | 31.336 | 13.500 s / 30.1% saved |
| Warm worker, six planned requests per path, median | 32.128 | 13.119 | 19.009 s / 59.2% saved |
| Warm worker, six planned requests per path, range | 29.189–33.819 | 10.364–15.021 | All values retained |
| Warm worker, mean / sample standard deviation | 31.879 / 2.096 | 12.746 / 1.959 | Descriptive only; small sample |

Warm preset MFA-subprocess median decreased from 29.762 to 10.259 s. Measured lock waits were milliseconds, not the dominant delay. Cache verification/copy/publication overhead is included in the MFA-operation and outer totals, not its subprocess timer. There is no separate cache-preparation timer, so no precise standalone preparation cost is claimed.

No model preparation was moved outside the user request. First ASR stages still include model loading plus inference (12.777–16.408 s in the fresh preset calls); warm ASR/check stages were 0.761–1.417 s. Existing timers cannot separate model loading from inference within those stages. Worker-ready measurements in the individual table include diagnostic imports/spawn/IPC and are already included in total; they are not production server-readiness timings.

### Confirmed-text flow: separate operations

| Clip | Baseline ASR + analysis | Optimized ASR + analysis | Combined saved | Analysis-only saving |
| --- | --- | --- | --- | --- |
| think | 11.251 + 20.684 = 31.934 s | 12.371 + 10.716 = 23.087 s | 8.847 s / 27.7% | 9.968 s / 48.2% |
| ship | 0.710 + 25.365 = 26.075 s | 0.821 + 9.816 = 10.638 s | 15.437 s / 59.2% | 15.549 s / 61.3% |
| bad_bed | 0.993 + 26.600 = 27.593 s | 0.666 + 9.098 = 9.764 s | 17.829 s / 64.6% | 17.502 s / 65.8% |

The think transcription starts a fresh worker; the following analyses run in that same worker after transcription. For each path, ship and bad_bed then use the reused worker. Only one pair per clip in this supplementary series; do not treat it as a repeated-trial distribution. Confirmation time is excluded. Preset and confirmed paths assess different target sets, so their totals are not pooled into a single speed comparison.

## Correctness evidence

- **25 real MFA alignments completed**, comprising 18 preset, six confirmed-text and one control alignment, in distinct request directories. Every before/after same-clip alignment matched exactly for phone/word labels, sequence, boundaries, prepared-audio hash, duration, rate and supplied transcript. Cache entries held only four dictionary files plus an integrity manifest (about 110 MB of resource files), not WAVs, transcripts, alignments or pronunciation findings.
- All 19 preset/control calls recognized matching text, completed phoneme sequence evidence, produced feedback and saved results. They remained `partial` because experimental local evidence was uncertain, not because a required stage was skipped. For think, seven speech segments stayed uncertain; ship, ten; bad_bed, eleven uncertain and one scored. Silence remained skipped. Target decision labels and feedback were unchanged across paths.
- Six independent transcriptions returned `completed`, with equal recognition/provenance for each clip across paths. All six confirmed-text analyses returned `completed`; same-clip sound-result records and limitations matched. Eligible targets were experimental `supported` findings in these fixtures, not validated correctness labels.
- All confirmed analyses retained the intended original source hash, learner asset ID, attempt/job ID, revision 2 and confirmed text. The normalized confirmed text reached MFA, and prepared-audio identity matched across alignment and scoring. Their MFA working directories were absent after return, demonstrating context cleanup. Preset audit outputs were intentionally retained.
- **Not bitwise-identical neural scores for ship:** original baseline vs optimized raw-score/sequence values differed by at most `0.000048100948333740234`; alignment, categorical statuses, alternatives selected and feedback did not change. A new unoptimized fresh-worker control reproduced the optimized phoneme/target-assessment outputs exactly while differing from the original unoptimized run. This establishes that the observed variation is not specific to the dictionary-cache option. Lower-level numerical/backend cause was not isolated. No thresholds, rounding or model settings were changed to hide it. Full differences are in `verification.json`.
- Real-model performance cases did not include unsupported dictionary words, deliberate substitutions, silence or ambiguous human speech. Conservative handling, generated-role rejection, input revisions and stale publication are supported here by unit/integration regressions, not by new human accuracy evidence or a real authenticated model job. These limitations remain explicit.

### Additional numeric-repeatability control (run 31)

Unoptimized ship, fresh worker: **39.279 s total**, MFA subprocess **24.621 s**, MFA operation **24.631 s**, lock **0.953 ms**. Full stage measurements are in `numeric-control.json` and the individual timing tables below. It completed successfully with unchanged sound decisions and alignment. Its faster timing than the earlier baseline also demonstrates environmental/time-order variability; it was not substituted for the planned baseline.

## Regression and failure verification

Commands actually executed, after model benchmarking finished:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_mfa*.py' -v
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py' -v
git diff --check
```

- Focused MFA tests: **14 passed**, zero failures, 0.259 s. These use actual temporary files for cache artifacts and controlled subprocess/clock doubles for the MFA hook. Covers resource identity/invalidation, independent copies, malformed/corrupt manifests, incomplete publication, copy failure, unsupported installation bypass, lock/timer boundaries, publication failure and timeout nonpublication. No real MFA inference is claimed for these 14 tests.
- Full regressions: **165 tests run; 164 passed, one skipped, zero failures; 27.615 s**. The skip is the existing Windows symlink-creation limitation. Logs: `runs/day4-phase4-mfa-tests.log` and `runs/day4-phase4-regressions.log`. Existing Transformers/Starlette/httpx/resource/deprecation warnings remain; they are not new failures.
- Relevant groups within that full suite: transcription 11, transcript preparation 12, confirmed analysis 13, pipeline 22, reference-free behavior 5, assessment 11, evidence quality 8, practice sessions 10 and HTTP account integration 6. These include real audio/text preparation and real temporary SQLite/HTTP storage checks with controlled speech/generation engines. They cover limits, unsupported words/sounds, conservative uncertain results, original-vs-generated roles, ownership, revision updates and stale-result rejection. They do not establish real-model pronunciation accuracy.
- Release checks: 11 tests, ten passed and the symlink case skipped. Includes real owned subprocess timeout/cleanup followed by recovery, real cross-process file-lock exclusion/release after a crash, and controlled worker timeout/restart/concurrent-job rejection. No speculative concurrency or timeout changes were introduced.
- Existing playback rendering wrapper passed its ten JavaScript scenarios; this remains a rendering test, not a new authenticated browser/audio-playback test.
- `git diff --check` passed. Application/settings/protected Day 3 SHA-256 hashes matched before and after benchmarking and again after regressions. The Day 3 playback fix remains untouched. No project Python/MFA process remained after verification; no service was started.

## Limits and recommendation

Retain the implementation as **opt-in and version-limited to the inspected Windows MFA 3.3.7 installation**. The measured benefit applies to new audio that can reuse unchanged dictionary resources, while each request still performs its own alignment and model inference. It is resource reuse, not cached pronunciation results or omitted validation. Corrupt/missing resources can use the original compilation path; existing timeout/error behavior remains. Such fallback requests may be slow, so this is not a universal latency guarantee.

Keep the first-build regression and the 31–47 s fresh-worker costs visible in demo planning. No prewarming cost has been moved out of the measurements, and the website target is not fully met. Human-speech correctness, maximum-length recordings, multiple concurrent users, browser end-to-end latency and near-threshold decisions remain unverified by this small synthetic performance series. The tiny neural-score variation exists without the optimization as well; it remains relevant to future threshold validation.

The next decision is whether to authorize local activation and a browser-level demo rehearsal against the same safeguards. This phase has not activated the setting, implemented a preload mechanism or performed any further optimization. A correctness failure on additional inputs would require investigation and disabling the opt-in path until resolved.

## Reproduction and artifacts

Benchmark harnesses are isolated ignored artifacts, not application modules:

```powershell
.\.venv\Scripts\python.exe -B runs/day4_phase4_verify.py
.\.venv\Scripts\python.exe -B runs/day4_phase4_control.py runs/day4-phase4-20261018T194539Z
.\.venv\Scripts\python.exe -B runs/day4_phase4_summarize.py runs/day4-phase4-20261018T194539Z
```

The first command creates a new timestamped directory and empty resource-cache namespace. On reproduction, pass that newly printed directory to the control/summarizer instead of the historical path shown above. The retained JSON records harness/source hashes, model package versions, every call, all existing stage measurements, observers and source-hash parity. Summarizer verification compares like-for-like outputs; no assertion tolerance was used to conceal categorical differences. Numerical differences are listed explicitly.

Only this report and ignored benchmark/log/result artifacts were added in Phase 4. The prior optimization and unrelated Day 3 changes remain uncommitted. Index remains empty; no merges, history changes or pushes.

## Individual run tables

The following tables retain every planned run plus the later baseline control. Empty cells mean a measurement is unavailable or not applicable, not zero elapsed time. All elapsed durations use monotonic clocks or existing monotonic stage timers.


## Preset assessments

ASR is the existing content-check stage (transcription plus comparison). Boot is time to the diagnostic worker-ready notification and is already included in total. Lock is in milliseconds; all other durations are seconds.

| Run | Clip | Path | Worker | Resource cache | Boot | ASR/check | MFA lock ms | MFA subprocess | Phonemes | Total |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | think | baseline | fresh | disabled | 1.155 | 12.777 | 0.516 | 28.512 | 3.323 | 45.830 |
| 2 | think | baseline | warm | disabled |  | 0.980 | 0.855 | 31.867 | 0.846 | 33.733 |
| 3 | think | baseline | warm | disabled |  | 1.417 | 0.679 | 31.266 | 0.959 | 33.685 |
| 4 | think | optimized | fresh | miss | 1.535 | 13.130 | 1.843 | 29.064 | 2.312 | 46.749 |
| 5 | think | optimized | warm | hit |  | 1.169 | 0.604 | 12.372 | 0.846 | 15.021 |
| 6 | think | optimized | warm | hit |  | 1.238 | 0.617 | 11.630 | 0.853 | 14.406 |
| 7 | ship | optimized | fresh | hit | 1.803 | 15.530 | 0.658 | 11.393 | 2.681 | 32.111 |
| 8 | ship | optimized | warm | hit |  | 1.297 | 0.552 | 10.432 | 0.905 | 13.267 |
| 9 | ship | optimized | warm | hit |  | 1.333 | 0.555 | 10.085 | 0.931 | 12.971 |
| 10 | ship | baseline | fresh | disabled | 1.537 | 14.545 | 1.073 | 29.083 | 1.606 | 46.846 |
| 11 | ship | baseline | warm | disabled |  | 1.294 | 0.525 | 27.152 | 0.710 | 29.189 |
| 12 | ship | baseline | warm | disabled |  | 1.319 | 0.533 | 28.258 | 0.951 | 30.570 |
| 13 | bad_bed | baseline | fresh | disabled | 1.725 | 14.714 | 1.144 | 26.443 | 1.878 | 44.836 |
| 14 | bad_bed | baseline | warm | disabled |  | 1.318 | 0.310 | 31.501 | 0.953 | 33.819 |
| 15 | bad_bed | baseline | warm | disabled |  | 1.302 | 0.927 | 27.965 | 0.955 | 30.279 |
| 16 | bad_bed | optimized | fresh | hit | 1.571 | 16.408 | 0.571 | 10.991 | 1.664 | 31.336 |
| 17 | bad_bed | optimized | warm | hit |  | 0.856 | 0.905 | 8.515 | 0.447 | 10.450 |
| 18 | bad_bed | optimized | warm | hit |  | 0.761 | 0.693 | 8.567 | 0.471 | 10.364 |
| 31 | ship | baseline | fresh | disabled | 1.759 | 11.182 | 0.953 | 24.621 | 1.569 | 39.279 |

## Additional existing preset timers

| Run | Input preparation | DSP | MFA wrapper preparation | MFA whole operation | Output handling | Total before save |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.001 | 0.045 | 0.005 | 28.521 | 0.003 | 44.671 |
| 2 | 0.002 | 0.019 | 0.005 | 31.876 | 0.002 | 33.729 |
| 3 | 0.002 | 0.022 | 0.005 | 31.274 | 0.001 | 33.680 |
| 4 | 0.001 | 0.047 | 0.007 | 29.715 | 0.003 | 45.209 |
| 5 | 0.002 | 0.024 | 0.005 | 12.967 | 0.003 | 15.013 |
| 6 | 0.002 | 0.024 | 0.006 | 12.276 | 0.003 | 14.400 |
| 7 | 0.002 | 0.050 | 0.004 | 12.034 | 0.003 | 30.302 |
| 8 | 0.002 | 0.029 | 0.004 | 11.021 | 0.004 | 13.261 |
| 9 | 0.003 | 0.022 | 0.005 | 10.669 | 0.002 | 12.965 |
| 10 | 0.001 | 0.056 | 0.005 | 29.093 | 0.002 | 45.304 |
| 11 | 0.001 | 0.017 | 0.004 | 27.159 | 0.002 | 29.186 |
| 12 | 0.001 | 0.019 | 0.005 | 28.269 | 0.004 | 30.565 |
| 13 | 0.001 | 0.052 | 0.006 | 26.455 | 0.003 | 43.105 |
| 14 | 0.002 | 0.023 | 0.005 | 31.510 | 0.003 | 33.812 |
| 15 | 0.001 | 0.034 | 0.007 | 27.978 | 0.003 | 30.275 |
| 16 | 0.001 | 0.065 | 0.005 | 11.610 | 0.003 | 29.757 |
| 17 | 0.001 | 0.025 | 0.005 | 9.112 | 0.002 | 10.445 |
| 18 | 0.001 | 0.017 | 0.004 | 9.106 | 0.002 | 10.359 |
| 31 | 0.001 | 0.127 | 0.005 | 24.631 | 0.003 | 37.516 |

## Independent transcription and confirmed-text analysis

ASR and analysis are separate service calls. Their sum excludes human confirmation time. Analysis reuses actual transcription provenance; it does not recognize the audio again.

| Run | Clip | Path | Operation | Worker | Resource cache | Boot | Lock ms | MFA subprocess | Phonemes | Total |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 19 | think | optimized | transcription | fresh | n/a | 1.478 |  |  |  | 12.371 |
| 20 | think | optimized | confirmed_analysis | warm_after_transcription | hit |  | 0.367 | 8.585 | 1.323 | 10.716 |
| 21 | ship | optimized | transcription | warm | n/a |  |  |  |  | 0.821 |
| 22 | ship | optimized | confirmed_analysis | warm_after_transcription | hit |  | 0.254 | 8.643 | 0.451 | 9.816 |
| 23 | bad_bed | optimized | transcription | warm | n/a |  |  |  |  | 0.666 |
| 24 | bad_bed | optimized | confirmed_analysis | warm_after_transcription | hit |  | 0.278 | 7.943 | 0.442 | 9.098 |
| 25 | think | baseline | transcription | fresh | n/a | 1.431 |  |  |  | 11.251 |
| 26 | think | baseline | confirmed_analysis | warm_after_transcription | disabled |  | 0.321 | 19.595 | 0.894 | 20.684 |
| 27 | ship | baseline | transcription | warm | n/a |  |  |  |  | 0.710 |
| 28 | ship | baseline | confirmed_analysis | warm_after_transcription | disabled |  | 0.320 | 24.394 | 0.783 | 25.365 |
| 29 | bad_bed | baseline | transcription | warm | n/a |  |  |  |  | 0.993 |
| 30 | bad_bed | baseline | confirmed_analysis | warm_after_transcription | disabled |  | 1.144 | 25.251 | 1.104 | 26.600 |

## Like-for-like preset latency comparisons

| Clip | Worker | Baseline | Optimized | Seconds saved | Percent saved |
| --- | --- | ---: | ---: | ---: | ---: |
| think | fresh | 45.830 | 46.749 | -0.920 | -2.007 |
| think | warm | 33.709 | 14.713 | 18.996 | 56.352 |
| ship | fresh | 46.846 | 32.111 | 14.735 | 31.454 |
| ship | warm | 29.880 | 13.119 | 16.761 | 56.095 |
| bad_bed | fresh | 44.836 | 31.336 | 13.500 | 30.110 |
| bad_bed | warm | 32.049 | 10.407 | 21.642 | 67.529 |

Fresh think includes an optimized cache miss/build. Other optimized rows are resource hits, not cached assessment results. Warm rows above use the median of two retained runs per clip/path. Control run 31 is retained separately and excluded from the planned timing summaries.

### Other existing confirmed-analysis timers

All durations below are milliseconds except the outer operation total in the preceding table.

| Run | Audio preparation | Analysis lock queue | Analysis processing | Alignment stage |
| --- | ---: | ---: | ---: | ---: |
| 20 | 16.742 | 0.374 | 10634.533 | 9202.124 |
| 22 | 16.832 | 0.416 | 9705.732 | 9143.634 |
| 24 | 14.043 | 0.471 | 9020.495 | 8475.288 |
| 26 | 16.891 | 0.411 | 20603.431 | 19600.945 |
| 28 | 13.071 | 0.552 | 25288.078 | 24401.354 |
| 30 | 13.770 | 0.321 | 26494.385 | 25257.930 |
