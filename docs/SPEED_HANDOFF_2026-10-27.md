# Speed handoff, October 27, 2026

## Final disposition

This document preserves the earlier stages of today's investigation, including the pre-graph-cache website baseline. The final approved graph-resource experiment and retain decision are documented in **SPEED_COMPLETION_REPORT_2026-10-27.md**, which supersedes the earlier readiness and next-action statements below. The current prepared-analysis median is 8.19 seconds; a strict ten-second maximum remains unproven.

## Earlier pre-graph-cache decision and readiness

The reusable MFA interpreter improves the isolated engineering benchmark, but **the live website does not yet reliably meet a ten-second target**. Retain process reuse and the bounded ten-minute idle policy with the limitations below. Do not advertise five-second website processing based on the isolated benchmark.

The latest steady live diagnostic measured 12.077 seconds server-side and 12.651 seconds click-to-observed completion, including 9.072 seconds in MFA execution. The dictionary cache hit, the interpreter was reused, and lock waiting was 0.0014 seconds. Remaining delay is inside MFA execution, not explained by the HTTP queue or lock waiting. The cause of the difference from isolated execution remains unresolved.

The app is suitable for an honest experimental demonstration with preparation and visible processing. It is not verified against a maximum ten-second service promise, maximum-length recordings, or concurrent-user load. Completed processing is not proof of pronunciation accuracy.

## Git and preservation

Branch `feature/speed-free-speech`, HEAD `e7f57d9ce37f95cb6c3cc30a870c8aae284656d7`. The index remains empty. No staging, commits, merges, pushes, stashes, resets or discarded work.

Existing uncommitted playback, Practice-result display, storage/revision safeguards, dictionary caching and reliability work is retained. This continuation changes only MFA lifetime configuration/dispatch, optional diagnostic output, related tests and reports. UI, authentication, session storage, transcript logic, models, thresholds, alignment arguments and execution deadlines were not changed during this continuation.

## Implementation

- Existing process reuse runs the installed, unmodified MFA 3.3.7 CLI through an owned private-pipe interpreter. Every assessment still gets its own audio, transcript, working directory, alignment and scoring. No assessment-result cache was introduced.
- The new `mfa_execution.idle_sec` option is restricted to integer values 30–600, defaulting to the previous 120 seconds. The tested local configuration explicitly uses 600. Changing the lifetime policy replaces the previous owned client. Natural idle exit, retirement after 32 jobs, timeout cleanup, crash recovery and original CLI fallback remain.
- Live tests showed MFA had exited before the second and third fresh recordings under the two-minute policy. The longer policy demonstrably retained it beyond two minutes. It does not eliminate first-use preparation and does not guarantee ten-second processing.
- Optional approved diagnostics copy existing MFA timers, dictionary-cache status and interpreter-reuse metadata to `runs/mfa-live-diagnostics.jsonl`. They log no waveform, transcript, credential, environment value or internal command. Logging failures cannot fail an assessment. **Capture is now disabled** in local settings; it defaults off.
- Normal MFA timeout remains 120 seconds; service deadline remains 180 seconds. Existing locking and stale-publication checks are unchanged.

## Earlier comparable control and optimized benchmark

These series used the same three supplied WAVs and six calls per path, with serial execution, one fresh worker followed by five reused-worker calls. Calls 2 and 3 introduce the other two waveforms to the warm worker; calls 4–6 repeat earlier inputs. These are engineering measurements, not new browser acceptance tests. Resource-cache hits reuse compiled dictionaries, not saved pronunciation results.

| Flow | First control s | First reuse s | Warm control median s | Warm reuse median s | Warm reduction |
| --- | ---: | ---: | ---: | ---: | ---: |
| preset | 27.270 | 25.588 | 10.689 | 4.768 | 55.4% |
| confirmed | 22.357 | 24.056 | 9.713 | 5.175 | 46.7% |

The first confirmed-text reuse run was slower than its control (24.056 versus 22.357 seconds); it is retained. No run was discarded. Both startup/model loading and alignment are included in first service calls, not timed as a separate complete app-start metric.

