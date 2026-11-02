# Speed completion report, October 27, 2026

## Result

**Retain the approved opt-in graph-resource cache for this tested local build.** In the actual website, median prepared analysis decreased from **12.03 to 8.19 seconds**, a **31.9% reduction**. Median browser wait decreased from **12.56 to 9.40 seconds**. All six planned paired optimized runs preserved alignment fingerprints, sound outcomes, limitations, recording identity, confirmed text and revision.

A genuinely new microphone recording subsequently completed in **7.86 seconds server-side** and **9.35 seconds from Analyze to visible completion**, with both graphs reused and real alignment/scoring performed. Its separate transcription job took **4.01 seconds**. The original learner audio hash was verified; the waveform differs from earlier supplied clips.

**This establishes typical sub-ten-second prepared analysis in the tested cases, not a maximum.** Five of six optimized runs were below ten seconds. One took **11.48 seconds server-side / 12.66 seconds through the browser** and remains in the table. The fresh clip's two server jobs total about **11.88 seconds**, excluding queue/upload/polling and human transcript review. A combined ten-second workflow and a cold-start ten-second result have not been established.

## What changed

1. Reused the owned MFA interpreter instead of importing its libraries in a new process on every alignment. The earlier isolated comparison measured warm preset medians of 10.69 versus 4.77 seconds and confirmed-text medians of 9.71 versus 5.18 seconds. These are engineering measurements, not website timings.
2. Made idle retention explicit and bounded: the local worker now stays available for ten idle minutes instead of two. Previous live tests showed the interpreter had exited between recordings. The setting remains opt-in and the previous 120-second default is preserved when it is absent.
3. Profiled one initialized request in the actual website, with the user's separate approval. It spent **3.79 profiled seconds loading L.fst and L_align.fst**. Profiled durations were diagnostic only and excluded from latency comparisons. The installed MFA files were not edited.
4. Added an opt-in, worker-local cache of those two compiled dictionary graphs. Each request receives an independent graph copy. Content hashes invalidate changed resources; hashing/copying issues use the original loader; an original loader error still fails normally. Only two graph masters are retained. No learner recording, transcript, alignment or assessment result is cached.
5. Added optional privacy-preserving local diagnostics for the existing MFA timers, reuse counters and alignment fingerprints. **Diagnostics and profiling are now disabled.**

The current ignored local setting is:

```json
"mfa_execution": {"reuse_process": true, "idle_sec": 600, "reuse_lexicon_graphs": true}
```

This does not replace the existing model/MFA path settings. The optimization is limited to the inspected Windows MFA 3.3.7 installation. Other runtimes retain the normal CLI fallback. To disable only graph reuse, set `reuse_lexicon_graphs` to false; the next request uses the original loaders and clears the graph masters. Disabling `reuse_process` restores the ordinary CLI execution path.

## Same-app verification method

- The user manually provided three fresh human clips used for the paired comparison: I think so, The ship is here, and That is a bad bed. Their durations were 2.28, 2.04 and 3.48 seconds, 48 kHz mono PCM WAV, within the existing five-second and 10 MB limits.
- Six predeclared cache-off runs and six cache-hit runs: two per clip. The source recordings, confirmed transcripts, revisions, models, arguments, validation, serial queue, deadlines and scoring settings were unchanged. Both groups ran in the **same initialized MFA process, PID 40700**, with compiled dictionary resource hits. No service restart occurred between the groups.
- Baseline order: think, ship, bad-bed, bad-bed, ship, think. Optimized order used the same sequence. A separate population request built the two in-memory masters before the cache-hit group. All preparation, extra controls, slow runs and profiler work remain in the raw evidence and are labeled separately.
- Browser times use a monotonic clock around the actual button click and visible completion, including HTTP, UI polling and automation overhead. Server times come from existing saved timers. ASR was reused for these paired reassessments, so these results are **analysis-only**, not combined new-recording timings.
- The user confirmed the final earlier ship upload reused an old WAV, so it was not counted as fresh. The later microphone clip is a distinct waveform. No synthetic clip substituted for these human cases.
- Conditions were sequential and not randomized. Temperature/background activity was not fully controlled. The small sample cannot support a service-level maximum or a reliable population 95th percentile.

## Individual paired runs

Times are seconds. Dictionary resource cache hit and initialized process reuse were observed for every listed row. Graph hits are zero/off in controls and two per optimized request. No listed request failed or retried.

