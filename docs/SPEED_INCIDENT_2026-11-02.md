# Speed incident: November 2, 2026

## Status

The current website missed the ten-second target. No performance fix or recovered latency is claimed by this investigation. Existing speed settings and safeguards have been preserved. These observations were collected before running publication regression tests, so those tests did not compete with the two reported assessments.

The user supplied the screenshot and manually executed the follow-up through the website. The investigator read saved results through a read-only SQLite connection, inspected current configuration/process metadata, and sampled Windows memory/power counters. No database record, model, setting, application process or timeout was changed to diagnose the incident. Browser automation was unavailable; the follow-up was not an automated browser benchmark.

## Observed results

All durations below are measured server-side seconds. They exclude human transcript review and are not browser stopwatch measurements.

| Run | Transcription | Audio preparation | Alignment | Phoneme analysis | Total |
| --- | ---: | ---: | ---: | ---: | --- |
| Free speech, first assessment after app startup | 93.00 | 6.61 | 28.27 | 5.52 | Analysis 41.05; transcription plus analysis 134.05 |
| Subsequent preset, I think so | 9.39 | 0.03 | 15.27 | 7.07 | Complete preset pipeline before saving 32.54 |

The two rows perform different work. The preset also computes DSP (0.68 seconds); its total includes transcription. The free-speech analysis reuses the separately completed transcription. Do not compare their total columns as equivalent analysis-only work, or describe the second row as a fresh free-speech retry.

For the first row, saved queue waits were 0.050 seconds for transcription and 0.027 seconds for analysis. Application/model startup and inference are not separately timed within the 93.00-second transcription job. The server started at about 08:16 Central, the assessment worker at 08:16:54, and its MFA interpreter at 08:18:41. The saved assessment completed at about 08:19:14.

For the second row, alignment metadata explicitly reports:

- Persistent MFA mode, the same owned interpreter, `reused: true`, and zero interpreter startup time for this request.
- A compiled dictionary cache hit.
- Two graph-resource cache hits, zero misses, zero fallbacks.
- MFA lock wait 0.006 seconds and subprocess execution 10.618 seconds within 15.270 seconds total alignment. The remaining alignment time is not split into invented internal stages.

Both assessments completed and returned experimental findings. Completion is not evidence of pronunciation accuracy or of meeting the latency target. The user's approximate follow-up observation was around 20 seconds; the saved complete preset pipeline measurement is 32.54 seconds and has a different measurement boundary.

## Environment observations

The ignored local configuration still enables `reuse_process`, 600-second idle retention and `reuse_lexicon_graphs`. The dictionary resource directories exist. The application health endpoint returned ready and the served account script matched the current source hash. No cache or scorer was disabled by the profile UI integration.

Initial Windows snapshots reported only about 0.37 to 0.45 GiB of available physical RAM on the 16-GB laptop, with active page-ins (one sample: 7,616 pages/second and 1,162 page reads/second). The laptop was initially discharging. The user subsequently connected power and closed unneeded apps. Later snapshots still showed only roughly 0.4 to 0.5 GiB available. These are point samples, not measurements integrated across either assessment. They do not prove how many seconds were caused by paging or power management.

## Explanation supported by the evidence

1. The initial run had fresh assessment/MFA processes. The earlier sub-ten-second result applied to prepared analysis, not initial transcription plus analysis. Startup is a verified difference; its individual model-loading costs are not isolated in the saved timers.
2. The later preset remained slow even with demonstrated cache hits and interpreter reuse. Therefore startup alone does not explain the current performance, and merely enabling the existing cache is not a new fix.
3. Severe memory pressure and paging are observed. Their contribution to widespread transcription, alignment and inference slowdown is a strong hypothesis requiring a comparable resource-controlled test. A UI regression, disk interference, CPU scheduling or power effects have not been individually proved or ruled out.

Earlier evidence remains in `SPEED_COMPLETION_REPORT_2026-10-27.md`: prepared analysis median 8.19 seconds, five of six optimized paired runs below ten seconds, with a slower outlier. A later fresh microphone case took 7.86 seconds for analysis plus a separate 4.01-second transcription job. Those historical results never established a strict ten-second maximum or a ten-second whole workflow.

## Next verification

Preserve the current app/settings. Use one known clip and one measurement boundary, record worker state and resource conditions, and repeat sequentially after adequate memory headroom is available. Compare complete saved stage timings, not estimated time. If warm alignment is still slow, use a separately approved diagnostic to isolate its resource/setup versus execution cost; present existing instrumentation gaps explicitly. Do not change scoring, validation, identity, revisions, locking or deadlines to improve the apparent result.

The demo and teammate handoff must call current speed unresolved until comparable runs establish recovery. A saved historical result may explain the output but must be labeled historical and must not be presented as a newly completed fast assessment.
