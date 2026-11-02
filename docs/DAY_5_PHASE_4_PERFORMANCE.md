# Day 5, Phase 4: Available-recording performance measurements

October 21, 2026. Branch `feature/speed-free-speech`; HEAD `e7f57d9ce37f95cb6c3cc30a870c8aae284656d7`.

## Conclusion

The compiled-dictionary optimization is active and working for the tested inputs. All six new diagnostic assessments performed real alignment and phoneme inference, retained correct recording/text/job/revision identities, and completed. All five reused-worker assessments were below 20 seconds (14.359-19.434 s). However, only one fresh human recording exists, its two warm measurements repeat the same audio, and the other inputs are synthetic engineering fixtures. These measurements **do not establish reliable under-20-second assessment of independently new human recordings**.

First use remains slow: transcription plus analysis of the human clip took **69.211 s** in a fresh diagnostic worker. The original application's saved Case 1 observation was **41.369 s** of transcription plus analysis processing with unknown worker/cache state. Both slow observations are retained.

No contemporaneous disabled-cache comparison was performed because this phase prohibits changing caching/settings. Day 4's controlled 59.2% warm-preset median reduction remains historical evidence, not a newly reproduced improvement percentage. Current fixture runs are slower than the previous optimized confirmed-text runs, under different power and memory conditions.

## Procedure and unchanged behavior

Command, from the repository:

```powershell
.\.venv\Scripts\python.exe -B runs/day5_measure_available.py
```

The local driver supplies inputs to the existing `AnalysisService` and reuses the existing Day 4 `observed_worker` unchanged with `cache_directory=None`. In that observer, None leaves the loaded settings unchanged; it does **not** disable the persistent cache. No application instrumentation, model parameters, thresholds, timeout, locking, dictionary, concurrency setting, or persistent configuration was changed. Existing MFA timers, existing confirmed-analysis stage timers and the established outer service-call elapsed-time method were used.

One diagnostic worker processes six transcription/confirmed-analysis pairs serially: human, ship, human, bad_bed, human, think. Every transcription executes again. Every analysis executes fresh MFA alignment and phoneme inference. Only model objects and compiled dictionary resources are reused; no recording-level assessment-result cache is used. Human repetitions are planned repeat measurements, not new human clips or automatic retries.

The human input is the authorized Phase 3 Case 1 original learner asset, read from that exact private session. Its bytes were copied into an owned private temporary directory and removed after the benchmark. The original production attempt was not requeued or changed. Diagnostic jobs reuse its attempt/learner/revision identifiers with explicitly diagnostic job IDs; they do not publish to production storage. Fixtures use diagnostic identities. This checks engine behavior and input association, not browser acceptance, production authorization, or persistent publication.

Raw metadata/results: `runs/day5-phase4-20261021T201524Z/measurements.json`. Console log: `runs/day5-phase4-console.log`. Measurements span 20:15:24-20:17:53 UTC (15:15-15:17 America/Chicago). These ignored diagnostic artifacts do not contain a retained copy of the human waveform.

## Inputs

| Label | Source | Confirmed text | Duration | Original format | Bytes |
| --- | --- | --- | ---: | --- | ---: |
| H1 | Fresh human Case 1, previously saved/analyzed by the user | I think so. | 1.920 s | 48 kHz mono PCM16 | 184,364 |
| S | Existing synthetic engineering fixture | The ship is here | 1.905 s | 16 kHz mono PCM16 | 61,006 |
| B | Existing synthetic engineering fixture | That is a bad bed | 2.010 s | 16 kHz mono PCM16 | 64,366 |
| T | Existing synthetic engineering fixture | I think so | 1.730 s | 16 kHz mono PCM16 | 55,406 |

The human original is resampled through the existing time-preserving 16 kHz preparation path. All clips are within five seconds and 10 MiB; confirmed text is within 12 words and 200 characters. No reference comparison or generated-listening-example request was made. Synthetic fixtures are supplemental engineering inputs, not fresh human acceptance evidence.

## Individual measurements

All columns are seconds except lock waiting in milliseconds. Total is **transcription service wall time plus confirmed-analysis service wall time**. MFA/phoneme columns are nested inside analysis, not extra time to add to Total. Upload, browser polling, user review/confirmation, production job queues and storage publication are excluded.