The post-retention diagnostic rerun completed all six cases. First call: 23.131 seconds; five warm calls: 4.517–5.221 seconds, median 4.654. This reproduced fast isolated processing while the site itself remained slower. The normal app and its idle worker stayed running; the diagnostic worker used additional memory. This is not a controlled browser comparison or evidence that closing Chrome solved the gap.

Phone sequences, word boundaries and categorical target decisions matched exactly in all six earlier preset control/reuse pairs. All six earlier confirmed-text optimized calls retained attempt/job identity, revision, original-audio identity/hash and confirmed text. These checks verify the tested engineering cases, not universal acoustic equivalence or human-label accuracy.

### Individual engineering runs

All durations are seconds. `ASR` is the preset content-check timer for preset runs and the independent transcription outer duration for confirmed-text runs; these scopes differ and are not directly interchangeable. Total confirmed flow includes transcription plus analysis, excluding human review. MFA execution includes interpreter startup when applicable. Missing values are not estimated.

| Series | Run | Clip | Worker | ASR | Lock | MFA exec | MFA total | Phoneme | Total |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cli-preset | 1 | think | fresh | 12.225 | 0.000 | 10.321 | 10.867 | 1.001 | 27.270 |
| cli-preset | 2 | ship | reused | 0.808 | 0.000 | 9.138 | 9.693 | 0.600 | 11.133 |
| cli-preset | 3 | bad_bed | reused | 0.875 | 0.000 | 9.166 | 9.737 | 0.569 | 11.224 |
| cli-preset | 4 | bad_bed | reused | 0.810 | 0.000 | 8.541 | 9.145 | 0.590 | 10.580 |
| cli-preset | 5 | ship | reused | 0.713 | 0.000 | 8.851 | 9.397 | 0.536 | 10.689 |
| cli-preset | 6 | think | reused | 0.803 | 0.001 | 8.207 | 8.828 | 0.551 | 10.221 |
| persistent-preset | 1 | think | fresh | 11.201 | 0.001 | 9.588 | 10.167 | 0.973 | 25.588 |
| persistent-preset | 2 | ship | reused | 0.601 | 0.000 | 3.107 | 3.732 | 0.464 | 4.825 |
| persistent-preset | 3 | bad_bed | reused | 0.670 | 0.000 | 2.831 | 3.355 | 0.552 | 4.608 |
| persistent-preset | 4 | bad_bed | reused | 0.617 | 0.000 | 3.029 | 3.594 | 0.537 | 4.778 |
| persistent-preset | 5 | ship | reused | 0.690 | 0.000 | 2.906 | 3.434 | 0.513 | 4.666 |
| persistent-preset | 6 | think | reused | 0.620 | 0.000 | 3.058 | 3.546 | 0.565 | 4.768 |
| cli-confirmed | 1 | think | fresh | 9.446 | 0.000 | 9.431 | 9.981 | 1.149 | 22.357 |
| cli-confirmed | 2 | ship | reused | 0.606 | 0.000 | 7.474 | 7.988 | 0.487 | 9.258 |
| cli-confirmed | 3 | bad_bed | reused | 0.664 | 0.000 | 7.743 | 8.284 | 0.611 | 9.760 |
| cli-confirmed | 4 | bad_bed | reused | 0.659 | 0.000 | 7.832 | 8.356 | 0.524 | 9.713 |
| cli-confirmed | 5 | ship | reused | 0.677 | 0.000 | 7.680 | 8.173 | 0.534 | 9.581 |
| cli-confirmed | 6 | think | reused | 0.740 | 0.000 | 7.921 | 8.428 | 0.570 | 9.920 |
| persistent-confirmed | 1 | think | fresh | 12.769 | 0.000 | 8.256 | 8.743 | 1.143 | 24.056 |
| persistent-confirmed | 2 | ship | reused | 0.659 | 0.000 | 3.236 | 3.741 | 0.579 | 5.175 |
| persistent-confirmed | 3 | bad_bed | reused | 0.735 | 0.000 | 3.311 | 3.869 | 0.568 | 5.359 |
| persistent-confirmed | 4 | bad_bed | reused | 0.673 | 0.000 | 3.424 | 3.981 | 0.543 | 5.382 |
| persistent-confirmed | 5 | ship | reused | 0.709 | 0.000 | 2.917 | 3.459 | 0.549 | 4.897 |
| persistent-confirmed | 6 | think | reused | 0.622 | 0.000 | 3.079 | 3.591 | 0.655 | 5.083 |
| post-retention-confirmed | 1 | think | fresh | 11.661 | 0.000 | 8.480 | 8.973 | 1.126 | 23.131 |
| post-retention-confirmed | 2 | ship | reused | 0.631 | 0.000 | 3.259 | 3.743 | 0.471 | 5.018 |
| post-retention-confirmed | 3 | bad_bed | reused | 0.690 | 0.000 | 3.190 | 3.776 | 0.551 | 5.221 |
| post-retention-confirmed | 4 | bad_bed | reused | 0.635 | 0.001 | 2.784 | 3.290 | 0.541 | 4.654 |
| post-retention-confirmed | 5 | ship | reused | 0.637 | 0.000 | 2.769 | 3.255 | 0.487 | 4.547 |
| post-retention-confirmed | 6 | think | reused | 0.593 | 0.000 | 2.738 | 3.254 | 0.502 | 4.517 |

