# Day 2 Phase 5: isolated MFA timing

Implemented October 13, 2026 on `feature/speed-free-speech`. Previous Phase 2–4 local changes are preserved.

## Instrumentation and boundaries

`phoneme_scoring.align_audio.align_audio` now returns a `timings_sec` object using `time.monotonic()`:

- `input_preparation`: entry through settings/audio preparation, creating the fresh work directory, WAV/LAB creation and command construction, stopping immediately before lock acquisition.
- `lock_wait`: immediately before entering the existing file-lock context through successful acquisition. This includes lock-file setup and its existing polling interval. On acquisition failure it reports elapsed acquisition time; subprocess time is omitted.
- `subprocess_execution`: immediately before `run_mfa` through its return/exception, after lock acquisition and log opening. Includes process creation, Conda launcher, MFA initialization/execution and owned-process cleanup on timeout. It excludes lock waiting.
- `output_processing`: successful output checks, TextGrid parsing, boundary normalization and word association. Omitted when processing fails before completion.
- `total`: entry through final success/error handling, including lock release and cleanup. Missing stage measurements are omitted rather than reported as zero. The sum of sub-stages can differ slightly from total because context/log transitions and failure handling are outside those individual boundaries.

Locks, polling, process arguments, timeout settings, process-tree cleanup, error handling, temporary-file retention and existing model caches are preserved. The addition changes result metadata only; it adds no transcript/audio/credential logging. Existing internal alignment result fields and audit files remain unchanged.

The shared MFA file lock still serializes app instances because MFA extracts shared model files. The separate in-process pipeline lock may delay a caller before `align_audio` starts; that wait is outside this timer and remains a separate pipeline/worker measurement. Shared ownership remains Sarrvesh's alignment module; no app, storage or generation interface changes were made.

## Benchmark conditions

`tools/benchmark_mfa.py` calls the alignment component directly for the three existing synthetic clips in three serial rounds, then repeats think with a controlled two-second holder of the same OS file lock. Synthetic examples are microbenchmark inputs only; this does not feed generated audio into the confirmed learner-assessment API.

The installed model files are already present; no model downloads or cache clearing are performed. All calls run in one Python process, but each launches a new MFA subprocess through the same configured Conda command and creates fresh work/output directories. Existing alignment outputs are never reused. The first call in this study is not a cold-install measurement. Python/import startup before calling align_audio is excluded.

The study's first think call overlapped the tail of the regression-test process. It is reported but excluded from clean repeated-case statistics and any claim about first-run initialization. Background OS activity is uncontrolled. The deliberately contended call is reported separately and excluded from ordinary variability statistics.

## Verification and limitations

- Four deterministic timing tests passed. They verify exact stage boundaries, acquisition failure without fabricated subprocess time, subprocess timeout including cleanup, lock release, preserved command/options and missing-executable handling. These use fake elapsed time and a fake MFA process.
- Full regression suite: 120 tests executed; 119 passed and one existing Windows symlink test skipped. Includes actual subprocess timeout cleanup and cross-process locking tests, plus preset/confirmed-analysis regressions.
- Real benchmark calls use the installed MFA executable, installed dictionary/acoustic model, existing audio preparation and actual file lock.
- Existing MFA console log files inspected for completed cases were empty. Their output artifacts exist, but they supply no reliable model-loading/feature-extraction/decoding durations. Those internal stages remain unmeasured.
- No speech transcription, phoneme model inference, browser rendering, full app startup, production queue or server migration is measured here. This is an alignment-component benchmark, not a new whole-app latency benchmark.

## Recommended next experiment

Investigate process-startup overhead by testing a direct launch of the installed MFA environment against the current Conda launcher. Subprocess execution dominates the ordinary calls, while serial lock wait is negligible. This supports investigating time inside that subprocess; it does not prove Conda is the dominant internal cost.

In a separate approved optimization phase, prepare the environment correctly and alternate the two launch methods over the same clips, transcript, dictionary, acoustic model, timeout and fresh-directory rules. Keep the same lock. Compare successful output words/phones/boundaries, failure/timeout cleanup and execution-time distributions. Record startup versus internal MFA work if additional reliable timers can be introduced. Adopt a launch change only if repeated measurements show a useful improvement without alignment or cleanup regressions. No speed improvement is claimed from this instrumentation itself.

## Reproduce

From the repository directory in PowerShell:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_mfa_timings.py -v
.\.venv\Scripts\python.exe -B tools/benchmark_mfa.py
```

Run the benchmark while other project analysis jobs and tests are idle. The controlled holder temporarily uses the existing shared MFA lock; it does not change its behavior. Do not run several copies of the benchmark simultaneously if ordinary serial variability is the intended measurement.

Files: alignment timing metadata, `tests/test_mfa_timings.py`, `tools/benchmark_mfa.py`, and this report. Changes have not been committed or pushed.

## Measured findings

Ten real alignments succeeded: nine ordinary serial calls (three clips, three rounds) and one controlled contention call. Zero failures and zero retries. Windows 11, Python 3.13.1, MFA 3.3.7; configured Conda environment `accent-coach-mfa`, installed `english_us_arpa` dictionary/acoustic model.

| Clip / run | Lock wait (s) | Subprocess (s) | Total (s) |
| --- | ---: | ---: | ---: |
| think / 1 (test overlap) | 0.000383 | 33.905 | 33.932 |
| ship / 1 | 0.000291 | 26.731 | 26.749 |
| bad_bed / 1 | 0.000433 | 28.858 | 28.878 |
| think / 2 | 0.000245 | 25.955 | 25.962 |
| ship / 2 | 0.000261 | 24.035 | 24.040 |
| bad_bed / 2 | 0.000651 | 52.746 | 52.753 |
| think / 3 | 0.000272 | 38.167 | 38.187 |
| ship / 3 | 0.000270 | 23.474 | 23.496 |
| bad_bed / 3 | 0.000274 | 25.179 | 25.200 |
| think / 4 (controlled contention) | 2.009057 | 21.701 | 23.720 |

Clean serial statistics exclude the first overlapping think call and the contention case. Small sample sizes do not support confidence intervals or a general cold-start claim.

| Clip | Clean n | Subprocess median (s) | Subprocess min–max (s) | Total median (s) |
| --- | ---: | ---: | ---: | ---: |
| think | 2 | 32.061 | 25.955–38.167 | 32.074 |
| ship | 3 | 24.035 | 23.474–26.731 | 24.040 |
| bad_bed | 3 | 28.858 | 25.179–52.746 | 28.878 |

Clean serial lock waits ranged from 0.245 to 0.651 ms. Input preparation ranged from 2.981 to 5.853 ms; successful output processing from 1.407 to 17.186 ms. Subprocess execution accounts for 99.95% of total clean serial alignment time.

The controlled holder produced 2.009 seconds of measured lock wait and 21.701 seconds of subprocess execution, for 23.720 seconds total. This confirms the real lock wait is measured separately. It is a scheduling experiment, not a claim about production queue contention.

The repeated think timings do not monotonically decrease, and bad_bed includes a 52.746-second subprocess outlier. First-run, warm-cache and background-load effects cannot be disentangled from these samples. No per-stage acoustic-model initialization or decoding duration was inferred.

Raw measurements: `runs/day2-phase5-20261013T212424Z/measurements.json`; console timing log: `runs/day2-phase5-benchmark.log`; regression log: `runs/day2-phase5-regression.log`. Raw artifacts remain local under the ignored runs directory.