| Run | Input / worker state | Transcription | Analysis | MFA lock ms | MFA subprocess | MFA operation | Phoneme stage | Total | Resource cache | Failure / retry |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | H1, fresh diagnostic worker; first phoneme-model use | 46.551 | 22.660 | 0.401 | 17.725 | 18.409 | 2.042 | **69.211** | Hit | None / no |
| 2 | S, reused worker; first different fixture in series | 1.343 | 18.091 | 0.409 | 16.258 | 17.111 | 0.643 | **19.434** | Hit | None / no |
| 3 | H1, reused worker; same human clip repeated | 1.018 | 14.430 | 0.494 | 12.783 | 13.460 | 0.672 | **15.448** | Hit | None / no |
| 4 | B, reused worker; first different fixture in series | 1.069 | 13.291 | 0.464 | 11.705 | 12.379 | 0.642 | **14.359** | Hit | None / no |
| 5 | H1, reused worker; same human clip repeated again | 1.040 | 13.781 | 0.354 | 11.971 | 12.812 | 0.709 | **14.821** | Hit | None / no |
| 6 | T, reused worker; first different fixture in series | 1.049 | 13.908 | 0.345 | 12.348 | 12.992 | 0.634 | **14.957** | Hit | None / no |

- Six complete assessments; zero operational failures, timeouts, automatic retries or skipped analyses in this series. Every result, including the 69.211-second run, is retained.
- Reused-worker series: n=5, median **14.957 s**, range **14.359-19.434 s**. This descriptive mixed-input statistic is not a controlled per-clip distribution or human population estimate.
- Same-human warm repetitions: n=2, median **15.134 s**, individual values 15.448/14.821 s. They do not establish new-human-recording performance.
- All six resource hits are compiled dictionary hits, not cached assessment outputs. The first run's Whisper/model cache records a miss; subsequent model counters show reuse while inference still executes. The phoneme model similarly has a first miss and subsequent hits.
- The existing observer's initial child import marker measured **1.301 s**, included in the first transcription call. Full model loading versus inference is not separately timed; no standalone model-startup duration is claimed. No preparation work was moved outside requests.

### Original Phase 3 application observation, retained separately

| Input | Worker / resource-cache state | Transcription processing | Analysis processing | Alignment stage | Phoneme stage | Sum of processing |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| H1, original saved user attempt | Unknown / unknown | 2.316 | 39.054 | 27.019 | 5.001 | **41.369 s** |

Original queue measurements: transcription 0.0199 s; analysis 0.0253 s. The saved session does not expose separate MFA lock/subprocess durations. These are production job-processing measurements, not the diagnostic service-wall timing boundary above. Do not relabel the original result as cold or warm or infer that a change between these observations was caused by an optimization performed today.

## Environment and comparability

- Windows 11 build 26200, Python 3.13.1, Intel i7-1360P, approximately 15.70 GiB usable RAM. Existing CPU inference settings use two threads.
- Pinned Whisper `openai/whisper-base.en` revision `911407f4214e0e1d82085af863093ec0b66f9cd6`; phoneme model `facebook/wav2vec2-xlsr-53-espeak-cv-ft` revision `2c733782da5604684829819a5eb744c193fe9398`.
- Existing direct MFA 3.3.7 and `english_us_arpa` dictionary/acoustic model; MFA timeout 120 s, service default deadline unchanged at 180 s. Dictionary cache was already enabled/populated before this phase.
- **Battery operation:** PowerOnline false, discharging, battery 73% at preflight and 70% after the series. Balanced plan was left unchanged. Day 4's comparison used AC power and 100% battery.
- Preflight CPU sample: 0%; free physical RAM approximately **1.79 GiB**. Preview server plus its idle model worker stayed running. Day 4's main comparison had no preview listener/worker running. Background OS activity, thermal limits, paging and antivirus were not controlled or individually timed.
- Zero stored active application attempts before the series, before each assessment pair, and after it; only one diagnostic analysis ran at a time. Observed MFA lock waits of 0.345-0.494 ms show no material lock contention in these calls, but do not prove absence of all background work.
- No Kernel-Power sleep/standby events 42/107/506/507 were found within the measured interval. The laptop's power policy was not changed.
- Current assessment/worker/ASR/MFA/scoring source hashes and base settings match the saved Day 4 benchmark source hashes. Persistent local settings differ from the original Day 4 file because dictionary caching was activated on October 18, as already documented. All source/settings hashes were unchanged across today's runs.