All 30 engineering calls completed, with no retries or reported errors and dictionary resource hits. Each series retained source hashes and confirmed the original production attempts were unchanged. First worker calls are fresh interpreters with existing OS/model files; they are not cold-disk tests. Full startup/import/cache observations and result objects remain in each `measurements.json`.

## Live browser and human-recording evidence

The user manually recorded clips 1–4 with consent. Their audio differs from the earlier benchmark WAVs. The final ship upload was byte-identical to the earlier benchmark clip; the user confirmed reusing it. It is a reused upload, not a fifth fresh human recording. All later reassessments and preparation calls are labeled accordingly.

Every completed live analysis retained the selected recording asset, confirmed transcript and revision; results appeared in Practice and were saved through the normal private-session workflow. Original audio roles and hashes were verified from selected attempt records using read-only database access. Raw learner audio was not copied into report artifacts.

ASR and analysis are separate jobs. The following table does not include human transcript-review time. Transcription shown as `reused` was not executed during that reassessment. Browser observations include HTTP/UI polling and automation overhead. The first run, preparation and log-inspection rows contain observation gaps, so their browser values are upper bounds rather than precise completion latencies. Saved server timers are authoritative for those rows. An observer deadline is not an analysis timeout.

| Case | Seconds audio | ASR job s | Analysis server s | Alignment s | Phoneme s | Browser observed s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| fresh-human-1 | 2.280 | 27.908 | 26.712 | 18.090 | 4.933 | 36.131 |
| fresh-human-2 | 2.040 | 2.527 | 18.771 | 16.432 | 1.871 | 20.044 |
| fresh-human-3 | 3.480 | 2.785 | 19.214 | 15.790 | 2.950 | 19.955 |
| preparation-existing-recording-after-restart | 3.480 | reused | 45.860 | 15.978 | 21.238 | 72.647 |
| fresh-human-4-post-retention | 2.160 | 4.250 | 20.551 | 18.183 | 1.898 | 21.413 |
| warm-reassessment-human-4 | 2.160 | reused | 11.418 | 9.127 | 1.843 | 12.415 |
| reused-upload-5-load-reduced | 2.304 | 2.917 | 12.329 | 9.516 | 2.319 | 13.930 |
| warm-reassessment-existing-ship-log-review | 2.304 | reused | 12.149 | 9.498 | 2.144 | 54.235 |
| warm-reassessment-ship-existing-log-capture | 2.304 | reused | 11.762 | 9.244 | 2.020 | 12.499 |
| diagnostic-cold-existing-ship | 2.304 | reused | 50.008 | 16.908 | 24.328 | - |
| diagnostic-warm-existing-ship | 2.304 | reused | 20.167 | 17.466 | 2.210 | 21.636 |
| diagnostic-steady-existing-ship | 2.304 | reused | 12.077 | 9.933 | 1.714 | 12.651 |
| final-normal-reassessment-human-1-diagnostics-off | 2.280 | reused | 12.291 | 9.767 | 2.151 | 13.885 |
| profile-preparation-cold-existing-ship | 2.304 | reused | 57.567 | 19.016 | 29.034 | 66.986 |
| profile-preparation-existing-ship-second | 2.304 | reused | 26.918 | 21.759 | 2.264 | 29.640 |
| profiled-warm-existing-ship-not-a-benchmark | 2.304 | reused | 13.172 | 10.441 | 2.217 | 13.899 |
| graph-experiment-cache-off-preparation-1 | 2.304 | reused | 55.490 | 20.166 | 24.239 | 56.964 |
| graph-experiment-cache-off-preparation-2 | 2.304 | reused | 23.790 | 21.398 | 1.875 | 24.359 |
| graph-off-think-round1 | 2.280 | reused | 11.957 | 9.629 | 1.765 | 12.570 |
| graph-off-ship-round1 | 2.040 | reused | 12.098 | 9.824 | 1.690 | 12.541 |
| graph-off-bad_bed-round1 | 3.480 | reused | 12.748 | 9.639 | 2.584 | 13.965 |
| graph-off-bad_bed-round2 | 3.480 | reused | 12.522 | 9.209 | 2.760 | 14.029 |
| graph-off-ship-round2 | 2.040 | reused | 10.662 | 8.515 | 1.656 | 10.838 |
| graph-off-think-round2 | 2.280 | reused | 11.842 | 9.590 | 1.728 | 12.535 |
| graph-on-preparation-think-round0 | 2.280 | reused | 11.689 | 9.442 | 1.760 | 12.495 |
| graph-on-think-round1 | 2.280 | reused | 8.018 | 5.850 | 1.665 | 9.377 |
| graph-on-ship-round1 | 2.040 | reused | 8.806 | 6.465 | 1.814 | 9.417 |
| graph-on-bad_bed-round1 | 3.480 | reused | 11.485 | 6.879 | 3.798 | 12.665 |
| graph-on-bad_bed-round2 | 3.480 | reused | 7.793 | 5.239 | 2.089 | 9.359 |
| graph-on-ship-round2 | 2.040 | reused | 8.359 | 6.248 | 1.383 | 9.452 |
| graph-on-think-round2 | 2.280 | reused | 8.008 | 5.715 | 1.746 | 9.277 |
| graph-off-control-think-round3 | 2.280 | reused | 10.618 | 8.488 | 1.501 | 10.850 |
| graph-off-control-think-round4 | 2.280 | reused | 11.985 | 9.908 | 1.580 | 12.526 |
| graph-on-preparation-after-control-think-round0 | 2.280 | reused | 10.184 | 7.965 | 1.552 | 10.873 |
| fresh-human-6-graph-cache-enabled | 2.040 | 4.012 | 7.864 | 5.810 | 1.522 | 9.347 |