| Mode | Clip | Round | Server analysis | Browser wait | MFA lock | MFA execution | Alignment | Phoneme analysis |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| off | think | 1 | 11.957 | 12.570 | 0.0010 | 8.639 | 9.629 | 1.765 |
| off | ship | 1 | 12.098 | 12.541 | 0.0009 | 8.706 | 9.824 | 1.690 |
| off | bad_bed | 1 | 12.748 | 13.965 | 0.0007 | 8.568 | 9.639 | 2.584 |
| off | bad_bed | 2 | 12.522 | 14.029 | 0.0005 | 8.164 | 9.209 | 2.760 |
| off | ship | 2 | 10.662 | 10.838 | 0.0006 | 7.514 | 8.515 | 1.656 |
| off | think | 2 | 11.842 | 12.535 | 0.0003 | 8.499 | 9.590 | 1.728 |
| on | think | 1 | 8.018 | 9.377 | 0.0007 | 4.804 | 5.850 | 1.665 |
| on | ship | 1 | 8.806 | 9.417 | 0.0008 | 5.440 | 6.465 | 1.814 |
| on | bad_bed | 1 | 11.485 | 12.665 | 0.0008 | 5.736 | 6.879 | 3.798 |
| on | bad_bed | 2 | 7.793 | 9.359 | 0.0014 | 4.226 | 5.239 | 2.089 |
| on | ship | 2 | 8.359 | 9.452 | 0.0012 | 5.142 | 6.248 | 1.383 |
| on | think | 2 | 8.008 | 9.277 | 0.0004 | 4.683 | 5.715 | 1.746 |

### Preparation, controls and outliers

- First cache-off requests after app restart took 55.49 and 23.79 seconds server-side. Another earlier cold preparation reached 57.57 seconds. These are preparation observations, not speed successes; a full final-config cold-start series remains unverified.
- Initial graph-cache population: 11.69 seconds server-side / 12.50 seconds browser. Re-population after disabling the cache for controls: 10.18 / 10.87 seconds. Both performed original graph loading and are excluded from cache-hit medians, but retained here.
- The 11.48-second optimized bad-bed run is the slowest planned optimized run. Its alignment and outcomes matched the baseline. The next bad-bed repetition took 7.79 seconds; the slow run was not replaced.
- Two extra cache-off think controls took 10.62 and 11.99 seconds server-side. They were diagnostic controls after the planned groups, excluded from the balanced medians, and remain in the evidence.
- One population request and one later cache-off control had different alignment fingerprints from the main think baseline. Their sound outcomes were unchanged. Thus variation occurs with graph reuse disabled as well. The installed acoustic-model metadata declares dither=1, and its original feature settings were preserved. Dithering is a plausible contributor; the exact cause and size of the boundary variation were not isolated because those diagnostics retained hashes, not full boundary arrays. Do not claim universal exact alignment equivalence.

## Correctness and safeguards

All six main cache-hit comparisons had exact fingerprint agreement with their paired baseline. Their projected sound results (word/phone occurrences, expected/alternative phones, outcome and reason), limitations, input revision, learner asset and confirmed transcript also matched. The bad-bed clip was recognized as “That is a bad bet” and confirmed as “That is a bad bed”; it remained CONTENT_UNVERIFIED and inconclusive throughout. Unsupported/uncertain evidence was not promoted to a grade.

The fresh final microphone clip was recognized and confirmed as “I think so.” Its TH practice and IH supported outcomes are experimental model findings, not a human-validated error/accuracy label. Its timing is a new-recording check, not a replay of an old assessment. Actual browser navigation to private History and back verified identical attempt, learner asset, confirmed text, revision and saved timings. The final Practice result was left open. Screenshot: `runs/speed-optimized-fresh-mic-20261027.jpg`.

Existing preset entry points, recording/text limits, original-audio role/hash validation, authentication/ownership, attempt/job identities, stale-revision publication checks, generated-audio separation, cross-process locking, 120-second MFA timeout, 180-second service deadline and worker failure recovery were not weakened. Every optimized request still performed new alignment and phoneme inference. Normal CLI fallback and graph-loader fallback remain available.

## Tests actually run