## Day 4 comparison

Historical controlled comparison: warm **preset** backend median 32.128 s without the optimization versus 13.119 s with it (59.2% lower), six warm requests per configuration. Today's **confirmed-text** measurements assess different target sets from preset processing, so their medians must not be pooled or treated as an identical repeat of that study.

The following uses the same fixture bytes and confirmed-text path. Environmental differences and small sample sizes still prevent causal attribution:

| Fixture / condition | Day 4 baseline ASR + analysis | Day 4 optimized ASR + analysis | Day 5 current ASR + analysis |
| --- | ---: | ---: | ---: |
| ship, reused worker | 26.075 s | 10.638 s | 19.434 s |
| bad_bed, reused worker | 27.593 s | 9.764 s | 14.359 s |
| think, differing model-startup conditions | 31.934 s, fresh transcription worker | 23.087 s, fresh transcription worker | 14.957 s, reused worker |

Ship and bad_bed remain numerically faster than the historical unoptimized observations, but slower than the historical optimized observations. This is compatible with a functioning optimization under a slower environment; it does not isolate the size of the current benefit. Think's total has a different worker-start condition and is shown for completeness, not as a speed-up comparison. There is no Day 4 measurement of this human waveform.

## Correctness and complete-work checks

- All six analyses returned `ok=true`, `analysis_status=completed`, and alignment `available`.
- Source waveform hash, learner asset ID, confirmed text, attempt ID, diagnostic job ID and input revision matched their supplied snapshots in every case. The human input retained the original Case 1 learner asset and revision 3.
- All three human runs recognized `I think so.` and returned TH **inconclusive** and IH **supported**, matching the original saved sound outcomes. This is experimental evidence, not an independent pronunciation accuracy label.
- Ship returned two supported IH findings; bad_bed three supported findings (AE/IH/AE); think fixture TH/IH supported. None was made decisive by changing thresholds or weakening safeguards.
- For each of the three fixtures, Day 5 versus Day 4 optimized confirmed analysis matched exactly for phone segments, word segments, prepared-audio hash, duration, sample rate, normalized transcript and boundary-rounding corrections. Full sound-result records also matched.
- The production Case 1 state hash was unchanged after benchmarking; the human temporary file was removed. This diagnostic harness did not test new browser actions or persistent owner/revision publication transactions.

## Bottleneck and timing gaps

For reused workers, MFA subprocess execution accounts for **82.34%** of aggregate transcription-plus-analysis wall time. Its range is 11.705-16.258 s; lock waiting is sub-millisecond. MFA remains the largest measured steady-state stage. Removing the lock is not supported by these measurements.

For first use, the **46.551-second transcription call** is larger than the subsequent analysis call. Its imports, model load and inference are not separately timed. Battery limits, memory pressure and model initialization are plausible contributors, not individually proven causes. No hardware or configuration change is recommended as already validated by this phase.

Unmeasured separately: model load versus inference, MFA interpreter/import/model/feature/decoding costs, dictionary hash/copy overhead, production/browser end-to-end waits and thermal/paging effects. The small sample cannot establish a reliable 95th-percentile latency or real-user failure rate.

## Under-20-second assessment

**Observed:** 5/5 reused-worker diagnostic assessments completed below 20 seconds, including two repeats of the one human clip and three engineering fixtures with different audio. The slowest was 19.434 s, leaving little margin for browser/queue overhead.

**Not established:** consistent under-20-second processing of independently new human recordings, first-use performance below 20 seconds, browser end-to-end latency below 20 seconds, or reproduction of Day 4's exact improvement percentage under current conditions. The other five human cases remain deferred. No cache-hit repeat is counted as an independent new human recording.

The optimization remains technically representative for the checked alignment/resource behavior. Its numerical benefit and broader real-user target need a later controlled comparison and additional fresh recordings. Stop here: no further optimization, power change, server restart, tests that alter behavior, commit or push was performed.