Fresh clips 1 and 2 preserved recognized/confirmed “I think so” and “The ship is here” respectively. Clip 3 was recognized as “That is a bad bet” and confirmed as “That is a bad bed”; its results correctly remained inconclusive with CONTENT_UNVERIFIED. Clip 4 produced experimental TH practice and IH supported findings. None is a validated human pronunciation grade. Completed analyses and inconclusive findings were kept separate from processing failures.

No live pipeline failures or retries after a deliberately induced failure were tested. Reassessment is not failure recovery. Timeout/crash/recovery safeguards are covered by the controlled lifecycle/regression tests, not a forced live outage.

### Existing MFA timer capture from the site

| Recorded UTC | Cache | Process reused | Lock s | MFA exec s | CLI request s | Startup s | MFA total s |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2026-10-27T15:18:30.727788+00:00 | hit | False | 0.001 | 15.989 | 13.281 | 2.594 | 16.907 |
| 2026-10-27T15:20:36.005661+00:00 | hit | False | 0.003 | 16.527 | 13.391 | 2.609 | 17.456 |
| 2026-10-27T15:22:02.868972+00:00 | hit | True | 0.001 | 9.072 | 9.079 | 0.000 | 9.931 |
| 2026-10-27T15:37:02.525558+00:00 | hit | False | 0.001 | 18.107 | 14.188 | 3.765 | 19.014 |
| 2026-10-27T15:38:13.827275+00:00 | hit | False | 0.000 | 19.256 | 13.969 | 4.594 | 21.756 |
| 2026-10-27T15:38:42.380775+00:00 | hit | True | 0.001 | 9.563 | 9.547 | 0.000 | 10.440 |
| 2026-10-27T15:49:55.266708+00:00 | hit | False | 0.001 | 19.117 | 13.297 | 5.594 | 20.164 |
| 2026-10-27T15:50:57.783426+00:00 | hit | False | 0.000 | 20.451 | 15.328 | 4.610 | 21.396 |
| 2026-10-27T15:51:45.597547+00:00 | hit | True | 0.001 | 8.639 | 8.640 | 0.000 | 9.628 |
| 2026-10-27T15:51:59.085332+00:00 | hit | True | 0.001 | 8.706 | 8.703 | 0.000 | 9.822 |
| 2026-10-27T15:52:21.830059+00:00 | hit | True | 0.001 | 8.568 | 8.563 | 0.000 | 9.638 |
| 2026-10-27T15:52:36.127196+00:00 | hit | True | 0.000 | 8.164 | 8.157 | 0.000 | 9.208 |
| 2026-10-27T15:52:55.912213+00:00 | hit | True | 0.001 | 7.514 | 7.500 | 0.000 | 8.514 |
| 2026-10-27T15:53:08.447439+00:00 | hit | True | 0.000 | 8.499 | 8.500 | 0.000 | 9.587 |
| 2026-10-27T15:53:42.035432+00:00 | hit | True | 0.000 | 8.438 | 8.422 | 0.000 | 9.441 |
| 2026-10-27T15:53:51.475753+00:00 | hit | True | 0.001 | 4.804 | 4.813 | 0.000 | 5.849 |
| 2026-10-27T15:56:57.981195+00:00 | hit | True | 0.001 | 5.440 | 5.438 | 0.000 | 6.454 |
| 2026-10-27T15:57:08.748531+00:00 | hit | True | 0.001 | 5.736 | 5.735 | 0.000 | 6.862 |
| 2026-10-27T15:57:42.460706+00:00 | hit | True | 0.001 | 4.226 | 4.218 | 0.000 | 5.237 |
| 2026-10-27T15:57:53.731352+00:00 | hit | True | 0.001 | 5.142 | 5.141 | 0.000 | 6.247 |
| 2026-10-27T15:58:27.267749+00:00 | hit | True | 0.000 | 4.683 | 4.672 | 0.000 | 5.713 |
| 2026-10-27T15:59:38.692693+00:00 | hit | True | 0.000 | 7.605 | 7.594 | 0.000 | 8.487 |
| 2026-10-27T15:59:51.342353+00:00 | hit | True | 0.000 | 8.930 | 8.922 | 0.000 | 9.906 |
| 2026-10-27T16:01:40.684337+00:00 | hit | True | 0.006 | 7.029 | 7.031 | 0.000 | 7.964 |
| 2026-10-27T16:03:17.642151+00:00 | hit | True | 0.001 | 4.686 | 4.688 | 0.000 | 5.803 |