| Check | Outcome and category |
| --- | --- |
| `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_fst_resource_cache.py' -v` | 9 passed; controlled loader/graph tests for independent copies, content invalidation, bounds, failures and restoration |
| `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_persistent_mfa.py' -v` | 15 passed; real private subprocess protocol with a controlled CLI, including timeout/crash cleanup, idle policy and optional profiler behavior |
| `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_mfa_timings.py' -v` | 10 passed; controlled timing boundaries and diagnostic privacy/failure tests |
| Installed MFA Python, real Pynini and LexiconCompiler with tiny FST files | Passed; two cache hits/two misses, independent native copies, original loaders restored. This is an API test, not acoustic inference |

| `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py' -v` with final local flags | **195 tests run, 194 passed, one skipped**, 47.753 seconds; zero failures |
| Actual website with real speech engines | Six cache-off and six optimized reassessments, a fresh microphone assessment, separately labeled preparation and controls; all completed |
| `git diff --check` | Passed |

The skip is the existing Windows symlink-creation limitation. The full suite includes the production JS renderer wrapper (25 Node scenarios counted as one Python test) and actual temporary HTTP/SQLite tests with controlled speech engines. It does not establish real-model pronunciation accuracy. No live timeout or crash was deliberately induced; recovery tests use controlled subprocesses. Earlier real-model smoke outputs are retained in the detailed handoff.

## Memory and operating limits

The graph cache trades memory for latency. The retained MFA process was observed at about **782 MB working set (746 MiB)** with the cache populated; an earlier unpopulated interpreter was about 270 MB. Those are snapshots across process lifetimes, not a controlled peak-memory attribution. The main model worker was about 2 GiB. Two cached graph masters are bounded, but their native representation and temporary copies can use substantially more memory than the serialized FST files. Retention ends on idle expiry, 32-request retirement, process failure or shutdown.

The machine has 16 GB RAM. Closing Chrome raised free RAM from roughly 1.1 to 3.4 GiB but did not independently establish the speed target. AC power and the existing Balanced plan were observed; no power settings or hardware were changed. Models and installed dependencies were neither upgraded nor downloaded.

Remaining gaps: final-config cold-start series, maximum five-second/twelve-word inputs, multiple simultaneous users and queue delays, broader fresh-human pronunciation validation, and fuller alignment-variation auditing. A ten-second combined machine workflow remains unproven. Do not present cached/prepared resources as a cached learner assessment, or an older result as a newly recorded result.

## Files and preservation

This continuation adds `phoneme_scoring/fst_resource_cache.py` and `tests/test_fst_resource_cache.py`; extends `persistent_mfa.py`, `mfa_worker.py` and the dispatch/diagnostic portions of `align_audio.py`; and extends the related lifecycle/timer tests. The earlier worker, dictionary-file cache, playback/Practice-result UI, revision/storage and reliability changes remain in place. Shared storage, UI, models and scoring files were not changed by the graph-cache experiment.

The ignored local config enables the tested flags. Raw recordings remain in the existing private storage. Only metadata, timings, alignment hashes, outcomes and local diagnostic artifacts were written into ignored reports. No login credentials or raw voice were added to reports or Git.

Branch remains `feature/speed-free-speech`, HEAD `e7f57d9ce37f95cb6c3cc30a870c8aae284656d7`. Nothing was staged, committed, merged, reset, stashed or pushed. Hash checks confirmed that `web_assets/accounts.js` and `accounts/sessions.py` were unchanged throughout this speed continuation, as were core pipeline, confirmed-analysis, transcription and phoneme-model code. Other local model configuration was unchanged. The app health endpoint returned ready. Keep prior UI/playback work, dictionary-file caching, reusable-worker/graph caching, and reports as separate reviewable scopes. Sarrvesh owns the analysis changes; Lucas should review the earlier shared History UI independently. No new API/storage/generation interface change is required from Lucas or Parthiban.

## Handoff and next action

Use SPEED_DEMO_RUNBOOK_2026-10-27.md. Keep the final tested local flags, prepare the full workflow before a demo, show the real progress state, and state that prepared analysis is typically under ten seconds in these tests. Keep the outlier, startup costs and separate transcription cost visible. The speed experiment and report are complete; the strict maximum/whole-workflow performance objective remains open.

Preserved evidence: `runs/graph-cache-live-comparison-20261027.json`, `graph-cache-live-parity-20261027.json`, `graph-cache-final-summary-20261027.json`, `speed-live-20261027.json`, `mfa-live-diagnostics.jsonl`, `mfa-live-profile.pstats`, `mfa-live-profile-summary.txt`, and the earlier raw benchmark directories named in `speed-final-evidence-20261027.json`. The detailed historical appendix is SPEED_HANDOFF_2026-10-27.md.