## Environment and measurement limits

Windows, app Python 3.13, MFA 3.3.7 in its existing Python 3.11 Conda environment, local CPU models, 16 GB RAM. AC power and the existing Balanced plan were observed. No power, dependency, model, thread, concurrency or hardware changes were made. CPU samples between requests were approximately 15–23%; these do not characterize CPU/thermal behavior during inference.

Available memory fell to about 1.1 GiB before the user closed Chrome, then rose to about 3.4 GiB. The website still exceeded ten seconds afterward; memory pressure is a possible contributor, not an established root cause or a demonstrated fix. The MFA process used about 260 MiB and the main model worker about 2 GiB working set in observed samples. Memory use is not a resource guarantee.

Normal private-session output retains aggregate alignment time, not the full internal MFA breakdown. Approved temporary capture supplied three comparable timer records. Attempts to read ephemeral MFA logs externally captured no usable log lines before cleanup; no internal phase split was invented. Exact acoustic-model loading, dictionary initialization and alignment subcosts remain unresolved in the live process.

The latest isolated full-flow warm result is about 4.65 seconds; the live steady analysis alone is about 12 seconds, plus separate transcription when needed. Therefore neither a ten-second browser maximum nor a ten-second combined new-recording workflow has been established.

## Verification and handoff

Focused lifecycle suite: 13 passed. Covers previous process reuse, argument preservation, error/timeout cleanup, malformed replies, runtime gating, lock scope, and new bounded idle-policy validation/identity plus natural idle exit using the real worker protocol with a controlled CLI substitute.

Focused MFA timer/diagnostic suite: 10 passed. Existing clock/lock boundaries retained; diagnostic capture is opt-in, omits private content and cannot fail an otherwise successful alignment on write errors. These are controlled tests, not real-model pronunciation tests.

Final full regression outcome: see `runs/speed-final-regressions-20261027.log` and the final verification section appended after completion. No unexecuted test is claimed here.

The earlier 17-check private HTTP/real-engine smoke remains in `runs/speed-integration-20261027T135729Z/real-smoke.json`. It includes real transcription, analysis, generated-example playback and generated-reupload rejection. Some corrected transcripts deliberately disagreed with the waveform and conservatively abstained; this is not a human accuracy dataset.

## Files and proposed commit boundaries

1. Preserve the earlier playback/Practice-result UI changes as their own scope with Lucas review. They are not part of the speed commit.
2. MFA dictionary cache and its tests remain a separate previously uncommitted scope.
3. Reusable MFA interpreter/worker, dispatch tests and the idle-policy extension form the speed scope. Sarrvesh owns speech analysis; no Lucas/Parthiban storage/generation API change is required.
4. Optional diagnostic capture and privacy/failure tests can be reviewed separately. It is disabled by default and in the current local configuration.
5. Reports/runbook and source-manifest references are documentation. Ignored local config, voice data, model weights, private database and diagnostic outputs must not be committed.

This continuation modified `phoneme_scoring/persistent_mfa.py`, the dispatch/optional diagnostic portions of `phoneme_scoring/align_audio.py`, `tests/test_persistent_mfa.py`, and `tests/test_mfa_timings.py`. It set ignored local `mfa_execution.idle_sec` to 600 and temporarily enabled then disabled diagnostics. No other application files were changed in this continuation. The pre-existing broad working tree remains uncommitted.

## Next action and demo claim

Keep the verified reuse/lifetime improvement, but do not describe the speed objective as finished. The next targeted investigation is a paired profile of the actual website's initialized MFA CLI request versus the isolated worker. Resolve that execution-path/environment gap before another optimization. A five-second isolated result is not evidence that the public-facing workflow has the same latency.

Demonstrate the real current result and say: “Processing is faster in our engineering benchmark, but the live app still takes around twelve seconds once prepared. First use can take substantially longer. Feedback is experimental.” Do not show an old result as if it came from a new recording.

Artifacts: `runs/speed-final-evidence-20261027.json`, individual source directories named in that file, `runs/speed-live-20261027.json`, `runs/mfa-live-diagnostics.jsonl`, and `runs/speed-final-source-manifest-20261027.json`. No raw voice or login token is included in these report artifacts.


## Final verification observed

Full regression command: `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py' -v`. **195 tests run: 194 passed, one skipped, zero failures**, 47.753 seconds. The skip is the existing Windows symlink-creation limitation. The production-renderer wrapper includes its 25 Node scenarios as one Python test, not 25 extra Python tests.

The final normal website reassessment with diagnostics off completed correctly, preserved the first recording's TH inconclusive and IH supported outcomes, and retained its original audio and confirmed text. Its actual duration remains in the live table; it is not a fresh-clip or ten-second success claim. `git diff --check` passed. Nothing was staged or committed.
